# -*- coding: utf-8 -*-
"""为英文财经早报预生成 MP3 广播音频。
主引擎: Kokoro 本地神经语音（免费、稳定，新闻主播式双声配置）
  - 开场导语 intro → af_heart (美式女声, 清晰明亮)
  - 正文条目     → am_michael (美式男声, 沉稳)
备选音色: bm_george (英式男声) 可在 VOICE_PLAN 里替换
兜底引擎: Edge 神经语音 (en-US-AndrewNeural), Kokoro 不可用时自动切换
用法: python gen_audio.py [--force]
为 data/news.json 中每期生成 data/audio/<date>/intro.mp3 与 item-XX.mp3，
已存在的文件自动跳过（--force 重新生成）。
"""
import asyncio, json, os, re, sys, shutil, time, tempfile

sys.stdout.reconfigure(encoding="utf-8")

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
MODELS = os.path.join(ROOT, "models")
MIN_VALID_SIZE = 2000                # 小于该字节数视为损坏文件, 重新生成
# 语速固定 1.0 —— 与用户认可的试听样本一致; 播放端可用 playbackRate 微调

# 播报配置: 用户指定全部用男声(男声更稳、更适合财经文)
VOICE_INTRO_KOKORO = "am_michael"
VOICE_ITEM_KOKORO = "am_michael"
VOICE_EDGE = "en-US-AndrewNeural"

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


def synth_kokoro(text, path, voice):
    """Kokoro 本地合成, 直接写 MP3 (libsndfile 1.2+ 原生支持)。
    长文本整段合成韵律会漂移, 所以切成短小段逐段合成后拼接:
    逗号/连词处 0.22s, 句末 0.45s —— 换气感自然, 音质等同短句试听样本。"""
    import numpy as np, soundfile as sf
    k = get_kokoro()
    if k is None:
        return False
    units = split_units(text)
    if not units:
        return False
    sr = 24000
    parts = [np.zeros(int(sr * 0.15), dtype=np.float32)]     # 开头留白
    for i, (txt, pause) in enumerate(units):
        samples, _sr = k.create(txt, voice=voice, speed=1.0, lang="en-us")
        samples = np.asarray(samples, dtype=np.float32)
        if samples.ndim > 1:
            samples = samples[:, 0]
        parts.append(samples)
        if i < len(units) - 1:
            parts.append(np.zeros(int(sr * pause), dtype=np.float32))
    sf.write(path, np.concatenate(parts), sr, format="MP3")
    return True


async def synth_edge(text, path):
    c = edge_tts.Communicate(tts_sanitize(text), VOICE_EDGE, rate="+6%")
    await c.save(path)


async def synth(text, path, is_intro):
    text = tts_sanitize(text)
    k = get_kokoro()
    if k is not None:
        voice = VOICE_INTRO_KOKORO if is_intro else VOICE_ITEM_KOKORO
        for attempt in range(2):
            try:
                synth_kokoro(text, path, voice)
                return "kokoro"
            except Exception as e:
                print(f"    Kokoro 尝试 {attempt+1}/2 失败: {type(e).__name__} {e}")
                get_kokoro_force_reload()
    if _edge_ok:
        await synth_edge(text, path)
        return "edge"
    raise RuntimeError("无可用语音引擎")


def get_kokoro_force_reload():
    global _kokoro
    _kokoro = None


def build_jobs(ed):
    jobs = []
    intro = "The Daily Brief. {}, {}. {} stories.".format(
        ed.get("weekday_en", ""), ed.get("date", ""), len(ed.get("items", [])))
    if ed.get("lead_en"):
        intro += " " + ed["lead_en"]
    jobs.append(("intro.mp3", intro, True))
    for i, it in enumerate(ed.get("items", [])):
        title = (it.get("title_en") or it.get("title_zh") or "").strip().rstrip(".") + "."
        body = (it.get("body_en") or "").strip()
        txt = (title + " " + body).strip()
        if len(txt) > 3:
            jobs.append((f"item-{i:02d}.mp3", txt, False))
    return jobs


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
    made = failed = 0
    t0 = time.time()
    for ed in data["editions"]:
        date = ed["date"]
        adir = os.path.join(ROOT, "data", "audio", date)
        os.makedirs(adir, exist_ok=True)
        jobs = build_jobs(ed)
        for fname, txt, is_intro in jobs:
            fpath = os.path.join(adir, fname)
            if not force and os.path.exists(fpath) and os.path.getsize(fpath) > MIN_VALID_SIZE:
                continue
            ok = engine = False
            for attempt in range(3):
                try:
                    engine = await synth(txt, fpath, is_intro)
                    ok = True
                    break
                except Exception as e:
                    print(f"  重试 {date}/{fname} ({attempt+1}/3): {type(e).__name__} {e}")
                    await asyncio.sleep(2.5)
            if ok:
                made += 1
                print(f"  {date}/{fname}  {os.path.getsize(fpath)//1024} KB  [{engine}]")
            else:
                failed += 1
                print(f"  失败 {date}/{fname}")
        ed["audio_ready"] = failed == 0
    save_editions(data)
    print(f"完成: 生成 {made} 个文件, 失败 {failed}, 用时 {time.time()-t0:.0f}s")


if __name__ == "__main__":
    asyncio.run(main(force="--force" in sys.argv))
