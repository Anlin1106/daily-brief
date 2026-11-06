# -*- coding: utf-8 -*-
"""版面三 · 每日一笑 —— 财经圈趣闻/经典段子，语料与分配。

设计:
- 语料 = 内置 BUILTIN + data/jokes.json 追加(每日自动化可补一则)
- 分配规则与 story.py 相同: 每期若无 joke, 从未用过的语料里按日期哈希稳定挑一则;
  写进 ed["joke"] 后固定不变
- 英文为口播稿: 短句、少数字、有停顿感的讲述体; 中文只是对照参考
- 内容红线: 只用流传广泛、无冒犯性的财经幽默/名言轶事, 不影射具体在世机构与个人
"""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
EXTRA = os.path.join(ROOT, "data", "jokes.json")

# 内置语料: 10 则。英文刻意短句化, 便于 Kokoro/Edge 朗读出"讲笑话"的节奏。
BUILTIN = [
    {
        "id": "lost-interest",
        "tag_zh": "华尔街双关", "tag_en": "Wall Street Wordplay",
        "title_zh": "银行家为什么辞职？他失去了“利息”",
        "title_en": "Why Did the Banker Quit? He Lost Interest",
        "body_zh": "一位年轻银行家在大银行干满一年就辞职了。朋友都问他为什么，他只说了一句：我失去了利息。这个笑话妙在双关。英文里利息和兴趣是同一个词。对银行家来说，这两样东西缺一样都干不下去。所以下次见到闷闷不乐的银行家，你可以关心地问一句：是利息的问题，还是兴趣的问题？",
        "body_en": "A young banker worked at a big bank for exactly one year. Then he quit. His friends all asked why. He gave them a one line answer. I lost interest. The joke works in two ways. In English, the money a bank pays you, and the feeling of caring, are the same word. A banker cannot survive without either one. So next time you meet a sad banker, ask politely. Is it the interest, or the interest?",
    },
    {
        "id": "nine-of-five",
        "tag_zh": "经济学家的预言", "tag_en": "Economist Forecast",
        "title_zh": "过去五次衰退，经济学家预测中了九次",
        "title_en": "Nine of the Last Five Recessions",
        "body_zh": "经济学家萨缪尔森讲过一个流传至今的玩笑：股市在过去五次衰退里，预测中了九次。意思是股市总在喊狼来了，喊的次数远比狼真的来的次数多。所以听到谁信誓旦旦地预测崩盘，不用太紧张，也不用太得意，先数一数他之前喊过几次。预测市场这件事，连最聪明的人也常常只是运气好。",
        "body_en": "The economist Paul Samuelson left us a joke that never gets old. The stock market has predicted nine of the last five recessions. Read that again. Nine predictions. Five real recessions. The market cries wolf far more often than the wolf arrives. So when someone loudly predicts the next crash, stay calm. Count how many times they called it before. Predicting the market is hard. Even for the smartest people in the room.",
    },
    {
        "id": "getty-bank",
        "tag_zh": "石油大亨名言", "tag_en": "Oil Baron's Wisdom",
        "title_zh": "欠银行一百块是你的麻烦，欠一个亿是银行的麻烦",
        "title_en": "Owe the Bank a Hundred, or a Hundred Million",
        "body_zh": "石油大亨保罗·盖蒂说过一句冷幽默：如果你欠银行一百块还不上，那是你的麻烦。如果你欠银行一个亿还不上，那是银行的麻烦。听着像玩笑，其实是他做生意的心得。债务大到一定程度，就成了一种筹码，银行反而要想法子让你活下来。这句话后来成了金融圈讲风险时最常引用的段子之一。",
        "body_en": "The oil billionaire J. Paul Getty had a piece of dark humor. If you owe the bank one hundred dollars and cannot pay, that is your problem. If you owe the bank one hundred million and cannot pay, that is the bank's problem. It sounds like a joke, but it was real business advice. Big debt can become leverage. Past a certain size, the bank needs you to survive. Traders still quote this line today, half laughing, half serious.",
    },
    {
        "id": "truman-recession",
        "tag_zh": "总统的定义", "tag_en": "A President's Definition",
        "title_zh": "邻居失业叫衰退，自己失业叫萧条",
        "title_en": "A Recession Is When Your Neighbor Loses His Job",
        "body_zh": "据说杜鲁门总统这样区分经济术语：邻居失业，叫衰退；自己失业，才叫萧条。一句话戳破了宏大叙事——经济数据再漂亮，落到每个具体的人身上，感受是完全不同的。这也提醒我们读新闻时留个心眼：报表上的百分比，都是别人的人生。理解经济，要从理解一个具体的人开始。",
        "body_en": "President Truman supposedly explained economic terms this way. A recession is when your neighbor loses his job. A depression is when you lose yours. One sentence, and all the big words collapse. Growth rates look beautiful on paper. But every percentage point is somebody's real life. It is a good habit when reading the news. Behind every statistic, there is a person. Economics starts with people, not charts.",
    },
    {
        "id": "rothschild-early",
        "tag_zh": "金融世家心得", "tag_en": "Banking Family Secret",
        "title_zh": "我是靠卖得太早赚的钱",
        "title_en": "I Made My Fortune by Selling Too Early",
        "body_zh": "罗斯柴尔德家族的男爵说过一句反直觉的话：我是靠卖得太早，才赚到钱的。人人都怕卖早了少赚，可他偏偏说卖早是美德。背后的道理是：没人能卖在最高点，总想赚最后一分钱的人，往往连本带利还回去。留给读者一个问题：你手里的盈利，是因为贪心多等了几天，还是因为纪律提前落袋？",
        "body_en": "Baron Rothschild said something that sounds backwards. I made my fortune by selling too early. Everyone fears selling too soon and missing the top. He called selling early a virtue. The logic is simple. Nobody sells at the exact peak. People who chase the last penny usually return everything, and more. So here is a question worth thinking about. Your last winning trade. Did you hold longer out of greed, or exit early out of discipline?",
    },
    {
        "id": "bull-bear-pig",
        "tag_zh": "老交易员口头禅", "tag_en": "Old Trader's Chant",
        "title_zh": "牛市赚钱，熊市赚钱，猪被宰",
        "title_en": "Bulls Win, Bears Win, Pigs Get Slaughtered",
        "body_zh": "华尔街有句老话：牛市能赚钱，熊市也能赚钱，只有猪会被宰。牛是看涨的人，熊是看跌的人，猪是指贪得无厌的人。这句话的重点不是让你判断方向，而是提醒你：方向从来不是死因，贪心才是。涨了还想更多，亏了想一夜翻本，这类动作才最危险。行情永远都在，本金没了就真的没了。",
        "body_en": "Wall Street has an old chant. Bulls make money. Bears make money. Pigs get slaughtered. Bulls expect prices to rise. Bears expect prices to fall. And pigs are the greedy ones. The lesson is not about picking a direction. Direction is rarely what kills an account. Greed is. Holding for more when you are up. Doubling down to win it all back overnight. Markets are always open. But lost capital does not come back.",
    },
    {
        "id": "shoeshine-boy",
        "tag_zh": "1929年的擦鞋童", "tag_en": "The Shoeshine Boy, 1929",
        "title_zh": "擦鞋童都在荐股的那天，他清仓离场",
        "title_en": "When the Shoeshine Boy Gave Stock Tips",
        "body_zh": "一九二九年，约瑟夫·肯尼迪让擦鞋童擦鞋，小孩却热心地给他推荐起股票来。他回到办公室立刻清仓。他的逻辑是：连擦鞋童都在荐股，说明最后一批买家已经进场，接下来只有卖盘了。没过多久，大崩盘来了。这个观察后来被称为擦鞋童理论：当所有人都在谈论某样东西时，往往意味着它已经不便宜了。",
        "body_en": "New York, nineteen twenty-nine. Joseph Kennedy got his shoes polished, and the shoeshine boy happily gave him stock tips. Kennedy walked back to his office and sold everything. His logic was sharp. If the shoeshine boy is giving stock tips, the last buyers have already arrived. Who is left to buy? Soon after, the market crashed. People still call it the shoeshine boy theory. When everybody talks about something, it is usually no longer cheap.",
    },
    {
        "id": "glass-engineer",
        "tag_zh": "工程师的答案", "tag_en": "The Engineer's Answer",
        "title_zh": "杯子半满？工程师说杯子太大了",
        "title_en": "Half Full? The Engineer Says the Glass Is Too Big",
        "body_zh": "乐观主义者说杯子是半满的，悲观主义者说是半空的，工程师看了看说：这个杯子比实际需要的大了一倍。放到市场里也一样：同一个行情，多头看到机会，空头看到风险，而真正干活的人只关心一件事——估值和实际价值差多少。别急着站队，先量一量杯子。",
        "body_en": "The optimist says the glass is half full. The pessimist says it is half empty. The engineer looks at both and says, the glass is twice as big as it needs to be. Markets work the same way. The bull sees opportunity. The bear sees risk. The person doing the actual work asks only one question. How far is the price from the real value? Do not rush to pick a side. First, measure the glass.",
    },
    {
        "id": "efficient-hundred",
        "tag_zh": "街头十美元", "tag_en": "The Ten Dollar Bill",
        "title_zh": "地上有一张十美元，经济学家为什么不捡",
        "title_en": "Why Economists Never Pick Up Money",
        "body_zh": "两个经济学家走在街上，看见地上躺着一张十美元。年轻的说，快去捡。老的说，不可能，如果是真的，早就被人捡走了。这是对有效市场理论最经典的调侃：所有信息都已经反映在价格里，天上不会掉馅饼。玩笑归玩笑，它也留了个真实的尾巴——市场大多数时候确实很有效，但偶尔，地上的钱是真的。",
        "body_en": "Two economists walk down the street. They spot a ten dollar bill on the ground. The young one says, pick it up. The old one says, it cannot be real. If it were real, someone would have picked it up already. This is the classic joke about efficient markets. All information is already in the price. Free money does not lie on the street. But here is the twist. Markets are efficient most of the time. Only most. Once in a while, the money on the ground is real.",
    },
    {
        "id": "einstein-compound",
        "tag_zh": "传说的第八大奇迹", "tag_en": "The Legendary Eighth Wonder",
        "title_zh": "爱因斯坦说复利是第八大奇迹？",
        "title_en": "Did Einstein Call Compounding the Eighth Wonder?",
        "body_zh": "据说爱因斯坦讲过：复利是世界第八大奇迹，懂的人赚它，不懂的人付它。这句话他大概率没说过，却成了金融圈流传最广的名言。真假不重要，道理是真的：时间+利率，是普通人和财富之间最诚实的一条路。反过来也一样，利滚利的债，也会按同样的数学惩罚不守纪律的人。",
        "body_en": "People say Einstein once called compound interest the eighth wonder of the world. Those who understand it earn it. Those who do not, pay it. He probably never said it. But the quote refuses to die, because the math is real. Time, plus a steady rate, is the most honest road to wealth for ordinary people. And the road works both ways. Debt compounds too, with the same mathematics, punishing those who break their rules.",
    },
]


