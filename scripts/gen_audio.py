# -*- coding: utf-8 -*-
"""为英文财经早报预生成 MP3 广播音频。
主引擎: Kokoro 本地神经语音（免费、稳定，新闻主播式双声配置）
  - 开场导语 intro → am_michael (美式男声, 沉稳)
  - 正文条目     → 男女交替播报: 偶数条 am_michael 男声 / 奇数条 af_heart 女声
备选音色: bm_george (英式男声) / af_bella, af_sky (女声) 可在 VOICE_* 里替换
兜底引擎: Edge 神经语音 (男 Andrew / 女 Jenny), Kokoro 不可用时自动切换
每期还会把 intro + 全部条目合并成 broadcast.mp3 (单文件连播):
  手机浏览器在后台会冻结网页脚本, "一条播完再触发下一条"会失效,
  单个连续音频文件则可以在后台一直播完 —— 这是解决后台连播的关键。
用法: python gen_audio.py [--force]
为 data/news.json 中每期生成 data/audio/<date>/intro.mp3、item-XX.mp3 与 broadcast.mp3，
并把每条在 broadcast.mp3 里的起始时间写进 news.json 的 ed["broadcast"]["segments"]，
已存在的文件自动跳过（--force 重新生成）。
"""
import asyncio, json, os, re, sys, shutil, time, tempfile

sys.stdout.reconfigure(encoding="utf-8")

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
MODELS = os.path.join(ROOT, "models")
MIN_VALID_SIZE = 2000                # 小于该字节数视为损坏文件, 重新生成
# 语速固定 1.0 —— 与用户认可的试听样本一致; 播放端可用 playbackRate 微调

# 播报配置: 双主播 —— 男声 Michael 播导语和偶数条, 女声 Heart 播奇数条, 交替像双人新闻节目
VOICE_INTRO_KOKORO = "am_michael"
VOICE_MALE_KOKORO = "am_michael"        # 男声 (备选: bm_george)
VOICE_FEMALE_KOKORO = "af_heart"        # 女声 (备选: af_bella / af_sky)
VOICE_JOKE_KOKORO = "bm_george"         # 版面三每日一笑: 固定英式男声, 与新闻/人物志的声音区分
# 版面二广播剧多声线阵容(已探测 voices.bin 全部可用音色):
#   N=旁白(英式 fable, 讲小说感)  M=男角色1(adam)  M2=男角色2(michael)
#   F=女角色1(bella)  F2=女角色2(nicole)  F3=女角色3(heart)
STORY_VOICES_KOKORO = {"N": "bm_fable", "M": "am_adam", "M2": "am_michael",
                       "F": "af_bella", "F2": "af_nicole", "F3": "af_heart"}
STORY_VOICES_EDGE = {"N": "en-GB-RyanNeural", "M": "en-US-AndrewNeural", "M2": "en-US-GuyNeural",
                     "F": "en-US-JennyNeural", "F2": "en-US-AriaNeural", "F3": "en-GB-SoniaNeural"}
STORY_GAP = 0.55                        # 广播剧句与句之间的留白秒数(听小说的呼吸感)
STORY_PLAN = "storycast-v1(N-fable,M-adam,M2-michael,F-bella,F2-nicole,F3-heart)"
VOICE_MALE_EDGE = "en-US-AndrewNeural"
VOICE_FEMALE_EDGE = "en-US-JennyNeural"
VOICE_JOKE_EDGE = "en-GB-RyanNeural"
BROADCAST_GAP = 0.9                     # broadcast.mp3 里条目之间的间隔秒数
# 声音方案版本号: 写入每期 news.json 的 voice_plan 字段。
# 改动音色/交替规则时把它 +1, 旧音频会在下一次运行时自动按新方案重新生成(无需 --force)。
VOICE_PLAN = "intro-michael+items-michael-heart-alt-v2"

_kokoro = None
_edge_ok = True
try:
    import edge_tts
except Exception:
    _edge_ok = False


