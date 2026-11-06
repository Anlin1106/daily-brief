# -*- coding: utf-8 -*-
"""版面二 · 财经人物广播剧 —— 语料与分配。

设计（多声线沉浸版）:
- 每则故事是一个"广播剧脚本": lines = [{k, who, g, en, zh}, ...]
  k: "narr" 旁白 / "dial" 角色台词
  g: 声线代号 N=旁白(英式 fable) M=男1(adam) M2=男2(michael) F=女1(bella) F2=女2(nicole) F3=女3(heart)
  en: 英文口播台词(句子短、数字口语化, 供 TTS)  zh: 中文对照(页面显示)
- 语料 = 内置 BUILTIN + data/stories.json 追加的增量(自动化可补写, 同样用 lines 格式)
- 分配规则: 按自然周轮换 —— 同一周内的期共用同一篇(一周多更新一篇即可), 换周自动换新;
  已分配的期写进 news.json 后固定不变
- 兼容: 老格式(body_en/body_zh 纯文本)依然可播(单女声兜底); assign 会自动把已分配但
  还是老格式的期迁移成脚本版(音频指纹会变 → 自动重新配音)
"""
import json
import os
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
EXTRA = os.path.join(ROOT, "data", "stories.json")

# 内置语料: 12 则财经名人"广播剧"(中英双语)。英文是口播稿, 句子短, 数字口语化, 便于 TTS。
BUILTIN = [
    {
        "id": "buffett-paper",
        "name_zh": "沃伦·巴菲特", "name_en": "Warren Buffett", "era": "1942 · 美国奥马哈",
        "title_zh": "送报纸的少年，和复利的第一课",
        "title_en": "The Paperboy Who Learned Compounding First",
        "body_zh": "巴菲特十一岁买了人生第一只股票，涨了没几天就卖掉，赚了六美元。可那只股票后来涨了他十倍。十三岁他承包了几条街的报纸投递，每个月存下钱来继续买股票。他说自己赚钱的秘密只有一条，就是时间——雪球要滚得大，先得找到很湿的雪和很长的坡。",
        "body_en": "Warren Buffett bought his first stock at eleven. He sold it quickly for a small profit of six dollars. The stock later rose ten times higher. At thirteen, he delivered newspapers and saved every dollar. His secret, he says, is time. A snowball grows big only on very wet snow, and on a very long hill.",
        "lines": [
            {"k": "narr", "who": "Narrator", "g": "N",
             "en": "Omaha, Nebraska. Nineteen forty-two. An eleven year old boy is staring at six dollars.",
             "zh": "内布拉斯加州，奥马哈。1942 年。一个十一岁的小男孩正盯着六美元发呆。"},
            {"k": "dial", "who": "Warren", "g": "M",
             "en": "Dad, I sold it too soon. It just kept climbing without me.",
             "zh": "爸爸，我卖太早了。它还在涨，却不带我玩了。"},
            {"k": "dial", "who": "Howard", "g": "M2",
             "en": "Then remember how this feels. Patience is also a position.",
             "zh": "那就把这种滋味记住。耐心，也是一种仓位。"},
            {"k": "narr", "who": "Narrator", "g": "N",
             "en": "The boy was Warren Buffett. That stock later rose ten times higher. He never forgot it.",
             "zh": "这个男孩就是沃伦·巴菲特。那只股票后来涨了十倍。他一辈子没忘。"},
            {"k": "narr", "who": "Narrator", "g": "N",
             "en": "At thirteen, he ran his own newspaper routes, and saved every single dollar.",
             "zh": "十三岁，他承包了好几条街的送报路线，每一美元都存下来。"},
            {"k": "dial", "who": "Warren", "g": "M",
             "en": "People ask me the secret. It is simple. Time. Wet snow, and a very long hill.",
             "zh": "别人问我赚钱的秘密。很简单：时间。很湿的雪，和很长的坡。"},
            {"k": "narr", "who": "Narrator", "g": "N",
             "en": "The snowball had started rolling. It has not stopped for eighty years.",
             "zh": "雪球从那天开始滚，一滚就是八十年，到现在都没停。"},
        ],
    },
    {
        "id": "graham-1929",
        "name_zh": "本杰明·格雷厄姆", "name_en": "Benjamin Graham", "era": "1929 · 华尔街",
        "title_zh": "在大崩盘里亏光的人，写出了投资教科书",
        "title_en": "The Man Who Lost It All in 1929, Then Wrote the Textbook",
        "body_zh": "格雷厄姆年轻时是华尔街的明星，一九二九年股灾来了，他加了杠杆的账户几乎归零。痛苦让他想通了一件事：预测市场靠不住，能靠的只有价格和价值的差距。后来他写出《证券分析》，提出安全边际——用五毛钱买一块钱的东西。",
        "body_en": "Benjamin Graham was a rising star on Wall Street. Then came the crash of nineteen twenty-nine. His leveraged account was almost wiped out. The pain taught him one thing. You can only rely on the gap between price and value. He wrote Security Analysis, and invented the margin of safety. Buy a dollar for fifty cents.",
        "lines": [
            {"k": "narr", "who": "Narrator", "g": "N",
             "en": "New York, autumn, nineteen twenty-nine. The party on Wall Street is about to end.",
             "zh": "纽约，1929 年秋。华尔街这场狂欢，马上就要散场了。"},
            {"k": "narr", "who": "Narrator", "g": "N",
             "en": "Benjamin Graham was a rising star. He used borrowed money, and he was sure he was right.",
             "zh": "本杰明·格雷厄姆是当红新星，他借钱加杠杆，自以为万无一失。"},
            {"k": "dial", "who": "Client", "g": "F",
             "en": "Mr. Graham, the market is falling every day. What do we do now?",
             "zh": "格雷厄姆先生，市场天天在跌，我们现在怎么办？"},
            {"k": "dial", "who": "Graham", "g": "M2",
             "en": "Hold on. It has to come back. It always comes back.",
             "zh": "再撑一撑，会回来的，一直都回来的。"},
            {"k": "narr", "who": "Narrator", "g": "N",
             "en": "It did not come back fast enough. His account was almost wiped out. It took him years to recover.",
             "zh": "可它回来得太慢了。他的账户几乎归零，用了好几年才缓过来。"},
            {"k": "dial", "who": "Graham", "g": "M2",
             "en": "I was wrong about one thing. You cannot predict the market. You can only measure the gap between price and value.",
             "zh": "我想明白一件事：预测市场靠不住。能靠的，只有价格和价值之间的差距。"},
            {"k": "narr", "who": "Narrator", "g": "N",
             "en": "So he wrote the book that fed generations of investors. His rule is famous. Buy a dollar for fifty cents.",
             "zh": "于是他写出了那本养活几代投资者的书。规则很有名：用五毛钱，买一块钱的东西。"},
        ],
    },
    {
        "id": "munger-invert",
        "name_zh": "查理·芒格", "name_en": "Charlie Munger", "era": "美国 · 伯克希尔副手",
        "title_zh": "倒过来想，总是倒过来想",
        "title_en": "Invert, Always Invert",
        "body_zh": "芒格不喜欢问怎么成功，他喜欢问怎么失败。有人问他怎么把投资做好，他说：先列出所有让人亏钱的方法，然后一辈子别碰。巴菲特说，是芒格把他从捡烟蒂变成了买好公司。",
        "body_en": "Charlie Munger rarely asked how to succeed. He asked how to fail. List every way to lose money, then avoid all of it, forever. Buffett said Munger moved him from cheap stocks to great businesses.",
        "lines": [
            {"k": "narr", "who": "Narrator", "g": "N",
             "en": "Every year, thousands of investors make the pilgrimage to Omaha. Most of them come for two men, not one.",
             "zh": "每年都有成千上万的投资者去奥马哈朝圣。他们大多是为两个人来的，不是一个人。"},
            {"k": "dial", "who": "Shareholder", "g": "F2",
             "en": "Mr. Munger, how do I become a great investor?",
             "zh": "芒格先生，我怎样才能成为优秀的投资者？"},
            {"k": "dial", "who": "Munger", "g": "M2",
             "en": "Wrong question. Ask me how to be a terrible one.",
             "zh": "问题就问错了。你应该问我，怎么变成一个糟糕的投资者。"},
            {"k": "dial", "who": "Shareholder", "g": "F2",
             "en": "All right then. How do I lose all my money?",
             "zh": "行吧，那我怎么才能把钱全亏光？"},
            {"k": "dial", "who": "Munger", "g": "M2",
             "en": "Easy. Use leverage. Chase rumors. Buy what is hot. Pretend you understand. Then avoid all of it, forever.",
             "zh": "太简单了。加杠杆、听消息、追热门、不懂装懂。然后一辈子都别碰这些。"},
            {"k": "narr", "who": "Narrator", "g": "N",
             "en": "Buffett once said Munger pushed him from cheap stocks to wonderful businesses. Cheap is not enough. A cheap, wonderful business is the goal.",
             "zh": "巴菲特说，是芒格把他从捡烟蒂推向了买好公司。便宜不是终点，便宜的好生意才是。"},
        ],
    },
    {
        "id": "lynch-lipstick",
        "name_zh": "彼得·林奇", "name_en": "Peter Lynch", "era": "1980s · 富达麦哲伦基金",
        "title_zh": "口红卖得越好，经济可能越差",
        "title_en": "When Lipstick Sells, Watch Out",
        "body_zh": "林奇管麦哲伦基金时发现：经济越不景气，口红反而卖得越好。钱紧的时候，女人买不起新衣服，就买支口红让自己开心一下。机会藏在生活里，超市里什么卖得好，往往比研报更早告诉你答案。",
        "body_en": "Peter Lynch noticed something strange at Fidelity. The worse the economy felt, the better lipstick sold. When money is tight, lipstick is the cheapest happiness. Great ideas hide in daily life. He beat the market for thirteen years.",
        "lines": [
            {"k": "narr", "who": "Narrator", "g": "N",
             "en": "Boston, nineteen eighty. The star manager of the Magellan Fund is walking through a department store, not a trading floor.",
             "zh": "波士顿，1980 年。麦哲伦基金的明星经理逛的不是交易厅，是百货商场。"},
            {"k": "dial", "who": "Analyst", "g": "M",
             "en": "Peter, why are you looking at the cosmetics counter? We invest in companies, not makeup.",
             "zh": "彼得，你看化妆品柜台干什么？我们投的是公司，不是口红。"},
            {"k": "dial", "who": "Lynch", "g": "M2",
             "en": "Look at the sales data. The worse the economy feels, the better lipstick sells.",
             "zh": "你看看销售数据。经济越差，口红反而卖得越好。"},
            {"k": "dial", "who": "Analyst", "g": "M",
             "en": "That makes no sense. Why would anyone buy lipstick in a recession?",
             "zh": "这不合理啊。经济衰退谁还买口红？"},
            {"k": "dial", "who": "Lynch", "g": "M2",
             "en": "When money is tight, she skips the new dress. But a lipstick is the cheapest happiness she can still afford.",
             "zh": "钱紧的时候，新衣服不买了。但口红，是她还买得起的、最便宜的开心。"},
            {"k": "narr", "who": "Narrator", "g": "N",
             "en": "People later called it the lipstick effect. Lynch's real lesson was this. Great ideas hide in daily life, and he beat the market for thirteen years by paying attention.",
             "zh": "后来人们把这叫作口红效应。林奇真正的心得是：机会藏在生活里。他靠这份留心，跑赢市场十三年。"},
        ],
    },
    {
        "id": "dalio-1982",
        "name_zh": "瑞·达利欧", "name_en": "Ray Dalio", "era": "1982 · 桥水基金初创",
        "title_zh": "最自信的一年，他差点赔光一切",
        "title_en": "The Year of Total Confidence Nearly Ruined Him",
        "body_zh": "一九八二年，达利欧公开判断美国经济将走向萧条并重仓押注。结果墨西哥违约后市场不跌反涨，公司只剩他一个人。他从此写下每笔决策的依据，把痛苦变成算法，后来的桥水成了全球最大对冲基金。",
        "body_en": "In nineteen eighty-two, Ray Dalio predicted a depression, loudly and publicly. Then Mexico defaulted, and markets rose instead of falling. His company shrank to one person: himself. From then on, he logged every decision. Pain became an algorithm. That log built Bridgewater, the largest hedge fund in the world.",
        "lines": [
            {"k": "narr", "who": "Narrator", "g": "N",
             "en": "Nineteen eighty-two. A young trader goes on television, and says the word everyone fears. Depression.",
             "zh": "1982 年。一个年轻交易员上电视，说出了所有人害怕的那个词：萧条。"},
            {"k": "dial", "who": "Dalio", "g": "M",
             "en": "I am completely certain. The economy is going down. I have bet everything on it.",
             "zh": "我非常确定，经济要往下走。我把全部身家都押上了。"},
            {"k": "narr", "who": "Narrator", "g": "N",
             "en": "Then Mexico defaulted. And the market did the one thing he did not expect. It rose.",
             "zh": "然后，墨西哥违约了。市场做了他唯一没料到的事：上涨。"},
            {"k": "dial", "who": "Friend", "g": "F",
             "en": "Ray, you have to close the company. You have lost everything.",
             "zh": "瑞，你得把公司关了，你什么都赔光了。"},
            {"k": "dial", "who": "Dalio", "g": "M",
             "en": "I have four thousand dollars left, borrowed from my father. And one employee. Me.",
             "zh": "我还剩向我爸借的四千美元，和一个员工——我自己。"},
            {"k": "narr", "who": "Narrator", "g": "N",
             "en": "He later called it the most valuable event of his life. From then on, he wrote down the reason behind every decision. Every mistake was logged and studied. Pain became an algorithm.",
             "zh": "他后来称这次经历是一生中最宝贵的。从那以后，他把每个决策的依据都写下来，每个错误都记录归档。痛苦，变成了算法。"},
        ],
    },
    {
        "id": "soros-pound",
        "name_zh": "乔治·索罗斯", "name_en": "George Soros", "era": "1992 · 伦敦",
        "title_zh": "一夜之间，与英格兰银行对赌的人",
        "title_en": "The Night He Bet Against the Bank of England",
        "body_zh": "一九九二年，英镑被固定汇率锁在偏高的位置。索罗斯判断英国撑不住。九月十六日英国一天加息两次仍挡不住卖盘，当晚英镑暴跌。他的基金净赚约十亿美元，报纸标题写着打垮了英格兰银行。",
        "body_en": "In nineteen ninety-two, the British pound was locked into a fixed exchange rate that was too high. On September sixteenth, Britain raised rates twice in one day. It was not enough. That evening, the pound crashed. His fund made about one billion dollars.",
        "lines": [
            {"k": "narr", "who": "Narrator", "g": "N",
             "en": "London, September, nineteen ninety-two. Black Wednesday is only hours away.",
             "zh": "伦敦，1992 年 9 月。距离黑色星期三，只剩几个小时了。"},
            {"k": "dial", "who": "Trader", "g": "M2",
             "en": "George, the Bank of England keeps defending the pound. Rates went up again this morning.",
             "zh": "乔治，英格兰银行还在死守英镑，今天上午又加息了。"},
            {"k": "dial", "who": "Soros", "g": "M",
             "en": "A weak economy cannot defend an overvalued currency forever. Increase the position.",
             "zh": "疲软的经济，守不住高估的货币。继续加仓。"},
            {"k": "dial", "who": "Trader", "g": "M2",
             "en": "All of it? This is the Bank of England we are betting against.",
             "zh": "全部押上？我们赌的对手可是英格兰银行。"},
            {"k": "dial", "who": "Soros", "g": "M",
             "en": "When a trade is right, go for the jugular.",
             "zh": "当一笔交易是对的，就要直取要害。"},
            {"k": "narr", "who": "Narrator", "g": "N",
             "en": "That evening Britain gave up, and the pound crashed out of the system. His fund made about one billion dollars. Newspapers said he broke the Bank of England.",
             "zh": "当晚，英国投降了，英镑暴跌退出汇率机制。他的基金净赚约十亿美元。报纸标题写着：他打垮了英格兰银行。"},
        ],
    },
    {
        "id": "morgan-1907",
        "name_zh": "J.P. 摩根", "name_en": "J.P. Morgan", "era": "1907 · 纽约",
        "title_zh": "把银行家锁进书房，直到他们答应救市",
        "title_en": "The Night He Locked the Bankers In",
        "body_zh": "一九〇七年十月纽约股市崩盘，没有央行兜底的美国眼看滑向恐慌。六十九岁的摩根把几十位银行总裁锁进书房，逼出两千五百万美元救市资金，凌晨签下协议，恐慌停了。五年后美联储成立。",
        "body_en": "In October nineteen oh seven, New York was in panic. America had no central bank. J.P. Morgan, sixty-nine years old, summoned bank presidents to his library and locked the doors. The deal was signed after midnight. The panic stopped. Five years later, the Federal Reserve was born.",
        "lines": [
            {"k": "narr", "who": "Narrator", "g": "N",
             "en": "New York, October, nineteen oh seven. Depositors are lining up in the streets. America has no central bank, and the panic is spreading.",
             "zh": "纽约，1907 年 10 月。储户在街头排起长队。美国没有央行，恐慌正在蔓延。"},
            {"k": "narr", "who": "Narrator", "g": "N",
             "en": "So the most powerful banker in America did something nobody would dare today.",
             "zh": "于是，全美最有权势的银行家做了一件今天没人敢做的事。"},
            {"k": "dial", "who": "Morgan", "g": "M2",
             "en": "Gentlemen, you will all come to my library tonight. Bring your real numbers, not the ones for newspapers.",
             "zh": "诸位，今晚都到我的书房来。带上真实的账目，别带给报纸看的那份。"},
            {"k": "narr", "who": "Narrator", "g": "N",
             "en": "He questioned each president one by one, behind closed doors, until the true holes were on the table.",
             "zh": "他关门一个个逼问各位总裁，直到真实的窟窿全部摆上桌面。"},
            {"k": "dial", "who": "Morgan", "g": "M2",
             "en": "It is almost twelve o'clock. Nobody leaves this room until the papers are signed.",
             "zh": "现在快十二点了。文件不签完，谁也别想出这个门。"},
            {"k": "narr", "who": "Narrator", "g": "N",
             "en": "After midnight, twenty-five million dollars was pledged. The panic stopped. Five years later, partly because of this night, the Federal Reserve was born.",
             "zh": "午夜过后，两千五百万美元的救市资金凑齐了。恐慌停了。五年后，正因为这一夜，美联储诞生了。"},
        ],
    },
    {
        "id": "rockefeller-drop",
        "name_zh": "约翰·洛克菲勒", "name_en": "John D. Rockefeller", "era": "1870s · 美国俄亥俄",
        "title_zh": "省下一滴焊料的人，成了首富",
        "title_en": "The Man Who Saved One Drop of Solder",
        "body_zh": "洛克菲勒参观自家炼油厂，问工人焊一个油桶用几滴焊料。答：四十滴。他让人试试三十八滴，一滴不漏。就为这两滴，工厂每年省下大笔钱。他说：巨大的财富，就是对小事的巨大认真。",
        "body_en": "Young Rockefeller once watched workers seal oil barrels. He asked how many drops of solder each barrel took. Forty, they said. He asked them to try thirty-eight. Not a single barrel leaked. His ledgers went to three decimal places. Great wealth comes from great attention to small things.",
        "lines": [
            {"k": "narr", "who": "Narrator", "g": "N",
             "en": "Ohio, eighteen seventy. A quiet man in a dark suit is watching workers seal oil barrels, one by one.",
             "zh": "俄亥俄，1870 年。一个穿黑西装的安静男人，正看着工人们一个一个焊接油桶。"},
            {"k": "dial", "who": "Rockefeller", "g": "M",
             "en": "How many drops of solder does one barrel take?",
             "zh": "焊一个桶，要用几滴焊料？"},
            {"k": "dial", "who": "Worker", "g": "M2",
             "en": "Forty drops, sir. Same as always.",
             "zh": "四十滴，先生。一直都是四十滴。"},
            {"k": "dial", "who": "Rockefeller", "g": "M",
             "en": "Try thirty-eight.",
             "zh": "试试三十八滴。"},
            {"k": "narr", "who": "Narrator", "g": "N",
             "en": "They tried. Not a single barrel leaked. Those two drops saved the plant real money, every single year.",
             "zh": "工人们试了。一滴都没漏。就这两滴，每年给工厂省下真金白银。"},
            {"k": "dial", "who": "Rockefeller", "g": "M",
             "en": "Great wealth comes from great attention to small things. Saved one drop at a time.",
             "zh": "巨大的财富，就是对小事的巨大认真，一滴一滴攒出来的。"},
        ],
    },
    {
        "id": "carnegie-telegraph",
        "name_zh": "安德鲁·卡内基", "name_en": "Andrew Carnegie", "era": "1850s · 美国匹兹堡",
        "title_zh": "从每周一美元二毛，到钢铁大王",
        "title_en": "From a Dollar Twenty a Week to Steel",
        "body_zh": "卡内基十三岁移民美国，第一份工每周挣一美元二毛。当电报信童时，他背下全城商户的名字和脸。二十几岁把全部身家压进钢铁，建成世界最大钢铁厂。晚年捐出九成财产。",
        "body_en": "Andrew Carnegie arrived in America from Scotland at thirteen. His first job paid one dollar and twenty cents a week. As a messenger boy, he memorized every business in town. In his thirties he bet everything on steel, built the largest steel company in the world, then gave away ninety percent of it.",
        "lines": [
            {"k": "narr", "who": "Narrator", "g": "N",
             "en": "Pittsburgh, eighteen fifty. A thirteen year old Scottish immigrant starts his first job. It pays one dollar and twenty cents a week.",
             "zh": "匹兹堡，1850 年。一个十三岁的苏格兰移民开始第一份工作，周薪一美元二毛。"},
            {"k": "dial", "who": "Foreman", "g": "M2",
             "en": "Boy, the telegraph office needs a messenger. Can you learn the streets?",
             "zh": "小子，电报局要个信童。你能把街巷记熟吗？"},
            {"k": "dial", "who": "Carnegie", "g": "M",
             "en": "I will learn more than the streets, sir. I will learn every business in town, and every face behind the door.",
             "zh": "先生，我记的不只是街巷。我要记住全城每一家商户，和每扇门后面的每张脸。"},
            {"k": "narr", "who": "Narrator", "g": "N",
             "en": "While other boys played, he drilled himself on the telegraph key, and became the fastest ear in the city.",
             "zh": "别的孩子去玩了，他对着电报机日夜苦练，成了全城收发电报最快的人。"},
            {"k": "dial", "who": "Carnegie", "g": "M",
             "en": "Save it, invest it early, and when you find your industry, bet everything on it.",
             "zh": "把钱存下来，早一点投出去。找到属于自己的行业时，就把全部身家押上去。"},
            {"k": "narr", "who": "Narrator", "g": "N",
             "en": "He built the largest steel company in the world. Then he gave ninety percent of it away, with one line for the history books. Dying rich is a disgrace.",
             "zh": "他建成了世界最大的钢铁公司，然后捐出了九成财产，只留给历史一句话：带着巨富死去，是一种耻辱。"},
        ],
    },
    {
        "id": "fisher-scuttlebutt",
        "name_zh": "菲利普·费雪", "name_en": "Philip Fisher", "era": "1950s · 美国加州",
        "title_zh": "不读财报的调研法：去和对手闲聊",
        "title_en": "The Scuttlebutt Method",
        "body_zh": "费雪调研公司有个怪招：不急着看报表，先去闲聊。找离职员工、供应商、同行工程师，一家公司的真实成色就浮出来了。他管这叫闲聊法，靠它拿了摩托罗拉十多年。",
        "body_en": "Philip Fisher had an odd way to research a company. Before reading reports, he went out and chatted. Former employees, salesmen, suppliers, rival engineers. From these talks, the truth surfaced. He called it the scuttlebutt method.",
        "lines": [
            {"k": "narr", "who": "Narrator", "g": "N",
             "en": "California, nineteen fifty. While other analysts read annual reports, Philip Fisher does something strange. He goes out for coffee, and small talk.",
             "zh": "加州，1950 年。别的分析师在读年报，菲利普·费雪却在干一件怪事：出门喝咖啡、闲聊。"},
            {"k": "dial", "who": "Fisher", "g": "M2",
             "en": "You used to work at their plant. Was the new product real quality, or just a good story?",
             "zh": "你以前在他们的厂里干过。新品是真有实力，还是故事讲得好？"},
            {"k": "dial", "who": "Ex-employee", "g": "F",
             "en": "Honestly? The lab is serious. But the boss loses his temper, and good people keep leaving.",
             "zh": "说实话？实验室是认真的。但老板脾气大，能干的人一直在走。"},
            {"k": "dial", "who": "Fisher", "g": "M2",
             "en": "And the competitors say the same thing, from the other side. Now the picture is complete.",
             "zh": "竞争对手从另一头说出来的，也是同样的话。拼图这就完整了。"},
            {"k": "narr", "who": "Narrator", "g": "N",
             "en": "He called it the scuttlebutt method. It led him to hold Motorola for decades. His advice shaped Buffett too. If it is a wonderful company, almost never sell.",
             "zh": "他管这叫闲聊法。靠它，他拿住了摩托罗拉十多年。这条建议也影响了巴菲特：真正的好公司，几乎永远别卖。"},
        ],
    },
    {
        "id": "kostolany-dog",
        "name_zh": "安德烈·科斯托拉尼", "name_en": "André Kostolany", "era": "欧洲 · 布达佩斯投机家",
        "title_zh": "经济和股市，是主人和狗",
        "title_en": "The Economy and the Dog on a Leash",
        "body_zh": "科斯托拉尼有个流传最广的比喻：经济是主人，股市是狗。狗前后乱跑，但拴着绳，最终都会跟着主人回家。他从不因股市涨跌过度兴奋或恐慌，只盯着绳子另一头。他的忠告：有耐心的人才会赢。",
        "body_en": "André Kostolany left behind his most famous picture. The economy is the owner. The stock market is the dog. The dog runs ahead, then falls behind. But the leash connects them, and both arrive home together. Patience wins. Money alone does not.",
        "lines": [
            {"k": "narr", "who": "Narrator", "g": "N",
             "en": "A park in Europe. An old speculator is walking a big restless dog, and a young admirer is walking beside him.",
             "zh": "欧洲某公园。一个老投机家牵着一只躁动的大狗散步，身边跟着个仰慕他的年轻人。"},
            {"k": "dial", "who": "Young man", "g": "F2",
             "en": "Monsieur, the market ran up three percent this week, then fell back two. What should I do?",
             "zh": "先生，这周股市涨了百分之三，又跌回去两个点。我该怎么办？"},
            {"k": "dial", "who": "Kostolany", "g": "M",
             "en": "Look at my dog. He runs ahead of me, then falls behind. Up and down, back and forth.",
             "zh": "看我的狗。他一会儿冲到我前面，一会儿又落在后面。上蹿下跳，来回折腾。"},
            {"k": "dial", "who": "Young man", "g": "F2",
             "en": "But he always ends up where you end up?",
             "zh": "但最后他都跟着您走到同一个地方？"},
            {"k": "dial", "who": "Kostolany", "g": "M",
             "en": "Exactly. The economy is the owner. The market is the dog. Watch the far end of the leash, not the dog.",
             "zh": "正是。经济是主人，股市是狗。盯住绳子另一头的主人，别盯狗。"},
            {"k": "narr", "who": "Narrator", "g": "N",
             "en": "After seventy years in markets, his advice was simple. Patience wins. Money alone does not.",
             "zh": "在股海浮沉七十年后，他的忠告只有一句：有耐心的人才会赢，光有钱不行。"},
        ],
    },
    {
        "id": "livermore-lesson",
        "name_zh": "杰西·利弗莫尔", "name_en": "Jesse Livermore", "era": "1929 · 纽约投机之王",
        "title_zh": "他赚过一个亿，也没能留住一个亿",
        "title_en": "He Made a Hundred Million, and Could Not Keep It",
        "body_zh": "利弗莫尔是二十世纪初最有名的投机者。1929 年大崩盘前他大量做空，一周赚下一亿美元。但他一生大起大落，破过四次产。他留下的教训：华尔街没有新鲜事，人性不变，我总在不守纪律的地方跌倒。",
        "body_en": "Jesse Livermore was the most famous speculator of his age. In nineteen twenty-nine, right before the crash, he shorted the market and made one hundred million dollars in days. Yet he went bankrupt four times. His lesson. Wall Street has nothing new. Human nature never changes.",
        "lines": [
            {"k": "narr", "who": "Narrator", "g": "N",
             "en": "New York, late October, nineteen twenty-nine. The party is ending, and one man is ready.",
             "zh": "纽约，1929 年 10 月底。盛宴将散，而有一个人早已备好。"},
            {"k": "dial", "who": "Broker", "g": "M2",
             "en": "Jessie, everyone says stocks can only go up. Why are you shorting everything?",
             "zh": "杰西，所有人都说股票只会涨，你怎么在做空？"},
            {"k": "dial", "who": "Livermore", "g": "M",
             "en": "Because the tape told me weeks ago. The big money is not in the fluctuation. It is in waiting for it.",
             "zh": "因为盘面几个星期前就告诉我了。大钱不在波动里，在等待里。"},
            {"k": "narr", "who": "Narrator", "g": "N",
             "en": "The crash came. He made one hundred million dollars in days. It was his crown, and it was also his trap.",
             "zh": "崩盘来了。几天之内，他赚下一亿美元。那是他的王冠，也是他的陷阱。"},
            {"k": "dial", "who": "Livermore", "g": "M",
             "en": "I went bankrupt four times. Not because the market changed. Because I never changed.",
             "zh": "我破产过四次。不是因为市场变了，是因为我一直没变。"},
            {"k": "narr", "who": "Narrator", "g": "N",
             "en": "His hardest lesson was about himself. Wall Street has nothing new. Human nature never changes. I always fell in the same place, where I broke my own rules.",
             "zh": "他最痛的教训是关于他自己：华尔街没有新鲜事，人性不变。所以我总在同一个地方跌倒——不守纪律的地方。"},
        ],
    },
]


