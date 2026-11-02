# -*- coding: utf-8 -*-
"""用大模型把机器翻译底稿改写成地道财经英文（替代原来由 Agent 手工精修的环节）。

没配 key 时直接跳过（保留机器翻译结果），便于本地先跑通。
需要的环境变量（GitHub Secrets）：
  LLM_API_KEY   必填，模型 API Key
  LLM_BASE_URL  可选，默认 https://api.deepseek.com/v1（任何 OpenAI 兼容接口都行）
  LLM_MODEL     可选，默认 deepseek-chat
"""
import json
import os
import re
import sys

import requests

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NEWS_F = os.path.join(BASE, "data", "news.json")

API_KEY = (os.environ.get("LLM_API_KEY") or "").strip()
API_BASE = (os.environ.get("LLM_BASE_URL") or "https://api.deepseek.com/v1").rstrip("/")
MODEL = os.environ.get("LLM_MODEL") or "deepseek-chat"
BATCH = 8

SYSTEM = (
    "You are a senior financial editor writing an English-language morning brief for "
    "professional investors. You rewrite Chinese wire copy into crisp, natural financial English.\n"
    "Rules:\n"
    "1. Preserve every fact: numbers, percentages, dates, company and institution names, units. "
    "Never invent or drop figures.\n"
    "2. Use correct English names: S&P 500, Nasdaq, Dow Jones, ECB, PBOC, CSRC, "
    "and proper company/institution names (e.g. ING, ServiceNow, Rivian, Longsys).\n"
    "3. Titles: one short sentence, no trailing period, headline style, <= 18 words.\n"
    "4. Bodies: 1-2 sentences, <= 45 words, active voice, plain professional tone. "
    "No 'reportedly' padding, no clickbait.\n"
    "5. Keep the meaning exactly; do not add analysis or opinion.\n"
    "6. Output valid JSON only."
)


def call_llm(payload_items, lead_zh, n_items):
    """返回 {id: {title_en, body_en}} 和 lead_en"""
    user = (
        "Rewrite the following Chinese financial brief into English.\n"
        "Return JSON: {\"lead_en\": \"...\", \"items\": [{\"id\": 0, \"title_en\": \"...\", \"body_en\": \"...\"}]}\n"
        f"lead_en = a 2-3 sentence English overnight wrap covering all {n_items} stories.\n"
        f"lead_zh (for reference): {lead_zh}\n"
        "items:\n" + json.dumps(payload_items, ensure_ascii=False)
    )
    r = requests.post(
        f"{API_BASE}/chat/completions",
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
        json={
            "model": MODEL,
            "messages": [{"role": "system", "content": SYSTEM},
                         {"role": "user", "content": user}],
            "temperature": 0.3,
            "response_format": {"type": "json_object"},
        },
        timeout=180,
    )
    r.raise_for_status()
    text = r.json()["choices"][0]["message"]["content"]
    m = re.search(r"\{.*\}", text, re.S)
    return json.loads(m.group(0) if m else text)


def num_tokens(s):
    return set(re.findall(r"\d+(?:[.,]\d+)*", s or ""))


def main():
    if not API_KEY:
        print("[polish] 未配置 LLM_API_KEY，跳过（保留机器翻译底稿）")
        return 0
    with open(NEWS_F, encoding="utf-8") as f:
        data = json.load(f)
    ed = data["editions"][0]
    items = ed.get("items", [])
    if not items:
        print("[polish] 本期没有条目")
        return 0

    ok = 0
    lead_candidates = []
    for start in range(0, len(items), BATCH):
        batch = items[start:start + BATCH]
        payload = [{"id": i, "title_zh": it.get("title_zh", ""), "body_zh": it.get("body_zh", "")}
                   for i, it in enumerate(batch)]
        try:
            res = call_llm(payload, ed.get("lead_zh", ""), len(items))
        except Exception as e:
            print(f"[polish] 第 {start//BATCH+1} 批失败: {type(e).__name__} {e}")
            continue

        by_id = {int(x["id"]): x for x in res.get("items", []) if "id" in x}
        for i, it in enumerate(batch):
            new = by_id.get(i)
            if not new:
                continue
            t_en = (new.get("title_en") or "").strip()
            b_en = (new.get("body_en") or "").strip()
            if len(t_en) < 6 or len(b_en) < 10:
                continue
            # 数字安全校验: 中文原文的关键数字必须出现在英文里, 否则保留机器翻译
            zh_nums = {n.replace(",", "") for n in num_tokens(it.get("body_zh", "") + " " + it.get("title_zh", ""))}
            en_nums = {n.replace(",", "") for n in num_tokens(b_en + " " + t_en)}
            missing = zh_nums - en_nums
            if len(missing) > max(2, len(zh_nums) // 3):
                print(f"[polish] 条目 {it.get('id')} 数字缺失 {sorted(missing)[:4]}，保留原译")
                continue
            it["title_en"], it["body_en"] = t_en, b_en
            ok += 1

        lead_en = (res.get("lead_en") or "").strip()
        if len(lead_en) > 40:
            lead_candidates.append(lead_en)

    if lead_candidates:
        ed["lead_en"] = max(lead_candidates, key=len)
    if not ed.get("lead_zh"):
        ed["lead_zh"] = "。".join(it.get("title_zh", "") for it in items[:3]) + "。"

    with open(NEWS_F, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"[polish] 精修完成 {ok}/{len(items)} 条")
    return 0


if __name__ == "__main__":
    sys.exit(main())