def get_kokoro():
    """惰性加载 Kokoro 引擎, 失败返回 None (走 Edge 兜底)"""
    global _kokoro
    if _kokoro is not None:
        return _kokoro
    try:
        from kokoro_onnx import Kokoro
        import soundfile as sf  # noqa: F401  提前暴露缺失依赖
        onnx_path = os.path.join(MODELS, "kokoro-v1.0.onnx")
        voices_path = os.path.join(MODELS, "voices.bin")
        if not (os.path.exists(onnx_path) and os.path.exists(voices_path)):
            print("  [Kokoro] 模型缺失, 走 Edge 兜底")
            return None
        print("  [Kokoro] 加载模型...")
        _kokoro = Kokoro(onnx_path, voices_path)
        return _kokoro
    except Exception as e:
        print(f"  [Kokoro] 初始化失败({type(e).__name__}: {e}), 走 Edge 兜底")
        return None


def load_editions():
    p = os.path.join(ROOT, "data", "news.json")
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save_editions(data):
    p = os.path.join(ROOT, "data", "news.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)


def tts_sanitize(t):
    """朗读前文本清洗: 让引擎断句自然。
    - & → and (S&P → S and P)
    - 破折号/省略号/间隔号/全角冒号 → 逗号(引擎对这些符号停顿生硬)
    - 各类弯引号/书名号去掉, 括号 → 逗号
    - 半角冒号在时间(9:30)里保留, 其余 → 逗号
    """
    t = t.replace(" & ", " and ").replace("&", " and ")
    t = re.sub(r"\s*[—–]+\s*", ", ", t)                    # 破折号 → 逗号
    t = t.replace("……", ", ").replace("…", ", ")
    t = re.sub(r"\s*[·・]\s*", ", ", t)                     # 间隔号 → 逗号
    t = t.replace("：", ", ")
    t = re.sub(r"(?<!\d):(?!\d)", ", ", t)                  # 冒号(非时间) → 逗号
    t = re.sub(r"[“”«»「」『』\"]", "", t)                   # 引号类去掉(保留撇号, 不动 it's/company's)
    t = re.sub(r"\s*[（(]\s*", ", ", t)                     # 左括号 → 逗号
    t = re.sub(r"\s*[）)]\s*", ", ", t)                     # 右括号 → 逗号
    t = re.sub(r"[;；]", ", ", t)                           # 分号 → 逗号
    t = re.sub(r"\.{2,}", ".", t)                           # 连续句点合并
    t = re.sub(r"\s*,[\s,]*", ", ", t)                      # 连续/空格间隔逗号合并
    t = re.sub(r",\s*\.", ".", t)                           # 逗号后接句点 → 句点
    t = re.sub(r"\s+,\s*", ", ", t)
    t = re.sub(r"\s{2,}", " ", t)
    return t.strip()


CONJ_WORDS = {"and", "but", "while", "then", "so", "yet", "because", "although",
              "whereas", "however", "meanwhile", "plus", "as"}
MIN_WORDS_TO_SPLIT = 12      # 分句词数超过该值才在连词处断开, 避免碎成短句
MIN_LEAD_WORDS = 6           # 连词前至少这么多词, 否则不值得断


def split_by_conj(clause):
    """长分句在并列连词(and/then/but...)处再断开 —— 用户反馈这些词直接连读过去没有换气"""
    words = clause.split()
    if len(words) <= MIN_WORDS_TO_SPLIT:
        return [clause]
    out, cur = [], []
    for w in words:
        lw = re.sub(r"[^\w]", "", w).lower()
        if lw in CONJ_WORDS and len(cur) >= MIN_LEAD_WORDS:
            out.append(" ".join(cur))
            cur = [w]
        else:
            cur.append(w)
    if cur:
        out.append(" ".join(cur))
    return out


def split_units(text):
    """把一段播报文本切成 (小段文本, 段后停顿秒数) 序列。
    句子边界 > 逗号边界 > 连词边界, 段内不再切, 保证每小段都短到韵律不漂。
    注意: 数字千分位逗号(4,066.85)先占位保护, 不能当断句符。"""
    units = []
    NUM_COMMA = "\x01"
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    for s in sents:
        body = s.rstrip(".!?")
        end_p = s[len(body):] or "."
        body = re.sub(r"(?<=\d),(?=\d)", NUM_COMMA, body)      # 保护千分位
        pieces = []
        for cl in [c.strip() for c in re.split(r",\s*", body) if c.strip()]:
            pieces.extend(split_by_conj(cl))
        if not pieces:
            continue
        for i, p in enumerate(pieces):
            p = p.replace(NUM_COMMA, ",")                     # 还原千分位
            last = i == len(pieces) - 1
            # 非结尾小段补逗号: 语调保持"未结束", 拼接处不会像硬切
            units.append((p + (end_p if last else ","), 0.45 if last else 0.22))
    return units


def synth_kokoro_samples(text, voice, speed=1.0):
    """Kokoro 合成一段文本, 返回 float32 采样数组(24kHz)。
    长文本整段合成韵律会漂移, 切成短小段逐段合成后拼接:
    逗号/连词处 0.22s, 句末 0.45s —— 换气感自然, 音质等同短句试听样本。"""
    import numpy as np
    k = get_kokoro()
    if k is None:
        raise RuntimeError("Kokoro 不可用")
    units = split_units(text)
    if not units:
        raise RuntimeError("空文本")
    sr = 24000
    parts = [np.zeros(int(sr * 0.15), dtype=np.float32)]     # 开头留白
    for i, (txt, pause) in enumerate(units):
        samples, _sr = k.create(txt, voice=voice, speed=speed, lang="en-us")
        samples = np.asarray(samples, dtype=np.float32)
        if samples.ndim > 1:
            samples = samples[:, 0]
        parts.append(samples)
        if i < len(units) - 1:
            parts.append(np.zeros(int(sr * pause), dtype=np.float32))
    return np.concatenate(parts)


def synth_kokoro(text, path, voice, speed=1.0):
    """Kokoro 本地合成, 直接写 MP3 (libsndfile 1.2+ 原生支持)。"""
    import soundfile as sf
    sf.write(path, synth_kokoro_samples(text, voice, speed), 24000, format="MP3")
    return True


async def synth_edge(text, path, gender):
    voice = {"M": VOICE_MALE_EDGE, "F": VOICE_FEMALE_EDGE, "G": VOICE_JOKE_EDGE}[gender]
    c = edge_tts.Communicate(tts_sanitize(text), voice, rate="+6%")
    await c.save(path)


def _resample_24k(data, file_sr):
    import numpy as np
    sr = 24000
    if data.ndim > 1:
        data = data[:, 0]
    if file_sr != sr:
        n_out = int(round(len(data) * sr / file_sr))
        data = np.interp(np.linspace(0.0, len(data) - 1, n_out),
                         np.arange(len(data)), data).astype(np.float32)
    return np.asarray(data, dtype=np.float32)


async def synth_story(lines, path):
    """广播剧合成: 逐句按角色声线生成, 句间留 STORY_GAP 呼吸感, 合并成单文件 story.mp3。
    返回 (引擎名, segments)。segments = 每句在文件中的 {start, dur, k, who, g},
    供前端"读到哪句高亮哪句"。旁白语速略慢(0.97)更沉稳, 角色台词原速更有戏感。"""
    import numpy as np, soundfile as sf, tempfile
    sr = 24000
    segs, parts, cursor = [], [], 0.25
    k = get_kokoro()
    if k is not None:
        parts.append(np.zeros(int(sr * cursor), dtype=np.float32))
        for ln in lines:
            voice = STORY_VOICES_KOKORO.get(ln.get("g"), VOICE_MALE_KOKORO)
            speed = 0.97 if ln.get("k") == "narr" else 1.0
            try:
                smp = synth_kokoro_samples(tts_sanitize(ln.get("en", "")), voice, speed)
            except Exception:
                k = None
                break
            dur = len(smp) / sr
            segs.append({"start": round(cursor, 3), "dur": round(dur, 3),
                         "k": ln.get("k", "narr"), "who": ln.get("who", ""), "g": ln.get("g", "N")})
            parts.append(smp)
            parts.append(np.zeros(int(sr * STORY_GAP), dtype=np.float32))
            cursor += dur + STORY_GAP
        if k is not None:
            sf.write(path, np.concatenate(parts), sr, format="MP3")
            return "kokoro", segs
        # Kokoro 中途失败 → 清空走 Edge 兜底
        segs, parts, cursor = [], [], 0.25
        get_kokoro_force_reload()
    if not _edge_ok:
        raise RuntimeError("无可用语音引擎")
    parts.append(np.zeros(int(sr * cursor), dtype=np.float32))
    for ln in lines:
        g = ln.get("g", "N")
        gender = {"N": "G", "M": "M", "M2": "M", "F": "F", "F2": "F", "F3": "F"}.get(g, "M")
        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tmp.close()
        try:
            await synth_edge(tts_sanitize(ln.get("en", "")), tmp.name, gender)
            data, fsr = sf.read(tmp.name, dtype="float32")
        finally:
            try:
                os.unlink(tmp.name)
            except Exception:
                pass
        smp = _resample_24k(data, fsr)
        dur = len(smp) / sr
        segs.append({"start": round(cursor, 3), "dur": round(dur, 3),
                     "k": ln.get("k", "narr"), "who": ln.get("who", ""), "g": g})
        parts.append(smp)
        parts.append(np.zeros(int(sr * STORY_GAP), dtype=np.float32))
        cursor += dur + STORY_GAP
    sf.write(path, np.concatenate(parts), sr, format="MP3")
    return "edge", segs


async def synth(text, path, gender="M"):
    """gender: 'M' 男声 / 'F' 女声 / 'G' 英式男声(笑话讲述人)"""
    text = tts_sanitize(text)
    k = get_kokoro()
    if k is not None:
        voice = {"M": VOICE_MALE_KOKORO, "F": VOICE_FEMALE_KOKORO, "G": VOICE_JOKE_KOKORO}[gender]
        for attempt in range(2):
            try:
                synth_kokoro(text, path, voice)
                return "kokoro"
            except Exception as e:
                print(f"    Kokoro 尝试 {attempt+1}/2 失败: {type(e).__name__} {e}")
                get_kokoro_force_reload()
    if _edge_ok:
        await synth_edge(text, path, gender)
        return "edge"
    raise RuntimeError("无可用语音引擎")


def get_kokoro_force_reload():
    global _kokoro
    _kokoro = None


def build_jobs(ed):
    """返回 (文件名, 文本, 声音性别) 列表。
    导语男声; 正文条目男女交替: 偶数条男声、奇数条女声;
    版面二 story.mp3 固定女声讲述(af_heart), 是"财经人物"栏目的声音名片。
    注意: story.mp3 不参与 broadcast.mp3 连播(见 main 里的 bjobs 过滤)。"""
    jobs = []
    intro = "The Daily Brief. {}, {}. {} stories.".format(
        ed.get("weekday_en", ""), ed.get("date", ""), len(ed.get("items", [])))
    if ed.get("lead_en"):
        intro += " " + ed["lead_en"]
    jobs.append(("intro.mp3", intro, "M"))
    for i, it in enumerate(ed.get("items", [])):
        title = (it.get("title_en") or it.get("title_zh") or "").strip().rstrip(".") + "."
        body = (it.get("body_en") or "").strip()
        txt = (title + " " + body).strip()
        if len(txt) > 3:
            jobs.append((f"item-{i:02d}.mp3", txt, "M" if i % 2 == 0 else "F"))
    s = ed.get("story")
    if s:
        if s.get("lines"):
            # 广播剧脚本: 整个脚本(含声线分配)参与指纹, 声线阵容一变就自动重配
            txt = STORY_PLAN + "|" + json.dumps(s["lines"], ensure_ascii=False)
            jobs.append(("story.mp3", txt, "CAST"))
        elif s.get("body_en") or s.get("title_en"):
            st = (s.get("title_en") or s.get("title_zh") or "").strip().rstrip(".") + "."
            st += " " + (s.get("body_en") or "").strip()
            jobs.append(("story.mp3", st.strip(), "F"))
    j = ed.get("joke")
    if j and (j.get("body_en") or j.get("title_en")):
        jt = (j.get("title_en") or j.get("title_zh") or "").strip().rstrip(".") + "."
        jt += " " + (j.get("body_en") or "").strip()
        jobs.append(("joke.mp3", jt.strip(), "G"))
    return jobs


def valid_audio(path):
    return os.path.exists(path) and os.path.getsize(path) > MIN_VALID_SIZE


def job_hash(txt, gender):
    """音频内容指纹: 文案或音色方案一变就翻转 → 自动重生成, 杜绝"文字更新了音频还是旧的"。
    (fetch_news 每天会重抓同一天的新闻, 条目内容可能和上一次不同)"""
    import hashlib
    raw = f"{VOICE_PLAN}|{gender}|{txt.strip()}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:12]


def merge_broadcast(adir, jobs):
    """把 intro + 全部条目合并成单文件 broadcast.mp3, 条目间留 0.9s 停顿。
    同时返回各条目在合并文件中的起始时间(秒)与时长, 供前端同步高亮。
    手机浏览器后台会冻结脚本, 单连续文件才能整期后台连播。"""
    import numpy as np, soundfile as sf
    sr = 24000
    gap = np.zeros(int(sr * BROADCAST_GAP), dtype=np.float32)
    parts, segments, cursor = [], [], 0.0
    for fname, _txt, _g in jobs:
        p = os.path.join(adir, fname)
        data, file_sr = sf.read(p, dtype="float32")
        if data.ndim > 1:
            data = data[:, 0]
        if file_sr != sr:                       # 理论上都是 24k, 保险起见用 numpy 线性重采样
            n_out = int(round(len(data) * sr / file_sr))
            g = np.interp(
                np.linspace(0.0, len(data) - 1, n_out),
                np.arange(len(data)), data).astype(np.float32)
        else:
            g = data
        dur = len(g) / sr
        segments.append({"file": fname, "start": round(cursor, 3), "dur": round(dur, 3)})
        parts.append(g)
        parts.append(gap.copy())
        cursor += dur + BROADCAST_GAP
    out = os.path.join(adir, "broadcast.mp3")
    sf.write(out, np.concatenate(parts), sr, format="MP3")
    return segments


def clean_old_audio(editions):
    adir = os.path.join(ROOT, "data", "audio")
    if not os.path.isdir(adir):
        return
    keep = {ed["date"] for ed in editions}
    for name in os.listdir(adir):
        if name not in keep:
            shutil.rmtree(os.path.join(adir, name), ignore_errors=True)
            print(f"  清理过期音频: {name}")


async def main(force=False):
    data = load_editions()
    clean_old_audio(data["editions"])
    # 版面二/三: 给没有故事的期分配财经人物小故事, 没有笑话的期分配每日一笑(分配结果持久化, 之后不再变)
    try:
        import story as _story
        _story.assign(data)
    except Exception as e:
        print(f"  [story] 分配失败, 本期无故事: {type(e).__name__} {e}")
    try:
        import joke as _joke
        _joke.assign(data)
    except Exception as e:
        print(f"  [joke] 分配失败, 本期无笑话: {type(e).__name__} {e}")
    made = failed = 0
    t0 = time.time()
    for ed in data["editions"]:
        date = ed["date"]
        adir = os.path.join(ROOT, "data", "audio", date)
        os.makedirs(adir, exist_ok=True)
        jobs = build_jobs(ed)
        # 连播文件只包含新闻(intro + 条目), story.mp3 / joke.mp3 单独播放
        bjobs = [j for j in jobs if j[0] not in ("story.mp3", "joke.mp3")]
        regen = False
        # 声音方案与当前不一致(或 --force)时, 该期全部重新生成 —— 用于双主播方案上线后自动迁移旧音频
        need = force or ed.get("voice_plan") != VOICE_PLAN
        if need and not force:
            print(f"  {date}: 声音方案变更({ed.get('voice_plan', '旧版')} → {VOICE_PLAN}), 重新生成")
        old_hashes = ed.get("audio_hashes") or {}
        hashes = {}
        story_ok = False                       # 本期广播剧是否(重)生成成功
        for fname, txt, gender in jobs:
            fpath = os.path.join(adir, fname)
            # --- 广播剧通道(story.mp3 有脚本): 独立版本号 story_plan, 与新闻音频互不影响 ---
            if gender == "CAST":
                h = job_hash(txt, "CAST")
                hashes[fname] = h
                need_st = force or ed.get("story_plan") != STORY_PLAN
                if not need_st and old_hashes.get(fname) == h and valid_audio(fpath):
                    story_ok = True
                    continue
                ok = engine = False
                for attempt in range(3):
                    try:
                        engine, segs = await synth_story(json.loads(txt.split("|", 1)[1]), fpath)
                        ok = True
                        break
                    except Exception as e:
                        print(f"  重试 {date}/{fname} ({attempt+1}/3): {type(e).__name__} {e}")
                        await asyncio.sleep(2.5)
                if ok:
                    made += 1
                    regen = True
                    story_ok = True
                    ed["story_audio"] = {"file": "story.mp3", "segments": segs}
                    print(f"  {date}/{fname}  {os.path.getsize(fpath)//1024} KB  广播剧{len(segs)}句  [{engine}]")
                else:
                    failed += 1
                    print(f"  失败 {date}/{fname}")
                continue
            h = job_hash(txt, gender)
            hashes[fname] = h
            # 只有"文案+音色都没变且文件有效"才跳过; 文案改了(当天重抓新闻)必须重生成
            if not need and old_hashes.get(fname) == h and valid_audio(fpath):
                continue
            ok = engine = False
            for attempt in range(3):
                try:
                    engine = await synth(txt, fpath, gender)
                    ok = True
                    break
                except Exception as e:
                    print(f"  重试 {date}/{fname} ({attempt+1}/3): {type(e).__name__} {e}")
                    await asyncio.sleep(2.5)
            if ok:
                made += 1
                regen = True
                print(f"  {date}/{fname}  {os.path.getsize(fpath)//1024} KB  [{engine}]")
            else:
                failed += 1
                print(f"  失败 {date}/{fname}")
        ed["audio_ready"] = failed == 0
        if failed == 0:
            ed["voice_plan"] = VOICE_PLAN
            ed["audio_hashes"] = hashes
            if story_ok:
                ed["story_plan"] = STORY_PLAN
            else:
                ed.pop("story_plan", None)     # 广播剧没生成成功 → 下次运行重试
            # 清掉本期已不存在条目的残留音频(条目数变少时, 旧 item-XX.mp3 会串进连播/被误点)
            keep_names = {j[0] for j in jobs} | {"broadcast.mp3"}
            for fn in os.listdir(adir):
                if fn.endswith(".mp3") and fn not in keep_names:
                    try:
                        os.remove(os.path.join(adir, fn))
                        print(f"  清理多余音频: {date}/{fn}")
                    except Exception:
                        pass
        # 合并整期连播文件(不含 story): 有新音频 / 文件缺失 / 段列表与当前条目不一致 时重建
        bpath = os.path.join(adir, "broadcast.mp3")
        job_files = [j[0] for j in bjobs]
        seg_files = [s.get("file") for s in (ed.get("broadcast") or {}).get("segments", [])]
        if failed == 0 and (regen or not valid_audio(bpath) or seg_files != job_files):
            try:
                segs = merge_broadcast(adir, bjobs)
                ed["broadcast"] = {"file": "broadcast.mp3", "segments": segs}
                print(f"  {date}/broadcast.mp3  {os.path.getsize(bpath)//1024} KB  ({len(segs)} 段)")
            except Exception as e:
                print(f"  broadcast 合并失败 {date}: {type(e).__name__} {e}")
                ed.pop("broadcast", None)
    save_editions(data)
    print(f"完成: 生成 {made} 个文件, 失败 {failed}, 用时 {time.time()-t0:.0f}s")
    # 关键: 本脚本会给 news.json 补上 broadcast 时间轴/voice_plan/音频指纹,
    # 而流水线里 build_data.py 排在配音之前 —— 不在这里重跑一次, 页面就拿不到连播数据
    # (表现为: 手机后台播完一条不自动接一条)。故收尾时强制刷新 news.js。
    try:
        sys.path.insert(0, os.path.join(ROOT, "scripts"))
        import build_data
        build_data.main()
        print("  已刷新 data/news.js")
    except Exception as e:
        print(f"  刷新 news.js 失败: {type(e).__name__} {e}")


if __name__ == "__main__":
    asyncio.run(main(force="--force" in sys.argv))