def load_corpus():
    """内置语料 + data/jokes.json 追加的增量(每日自动化可写一则)。"""
    corpus = list(BUILTIN)
    try:
        with open(EXTRA, encoding="utf-8") as f:
            extra = json.load(f)
        if isinstance(extra, list):
            have = {s["id"] for s in corpus}
            for s in extra:
                if isinstance(s, dict) and s.get("id") and s["id"] not in have and s.get("body_en"):
                    corpus.append(s)
                    have.add(s["id"])
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"  [joke] data/jokes.json 读取失败, 忽略: {type(e).__name__} {e}")
    return corpus


def assign(data):
    """给还没有 joke 的期分配一则(写进 ed["joke"] 后不再变化)。"""
    eds = data.get("editions", [])
    used = {ed.get("joke", {}).get("id") for ed in eds if ed.get("joke")}
    picked = 0
    keys = ("id", "tag_zh", "tag_en", "title_zh", "title_en", "body_zh", "body_en")
    for ed in eds:
        if ed.get("joke"):
            continue
        corpus = [s for s in load_corpus() if s["id"] not in used] or load_corpus()
        if not corpus:
            break
        idx = int(ed["date"].replace("-", "")) % len(corpus)
        s = corpus[idx]
        ed["joke"] = {k: s[k] for k in keys if k in s}
        used.add(s["id"])
        picked += 1
        print(f"  {ed['date']}: 分配笑话 [{s['tag_zh']}] {s['title_zh']}")
    return picked


def main():
    data = json.load(open(os.path.join(ROOT, "data", "news.json"), encoding="utf-8"))
    n = assign(data)
    with open(os.path.join(ROOT, "data", "news.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"OK: 新分配 {n} 期, 语料共 {len(load_corpus())} 则")


if __name__ == "__main__":
    main()
