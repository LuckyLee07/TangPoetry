# 第二卷制作与阅读指南

制作分支：`codex/volume-2`。本卷采用已确认的 305 首选目（304 首撷英对应篇目，加 1 首独立补选）。2026-10-04 已完成图文、展示元数据、阅读字形映射、压缩图与目录取景复核，并接入独立 Web 第二卷及可选原生双卷内容。默认第一卷仍为 320 首，两卷的收藏、已读和续读记录分别保存。

## 阅读入口

在此工作目录启动本地服务：

```bash
python3 -m http.server 8767 --bind 127.0.0.1
```

- [正式阅读界面的第二卷入口](http://127.0.0.1:8767/index.html?volume=2)：使用 `data/reader-volume-2/` 的 305 份详情；封面与设置支持切卷，提供目录、作者、体裁、搜索、20 首推荐、收藏、已读、简注和完整释义。第一卷仍为默认入口。第二卷已生成听校音轨但尚未正式发布，产品播放控件保持隐藏，设置中显示制作状态。
- [第二卷阅读校样](http://127.0.0.1:8767/tools/volume2-reader.html)：可切换屏幕尺寸与字号，检查长诗滚动、简意、标题、稀见字和正文留白，并可隐藏诗文查看插画。该工具独立保存人工标记与校样阅读位置，不与产品阅读记录混用。
- [图文总览](http://127.0.0.1:8767/tools/volume2-preview.html)：按原选目书序查看制作稿、整幅原图、解读、词注、来源和校勘笔记。总览的排版用于内容审阅，与客户端诗页不同。

产品阅读页和在线校样请使用 HTTP 服务，直接双击这些 HTML 无法加载 JSON；后文离线听校包的 HTML 已内嵌数据，可直接打开。校样与自动排版检查不能代替真机或完整人工阅读验收。

## 数据与素材

- [production.json](production.json)：汇总制作稿，保留稳定 ID、来源、现代诗意、分段解读、词注、插画路径、校订记录及校订前 `sourceText`。
- [commentary/](commentary/)：305 首现代释义、537 段完整解读和 849 条字词解释，另保留来源依据与画面构思。
- [display-metadata.json](display-metadata.json) 与 [DISPLAY_METADATA_REVIEW.md](DISPLAY_METADATA_REVIEW.md)：展示题名、朝代、真实诗体和目录分组。长题使用阅读展示题，原题和别名继续保存；体裁不是仅按句数猜测。
- [display-glyphs.json](display-glyphs.json)：稀见字的阅读呈现映射。映射只用于显示与阅读字形检查，不改归档正文、来源文本、稳定 ID 或插画回执。
- [illustrations/receipts/](illustrations/receipts/)：逐张提示词、文件哈希、尺寸与视觉检查记录；返工历史在各回执和 `illustrations/revisions.json` 中。
- `assets/volume-2/poem-art/`：305 幅独立竖版 PNG 原图，暖纸水墨风格，保留下部阅读留白。共 651,071,883 B，原图保持不变，按既有规则忽略入库，应另行备份。
- [delivery-framing.json](delivery-framing.json) 与 [delivery-assets.json](delivery-assets.json)：目录主体取景、压缩配方、原图和交付副本的哈希与尺寸。305 张目录图均已复核；Web 诗页共 29,550,890 B，目录图共 2,913,894 B，副本位于 `assets/volume-2/optimized/`。
- `data/reader-volume-2/catalog.json` 与 `poems/*.json`：305 首客户端目录与详情，包含阅读字形、完整释义、20 首推荐、展示元数据和来源回溯。
- [poems.json](poems.json)：原诗归档，本轮保持不变。
- [text-proposals/](text-proposals/) 与 [text-corrections.json](text-corrections.json)：有证据的校订建议和编辑稿采用的 11 项正文校订；不是把所有合法异文都认作错误。
- [EDITORIAL_NOTES.md](EDITORIAL_NOTES.md) 与 [SEMANTIC_REVIEW.md](SEMANTIC_REVIEW.md)：解释边界、异文、305 首逐首语义复核和修订依据。
- [READER_QA.md](READER_QA.md) 与 [reader-qa.json](reader-qa.json)：本轮浏览器、模拟器、字形和回归测试的验收结果与边界。
- [local-backup.json](local-backup.json)：本地素材归档位置、SHA-256 和逐文件校验数量；本地归档不是异地备份。
- [production-audit.json](production-audit.json)、`data/reader-volume-2/build-report.json` 与 [audio-plan.json](audio-plan.json)：覆盖、字段数量、素材完整性、交付体积和实际音频进度。

诗意依据原诗重新撰写，没有复制第三方现代译注。插画按每首的季节、人物、物象和情境分别制作，经过筛选或返工后保存接受稿。

## 重建与检查

```bash
python3 scripts/build_volume2_production.py --require-complete
python3 scripts/check_volume2_semantic_review.py
python3 scripts/build_volume2_reader.py
python3 scripts/build_volume2_production.py --check --require-complete
python3 scripts/build_volume2_reader.py --check
python3 tests/tang_second_volume_test.py
```

阅读交付副本的重建需要 `cwebp` 和 Python Pillow。构建检查 305 个稳定 ID、现代释义和元数据字段、原文与校订前文本、PNG 尺寸及 SHA-256、目录裁图边界和交付哈希；会验证已有正式第二卷音频清单与听校证据。图文构建不会调用付费接口或重新生成插画，也不会覆盖原诗归档及 305 幅 PNG 原图。

后续需要重做单幅原图时，可以用 `scripts/volume2_art_jobs.py --from 序号 --to 序号 --include-existing` 获取保存的风格与逐诗提示词，再用内置图像工具生成。必须实际查看结果并记录检查结论；`scripts/record_volume2_art.py` 复制原图并写回执，不负责自动判定画面质量。

## 原生内容快照

```bash
# 单独生成第二卷图文快照，不替换默认第一卷
python3 scripts/prepare_ios.py --volume 2
python3 scripts/prepare_ios.py --volume 2 --check

# 为本制作分支的 Xcode 工程生成可选双卷验收内容
python3 scripts/prepare_ios.py --include-volume-2
python3 scripts/prepare_ios.py --check
xcodegen generate --spec ios/project.yml
```

独立第二卷输出为 `ios/Volume2Content/`，包含 305 首详情与 610 张 JPEG，当前图文快照为 93,442,900 B、0 音轨，本轮生成后未重建。合卷输出保留第一卷的 `ios/Content/catalog.json`、原有资源与 320 首音频，在 `ios/Content/Volumes/2/` 中加入第二卷；原生仅在第二卷实际内置时显示切卷菜单。应用工程使用 `ios/Content/`，不直接使用独立快照目录。

无参数 `python3 scripts/prepare_ios.py` 仍只打包第一卷；需要双卷时应使用 `--include-volume-2`。快照生成采用哈希缓存与整体替换，校验失败保留旧快照。生成目录和本地媒体不入 Git，主工作区第一卷的原诗与插画没有被第二卷制作覆盖。

## 朗读制作与启用

2026-10-04 已完成 **305 首真实 MP3**，当前正文、SSML、文件哈希、时长和逐首解码校验均通过。音频共 **66,836,908 B**、**8,345.616 秒**（2 小时 19 分 5.616 秒）。[离线听校 ZIP](../../../output/audio-azure-volume-2/volume2-audio-audition.zip) 已创建，实际为 **56,871,046 B**，包内 305 份 MP3 已再核对 SHA-256；[离线 HTML](../../../output/audio-azure-volume-2/volume2-audio-audition/index.html) 与 [bundle-report.json](../../../output/audio-azure-volume-2/volume2-audio-audition/bundle-report.json) 保留真实快照，生成收据见 [audio-generation.json](audio-generation.json)。

当前听审仍为 **0 首批准、305 首待听校**，正式发布音轨及 App 可用第二卷音轨为 **0 首**，`narrationAvailable=false`。生成清单的 `release=full` 表示完整生成覆盖，不能据此视作已发布。已有原生快照仍为图文与 0 音轨，没有因试听包生成而重建。

先准备 SSML 与进度草稿；默认命令不联网合成，也不读取密钥值：

```bash
python3 scripts/generate_volume2_audio.py
```

本轮 Azure Speech Key 已在线验证有效，区域为 `eastasia`。使用 `--prompt-key` 在终端隐藏输入，仅供当前进程临时使用，未写入 `.env`。`audio-plan.json` 的 `speechCredentialsConfigured=false` 表示没有持久配置，不表示这次临时输入的 Key 无效。已有环境变量 `SPEECH_KEY`、`SPEECH_REGION` 或忽略入库的本地配置文件也可供脚本使用。

```bash
python3 scripts/generate_volume2_audio.py --generate --prompt-key --region eastasia --transport curl --jobs 3
# 必要时对未完成条目按联分段生成，已有有效条目可复用
python3 scripts/generate_volume2_audio.py --generate --prompt-key --region eastasia --transport curl --chunked --jobs 1
```

使用同一命令即可断点续做：仅当配方、当前 SSML 输入和文件哈希均匹配时保留已有 MP3。`--transport curl` 改变传输方式，沿用晓晓 `poetry-reading`、语速、停顿、响度和编码配方；`--chunked` 缓存联间分段并拼接为一首完整 MP3，标题与作者不会重复朗读。网络失败和待重试项留在本卷生成目录中，不切换正式清单。

生成后先进行完整校验，再制作本地离线听校包：

```bash
python3 scripts/generate_volume2_audio.py --audit
python3 scripts/package_volume2_audio.py --check-only
python3 scripts/package_volume2_audio.py
```

打包脚本要求 305 首完整覆盖、当前正文与 SSML、目录与制作资料哈希、文件哈希和逐首解码全部通过；生成 `output/audio-azure-volume-2/volume2-audio-audition/` 与同名 ZIP。完整解压后双击其中的 `index.html`，内嵌目录、正文、样式和脚本无需 HTTP 服务，播放器读取包内相对 `audio/{id}.mp3`。搜索、手动播放、进度定位、倍速和前后切换均可用；切换诗篇不会自动开始播放。实际 `file://` 播放验收仍待完成：本轮 IAB 禁止该协议，只验证了静态嵌入和相对路径。

也可在前述 HTTP 服务中打开 [第二卷朗读试听页](../../../tools/volume2-audio.html)（[本地 HTTP 入口](http://127.0.0.1:8767/tools/volume2-audio.html)）。该页读取实时生成清单，只播放 `output/audio-azure-volume-2/audio/{id}.mp3`；新音轨生成后可刷新清单，未生成条目保持等待。真实 HTTP 手动播放、倍速和切换时停止旧音轨已验证。试听页和打包脚本不修改或批准听审记录；生成完整与人工批准是两个状态，`generationComplete=true`、`listeningApproved=null` 不代表已获逐首听校批准。

逐首完整试听 `output/audio-azure-volume-2/audio/` 的实际 MP3，并在 `output/audio-azure-volume-2/listening-review.json` 对应行填写 `status=approved-after-listening`、真实 `reviewedBy`、带时区的 ISO 8601 `reviewedAt`，保留与该次输入和该文件一致的 `inputSHA256`、`audioSHA256`。必须检查生僻字、多音字、标题与作者读音、停顿和播放衔接；草稿 SSML、自动解码或覆盖计数都不是试听批准。

305 首生成、解码和逐首听校均通过后，再发布、启用并重建双卷内容：

```bash
python3 scripts/generate_volume2_audio.py --publish
python3 scripts/build_volume2_reader.py
python3 scripts/prepare_ios.py --include-volume-2
npm test
```

正式音频文件位于 `assets/volume-2/audio/xiaoxiao-poetry-v1/`，清单位于 `data/audio-volume-2/manifest.json`，永久听校证据位于 `data/audio-volume-2/listening-review.json`。阅读构建只有在全部 305 首、当前朗读输入、文件哈希和永久听校记录都匹配时，才自动将 `narrationAvailable` 设为 `true`。没有正式清单时仍为 0 首与不可播放；损坏、缺失、过期或未听校的已有清单会被拒绝，不应手工修改可用标记。

## 当前边界

图文与接入成果仍为 `editorial-draft`、`publicationReady=false`。305 首语义复核、展示元数据和阅读字形校验、压缩与目录取景复核已经完成；没有宣称逐页对过《唐诗撷英》纸书，也不能用构建通过代替出版终审。原诗归档和 305 幅 PNG 原图保持不变。

第二卷逐首完整听校与正式发布、真机长诗与大字号阅读、VoiceOver 实际体验、`file://` 实际播放及离线播放衔接和性能验收仍待完成。浏览器、字形探针、模拟器和自动检查的结论只适用于各自检查范围，不代表真机或纸书终校。第二卷尚未提交发布审核或上架。
