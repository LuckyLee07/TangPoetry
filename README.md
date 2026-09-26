# 唐诗画笺

手机竖屏唐诗读本：317 首全文与 317 幅专属插画，按体裁分卷，字号按诗体和篇幅适配，正文放在插画下方留白内，纸色、字号与简注可调；当前阅读界面不显示拼音。当前版本 **0.3.3**，同时包含可直接预览的网页和 SwiftUI iPhone 工程。

## 网页运行

需要 Python 3 和 Node.js 18 或更新版本。交付数据与 WebP 插图已入库，无需安装 npm 依赖。

```sh
npm start
```

打开 http://127.0.0.1:8765。请使用 HTTP 服务，直接双击 HTML 无法加载 JSON。

```sh
npm test
```

测试覆盖收藏迁移、同名诗独立收藏、异常设置恢复、题名别名/诗句/繁体搜索、加载重试与缓存，以及绝句、律诗、长诗的留白区排版；数据校验遍历全部诗文、体裁顺序、版式配置及图片引用。

## iPhone 运行

要求 macOS、完整 Xcode（最低部署目标 iOS 17）和 XcodeGen。工程无第三方 Swift 依赖。

```sh
python3 scripts/prepare_ios.py
xcodegen generate --spec ios/project.yml
open ios/TangPoetry.xcodeproj
```

在 Xcode 选择 **TangPoetry** scheme 和 iPhone 模拟器，点击运行。真机运行需要在 Signing & Capabilities 中选择自己的开发团队。iPhone 仅支持竖屏，未针对 iPad 设计。

命令行验证（把 destination 改成本机已安装的模拟器）：

```sh
DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer \
xcodebuild -project ios/TangPoetry.xcodeproj -scheme TangPoetry \
  -destination 'platform=iOS Simulator,name=iPhone 17,OS=26.2' \
  -derivedDataPath /tmp/tangpoetry-derived -parallel-testing-enabled NO test
```

`prepare_ios.py` 使用 macOS 自带 `sips`，将网页插图转成原生 JPEG 资源，并打包全部诗文。当前资源包含 634 份诗页大图与缩略图，以及独立保留的旧封面图，共 635 份图片。生成的 `ios/Content/` 不入库，首次打开工程前必须生成；应用安装后完全离线运行。内容目录使用 `Content`，避免与系统保留的 bundle 目录名称冲突。

## 编辑与重建

```text
归档内容 data/final/tang_poems_final.json
  + 编辑覆盖 data/editorial.json
  + 原有插画策划 data/visuals.json
  + 逐首插画与提示词 data/illustrations/plan.json
  + 构图刷新 assets/poem-art-refresh/（编辑配置指定）
  → scripts/build_reader.py
  → data/reader/catalog.json + poems/*.json + assets/optimized/*.webp
  → scripts/prepare_ios.py → ios/Content/
```

修改短诗意、展示题名、主题、拼音或精选状态，编辑 `data/editorial.json`；使用稳定 `tang-…` ID，不按标题关联收藏和插图。新增原图放入 `assets/featured/`，然后执行：

```sh
npm run build:data
npm test
python3 scripts/prepare_ios.py
```

重建图片需要 `cwebp`（如 Homebrew 的 `webp` 包）。重建更上游的归档源时，先在虚拟环境安装 `requirements.txt`，依次执行 `scripts/build_final_source.py`、`scripts/split_final_poems.py`，最后再构建阅读数据。历史 `data/poems.json` 不再作为客户端入口。

v0.3 已为 297 首补齐专属插画，原图放在 `assets/poem-art/`。v0.3.2 又将 7 张不适合下方留白排版的旧构图逐首重新生成，v2 原图放在 `assets/poem-art-refresh/`，提示词与来源回执在 `data/illustrations/refresh-a.json`、`refresh-b.json`。现行 317 幅诗页由 13 张继续使用的旧图、297 张补图和 7 张 v2 图组成；原有 20 张源文件仍保留，7 首的当前图片映射已改用 v2。客户端仅下载压缩后的大图和缩略图，原尺寸 PNG 用于保留和后续编辑。

