# 数据字典

编码：UTF-8。JSON 版本：`1.0.0`。所有 ID 列表都引用 `poems.json` 中的 `id`。JSON `null` 表示未收集或未验证，不表示不存在。

## 主数据顶层

| 字段 | 含义 |
| --- | --- |
| `name` / `schemaVersion` | 资料库名称、结构版本 |
| `collectedOn` | 本次采集日期，不是诗歌创作日期 |
| `status` | 固定为 `research-corpus-not-production-edition` |
| `scope` | 资料范围和与参考书的关系 |
| `publicationReady` | `false`，尚未作为可发布定本验收 |
| `bookCatalogComplete` | `false`，未取得完整书目 |
| `book` | 参考书书目、ISBN、出版信息、章节数及边界说明 |
| `stats` | 条目、作者、候选、重复、待核、组诗和体裁统计 |
| `existingLibrary` | 本次去重对象的路径、总篇目数和文件 SHA-256 |
| `poems` | 诗歌记录数组 |

## 单首诗歌

| 字段 | 类型 / 含义 |
| --- | --- |
| `id` | `yizhu-` 加来源身份的 SHA-256 前 16 位；主要来源改变时须维护迁移关系 |
| `order` | 本次生成的展示序号，可能随增删、体裁校订变化，不宜用作业务主键 |
| `title` | 简体来源题名；去掉门类前缀和部分题注，保留组诗序号，不保证等于现代通行名 |
| `titleTraditional` | 该展示题名的 OpenCC 繁体转换 |
| `titleTraditionalOrigin` | 明确说明繁体展示题名为机器转换 |
| `sourceTitle` | 主要来源的原始题名，含旧字形、组名、题注或原有异常 |
| `author` / `authorTraditional` | 简体作者名及来源作者名；不据此裁定跨作者争议 |
| `dynasty` / `dynastyBasis` | 唐诗选目范围；不是已核实的单篇创作时代 |
| `aliases` | 来源题名、经匹配的非组诗请求题名，以及明确收集的别名；对照选本的组诗编号不自动当别名 |
| `group` | 有可解析组诗序号时为 `{title, position}`；`position` 为整数；否则 `null` |
| `paragraphs` | 简体诗文段落数组，保留来源分段；通常一段一联，不能假定一段一句 |
| `paragraphsTraditional` | 繁体段落；原底本或机器转换，见下项 |
| `traditionalTextOrigin` | `source` 或 `OpenCC-s2t-generated-not-edition` |
| `text` | `paragraphs` 以换行连接，供检索与导出 |
| `sentences` | 依逗号、句号、问号、分号等拆出的诗句，保留标点；非人工韵律分句 |
| `textSha256` | 简体 `text` 的 UTF-8 SHA-256，用于检查文本变更；不是去重用的归一文本哈希 |
| `form` | 字数、句数及初步体裁，详见下一节 |
| `selection` | 选目依据、请求题名、书目确认状态及校订说明 |
| `sourceRefs` | 主要文本来源引用；其他版本的来源在 `witnesses[].sourceRef` 中 |
| `sourceRecordIds` | 本作品关联的原始仓库记录 UUID，可包含合并的多个版本 |
| `sourceAnnotations` | 从底本文字中分离的题注/脚注及补字记录；不等于给 App 用户看的简注 |
| `witnesses` | 对照版本全文、来源、相似程度和组诗编号差异 |
| `variants` | 对照版本的字符差异或来源明确报告的异文 |
| `existingLibraryMatches` | 与正式 App 诗歌的匹配关系 |
| `collectionStatus` | 是否重复或须先处理疑点，见状态表 |
| `review` | 校订状态及全部已发现的问题标签；没有标签不等于人工审定 |
| `enrichment` | 译文、字词注、赏析、创作年地、拼音的预留槽位，本次均未采集 |

## 句式与体裁 `form`

| 字段 | 含义 |
| --- | --- |
| `sentenceCount` | 分句数量 |
| `characterCounts` | 每一分句的汉字数，排除标点；未知字/私用区字符需另外校核 |
| `uniformLineLength` | 每句等长时为该字数，否则 `null` |
| `characterCount` | 各句汉字数总和 |
| `metricalShape` | 基于句数、字数的结构初分，不证明平仄和押韵合律 |
| `proposedGenre` | 优先参考明确来源分类，否则使用结构初分 |
| `status` | `shape-inferred`、`source-yuefu-heading` 或 `reference-classification` |
| `basis` | 推断说明或分类来源 |
| `prosodyVerified` | 当前均为 `false` |

