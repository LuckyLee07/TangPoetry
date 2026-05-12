# 唐诗三百首最终内容源

最终内容源文件：

- `tang_poems_final.json`
- `poems/index.json`
- `poems/*.json`

生成脚本：

- `../../scripts/build_final_source.py`
- `../../scripts/split_final_poems.py`

## 定位

`tang_poems_final.json` 是后续 App 应优先依赖的内容数据源。

它优先负责诗词内容、书序、标题、作者、正文、注释、标签和来源追踪；当某些诗已经完成产品化视觉准备时，会在单诗内追加 `visual` 字段，保存插画路径、核心意象、情绪和构图提示。精选状态、阅读页布局等仍由产品层单独控制。

如果 App 需要按需加载单首诗，可以先读取 `poems/index.json`，再按 `path` 加载 `poems/*.json`。

## 来源策略

- 基础内容：`../../唐诗三百首.json`
- 原书顺序与标准展示标题：`../sources/ctext_clean.json`
- 繁体正文与英文译文：`../sources/ctext_clean.json`
- 注释补充：`../../唐诗三百首.json` 与 `../sources/chiuinan_clean.json`
- 标签补充：`../sources/tang300_new_dedup.json`

## 顶层结构

```json
{
  "schemaVersion": "1.0.0",
  "generatedAt": "2026-05-10T14:20:00+00:00",
  "name": "唐诗三百首最终内容源",
  "sourcePolicy": {},
  "stats": {},
  "poems": []
}
```

## 单诗文件

`poems/index.json` 是单诗文件清单：

```json
{
  "schemaVersion": "1.0.0",
  "generatedAt": "2026-05-10T14:30:00+00:00",
  "sourceFile": "data/final/tang_poems_final.json",
  "poemCount": 317,
  "poems": [
    {
      "id": "tang-001-gan-yu-qi-yi",
      "order": 1,
      "section": "五言古诗",
      "title": "感遇其一",
      "author": "张九龄",
      "path": "poems/001-tang-001-gan-yu-qi-yi.json"
    }
  ]
}
```

每个 `poems/*.json` 的结构：

```json
{
  "schemaVersion": "1.0.0",
  "generatedAt": "2026-05-10T14:30:00+00:00",
  "sourceFile": "data/final/tang_poems_final.json",
  "poem": {}
}
```

文件名使用 `书序-id.json`。由于当前基础数据缺少 CText 书序 43、134、278，单诗文件名也会跳过 `043`、`134`、`278`。

## 单首字段

核心字段：

- `id`：稳定内容 ID
- `order`：按 CText 书序排列的序号
- `section`：体裁分卷，如 `五言古诗`
- `title`：标准展示标题
- `titleTraditional`：繁体标题
- `author`：简体作者
- `authorTraditional`：繁体作者
- `dynasty`：朝代
- `aliases`：原始标题、异名
- `lines`：简体正文行
- `linesTraditional`：繁体正文行
- `text`：简体全文拼接
- `textTraditional`：繁体全文拼接
- `displayLines`：移动端默认展示短行
- `displayRubyLines`：`displayLines` 对应的注音数据
- `rubyLines`：`lines` 全文对应的注音数据
- `notes`：注释数组，带来源
- `tags`：体裁和补充标签
- `english`：CText 英译原文及轻清洗版本
- `sourceRefs`：所有来源与匹配信息
- `visual`：可选视觉字段，包含插画路径、核心意象、情绪、色板、构图和生成提示；当前已为 35 首 `五言古诗` 补齐

## 当前统计

- 当前收录：317 首
- CText 书序匹配：317 首
- chiuinan 匹配：310 首
- new 标签源匹配：306 首
- 有注释：227 首
- 五言古诗视觉字段：35 首
- 缺少的 CText 书序：43、134、278

## 使用建议

App 的数据层优先读取 `poems`。

列表、目录、阅读顺序使用 `order`。

当前原型前端已经改为读取 `poems/index.json`，再按 `path` 加载单诗文件。`../poems.json` 只是旧的原型展示快照，不再作为当前前端入口。

诗页标题使用 `title`，不要再使用 `sourceRefs.base.title` 或旧源标题。

注音优先使用 `rubyLines`。当前原型已改为渲染全文 `rubyLines`，长诗在诗文区域内纵向滚动。

五言古诗插图优先读取单诗 `visual.image`，资产位于 `../../assets/illustrations-wuyan-gushi/`。这批图保持 941×1672 竖版比例，目标风格为淡彩水墨、宣纸质感、大面积留白，便于叠加诗文与注释。

英文译文当前仅作资料保留，因为 CText 页面源码中的英文空格已经丢失，直接展示前需要另行校对。