def load_corpus():
    """内置语料 + data/stories.json 追加的增量(可写脚本体, 也兼容老 body 体)。"""
    corpus = list(BUILTIN)
    try:
        with open(EXTRA, encoding="utf-8") as f:
            extra = json.load(f)
        if isinstance(extra, list):
            have = {s["id"] for s in corpus}
            for s in extra:
                if isinstance(s, dict) and s.get("id") and s["id"] not in have and (s.get("lines") or s.get("body_en")):
                    corpus.append(s)
                    have.add(s["id"])
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"  [story] data/stories.json 读取失败, 忽略: {type(e).__name__} {e}")
    return corpus


def _week_index(date_str):
    """自然周序号(0 起): 同一周共用同一篇, 换周换新 —— 故事更新频率一周多篇以内。"""
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
    except Exception:
        return 0
    return (d.isocalendar().year * 53 + d.isocalendar().week) % 100000


def slim(s):
    keys = ("id", "name_zh", "name_en", "era", "title_zh", "title_en",
            "body_zh", "body_en", "lines")
    return {k: s[k] for k in keys if k in s}


def assign(data):
    """给每期分配故事。
    - 没有 story 的期: 按"自然周轮换"挑一则(未用过的优先)
    - 已有 story 但还是老格式(无 lines)而语料里有脚本版: 自动迁移(指纹翻转→自动重配音)
    """
    eds = data.get("editions", [])
    corpus = load_corpus()
    used = {ed.get("story", {}).get("id") for ed in eds if ed.get("story")}
    picked = migrated = 0
    by_id = {s["id"]: s for s in corpus}
    for ed in eds:
        s0 = ed.get("story")
        if s0 and not s0.get("lines") and s0.get("id") in by_id and by_id[s0["id"]].get("lines"):
            ed["story"] = slim(by_id[s0["id"]])
            migrated += 1
            print(f"  {ed['date']}: 故事迁移为广播剧版 [{s0.get('name_zh')}]")
            continue
        if ed.get("story"):
            continue
        if not corpus:
            break
        wk = _week_index(ed["date"])
        idx = wk % len(corpus)
        s = corpus[idx]
        if s["id"] in used:                      # 该周故事恰好被更早期用过(语料耗尽时) → 找第一则没用过的
            rest = [c for c in corpus if c["id"] not in used]
            if not rest:
                rest = corpus
            s = rest[wk % len(rest)]
        ed["story"] = slim(s)
        used.add(s["id"])
        picked += 1
        print(f"  {ed['date']}: 分配故事 [{s['name_zh']}] {s['title_zh']}")
    if picked or migrated:
        print(f"  [story] 新分配 {picked} 期, 迁移 {migrated} 期, 语料共 {len(corpus)} 则")
    return picked + migrated


def main():
    data = json.load(open(os.path.join(ROOT, "data", "news.json"), encoding="utf-8"))
    n = assign(data)
    with open(os.path.join(ROOT, "data", "news.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"OK: 分配/迁移 {n} 期, 语料共 {len(load_corpus())} 则")


if __name__ == "__main__":
    main()
