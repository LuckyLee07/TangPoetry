# App 第二卷：撷英与补选

2026-10-04：**304 首原目录对应诗 + 1 首独立补选 = 305 首不与第一卷重复的诗**。已完成 305 首现代释义、537 段完整解读、849 条字词解释和 305 幅插画；本制作分支已接入独立 Web 第二卷及可选原生双卷内容。第一卷默认仍为 320 首。

[选目目录](CATALOG.md) · [原诗归档](poems.json) · [替换与版本依据](selection-policy.json) · [查重记录](audit.json) · [制作与阅读指南](PRODUCTION_GUIDE.md) · [展示元数据说明](DISPLAY_METADATA_REVIEW.md)

## 为什么原先净新增是 304 首

重叠作品为李白《子夜吴歌·冬歌》，第一卷题为《子夜四时歌冬歌》。两边同为：

> 明朝驿使发，一夜絮征袍。  
> 素手抽针冷，那堪把剪刀。  
> 裁缝寄远道，几日到临洮。

作者、完整正文一致，是同一首诗的不同题名；不是两首诗碰巧同名。反过来，《野望》《咏风》等相同题名可以对应不同作者或不同正文，不能仅按标题删除。

第一卷现有底本收齐李白《子夜吴歌》春、夏、秋、冬四篇，[Project Gutenberg 的《唐诗三百首》转录](https://www.gutenberg.org/cache/epub/52323/pg52323-images.html)也如此。第二卷这条由用户明确确认选冬歌。但尚未核实《唐诗撷英》纸书对应页、编选说明及其所据《唐诗三百首》版次，因此不能断言原书有误，也不能把版次差异当成已经证实的解释。

[《唐诗撷英》原目录档案](../tang-yizhu/xieying/README.md)保留原有 305 首和所有用户确认，方便今后对书。这里单独导出 App 第二卷选目，去掉已由第一卷承载的冬歌，加入补选。补选不标作《唐诗撷英》原收篇目。

## 补选：李白《早春寄王汉阳》

闻道春还未相识，走傍寒梅访消息。  
昨夜东风入武昌，陌头杨柳黄金色。  
碧水浩浩云茫茫，美人不来空断肠。  
预拂青山一片石，与君连日醉壶觞。

寻梅问春、杨柳新色与邀友同饮相接，适合本项目的赏诗、赏画体验。经与现有第一、三、四卷及原第二卷资料比对，未发现重复候选。此处按七言古诗收录，不因八句七言就认作律诗。

来源为既有固定版本《全唐诗》转录，另核 [《全唐诗》卷173](https://zh.wikisource.org/zh-hans/全唐詩/卷173)。正文采用“武昌”读法；来源“武阳”及“一作昌”的证据继续保存，不把异文判作确定错字。繁简来源全文见该记录的 `sourceReading`。该篇的现代释义为本项目重新撰写，独立插画已完成；朗读随本卷 305 首完成生成和解码检查，仍待逐首听校批准。

原目录中的暂定对应不会因导出而变为纸书已核；补选也仍需印本定稿，`publicationReady=false`。

## 当前四卷规划

| 卷 | 首数 |
| --- | ---: |
| 第一卷 | 320 |
| 第二卷 App 选目 | 305 |
| 第三卷 | 300 |
| 第四卷 | 300 |
| 去重后合计 | **1,225** |

这是四卷规划资料总量。本制作分支的客户端接入范围为默认第一卷 320 首与可选第二卷 305 首，合计 625 首；不能据此声称四卷 1,225 首都已接入或完成验收。

## 重建

```bash
python3 scripts/build_tang_second_volume.py
python3 scripts/build_tang_third_volume.py
python3 scripts/build_classical_fourth_volume.py
python3 tests/tang_second_volume_test.py
```

按第二、三、四卷顺序重建，保证下游查重与总数使用本选目。上述命令重建选目与查重资料，不承担客户端接入；图文和阅读数据的构建入口见 [制作与阅读指南](PRODUCTION_GUIDE.md#重建与检查)。

## 当前接入与资源

`data/reader-volume-2/catalog.json` 及 `poems/*.json` 提供 305 首阅读详情，展示题名、朝代、体裁、20 首推荐和字形映射均已整理并校验。网页入口为 `index.html?volume=2`；原生通过 `python3 scripts/prepare_ios.py --include-volume-2` 将第二卷放入 `ios/Content/Volumes/2/`，保留第一卷主目录。`python3 scripts/prepare_ios.py --volume 2` 只输出独立 `ios/Volume2Content/` 快照。

305 幅归档 PNG 原图共 651,071,883 B，Web 诗页共 29,550,890 B，目录缩略图共 2,913,894 B；压缩与目录取景复核已完成。当前第二卷独立原生图文快照为 93,442,900 B、0 音轨，本轮音频生成后未重建。原诗归档与 305 幅 PNG 原图没有被这些交付副本覆盖。

第二卷 305 首真实 MP3 已全部生成并逐首解码通过，共 66,836,908 B、8,345.616 秒（2 小时 19 分 5.616 秒）；[离线听校 ZIP](../../../output/audio-azure-volume-2/volume2-audio-audition.zip) 为 56,871,046 B，内含 305 份已核对 SHA-256 的 MP3、目录与正文。可使用 [在线试听页](../../../tools/volume2-audio.html)，或完整解压后打开 [离线 HTML](../../../output/audio-azure-volume-2/volume2-audio-audition/index.html)；生成结果见 [audio-generation.json](audio-generation.json)。真实 HTTP 手动播放、倍速及切换停止旧音轨已验证，IAB 禁止 `file://`，离线直接播放的实际验收尚未完成。

本轮 Azure Key 已在线验证有效，通过隐藏输入临时使用，未写 `.env`。计划中的 `speechCredentialsConfigured=false` 表示没有持久配置。听审仍为 **0 首批准、305 首待听校**，正式发布音轨和 App 可用第二卷音轨仍为 **0 首**；只有逐首听校、发布和完整性验证通过后才能开启产品播放。真机阅读、性能与朗读验收仍待完成，全部制作与接入成果仍为 `publicationReady=false`。
