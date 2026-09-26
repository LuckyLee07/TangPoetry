# 唐诗画笺

手机竖屏唐诗读本：**320 首全文、320 幅专属插画**，按体裁分卷，字号按诗体和篇幅适配，正文放在插画下方留白内。每首提供页面简意和完整译意，字词解释、异文与题序分开阅读；纸色、字号与简注可调，当前不显示拼音。当前版本 **0.5.0**，同时包含可直接预览的网页和 SwiftUI iPhone 工程。

## 网页运行

需要 Python 3 和 Node.js 18 或更新版本。交付数据与 WebP 插图入库，无需安装 npm 依赖。

```sh
npm start
```

打开 http://127.0.0.1:8765。请使用 HTTP 服务，直接双击 HTML 无法加载 JSON。

```sh
npm test
```

测试入口包含网页逻辑、注释呈现、内容构建、原生资源打包与阅读数据校验。检查覆盖稳定 ID、收藏迁移、搜索、设置、诗体排版、简注开关、阅读范围、段落续读、每日一首、分享图文字换行，以及原诗、题序、异文、编辑释义与图片的关联。最终执行结果记录在 [PROGRESS.md](PROGRESS.md)，测试能力不等同于真机视觉验收。

## iPhone 运行

要求 macOS、完整 Xcode（最低部署目标 iOS 17）和 XcodeGen。工程无第三方 Swift 依赖。

```sh
python3 scripts/prepare_ios.py
xcodegen generate --spec ios/project.yml
open ios/TangPoetry.xcodeproj
```

在 Xcode 选择 **TangPoetry** scheme 和 iPhone 模拟器，点击运行。真机运行需要在 Signing & Capabilities 中选择自己的开发团队并配置有效签名。本机本轮签名检查返回 `0 valid identities found`，尚未完成真机安装与验收。iPhone 仅支持竖屏，未针对 iPad 设计。

命令行验证（把 destination 改成本机已安装的模拟器）：

```sh
DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer \
xcodebuild -project ios/TangPoetry.xcodeproj -scheme TangPoetry \
  -destination 'platform=iOS Simulator,name=iPhone 17,OS=26.2' \
  -derivedDataPath /tmp/tangpoetry-derived -parallel-testing-enabled NO test
```

`prepare_ios.py` 使用 macOS 自带 `sips`，将网页插图转成原生 JPEG 资源，并打包全部诗文。当前生成目录实际包含 **641 份有效图片**：320 首的诗页大图与缩略图，加上独立保留的封面。已移除生成目录中未被引用的 13 张旧图，原始插画文件保留；JPEG 导出质量仍为 85。

打包先在暂存目录中生成并核对引用、图片哈希，再整体替换；失败时保留或恢复上一份完整内容。转换缓存按源文件字节与参数判断，支持可重复的增量构建。生成的 `ios/Content/` 不入库，首次打开工程前必须生成；应用安装后完全离线运行。内容目录使用 `Content`，避免与系统保留的 bundle 目录名称冲突。

```sh
python3 scripts/prepare_ios.py --check
python3 scripts/audit_ios_resources.py --output data/qa/ios-resource-audit.json
```

原生图片在专用队列异步读取、解码，并按展示尺寸降采样，最多同时执行两个解码任务；缓存同时限制为 32 MiB 解码字节与 24 项，收到内存警告后清空。缓存预算不代表 App 总内存上限。AppIcon 已生成并接入 Asset Catalog，以墨绿、宣纸、远山和朱印构成原创几何图形，源码为 `scripts/generate_app_icon.swift`。资源体积、失败恢复、图标与图片加载的细节见 [RELEASE_PREPARATION.md](RELEASE_PREPARATION.md)。

## v0.5.0 阅读体验

- **按诗集连续阅读**：目录支持体裁、主题、作者索引、搜索及收藏/精选组合筛选。打开结果后，左右翻页与上一首、下一首均在结果集中继续；底部显示当前范围和页码，可点“回全库”保留当前诗。取消收藏会更新收藏序列，结果集为空时回到全库。
- **长诗续读**：按稳定诗 ID 保存阅读到的诗句，返回该诗或重开后恢复。网页还保留句内比例，调整字号后尽量留在原段落；保存做节流处理。既有收藏、设置及上一首阅读位置继续兼容，各端记录保存在各自设备中。
- **每日一首**：封面显示每日推荐，按设备本地日期从完整 320 首中确定，当天结果稳定，不随目录排序或筛选变化。点击进入全库中的对应诗页，无推送通知。
- **保存或分享诗笺**：从阅读页的 Aa 设置进入“保存或分享当前诗笺”，先预览包含插画、题名、作者和完整正文的 PNG。长诗生成可纵向查看的长图，不截断诗句；iOS 调用系统分享面板，网页支持下载，浏览器支持文件分享时同时提供分享按钮。
- **画境微动**：设置中提供默认关闭的试点开关，仅《春晓》《江雪》《竹里馆》有轻微落花、雪点或竹叶。开启后只对当前诗页生效，弹层打开时暂停。两端遵循系统“减少动态效果”；原生在低电量模式和进入后台时暂停，网页在页面隐藏时暂停。

