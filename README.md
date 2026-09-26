# 唐诗画笺

手机竖屏唐诗读本：317 首全文与 317 幅专属插画，按体裁分卷，字号按诗体和篇幅适配，正文放在插画下方留白内，纸色、字号与简注可调；当前阅读界面不显示拼音。当前版本 **0.3.1**，同时包含可直接预览的网页和 SwiftUI iPhone 工程。

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

`prepare_ios.py` 使用 macOS 自带 `sips`，将网页插图转成原生 JPEG 资源，并打包全部诗文。生成的 `ios/Content/` 不入库，首次打开工程前必须生成；应用安装后完全离线运行。内容目录使用 `Content`，避免与系统保留的 bundle 目录名称冲突。

## 编辑与重建

```text
归档内容 data/final/tang_poems_final.json
  + 编辑覆盖 data/editorial.json
  + 原有插画策划 data/visuals.json
  + 逐首插画与提示词 data/illustrations/plan.json
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

原有 20 张专属图保留，本轮新增 297 张已全部生成、检查并接入。新增原图放在 `assets/poem-art/`，逐首提示词、输出来源和视觉检查记录在 `data/illustrations/`。客户端仅下载压缩后的大图和缩略图，原尺寸 PNG 用于保留和后续编辑。

```sh
python3 scripts/audit_illustrations.py --require-complete
```

该命令检查 297 张新增原图的完整性、竖幅尺寸、独立文件内容与视觉检查记录。当前生成及接入数量分别见 `data/illustrations/audit.json` 和 `data/reader/build-report.json`。

单诗的构图适配也放在 `data/editorial.json`：`artworkMode: "window"` 使用独立的上部画窗，`artworkFocusY` 取 0–1，表示与 CSS `object-position-y` 相同的垂直裁切位置；`textStart` 表示正文起点占页面高度的比例。只有配置过的字段才会写入目录。客户端限制正文起点只能从该诗体默认位置向下调整，最下到页面的 70%，避免覆盖上方插画。

## 自适应阅读

五言绝句以 26px、七言绝句以 24px 为基准；五律与七律以 22px、21px 为基准。古诗、乐府按实际分句长度与行数选择排版，不仅依赖分类标签。绝句正文从页面高度的 48% 起排，律诗、中等篇幅与长诗从 42% 起排，《静夜思》单独从 55% 起排。小屏、长标题和大字号不会把正文往上推到插画内；空间不足时在下方阅读区纵向滚动，简注跟随正文一起滚动。用户字号和 iOS 动态字体参与计算，并保留可读字号下限。

网页与原生端均使用等宽汉字单元，句尾标点独立定位。正文不叠加额外纸色背景或渐变，直接使用图片已有的留白。7 张旧满幅插画采用上图下文的画窗布局，并以各自的裁切位置保留主体；原图和图片映射保持不变。本轮暂不添加插画动画。

默认阅读与目录按七类排列：**五言绝句 29 首 → 七言绝句 50 首 → 五言律诗 79 首 → 七言律诗 53 首 → 五言古诗 35 首 → 七言古诗 28 首 → 乐府 43 首**。目录显示体裁分组标题，同组内沿用原书序。原始 `order` 和稳定 ID 不变，界面序号使用当前阅读顺序，不再拿原书序数字充当显示页码。

## 当前边界

- 20 首精选完成插画、短诗意与拼音初校，仍标记 `editorial-draft`，并非出版级终审。普通诗的主题为规则推断，拼音沿用来源数据。
- 原始 320 首书序中仍缺 43、134、278；现有 317 首全部保留全文，90 首仍缺来源注释。缺失不以占位文本冒充完成。
- 插画是否独立和内容是否精选分开管理，补图不会改变原有 20 首精选的编辑状态。
- 网页收藏与原生收藏各自保存在本机；网页兼容旧标题收藏迁移，不提供跨端同步。
- 尚未完成全库人工校勘、真机验收、App Icon、发布签名及 App Store 素材。

详细进度与验收记录见 [PROGRESS.md](PROGRESS.md)，产品方向见 [PRODUCT_DEVELOPMENT.md](PRODUCT_DEVELOPMENT.md)。
