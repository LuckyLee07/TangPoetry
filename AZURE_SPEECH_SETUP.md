# Azure Speech 开通与全库朗读

核对日期：2026-09-27。当前采用用户确认的「晓晓 · 诗歌朗读」，已授权扩展至全部 320 首。正式制作入口为 `scripts/generate_azure_audio.py`，完整命令和发布检查见 [README.md](README.md)。以下保留开通过程与三轮试听记录，其中的“五首试听”“尚未替换”描述对应当时阶段。

## 开通与最初三首试听

1. 在 [Azure 全球版](https://azure.microsoft.com/free/) 注册账户并开通订阅。已有订阅可直接使用。注册通常需要 Microsoft/GitHub 账户、手机及非预付信用卡或借记卡；账单地区按本人实际信息填写。[账户说明](https://azure.microsoft.com/en-us/pricing/purchase-options/azure-account)
2. 登录 [Azure 门户](https://portal.azure.com/)，搜索 **Speech / 语音**，创建 Speech 资源。资源组可新建 `tangpoetry`，资源名称使用可用的唯一名称；区域可选 **East Asia (`eastasia`)**，定价层先选 **Free F0**。当前官方页面列出普通 Neural TTS 每月 50 万字符免费额度，足够三首多版本试听；以门户实际可用选项为准。[价格](https://azure.microsoft.com/en-us/pricing/details/speech/)、[区域支持](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/regions?tabs=tts)
3. 部署完成后进入资源的 **Keys and Endpoint / 密钥和终结点**，保留一个密钥及资源区域。区域必须与实际创建的资源一致。[官方快速入门](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/get-started-text-to-speech)
4. 推荐在本机终端运行 `.venv/bin/python scripts/prepare_narration_trial.py --generate-azure --prompt-key`，按提示粘贴密钥并回车。密钥输入不回显，仅在进程内存中用于三首合成，不写入任何文件；区域默认 `eastasia`，其他区域用 `--region` 指定。脚本也支持 `SPEECH_KEY`/`SPEECH_REGION` 环境变量及旧的 `.env.azure-speech.local` 配置。密钥不发送到聊天，不放入前端或 iOS 包；不要将凭据配置文件放到对外提供 HTTP 服务的目录。

只想先听音色，可以打开 [Speech Studio 声音库](https://speech.microsoft.com/portal?projecttype=texttospeech)。官方说明声音库可免注册试听。重点对比云泽 `zh-CN-YunzeNeural` 和云健 `zh-CN-YunjianNeural`；最终效果仍需用实际诗文试听确认。

## 第一轮执行记录

- `scripts/prepare_narration_trial.py` 默认仅生成本地 Edge 输入、Azure SSML 稿和对照页；使用 `.venv/bin/python scripts/prepare_narration_trial.py --generate-edge` 生成三首 Edge 样例。
- Edge 样例位于 `output/tts-trial/`。保留原诗标点，上下句连读；登鹳雀楼、枫桥夜泊、鹿柴语速分别为 −5%、−10%、−8%。统一采用与现有版相同的 −18 LUFS 后处理，无配乐。
- Azure 稿暂选云泽男声，分别采用 `documentary-narration`、`sad`、`calm` 风格，已检查 XML 结构及诗句无增删。风格支持见 [微软声音列表](https://github.com/MicrosoftDocs/azure-ai-docs/blob/main/articles/ai-services/speech-service/includes/language-support/voice-styles-and-roles.md)。
- **Speech 资源已于 2026-09-27 创建并验证为活动状态**：资源名 `tangpoetry-speech`，资源组 `tangpoetry`，订阅 `Azure subscription 1`，区域 `eastasia`，定价层 `Free F0`。
- **Azure 三首音频已于 2026-09-27 实际合成成功**，位于 `output/tts-trial/*-azure.mp3`：登鹳雀楼 14.69 秒、枫桥夜泊 18.46 秒、鹿柴 14.69 秒。均为 24 kHz 单声道，使用同样的 −18 LUFS 后处理；MP3 结构、时长、采样率和声道检查通过。对照页现有三组版本可供试听，音色、情绪及多音字准确性仍需实际听评。
- 真实 API 调用通过隐藏输入临时使用用户提供的凭据，未创建 `.env.azure-speech.local`，密钥不写入项目文件、音频、页面或输出日志。建议在 Azure 轮换已在聊天中提供的密钥。
- 修复本机 Python 默认 CA 路径缺失导致的 TLS 连接失败：显式使用 `certifi` 的 CA 包并保持证书验证开启；音频依赖已记录该版本。Speech Studio 页面在 Chrome 中未成功加载不影响这次 API 合成。
- App 仍使用原五首 MP3，试听稿不自动覆盖发布音频或清单。

三首 Edge MP3 已通过时长、采样率和声道检查。本轮确认对照页包含 9 个音频播放器，三首 Azure 音频 HTTP 返回 200、内容与本地文件一致且彼此不同。此前 Codex 内置浏览器曾在点击播放时崩溃，本轮未将 HTTP 检查表述为实际浏览器播放验收；也可直接打开本地 MP3 试听。

## 第二轮：《登鹳雀楼》五版对照

`scripts/prepare_recitation_variants.py` 在 `output/tts-trial/recitation/` 生成独立试听页及四个新文件，A 直接引用上一轮云泽音频，原文件不变。

| 版本 | 处理 | 时长 |
| --- | --- | --- |
| A | 上一轮云泽旁白，作为参照 | 14.69 秒 |
| B | 云泽；逐句语速、音高、音量与联间停顿；「千里」「更上」局部调整 | 16.68 秒 |
| C | B 的全部编排不变，仅将风格强度从 1.2 提高到 1.85 | 16.63 秒 |
| D | B 的全部编排不变，仅换成云健男声 | 15.94 秒 |
| E | 晓晓女声，`poetry-reading` 风格，强度 1.3、语速 −6% | 16.03 秒 |

生成前通过东亚区域 voices API 确认所用三种音色支持对应风格，结果保存为 `voice-support.json`。四份 SSML 均检查正文与原诗逐字一致。`manifest.json` 记录各版参数、时长和音频/SSML 哈希，不含凭据。五版实测响度为 −18.68 至 −19.07 LUFS，差异 0.39 LU；真峰值均低于 −1.8 dBTP，无配乐。最终五个音频 URL 均返回 HTTP 200；新预览页五个 audio 元素均为 readyState 4、无媒体加载错误。A 文件哈希保持不变，B–E 哈希均与清单一致且彼此不同；模拟传输中断确认不会覆盖已有音频。

重新生成命令：`.venv/bin/python scripts/prepare_recitation_variants.py --generate --prompt-key`。若单版失败可用 `--only e-xiaoxiao-poetry` 指定；同一资源/区域的本轮短时重试可加 `--reuse-voice-check` 复用已确认的音色列表。女声首次音频传输及下一次列表查询中断，已单独重试成功，未保存残缺音频。点击内置浏览器播放按钮的自动化检查再次使预览目标中断，不能据此宣称浏览器播放验收通过；文件解码与响度检查已通过，情绪效果待用户试听。

## 第三轮：用户选定晓晓诗歌朗读风格

用户试听后认可 E 版，要求按同一版本再生成几首。`scripts/prepare_poetry_reading_samples.py` 沿用 `zh-CN-XiaoxiaoNeural`、`poetry-reading`、强度 1.3、正文语速 −6%、联间 500ms 的设置，新增以下四首；不替换 App 音频，也不扩展整库。

| 诗篇 | 体裁 | 时长 | 实测响度 |
| --- | --- | --- | --- |
| 鹿柴 | 五言绝句 | 15.60 秒 | −18.78 LUFS |
| 枫桥夜泊 | 七言绝句 | 17.98 秒 | −18.73 LUFS |
| 望月怀远 | 五言律诗 | 26.52 秒 | −18.64 LUFS |
| 登高 | 七言律诗 | 32.93 秒 | −18.73 LUFS |

新试听页与 MP3、SSML、参数清单、音频检查记录均位于 `output/tts-trial/poetry-reading/`，页面保留《登鹳雀楼》E 版作参照。正文经 SSML 逐字一致性检查，鹿柴沿用已有题名读音别名；旧的 A–E 朗读稿保持一致。四首均为 24 kHz 单声道，MP3 完整解码、哈希、真峰值检查通过；真峰值低于 −1.8 dBTP。四首及参照音频在浏览器中均达到 readyState 4、无加载错误；没有重复触发此前导致预览中断的自动点击播放操作，具体读音和情绪以人工试听为准。

生成命令：`.venv/bin/python scripts/prepare_poetry_reading_samples.py --generate --prompt-key`。可用 `--only` 指定单首；传输中断最多自动重试一次，完整合成后才替换输出文件。本轮鹿柴和枫桥夜泊各重试一次后成功，密钥未保存。


## 全库制作流程

在三轮试听后，用户明确同意把整库改成相同版本。共享配方 `scripts/narration_recipe.py` 生成与已认可样音逐字节相同的 SSML，正文语速 −6%、风格强度 1.3、联间 500ms；采样率、声道、响度与编码沿用试听设置。全库标题、作者、正文约 26,934 字，已认可的五首直接按哈希复用。

制作使用现有 East Asia / Free F0 资源，没有更改定价层。当前 F0 实时合成限制为每分钟 20 次请求、每次最多 10 分钟音频；脚本共用请求节拍，每次启动间隔至少 3.5 秒，最多 6 个请求可等待响应，暂时性失败计入相同限流器并自动重试。长篇保留全部诗句，生成稿与目录全文逐字核对。[官方限制](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/speech-services-quotas-and-limits)

`output/audio-azure-library/` 保存可恢复的暂存音频、SSML、输入/输出哈希、失败项和响度记录，不保存密钥。只有整库全部就绪、逐文件完整解码且源稿/参数/哈希验证通过后，`--publish` 才发布版本目录并原子替换正式清单；iOS 再将清单引用的 320 首文件打包为离线资源。生成命令重跑只补缺失或输入已改变的条目；已发布目录作为不可变版本保护，避免旧播放器读到另一版音频。

自动检查不能替代逐首人工多音字听校，发布后的内容听校仍需继续。

《兵车行》的整首传输连续重试仍中断，使用 `--generate --prompt-key --reuse-voice-check --jobs 1 --chunked` 恢复。按现有联间停顿拆为 5 段，保持相同音色、风格和语速，只有第一段含题名/作者。原始片段分别通过响应完整性和 MP3 检查后无重编码拼接，再统一做一次响度处理和最终编码；SSML 全文及停顿标记数量与原稿一致。发布检查额外核对每段的输入、音频哈希及最终全诗文件。其他 319 首均为整首合成。
