# 校订与待核说明

选目已完成；文本是可追溯的整理稿，尚未形成出版定本。

## 已明确处理的 7 项

| 作者 / 篇目 | 处理与依据 |
| --- | --- |
| 白居易《遗爱寺》 | 据对照页校正日/石；谿/溪属字形差别，保留底本，其余不变。 [来源](https://m.gushiwen.cn/shiwenv_981a524d54a5.aspx) |
| 李商隐《流莺》 | 底本仅六句，采用对照页八句全文，补回末联；漂/飘、度/渡及标点按所采页面，原六句另存。 [来源](https://www.gushiwen.cn/shiwenv_5c6a6e4c7cb2.aspx) |
| 李贺《马诗二十三首·其五》 | 据对照页校正首句山/沙；其余保留底本。 [来源](https://www.gushiwen.cn/shiwenv_55174e6ebe20.aspx) |
| 刘禹锡《元和十年自朗州至京戏赠看花诸君子》 | 展示题名据对照页作十年；原底本十一年题名继续保留，可按两种题名检索。 [来源](https://www.gushiwen.cn/shiwenv_8749583f7c50.aspx) |
| 刘长卿《送李判官之润州行营》 | 据对照页校正地名；底本归客与对照行客作为版本差异记录，暂留归客。 [来源](https://www.gushiwen.cn/gushiwen_fb20349512.aspx) |
| 杜甫《狂夫》 | 按对照页删除误断首句的逗号；其余字形与静/净异文沿底本，留待统一定本。 [来源](https://www.gushiwen.cn/mingju/juv_bbb33b4b9139.aspx) |
| 杜甫《羌村·其三》 | 据对照页校正块/愧；苦辞/莫辞、兵革/兵戈等差别未据此连带改动。 [来源](https://m.gushiwen.cn/shiwenv_5bc5500f6e92.aspx) |

校订仅作用于第三卷输出，上游候选库和前两卷均未改写。原文和原始哈希留在 `sourceReading`。

## 需要继续定本的具体项目

| 作者 / 篇目 | 说明 |
| --- | --- |
| 刘禹锡《酬乐天咏老见示》 | 底本作人谁不愿老、多炙、微霞；对照页作人谁不顾老、多灸、为霞。微霞亦见其他传本，暂不凭熟悉程度判错，选定统一定本时再处理。 [依据](https://www.gushiwen.cn/shiwenv.aspx?id=e07317133df0) |
| 李白《三五七言（秋风词）》 | 采用所存底本的三言、五言、七言六句正文；不拼入其他流传文本的追加段落。 |
| 王贞白《白鹿洞二首·其一》 | 作者跨唐五代；本诗按常见唐诗选目收录，具体写作年份尚未核定。 [依据](https://m.gushiwen.cn/shiwenv_0564d7f8b06b.aspx) |
| 韦庄《秦妇吟》 | 保留完整来源转录；原记录的引号跨段及若干罕见字需要以可靠印本逐句校勘，尚不可直接用于TTS或出版。 |
| 太宗皇帝《赠萧瑀（赐萧瑀）》 | 底本署太宗皇帝，阅读显示采用李世民（唐太宗）；赠萧瑀、赐萧瑀为同篇异题。 [依据](https://www.gushiwen.cn/mingju_719.aspx) |

## 自动检查继承的标记

杂言乐府天然可能长短句并存；`mixed-length-verse-review` 是检查入口，不能据此判作残诗。

| 作者 / 篇目 | 标记 |
| --- | --- |
| 白居易《杜陵叟》 | mixed-length-verse-review |
| 白居易《新丰折臂翁》 | mixed-length-verse-review |
| 李白《北风行》 | mixed-length-verse-review |
| 李白《夜宿山寺》 | attribution-or-edition-review |
| 元稹《田家词》 | mixed-length-verse-review |
| 李白《三五七言（秋风词）》 | mixed-length-verse-review |
| 刘禹锡《元和十年自朗州至京戏赠看花诸君子》 | title-variant-review |
| 张籍《牧童词》 | mixed-length-verse-review |
| 李商隐《赠荷花》 | embedded-annotations-separated、editorially-supplied-reading |
| 李贺《苏小小墓》 | mixed-length-verse-review |
| 李贺《苦昼短》 | mixed-length-verse-review |
| 杜甫《狂夫》 | mixed-length-verse-review |
| 白居易《上阳白发人》 | mixed-length-verse-review |
| 白居易《井底引银缾》 | mixed-length-verse-review |
| 白居易《母别子》 | mixed-length-verse-review |
| 白居易《红线毯》 | mixed-length-verse-review |
| 韦庄《秦妇吟》 | embedded-annotations-separated |

## 发布前的文本工作

- 选择统一的可靠校注本，对 300 首逐句校读；有争议处保留异文、出处和决定。
- 核对组诗篇次与异题；本次按来源中的单首身份计数，没有把整组算作一首。
- 对跨唐五代作者核单篇系年，检查来源署名与通行作者名的对应。
- 体裁目前是句式初分与底本乐府门类，未逐首验平仄和用韵。
- 个别罕见字、古字、长诗引号和来源标点尚需整理，尤其《秦妇吟》；未据猜测改字。
- 现代译文、词注、创作背景、拼音和朗读尚未新增；不把收录理由冒充校注或参考书原评。

本清单不妨碍选目审阅，但 `publicationReady` 在完成审校前保持 `false`。
