#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
英文财经早报 / The Daily Brief  ——  数据抓取与翻译流水线

流程:
  1. 抓取华尔街见闻 7x24 多频道快讯 (+ 新浪财经滚动做兜底)
  2. 清洗 / 归类 / 去重 / 打分排序
  3. 抓取指数快照 (东方财富)
  4. 中 -> 英机器翻译 (MyMemory, 带本地缓存, 节省配额)
  5. 写入 data/news.json  (合并最近 N 天为 editions 归档)

用法:
  python fetch_news.py                # 抓取并生成当天 edition
  python fetch_news.py --limit 18     # 指定条数
  python fetch_news.py --no-translate # 只抓中文, 不翻译 (供 agent 后续精译)
"""

import argparse
import hashlib
import html
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone

import requests

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
CACHE_F = os.path.join(DATA, ".mt_cache.json")
NEWS_F = os.path.join(DATA, "news.json")
TZ = timezone(timedelta(hours=8))

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
HEADERS = {"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"}

CHANNELS = [
    ("global-channel",    "macro",      "宏观",   "Macro"),
    ("a-stock-channel",   "a_share",    "A股",    "A-Shares"),
    ("us-stock-channel",  "us_market",  "美股",   "US Markets"),
    ("hk-stock-channel",  "hk_market",  "港股",   "HK Markets"),
    ("commodity-channel", "commodity",  "商品",   "Commodities"),
    ("bond-channel",      "bond",       "债券",   "Bonds"),
]

# 打分关键词: 命中即加权, 保证选出来的是"重要"消息而不是流水账
KEYWORDS = {
    "high": ["央行", "降准", "降息", "加息", "美联储", "公开市场", "MLF", "LPR", "逆回购",
             "国务院", "政治局", "财政部", "发改委", "证监会", "关税", "外交部", "商务部",
             "CPI", "PPI", "GDP", "PMI", "社融", "非农", "失业率", "外汇储备",
             "业绩预增", "净利润", "营收", "回购", "增持", "中标", "订单", "涨价",
             "重组", "并购", "IPO", "退市", "停牌", "立案", "处罚"],
    "theme": ["半导体", "芯片", "算力", "人工智能", "AI", "机器人", "新能源", "光伏", "储能",
              "锂电", "锂", "稀土", "固态电池", "核电", "电网", "特高压", "军工", "创新药",
              "白酒", "地产", "房地产", "汽车", "消费", "出口", "黄金", "原油", "铜", "白银",
              "英伟达", "台积电", "特斯拉", "苹果", "微软", "OpenAI"],
}
SCORE_HIGH, SCORE_THEME = 10.0, 4.0

STOP_MARK = ("免责声明", "广告", "点击查看", "扫码", "关注公众号",
             "以下均为北京时间", "日内请重点关注", "会议预告")

# 翻译前先把关键主体/术语替换成英文, 机器翻译才不会把人名机构名译飞
ENTITIES = {
    "美联储": "the Federal Reserve", "欧洲央行": "the ECB", "日本央行": "the Bank of Japan",
    "英国央行": "the Bank of England", "加拿大央行": "the Bank of Canada",
    "国家统计局": "the National Bureau of Statistics", "国务院": "the State Council",
    "证监会": "the CSRC", "财政部": "the Ministry of Finance", "发改委": "the NDRC",
    "商务部": "the Ministry of Commerce", "工信部": "the MIIT", "央行": "the PBOC",
    "拉加德": "Christine Lagarde", "沃什": "Kevin Warsh", "鲍威尔": "Jerome Powell",
    "荷兰国际集团": "ING Group", "百时美施贵宝": "Bristol-Myers Squibb", "礼来": "Eli Lilly",
    "甲骨文": "Oracle", "谷歌": "Google", "英伟达": "Nvidia", "台积电": "TSMC",
    "微软": "Microsoft", "苹果": "Apple", "特斯拉": "Tesla", "比亚迪电子": "BYD Electronic",
    "比亚迪": "BYD", "兆易创新": "GigaDevice", "上纬新材": "Swancor Advanced Materials",
    "白银有色": "Baiyin Nonferrous", "超图软件": "SuperMap Software",
    "微芯生物": "Chipscreen Biosciences", "兴业银行": "Industrial Bank",
    "广发证券": "GF Securities", "新联电子": "Xinlian Electronics",
    "归母净利润": "net profit attributable to shareholders", "扣非净利润": "net profit excluding non-recurring items",
    "营业收入": "revenue", "同比增长": "up year on year", "同比下降": "down year on year",
    "同比扭亏": "swung to a profit from a loss a year earlier", "盘前": "in premarket trading",
    "盘后": "after the bell", "回购": "share buyback", "中标": "won the bid for",
    "美联储决议": "the Fed decision", "国债收益率": "Treasury yields",
    "现货黄金": "spot gold", "现货白银": "spot silver", "原油": "crude oil",
    "欧元区": "the eurozone", "首次申请失业救济人数": "initial jobless claims",
    "江波龙": "Longsys", "迦南智能": "Canaan Intelligence", "芯德半导体": "Xinde Semiconductor",
    "贵州银行": "Bank of Guizhou", "淡水河谷": "Vale", "英特尔": "Intel", "亚马逊": "Amazon",
    "宁德时代": "CATL", "欣旺达": "Sunwoda", "杉杉股份": "Shanshan", "铠侠": "Kioxia",
    "士兰微": "Silan Microelectronics", "赛力斯": "Seres", "长城汽车": "Great Wall Motor",
}

GLOSSARY = [
    (r"\bmedium-term lending facilit\w*", "medium-term lending facility (MLF)"),
    (r"\breserve requirement ratio\b", "reserve requirement ratio (RRR)"),
    (r"\bcentral bank\b", "the central bank (PBOC)"),
    (r"\bShanghai Composite\b", "the Shanghai Composite"),
    (r"\bpre-disc\b", "premarket"),
    (r"\bstock price\b", "share price"),
    (r"\bA shares?\b", "A-shares"),
]


def log(*a):
    print(*a, flush=True)


def now_cn():
    return datetime.now(TZ)


# ---------------------------------------------------------------- fetch
def http_get(url, **kw):
    kw.setdefault("timeout", 20)
    kw.setdefault("headers", HEADERS)
    for i in range(3):
        try:
            r = requests.get(url, **kw)
            if r.status_code == 200:
                return r
        except Exception as e:
            if i == 2:
                log(f"  ! GET fail {url[:70]} :: {e}")
            time.sleep(1.2 * (i + 1))
    return None


def clean_text(s):
    if not s:
        return ""
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s)
    s = s.replace("\u200b", "").replace("\xa0", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def split_title(text):
    """从快讯正文里切出标题: 优先【】/： 之前的部分"""
    m = re.match(r"^【(.{4,40})】", text)
    if m:
        return m.group(1), clean_text(text[m.end():])
    for sep in ("：", ":"):
        if sep in text[:46]:
            head, tail = text.split(sep, 1)
            if 4 <= len(head) <= 40 and len(tail) > 12:
                return head.strip(), tail.strip()
    # 取第一句
    m = re.match(r"^(.{8,40}?[。！？])", text)
    if m:
        return m.group(1).rstrip("。！？"), text[m.end():].strip()
    return text[:38], text


def trim_body(text, limit=210):
    text = clean_text(text)
    if len(text) <= limit:
        return text
    cut = text[:limit]
    for p in ("。", "；", "！", "？"):
        idx = cut.rfind(p)
        if idx > limit * 0.55:
            return cut[:idx + 1]
    return cut + "…"


def refine_category(it):
    """频道分类经常串味(bond 频道里塞公司财报), 按标题内容纠偏"""
    t = it["title_zh"]
    ann = ("净利润" in t or "营收" in t or "回购" in t or "中标" in t
           or "股东" in t or "业绩" in t or "季报" in t or "净利" in t)
    bond_word = ("国债" in t or "收益率" in t or "债" in t or "利率" in t)
    if it["category"] in ("bond", "hk_market") and ann and not bond_word:
        it["category"], it["category_zh"], it["category_en"] = "a_share", "A股", "A-Shares"
    return it


def fetch_wscn(channel, limit=20):
    url = (f"https://api-one-wscn.awtmt.com/apiv1/content/lives"
           f"?channel={channel}&client=pc&limit={limit}")
    r = http_get(url)
    if not r:
        return []
    try:
        items = r.json().get("data", {}).get("items", []) or []
    except Exception:
        return []
    out = []
    for it in items:
        body = clean_text(it.get("content_text") or it.get("content") or "")
        if len(body) < 14:
            continue
        title = clean_text(it.get("title") or it.get("highlight_title") or "")
        if not title:
            title, body = split_title(body)
        else:
            body = clean_text(body.replace(title, "", 1))
            if len(title) < 7 and body and "：" not in title:
                # 标题只有一个公司名: 用正文首句补成信息型标题
                first = re.split(r"[。；！？]", body)[0]
                if len(first) > 8:
                    title = title.strip("：:") + "：" + first[:30].rstrip("，、 ")
        if any(k in title or k in body for k in STOP_MARK):
            continue
        out.append({
            "src_id": f"wscn-{it.get('id')}",
            "ts": it.get("display_time") or 0,
            "source": "华尔街见闻",
            "title_zh": title.strip("。 "),
            "body_zh": trim_body(body or title),
            "url": it.get("uri") or "",
        })
    return out


def guess_cat(text):
    """新浪标题自带市场代码: (09976)是港股, (6xxxxx)等是A股, 其余归宏观"""
    if re.search(r"[（(]0\d{4}[）)]", text):
        return "hk_market", "港股", "HK Markets"
    if re.search(r"[（(][368]\d{5}[）)]|沪深|A股|涨停|两市", text):
        return "a_share", "A股", "A-Shares"
    return "macro", "宏观", "Macro"


def fetch_sina(limit=20):
    url = ("https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2516"
           f"&num={limit}&page=1")
    r = http_get(url)
    if not r:
        return []
    out = []
    try:
        rows = r.json().get("result", {}).get("data", []) or []
    except Exception:
        return []
    for it in rows:
        title = clean_text(it.get("title"))
        intro = clean_text(it.get("intro") or it.get("summary") or "")
        if len(title) < 8:
            continue
        if any(k in title or k in intro for k in STOP_MARK):
            continue
        cat, cat_zh, cat_en = guess_cat(title)
        out.append({
            "src_id": f"sina-{it.get('docid') or it.get('url')}",
            "ts": int(it.get("ctime") or 0),
            "source": "新浪财经",
            "title_zh": title,
            "body_zh": trim_body(intro or title),
            "url": it.get("url") or "",
            "category": cat, "category_zh": cat_zh, "category_en": cat_en,
        })
    return out


# ---------------------------------------------------------------- rank
def score_item(it):
    text = it["title_zh"] + " " + it["body_zh"]
    s = 0.0
    for k in KEYWORDS["high"]:
        if k in text:
            s += SCORE_HIGH
    for k in KEYWORDS["theme"]:
        if k in text:
            s += SCORE_THEME
    if "：" in it["title_zh"] and 2 <= it["title_zh"].index("：") <= 6:
        s += 3          # "公司：公告类" 通常是硬信息
    n = len(it["body_zh"])
    if 40 <= n <= 200:
        s += 2
    # 时间衰减: 越新越靠前 (12 小时线性衰减)
    age_h = max(0.0, (time.time() - (it["ts"] or time.time())) / 3600)
    s += max(0.0, 6.0 - age_h * 0.5)
    return s


def dedupe(items):
    seen_ids, seen_key, out = set(), set(), []
    for it in sorted(items, key=lambda x: -(x["ts"] or 0)):
        if it["src_id"] in seen_ids:
            continue
        key = re.sub(r"[^\u4e00-\u9fa5A-Za-z0-9]", "", it["title_zh"])[:22]
        if not key:
            continue
        if key in seen_key:
            continue
        # 正文前缀近似去重
        pre = re.sub(r"[^\u4e00-\u9fa5A-Za-z0-9]", "", it["body_zh"])[:26]
        if pre and pre in seen_key:
            continue
        seen_ids.add(it["src_id"])
        seen_key.add(key)
        seen_key.add(pre)
        out.append(it)
    return out


ANNOUNCE_RE = re.compile(r"^[\u4e00-\u9fa5A-Za-z0-9]{2,6}[：:]")


def is_announcement(it):
    return bool(ANNOUNCE_RE.match(it["title_zh"])) or "公告" in it["title_zh"]


def select(items, total=20):
    """按频道配额 + 打分挑选, 避免被某一类(比如公司业绩公告)刷屏"""
    for it in items:
        s = score_item(it)
        if is_announcement(it):
            s -= 6.0                             # 公告类降权: 早报不该被财报刷屏
        it["_score"] = s
    items.sort(key=lambda x: -x["_score"])

    quota = {"macro": 5, "a_share": 4, "us_market": 3,
             "hk_market": 2, "commodity": 3, "bond": 2}
    scale = max(0.5, total / 19.0)
    quota = {k: max(1, round(v * scale)) for k, v in quota.items()}

    picked, cnt, ann_max = [], {}, max(2, int(total * 0.3))
    ann = 0
    # 第一轮: 按配额轮转
    for _ in range(max(quota.values()) + 2):
        for cat in quota:
            if cnt.get(cat, 0) >= quota[cat]:
                continue
            for it in items:
                if it["category"] != cat or it in picked:
                    continue
                if is_announcement(it) and ann >= ann_max:
                    continue
                picked.append(it)
                cnt[cat] = cnt.get(cat, 0) + 1
                if is_announcement(it):
                    ann += 1
                break
            if len(picked) >= total:
                break
        if len(picked) >= total:
            break
    if len(picked) < total:                       # 补齐
        for it in items:
            if it not in picked:
                picked.append(it)
            if len(picked) >= total:
                break
    picked.sort(key=lambda x: -x["_score"])
    return picked


# ---------------------------------------------------------------- indices
IDX_MAP = [
    ("1.000001", "上证指数", "SSE Composite", "CN"),
    ("0.399001", "深证成指", "SZSE Component", "CN"),
    ("0.399006", "创业板指", "ChiNext", "CN"),
    ("1.000688", "科创50", "STAR 50", "CN"),
    ("100.HSI",  "恒生指数", "Hang Seng", "HK"),
    ("100.DJIA", "道琼斯",   "Dow Jones", "US"),
    ("100.NDX",  "纳斯达克", "Nasdaq", "US"),
    ("100.SPX",  "标普500",  "S&P 500", "US"),
]


def fetch_indices():
    secids = ",".join(x[0] for x in IDX_MAP)
    for host in ("https://push2.eastmoney.com", "https://push2delay.eastmoney.com"):
        r = http_get(host + "/api/qt/ulist.np/get",
                     params={"fltt": 2, "invt": 2, "secids": secids,
                             "fields": "f2,f3,f4,f12,f13,f14,f124"})
        if not r:
            continue
        try:
            diff = r.json().get("data", {}).get("diff", []) or []
        except Exception:
            continue
        if not diff:
            continue
        by_code = {f"{d.get('f13')}.{d.get('f12')}": d for d in diff}
        out = []
        for secid, zh, en, market in IDX_MAP:
            d = by_code.get(secid)
            if not d or d.get("f2") in (None, "-"):
                continue
            out.append({"name_zh": zh, "name_en": en, "market": market,
                        "value": d.get("f2"), "chg_pct": d.get("f3")})
        if out:
            return out
    return fetch_indices_sina()


SINA_IDX = [("s_sh000001", "上证指数", "SSE Composite", "CN"),
            ("s_sz399001", "深证成指", "SZSE Component", "CN"),
            ("s_sz399006", "创业板指", "ChiNext", "CN"),
            ("s_sh000688", "科创50", "STAR 50", "CN"),
            ("rt_hkHSI", "恒生指数", "Hang Seng", "HK"),
            ("gb_$dji", "道琼斯", "Dow Jones", "US"),
            ("gb_$ixic", "纳斯达克", "Nasdaq", "US"),
            ("gb_$inx", "标普500", "S&P 500", "US")]


def fetch_indices_sina():
    codes = ",".join(x[0] for x in SINA_IDX)
    r = http_get("https://hq.sinajs.cn/list=" + codes,
                 headers={**HEADERS, "Referer": "https://finance.sina.com.cn/"})
    if not r:
        return []
    r.encoding = "gbk"
    m = dict(re.findall(r'hq_str_([^=]+)="([^"]*)"', r.text))
    out = []
    for code, zh, en, market in SINA_IDX:
        raw = (m.get(code) or "").split(",")
        if len(raw) < 4 or not raw[1]:
            continue
        try:
            if code.startswith("gb_"):            # 美股: 名称,现价,涨跌幅,...
                val, pct = float(raw[1]), float(raw[2])
            else:
                val, pct = float(raw[1]), float(raw[3])
        except Exception:
            continue
        out.append({"name_zh": zh, "name_en": en, "market": market,
                    "value": round(val, 2), "chg_pct": pct})
    return out


# ---------------------------------------------------------------- translate
class Translator:
    def __init__(self, enabled=True):
        self.enabled = enabled
        self.cache = {}
        self.calls = 0
        if os.path.exists(CACHE_F):
            try:
                with open(CACHE_F, encoding="utf-8") as f:
                    self.cache = json.load(f)
            except Exception:
                self.cache = {}

    def _save(self):
        os.makedirs(DATA, exist_ok=True)
        tmp = CACHE_F + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.cache, f, ensure_ascii=False)
        os.replace(tmp, CACHE_F)

    def _post_edit(self, txt):
        for pat, rep in GLOSSARY:
            txt = re.sub(pat, rep, txt, flags=re.I)
        txt = txt.replace("  ", " ").strip()
        if txt and txt[-1] not in ".!?\"'":
            txt += "."
        return txt

    def zh2en(self, text):
        if not text:
            return ""
        if not self.enabled:
            return ""
        key = hashlib.md5(text.encode("utf-8")).hexdigest()
        if key in self.cache:
            return self.cache[key]
        # MyMemory 单次上限约 500 字符, 超长切段
        chunks, cur = [], ""
        for piece in re.split(r"(?<=[。；！？])", text):
            if len(cur) + len(piece) > 420 and cur:
                chunks.append(cur)
                cur = piece
            else:
                cur += piece
        if cur:
            chunks.append(cur)
        outs = []
        for ch in chunks:
            got = self._mt(ch)
            if got:
                outs.append(got)
            time.sleep(0.9)
        en = self._post_edit(" ".join(outs)) if outs else ""
        if en:
            self.cache[key] = en
            self._save()
        return en

    def _sub_entities(self, text):
        """按长度倒序替换, 避免 '比亚迪电子' 被 '比亚迪' 先吃掉"""
        for zh in sorted(ENTITIES, key=len, reverse=True):
            if zh in text:
                text = text.replace(zh, f" {ENTITIES[zh]} ")
        return re.sub(r"\s{2,}", " ", text)

    def _mt(self, text):
        text = self._sub_entities(text)
        params = {"q": text, "langpair": "zh-CN|en", "de": "brief@example.com"}
        for i in range(3):
            try:
                r = requests.get("https://api.mymemory.translated.net/get",
                                 params=params, headers=HEADERS, timeout=25)
                self.calls += 1
                if r.status_code == 200:
                    j = r.json()
                    data = j.get("responseData") or {}
                    t = (data.get("translatedText") or "").strip()
                    if t and "MYMEMORY WARNING" not in t.upper() and j.get("responseStatus") == 200:
                        return t
                time.sleep(2 + i * 2)
            except Exception:
                time.sleep(2 + i * 2)
        return ""


# ---------------------------------------------------------------- build
def build(total=20, translate=True, keep_days=7):
    log("→ 抓取快讯 ...")
    raw = []
    for ch, cat, zh, en in CHANNELS:
        got = fetch_wscn(ch)
        for it in got:
            it["category"], it["category_zh"], it["category_en"] = cat, zh, en
            refine_category(it)
        log(f"   {zh:<3} {len(got):>3} 条  ({ch})")
        raw += got
    sina = fetch_sina()
    log(f"   新浪 {len(sina):>3} 条")
    raw += sina
    log(f"   合计 {len(raw)} 条")

    items = dedupe(raw)
    log(f"→ 去重后 {len(items)} 条")
    picked = select(items, total=total)
    log(f"→ 选中 {len(picked)} 条")

    log("→ 抓取指数快照 ...")
    idx = fetch_indices()
    log(f"   {len(idx)} 个指数")

    tr = Translator(translate)
    if translate:
        log("→ 翻译中 (MyMemory) ...")
    for i, it in enumerate(picked, 1):
        it["time"] = datetime.fromtimestamp(it["ts"] or time.time(), TZ).strftime("%H:%M")
        it["title_en"] = tr.zh2en(it["title_zh"])
        it["body_en"] = tr.zh2en(it["body_zh"]) if len(it["body_zh"]) > 12 else ""
        it.pop("_score", None)
        it["id"] = it.pop("src_id")
        if translate:
            log(f"   [{i:>2}/{len(picked)}] {it['title_en'][:70] or '(翻译失败)'}")

    ed = now_cn()
    edition = {
        "date": ed.strftime("%Y-%m-%d"),
        "weekday_en": ed.strftime("%A"),
        "weekday_zh": "周" + "一二三四五六日"[ed.weekday()],
        "generated_at": ed.strftime("%Y-%m-%d %H:%M"),
        "lead_en": "",
        "lead_zh": "",
        "indices": idx,
        "items": picked,
    }

    # 合并历史
    editions = []
    if os.path.exists(NEWS_F):
        try:
            with open(NEWS_F, encoding="utf-8") as f:
                old = json.load(f)
            editions = [e for e in old.get("editions", []) if e.get("date") != edition["date"]]
        except Exception:
            editions = []
    editions.insert(0, edition)
    editions = sorted(editions, key=lambda e: e["date"], reverse=True)[:keep_days]

    out = {
        "meta": {
            "site_zh": "英文财经早报",
            "site_en": "The Daily Brief",
            "updated_at": edition["generated_at"],
            "latest": edition["date"],
            "count": len(picked),
            "mt_calls": tr.calls,
        },
        "editions": editions,
    }
    os.makedirs(DATA, exist_ok=True)
    with open(NEWS_F, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    log(f"✓ 写入 {NEWS_F}  (归档 {len(editions)} 期, 翻译调用 {tr.calls} 次)")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--no-translate", action="store_true")
    ap.add_argument("--keep-days", type=int, default=7)
    a = ap.parse_args()
    return build(a.limit, not a.no_translate, a.keep_days)


if __name__ == "__main__":
    sys.exit(main())