“五言律诗”等标签若来源是 `shape-inferred`，只表示八句、每句五字的初筛结果。正式体裁字段应在定本阶段建立，不要不加核验地映射到生产端固定版式。

## 选目及收录状态

`selection.basis`：`independent-curation` 为独立选目，`book-public-preview` 为公开试读确认。`bookMembership` 只有 `confirmed` / `unconfirmed`，**未确认并不表示确定未收录**。

| `collectionStatus` | 解释 |
| --- | --- |
| `new-candidate` | 当前 App 未匹配到，且未触发指定的阻断性疑点；仍待内容校订 |
| `review-before-inclusion` | 有明确题名、归属、版本、字形或正文结构疑点，先保留资料，暂缓导入 |
| `already-in-app` | 与正式诗库内容相同或高度相近，应按异文/别名处理，而非新增一首 |

`review.status` 当前固定为 `collected-needs-editorial-review`。多个问题标签可同时出现：

| `review.issues` 标签 | 含义 |
| --- | --- |
| `title-variant-review` | 选目题名与底本存在需核对的差异 |
| `attribution-or-edition-review` | 作者署名或版本关系需专项确认 |
| `source-missing-character` | 发现缺字、占位符等 |
| `source-editorial-markers` | 正文含无法作为普通诗字处理的编辑标记、私用区字形等 |
| `embedded-annotations-separated` | 底本含注释，已分离保存；这是处理记录，不必然表示正文有误 |
| `editorially-supplied-reading` | `[欸]` 等编辑补字已保留字、移走外层标记 |
| `unclosed-source-annotation` | 来源括号未闭合，需检查自动分离范围 |
| `possible-preface-or-long-paragraph` | 可能含序言或不适合自动处理的长段 |
| `mixed-length-verse-review` | 句长不一致；可能是正常杂言，也可能是缺字，需结合原诗判断 |
| `reference-genre-shape-conflict` | 来源体裁与实际分句结构冲突 |
| `witness-cycle-numbering-differs` | 对照选本中的编号与主要底本不同，不自动替换 |
| `existing-library-author-differs` | 与 App 同诗的署名不同或作者姓名写法不同 |

## 来源、见证与异文

`sourceRef` 至少有 `sourceId`、`url`、`accessedOn`。GitHub 底本另存 `repositoryCommit`、`recordId` 和零基 `recordIndex`；《千家诗》见证另存卷类 `section`、条目索引和 `subchapter`；公开试读存 `chapterId`。

`witnesses[].paragraphs` 保存该对照来源的诗文，不覆盖主要文本。`comparison` 为 `normalized-text-agrees` 或 `text-variant`；`similarity` 是归一文本的序列相似度，**不是诗文正确率**。组诗序号不一致时增加 `numberingStatus: differs-from-base-cycle`。

自动异文比较会先转简体、去标点并折叠少量异体字。`differences[].baseOffset`、`witnessOffset` 是此归一汉字串的零基偏移，不能直接用于界面高亮原文。每项差异保留 `kind`、主要文本 `base`、对照文本 `witness`；原始版本均可回查。

`variants[].reportedVariants` 是来源页面明确说明的异文，不一定有对应的完整第二文本。机器识别出的差异只能称为“版本差异/疑点”，不能自动判定哪一方是错字。

## 作者与组诗

`authors.json`：每位作者含稳定名称 ID、`poemIds`、数量统计、底本小传和出处。小传标记为 `historical-biography-not-modern-fact-check`；`birthYear`、`deathYear` 为 `null`，避免把传统记载未经考证地作为精确人物数据。

`groups.json`：以作者 + 底本组名建索引，保存 `collectedPositions` 和对应 ID。`completeness` 固定 `not-asserted`。同一组在乐府卷、作者卷、后世选本中可能异名、异序，校订前不自动建立“全组已齐”的结论。

## 简单读取示例

在项目根目录运行：

```python
import json
from pathlib import Path

root = Path('data/expansion/tang-yizhu')
dataset = json.loads((root / 'poems.json').read_text())
candidates = [
    poem for poem in dataset['poems']
    if poem['collectionStatus'] == 'new-candidate'
]
li_bai = [poem for poem in candidates if poem['author'] == '李白']
for poem in li_bai[:5]:
    print(poem['id'], poem['title'], poem['sentences'][0])
```

该例只筛出候选，不会导入或改动正式诗库。
