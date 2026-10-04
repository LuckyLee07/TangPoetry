# 第二卷制作与阅读指南

制作分支：`codex/volume-2`。本卷采用已确认的 305 首选目（304 首撷英对应篇目，加 1 首独立补选）。2026-10-04 已完成图文、展示元数据、阅读字形映射、压缩图与目录取景复核，并接入独立 Web 第二卷及可选原生双卷内容。默认第一卷仍为 320 首，两卷的收藏、已读和续读记录分别保存。

## 阅读入口

在此工作目录启动本地服务：

```bash
python3 -m http.server 8767 --bind 127.0.0.1
```

- [正式阅读界面的第二卷入口](http://127.0.0.1:8767/index.html?volume=2)：使用 `data/reader-volume-2/` 的 305 份详情；封面与设置支持切卷，提供目录、作者、体裁、搜索、20 首推荐、收藏、已读、简注和完整释义。第一卷仍为默认入口。第二卷尚无音频，播放控件保持隐藏，设置中显示制作状态。
- [第二卷阅读校样](http://127.0.0.1:8767/tools/volume2-reader.html)：可切换屏幕尺寸与字号，检查长诗滚动、简意、标题、稀见字和正文留白，并可隐藏诗文查看插画。该工具独立保存人工标记与校样阅读位置，不与产品阅读记录混用。
- [图文总览](http://127.0.0.1:8767/tools/volume2-preview.html)：按原选目书序查看制作稿、整幅原图、解读、词注、来源和校勘笔记。总览的排版用于内容审阅，与客户端诗页不同。

请使用 HTTP 服务，直接双击 HTML 无法加载 JSON。校样与自动排版检查不能代替真机或完整人工阅读验收。

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

独立第二卷输出为 `ios/Volume2Content/`，包含 305 首详情与 610 张 JPEG，当前无音频快照为 93,442,900 B。合卷输出保留第一卷的 `ios/Content/catalog.json`、原有资源与 320 首音频，在 `ios/Content/Volumes/2/` 中加入第二卷；原生仅在第二卷实际内置时显示切卷菜单。应用工程使用 `ios/Content/`，不直接使用独立快照目录。

无参数 `python3 scripts/prepare_ios.py` 仍只打包第一卷；需要双卷时应使用 `--include-volume-2`。快照生成采用哈希缓存与整体替换，校验失败保留旧快照。生成目录和本地媒体不入 Git，主工作区第一卷的原诗与插画没有被第二卷制作覆盖。

## 朗读制作与启用

当前为 **0 首真实音频、305 首待生成与试听**，没有可用 Azure Speech 凭据。先准备 SSML 与进度草稿；默认命令不联网合成，也不读取密钥值：

```bash
python3 scripts/generate_volume2_audio.py
```

配置现有 Azure Speech 资源的 `SPEECH_KEY`、`SPEECH_REGION`，可使用环境变量或本地忽略入库的 `.env.azure-speech.local`。随后生成：

```bash
python3 scripts/generate_volume2_audio.py --generate --jobs 3
# 必要时对未完成条目按联分段生成，已有有效条目可复用
python3 scripts/generate_volume2_audio.py --generate --chunked --jobs 1
```

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

第二卷实际朗读生成和逐首试听、真机长诗与大字号阅读、VoiceOver 实际体验、离线播放衔接和性能验收仍待完成。浏览器、字形探针、模拟器和自动检查的结论只适用于各自检查范围，不代表真机或纸书终校。第二卷尚未提交发布审核或上架。