轻点插画或阅读空白可以收起、恢复工具栏；按钮点击、文字选择与纵向阅读滚动各自保持原行为。新功能沿用已经确认的诗文位置、无简注居中规则和 58% 注释弹层，不改变诗页正文排版。

## 内容结构与编辑入口

```text
归档来源 data/sources/ + 唐诗三百首.json
  + 显式校勘与补篇 data/content-corrections.json
  → scripts/build_final_source.py + scripts/split_final_poems.py
  → data/final/tang_poems_final.json + poems/*.json
  + 简意、完整译意、编辑词解 data/commentary/001-160.json、161-320.json
  + 展示题名、图片、版式、精选 data/editorial.json
  + 原有插画策划 data/visuals.json
  + 逐首插画 data/illustrations/plan.json
  → scripts/build_reader.py
  → data/reader/catalog.json + poems/*.json + assets/optimized/*.webp
  → scripts/prepare_ios.py → ios/Content/
```

`data/commentary/` 是页面简意和完整译意的编辑入口：`summary` 用于诗页简注，`interpretation` 按段解释全诗，`glossary` 补充必要词解。两份文件按原书序分工，使用稳定 `tang-…` ID 合并，必须覆盖全库且不可重复。释义依据原诗撰写，标记为 `editorial-draft`，与来源原注分别保留。

`data/editorial.json` 管理展示题名、别名、主题、图片、单诗版式、拼音覆盖和精选状态；历史 `note` 留作编辑记录，当前客户端简意以 `data/commentary/` 为准。不要按标题关联收藏或插图，同名作品各自使用稳定 ID。

注释弹层按内容分别呈现完整诗意、字词解释、异文和题序。页面简意不再作为展开后的重复段落；来源中换行拆开的词解会重新连接，重复词解和异文说明分别整理。原题与简繁来源仍可追溯，长题的展示简写不会改写归档题名。

`data/note-corrections.json` 保存 10 项来源词解的展示修订及依据，包括缺字、人物关系、地名和误带入的下一首题名。构建时严格匹配原注再应用修订；归档原注保留，内容变化时匹配失败会中止构建，避免修订悄然失效。

当前规范源已补入本地选本原书序 **043《长干行》、134《送李中丞归汉阳别业》、278 顾况《宫词》**，原有 317 首的 ID 与原书序保持不变。6 首序文独立保存，18 首末尾的“又作”说明移入异文；另有 22 处正文修订，以及作者、原题共 2 处元数据修订。具体字句、依据与处理规则以 `data/content-corrections.json` 为准，归档原始文件不覆盖。

规范源中仍有 **91 首没有来源原注**，这与产品是否有简意是两个指标：320 首均有编辑简意和完整译意。`data/reader/build-report.json` 分别记录 `sourceNotesMissing`、`notesMissing` 与 `interpretationsMissing`，不能再用来源缺注数量判断页面是否空缺。

## 重建与源校验

修改编辑释义、版式或图片后执行：

```sh
npm run build:data
npm test
python3 scripts/prepare_ios.py
```

重建图片需要 `cwebp`（如 Homebrew 的 `webp` 包）。重建更上游的规范源时，先在虚拟环境安装 `requirements.txt`，再依次执行：

```sh
python3 scripts/build_final_source.py
python3 scripts/split_final_poems.py
python3 scripts/validate_final_source.py
npm run build:data
```

`validate_final_source.py` 检查 320 首连续书序、原有 317 首身份不变、简繁正文及拆分文件一致，并反向重组题序、正文与异文，确认归档内容未丢失。对 **213 首固定体裁**另外检查每句汉字数和句数，结果写入 `data/final/content_audit.json`；古诗和乐府不强套绝句、律诗规则。结构验证不等同于逐字的版本学定本。历史 `data/poems.json` 不再作为客户端入口。

## 插画与单诗版式

现行 320 幅诗页由 **13 张继续使用的旧图、297 张 v0.3 补图、7 张 v0.3.2 构图刷新图、3 张 v0.4.0 补篇图**组成。原有源文件保留，本轮没有替换旧 317 幅诗页图。客户端使用压缩大图和缩略图，原尺寸 PNG 留作后续编辑。

| 范围 | 原图 | 提示词与回执 |
| --- | --- | --- |
| v0.3 补齐的 297 首 | `assets/poem-art/` | `data/illustrations/plan.json`、`receipts-*.json`、`audit.json` |
| v0.3.2 刷新的 7 首 | `assets/poem-art-refresh/` | `data/illustrations/refresh-a.json`、`refresh-b.json`、`refresh-audit.json` |
| v0.4.0 补入的 3 首 | `assets/poem-art-additions/` | `data/illustrations/edition-additions.json` |

