# 唐诗画笺

手机竖屏唐诗读本：317 首全文，20 首专属插画，纸色、拼音与简注可调。当前版本 **0.2**，同时包含可直接预览的网页和 SwiftUI iPhone 工程。

## 网页运行

需要 Python 3 和 Node.js 18 或更新版本。交付数据与 WebP 插图已入库，无需安装 npm 依赖。

```sh
npm start
```

打开 http://127.0.0.1:8765。请使用 HTTP 服务，直接双击 HTML 无法加载 JSON。

```sh
npm test
```

测试覆盖收藏迁移、同名诗独立收藏、异常设置恢复、题名别名/诗句/繁体搜索、加载重试与缓存；数据校验遍历全部诗文及图片引用。

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
  + 插画策划 data/visuals.json
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

11 张新增插画的原图与完整生成提示词保存在 `assets/featured/`；全部 20 张使用中的插图生成大图和缩略图两种 WebP，共约 2.73 MB。原图保留，客户端不直接下载原尺寸 PNG。

## 当前边界

- 20 首精选完成插画、短诗意与拼音初校，仍标记 `editorial-draft`，并非出版级终审。普通诗的主题为规则推断，拼音沿用来源数据。
- 原始 320 首书序中仍缺 43、134、278；现有 317 首全部保留全文，90 首仍缺来源注释。缺失不以占位文本冒充完成。
- 35 首五言古诗的视觉策划中还有 31 张未制作。阅读器使用有效背景回退，不显示破图，也不将它们计为精选。
- 网页收藏与原生收藏各自保存在本机；网页兼容旧标题收藏迁移，不提供跨端同步。
- 尚未完成全库人工校勘、真机验收、App Icon、发布签名及 App Store 素材。

详细进度与验收记录见 [PROGRESS.md](PROGRESS.md)，产品方向见 [PRODUCT_DEVELOPMENT.md](PRODUCT_DEVELOPMENT.md)。