```sh
python3 scripts/audit_illustrations.py --require-complete
```

该命令只检查 v0.3 的 297 张新增原图，覆盖完整性、竖幅尺寸、独立文件内容与视觉检查记录，不包含本轮 7 张 v2 图。7 张刷新图的独立验收记录由 `data/illustrations/refresh-audit.json` 保存，包含尺寸、SHA256、路径唯一性和接受状态，本轮 7 张均已通过。客户端实际接入数量见 `data/reader/build-report.json`。

单诗的构图适配也放在 `data/editorial.json`：`textStart` 表示正文起点的基础比例，按诗体默认值至 70% 的范围约束后，再应用固定上移量。只有配置过的字段才会写入目录。此前 7 首的 `artworkMode: "window"` 和裁切位置配置已删除，当前诗页统一采用全页插画。

## 自适应阅读

五言绝句以 26px、七言绝句以 24px 为基准；五律与七律以 22px、21px 为基准。古诗、乐府按实际分句长度与行数选择排版，不仅依赖分类标签。正文在 v0.3.2 的位置基础上再上移 20：原生按安全阅读区高度的 45%（绝句）、39%（律诗、中等篇幅与长诗）、52%（《静夜思》）计算后共减去 45pt；网页按阅读页高度采用相同比例并共减去 45px。极小屏仍保留最小起点。排版不会为了塞进一屏而继续向上推正文；空间不足时在下方阅读区纵向滚动，简注跟随正文一起滚动。用户字号和 iOS 动态字体参与计算，并保留可读字号下限。字号与行距继续沿用 v0.3.2 的拟合区域，位置微调不会改变字体大小。简注相对 v0.3.2 下移 15pt（网页为 15px），因此正常页面的诗文与简注间距增加 35pt。注释弹层约占可用高度的 58%，内容在内部滚动，关闭按钮始终可见。

网页与原生端均使用等宽汉字单元，句尾标点独立定位。正文不叠加额外纸色背景或渐变，直接使用图片已有的留白。7 张旧满幅构图已刷新为上方场景、下方留白的全页插画，不再使用独立画窗。iOS 图片铺满屏幕并延伸到上下安全区，正文和操作工具仍保持在安全阅读区域内。本轮暂不添加插画动画。

默认阅读与目录按七类排列：**五言绝句 29 首 → 七言绝句 50 首 → 五言律诗 79 首 → 七言律诗 53 首 → 五言古诗 35 首 → 七言古诗 28 首 → 乐府 43 首**。目录显示体裁分组标题，同组内沿用原书序。原始 `order` 和稳定 ID 不变，界面序号使用当前阅读顺序，不再拿原书序数字充当显示页码。

## 当前边界

- 20 首精选完成插画、短诗意与拼音初校，仍标记 `editorial-draft`，并非出版级终审。普通诗的主题为规则推断，拼音沿用来源数据。
- 原始 320 首书序中仍缺 43、134、278；现有 317 首全部保留全文，90 首仍缺来源注释。缺失不以占位文本冒充完成。
- 插画是否独立和内容是否精选分开管理，补图不会改变原有 20 首精选的编辑状态。
- 网页收藏与原生收藏各自保存在本机；网页兼容旧标题收藏迁移，不提供跨端同步。
- 尚未完成全库人工校勘、真机验收、App Icon、发布签名及 App Store 素材。

v0.3.3 已通过 5 项网页测试、317 首数据校验及 9 项 iOS XCTest；原生打包包含 317 首诗文与 635 份图片。模拟器已实看《回乡偶书》的诗文与简注独立位移，以及半屏以上的注释弹层。详细进度与验收记录见 [PROGRESS.md](PROGRESS.md)，产品方向见 [PRODUCT_DEVELOPMENT.md](PRODUCT_DEVELOPMENT.md)。
