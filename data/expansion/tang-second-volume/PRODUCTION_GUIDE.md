# 第二卷诗意与插画制作稿

制作分支：`codex/volume-2`。本卷采用已确认的 305 首选目（304 首撷英对应篇目，加 1 首独立补选），第一卷 App 保持原状。

## 查看内容

在此工作目录启动本地服务：

```bash
python3 -m http.server 8767 --bind 127.0.0.1
```

打开 [第二卷独立预览](http://127.0.0.1:8767/tools/volume2-preview.html)。支持按诗题、作者、诗句搜索，按体裁筛选，逐首切换，隐藏诗文查看整幅画，以及阅读完整解读、词注与校勘笔记。长诗在诗文区域内滚动；本页用于内容审阅，不代表最终 App 排版。

## 数据与素材

- [production.json](production.json)：供预览和后续接入使用的汇总制作稿。保留稳定 ID、来源、诗意、解读、词注、插画路径和校订记录。
- [commentary/](commentary/)：305 首独立撰写的诗意初稿，包含简短诗意、分段解读、必要词注、来源依据和画面构思。
- [illustrations/receipts/](illustrations/receipts/)：逐张生成提示词、文件哈希、尺寸及实际视觉检查记录。返工记录见各回执中的修订历史与 illustrations/revisions.json。
- `assets/volume-2/poem-art/`：305 幅独立竖版 PNG 原图，使用内置图像工具生成。采用暖纸水墨风格，保留下部阅读留白。素材按现有规则忽略，不提交 Git。
- [poems.json](poems.json)：原始整理底本，保持不变。
- [text-proposals/](text-proposals/) 与 [text-corrections.json](text-corrections.json)：有证据的校订建议及本次编辑预览采用的版本；校订前原文也保存在制作稿 `sourceText` 中。
- [EDITORIAL_NOTES.md](EDITORIAL_NOTES.md)：异文、解释边界和后续定稿注意事项；不是将所有异文都认作错字。
- [SEMANTIC_REVIEW.md](SEMANTIC_REVIEW.md)：305首的原诗意旨、具体对应、修订和解释分歧；字段前后稿见 semantic-review-audit.json。
- [production-audit.json](production-audit.json)：最新图文覆盖、数量、素材哈希和完整性检查结果。

诗意为依据原诗重新撰写的现代解读，没有复制第三方现代译注。插画按每首的季节、人物、物象和情境分别制作；生成中的错误候选经过筛选或返工后才保存为接受稿。

## 重建与检查

```bash
python3 scripts/build_volume2_production.py --require-complete
python3 scripts/build_volume2_production.py --check --require-complete
python3 tests/tang_second_volume_test.py
python3 scripts/check_volume2_semantic_review.py
```

构建会核对 305 个稳定 ID、每首字段、原文哈希、校订前文本、PNG 尺寸和 SHA-256，并检查是否误用同一文件。它不会调用付费接口，不会重新生成插画，也不会把第二卷导入第一卷 App。

后续如需另生成某首插画，可以用 `scripts/volume2_art_jobs.py --from 序号 --to 序号 --include-existing` 获取保存的统一风格与逐诗提示词，再用内置图像工具生成。必须实际查看结果，记录检查结论；`scripts/record_volume2_art.py` 用于复制原图和写入回执，不负责生成或自动判定画面质量。

## 当前边界

本批是完整的图文编辑初稿，`publicationReady=false`。诗文出处及疑点有记录，但已完成305首逐首语义复核，修订29首读者可见释义，另为1首补明解释笔记；并未宣称逐页对过《唐诗撷英》纸书，也不能以自动校验代替文字终审。后续正式接入时，还需处理展示题名、体裁与长篇排版、原图压缩及整卷真人审阅。没有在本次制作中生成第二卷朗读音频。
