# 字段与状态

## 目录 catalog.json

| 字段 | 含义 |
| --- | --- |
| `id` | 稳定的目录条目 ID，例如 `xieying-track-036` |
| `order` | 用户抄录顺序，1–297，包含序言 |
| `rawInput` | 完整原始抄录行，包含末尾数字和年月噪声 |
| `title` / `originalTitleOnly` | 去噪后的目录题名；原抄录疑似错字也保留 |
| `section` | 最近出现的【栏目】标记 |
| `sectionOccurrence` | 此栏目是第几次出现在抄录中，防止不同部分混在一起 |
| `albumPage` | 按专辑每页 30 条计算的页号，不等于纸书页码 |
| `kind` | `preface` 或 `poem-entry` |
| `status` | 见下方状态表 |
| `candidateIds` | 关联 `poems.json` 的候选作品 ID 列表 |
| `selectedPoemIds` | 暂定对应或用户确认选中的作品 ID，须结合 `status`；用户可以明确选择多首，按确认顺序保存。尚未确认的多候选为空 |
| `selectionBasis` | `unique-among-collected-candidates-not-user-confirmed` 为暂定对应，`explicit-user-confirmation` 为用户确认，`awaiting-user-choice` 为待确认 |
| `userConfirmation` | 已确认项的批次、日期、确认范围、说明及本地确认记录来源；仅确认作品身份和选篇，不等于逐字审校 |
| `filteredOutCandidates` | 与所标绝句/律诗句式不符的检索结果摘要；其 `sourceRecordIds` 指向原始来源子集，未冒充已选候选 |
| `sectionConflict` | 全部候选都与栏目句式不符；如明确为排律则有解释 |
| `matchingNote` / `matchingEvidenceUrls` | 异题、简称、疑字或归属线索及证据 |
| `titleReview` | 来源题名与用户所见纸书题名分开保存；`reportedBookTitle` 是用户报告，`bookPageIndependentlyChecked` 表示是否独立核对纸书页面；`adoptedTitle` 和 `titleConfirmation` 保存最终采用题名及用户确认，不等于独立核验纸书页面 |
| `sourceRefs` | 用户抄录行号、专辑地址、已核实的前 100 条公开 track ID |
| `sourceUrl` | 有真实 track ID 时为单条音频页面，否则为专辑页面 |

| 状态 | 含义 |
| --- | --- |
| `excluded-preface` | 序言仅保留目录项，不采集现代文章正文 |
| `matched-single-candidate` | 当前来源和规则下唯一对应；依然需要正式定本 |
| `user-confirmed-selection` | 用户明确确认作者和选篇，可包含多首；原候选列表保留用于追溯，未选候选不计为入选 |
| `needs-confirmation` | 多个候选或明确疑点，未选择 |
| `source-needed` | 没找到任何候选，保留空缺；当前为 0 条 |

## 作品 poems.json

每条对应一份来源作品身份，同一首跨作者异署可能保留两份记录；同作者同篇版本可保留为见证。

| 字段 | 含义 |
| --- | --- |
| `id` | 由来源身份生成的稳定作品 ID，不等于目录序号 |
| `title` / `sourceTitle` / `aliases` | 来源清理题名、原始题名及异题；目录题名始终另存 |
| `author` / `authorTraditional` | 来源署名；如上官昭容、章怀太子暂保留原称谓 |
| `dynasty` / `dynastyBasis` | 来源范围及已核查的时代例外；跨唐五代作者未逐人逐篇定年 |
| `paragraphs` / `text` / `sentences` | 简体正文段、换行拼接全文、按来源标点拆出的句子 |
| `paragraphsTraditional` / `traditionalTextOrigin` | 来源繁体，或明确标为机器转换的繁体 |
| `textSha256` | 当前正文指纹，便于后续改动与去重 |
| `group` | 数字编号组诗的来源组名和篇次，不能据此宣称全组收齐 |
| `form` | 分句数、字数、句式和体裁初分；不是格律审校结论 |
| `sourceRecordIds` / `sourceRefs` | 全唐诗 UUID、出处 URL、固定版本、文件内索引、采集日期 |
| `sourceAnnotations` | 从原文分离的括号校记和补字标记；原始数据另存 |
| `witnesses` / `variants` | 其他来源的完整古诗见证和规范化对比差异 |
| `editionDecision` | 采用某个补全或通行文本时的理由及出处，不静默改字 |
| `catalogEntryIds` | 该作品被哪些目录项列为候选 |
| `provisionallyMatchedEntryIds` | 哪些目录项暂定对应此作，仅对应 `matched-single-candidate` 状态 |
| `userConfirmedEntryIds` | 哪些目录项由用户明确选中此作，与暂定对应分开记录 |
| `selection.bookMembership` | 仅有独立纸书公开试读证据的 4 首可为 `confirmed`；其他音频候选不等于纸书确认 |
| `relatedResearchIds` | 与父目录此前独立收集资料的对应关系 |
| `existingLibraryMatches` | 与当前 App 的相同文本/近似同作比对，含相似度及作者是否一致 |
| `review` | 缺字、混合句式、异署等审校提示；自动检查不保证找出全部问题 |
| `enrichment` | 译注、赏析、拼音、创作时间地点等未收集项，保持空值 |

`matched-poems.json` 导出暂定对应与用户已确认的目录条目及完整作品，按条目状态区分，仍标记 `publicationReady: false`。`poems` 数组可含多首，例如《从军行》第四、第五首。`pending.json` 仅含尚待确认或未找到来源的条目，含作者、首句、候选 ID。

`sources/user-confirmations.json` 是用户确认输入，按批次保存每条目录的稳定 ID、预期题名与栏目、作者、选中的作品 ID 和原确认语意。脚本校验目录身份、作者以及作品是否属于原候选；无效引用会报错，不静默替换。

`authors.json` 的小传是底本古文，不是新写的人物研究；生卒年置空。作者索引通过 `provisionallyMatchedPoemIds` 与 `userConfirmedPoemIds` 分别列出暂定和已确认作品。`groups.json` 目前只索引数字篇次，春夏秋冬等命名篇章仍通过 `catalogEntryIds` 关联；`userConfirmedPoemIds` 表示已确认成员。仅当用户明确收全组且脚本核对来源组题数量与所选篇次连续齐全时，`wholeGroupConfirmed` 才为 `true`，目前为岑参《山房春事二首》。节选的《盆池》《南园》等仍为 `false`，不把个别篇目确认扩大成整组确认。

统计区分 `userConfirmedEntryCount`（用户确认的目录条目）、`userConfirmedPoemCount`（用户确认的不同诗作）、`selectedEntryCount`（已确认和暂定对应目录合计）与 `selectedUniquePoemCount`（对应的不同诗作合计），不能把组诗目录条目当成单首计数。

`audit.json.titleReviews` 单列题名考证记录；作品身份已确定但纸书题名尚未独立核对的情况，不重新计入 `pending.json` 的选篇疑问。