```sh
python3 scripts/audit_illustrations.py --require-complete
```

该命令只审计 v0.3 的 297 张补图，不能用它代表后来 7 张刷新图和 3 张补篇图。后两批分别保留独立回执，包含生成提示词、来源、接受状态和文件校验信息；客户端最终接入数量由阅读数据校验与 `build-report.json` 核对。

单诗正文起点使用 `data/editorial.json` 的 `textStart`。客户端把它限制在该诗体默认比例至 70% 之间，再应用全局位置规则。v0.4.0 针对 **24 首图文交界个例**补充起点配置，另保留《静夜思》既有 52% 配置；不因此移动其余诗页。书序 108 和 208 采用较短展示题，完整原题留在注释弹层。当前诗页统一采用全页插画，不再使用旧画窗配置。

## 自适应阅读与排版检查

五言绝句以 26px、七言绝句以 24px 为基准；五律与七律以 22px、21px 为基准。古诗、乐府根据实际分句长度与行数选择排版。用户字号和 iOS 动态字体参与计算，并保留可读字号下限。空间不足时在下方阅读区纵向滚动，不为塞满一屏而继续把诗文向上推；简注随正文滚动。

v0.5.0 继续保留已经确认的全局布局：有简注时沿用 v0.3.4 的正文和简注位置；无简注或关闭简注时，根据剩余留白向下居中，最多下移 60pt（网页为 60px）。字体拟合仍沿用 v0.3.2 的阅读高度，因此位置微调不改变字号与行距。注释弹层约占可用高度的 **58%**，内容内部滚动，关闭按钮保持可见。

默认正文起点按阅读区高度的 45%（绝句）或 39%（律诗、中等篇幅与长诗）减去 70pt 计算，网页使用相同比例和 70px；逐图配置替换基础比例，极小屏保留最小起点。简注相对 v0.3.2 累计下移 25pt，正常页面与诗文的间距累计增加 70pt。网页与原生均使用等宽汉字单元和独立句尾标点，正文不增加纸色背景或渐变。iOS 插画铺满屏幕并延伸至安全区，文字和操作工具保留在安全阅读区域。

默认阅读与目录按七类排列：**五言绝句 29 首 → 七言绝句 51 首 → 五言律诗 80 首 → 七言律诗 53 首 → 五言古诗 35 首 → 七言古诗 28 首 → 乐府 44 首**。同组保留原书序，界面页码采用当前阅读顺序。

HTTP 服务启动后，打开 http://127.0.0.1:8765/tools/layout-review.html 进行图文检查。检查页与产品共用 `reader-renderer.js` 的 HTML、字体、样式和排版函数，每组缩览 16 首，可切换字号与简注。全库矩阵覆盖 **4 个尺寸 × 4 个字号 × 2 种简注状态 × 320 首 = 10,240 组实际 DOM 排版**，检查横向溢出、标题和句尾标点越界、阅读区高度以及首屏是否能见诗句。长诗需要滚动属于正常状态；图文是否相互遮挡仍须结合人工缩览和重点诗页实看，不能只依据数字验收。

## 当前边界

- 全库编辑释义与 20 首精选均保留草稿审核状态，不视为出版级终审。普通诗的主题、原始拼音和部分来源词解仍需后续校对；拼音暂不显示。
- 内容校勘保留依据和原文回溯；不同选本的合法异文不会仅因字形或版本不同而统一替换。
- 插画是否专属与内容是否精选分别管理，补篇和补图不会扩大原有 20 首精选范围。画面检查不等于对服饰、建筑、器物的学术考证。
- 网页收藏与原生收藏各自保存在本机；网页兼容旧标题收藏迁移，暂不提供账号或跨端同步。
- 三首微动为默认关闭的试点，并未扩展到全库；当前没有朗读、推送通知、账号或跨端同步。
- AppIcon 与离线资源准备已完成，但本机尚无有效签名身份，真机安装、实际流畅度与峰值内存验收仍待完成；最大辅助字号已在模拟器抽查封面、目录与诗页，完整字号矩阵、VoiceOver 实际朗读和 App Store 素材仍待完成。当前版本尚未提交或上架。

v0.4.0 的历史验收包括全库 10,240 组实际 DOM 排版检查、全库缩览与重点模拟器体验检查。v0.5.0 的测试、资源和交互验收以 [PROGRESS.md](PROGRESS.md) 的本轮记录为准，不将模拟器或自动化检查等同于真机、辅助功能终验。产品方向见 [PRODUCT_DEVELOPMENT.md](PRODUCT_DEVELOPMENT.md)。
