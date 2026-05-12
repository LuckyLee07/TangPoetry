# 唐诗三百首 App 产品开发文档

版本：v0.1  
日期：2026-05-10  
当前原型：`index.html`

## 1. 产品定位

《唐诗三百首》不是一个工具型诗词查询 App，而是一款手机竖屏的唐诗画笺阅读 App。

核心体验：

> 一页一诗，一诗一画。用户只是左右滑动翻诗，也觉得安静、舒服、心旷神怡。

产品气质：

- 安静
- 淡雅
- 有纸感
- 有留白
- 有书卷气
- 像一本手机里的唐诗画册

不追求一开始功能很多。第一阶段优先把“翻诗”体验做到漂亮。

## 2. 目标用户

主要用户：

- 想轻松读唐诗的普通用户
- 给孩子看唐诗的家长
- 喜欢中国风、插画、古诗词审美的用户
- 想每天安静翻几首诗的人

使用场景：

- 睡前翻几首诗
- 家长陪孩子读诗
- 通勤时轻阅读
- 想找一首熟悉的唐诗
- 收藏喜欢的诗页

## 3. 核心原则

后续任何功能都要先问：

> 它会不会打扰用户安静地翻诗？

如果会打扰，就放到二级页面。  
如果不会打扰，才允许出现在阅读页。

阅读页优先级：

1. 插画氛围
2. 诗文
3. 拼音
4. 标题和作者
5. 简短诗意
6. 注释和更多解释
7. 工具操作

## 4. MVP 范围

第一版建议只做这些：

- 20-30 首精品画笺诗页
- 300 首基础诗词数据
- 手机竖屏阅读器
- 左右滑动翻诗
- 目录索引
- 分类浏览
- 搜索
- 收藏
- 拼音开关
- 注释开关
- 基础设置

第一版不要做：

- 朗读
- 动画
- 复杂互动
- 诗词测验
- 社区
- 账号系统
- 会员系统
- 过度复杂的学习体系

这些可以后续再评估。

## 5. 页面结构

### 5.1 阅读页

App 打开后默认进入阅读页。

阅读页结构：

- 全屏竖版插画
- 横排诗文
- 带声调拼音
- 轻量标题和作者
- 底部脚注式诗意/简注
- 右侧轻量页码点
- 点击页面后显示工具栏

默认状态尽量少 UI。

可显示工具：

- 目录
- 收藏
- 拼音开关
- 简注开关
- 当前页码

### 5.2 目录页

目录页应该像“诗笺索引”，不是普通列表。

内容：

- 诗页缩略图
- 诗名
- 作者
- 分类
- 收藏状态

分类：

- 思乡
- 山水
- 春日
- 送别
- 边塞
- 田园
- 咏物
- 怀古

### 5.3 搜索页

搜索不应该抢首页权重。

支持：

- 按诗名搜索
- 按作者搜索
- 按诗句搜索
- 按分类筛选

视觉上保持克制，避免工具感太强。

### 5.4 设置页

设置项：

- 拼音默认开关
- 简注默认开关
- 字号
- 护眼纸色
- 收藏管理
- 关于 App

## 6. 数据结构

建议每首诗用 JSON 描述。

```json
{
  "id": "jing-ye-si",
  "title": "静夜思",
  "author": "李白",
  "dynasty": "唐",
  "category": ["思乡", "月夜"],
  "featured": true,
  "illustration": "jing-ye-si.png",
  "layout": {
    "template": "center-low",
    "poemTop": "47%",
    "poemLeft": "46px",
    "poemRight": "46px",
    "poemAlign": "center",
    "poemSize": "23px",
    "noteBottom": "42px"
  },
  "lines": [
    {
      "text": "床前明月光，",
      "pinyin": ["chuáng", "qián", "míng", "yuè", "guāng"]
    },
    {
      "text": "疑是地上霜。",
      "pinyin": ["yí", "shì", "dì", "shàng", "shuāng"]
    }
  ],
  "noteTitle": "月光入室，乡心随起",
  "shortMeaning": "夜里的月色像霜一样铺在床前，诗人抬头看月，又低头想起远方的故乡。",
  "annotations": [
    {
      "word": "疑",
      "meaning": "好像。"
    }
  ]
}
```

## 7. 版式模板

不能 300 首都手工调位置。建议先定义 5 套模板。

### 7.1 中下留白型

适合：

- 静夜思
- 江雪
- 登鹳雀楼

特点：

- 插画主体在上半部
- 诗文居中偏下
- 注释在底部

### 7.2 左下题诗型

适合：

- 鹿柴
- 山居秋暝
- 终南望余雪

特点：

- 右侧或上方保留景深
- 诗文偏左
- 空间更安静

### 7.3 右中轻读型

适合：

- 春晓
- 相思
- 鸟鸣涧

特点：

- 花枝、窗、人物在左侧
- 诗文偏右
- 适合轻快氛围

### 7.4 大留白孤景型

适合：

- 江雪
- 登幽州台歌
- 独坐敬亭山

特点：

- 大面积空白
- 诗文不要太大
- 注释更轻

### 7.5 送别远路型

适合：

- 送元二使安西
- 黄鹤楼送孟浩然之广陵
- 赠汪伦

特点：

- 画面需要有路、江、水、远方
- 诗文避开人物
- 情绪克制，不做戏剧化

## 8. 插画规范

插画是产品成败关键。

统一风格：

- 9:16 竖版
- 淡彩水墨
- 宣纸肌理
- 低饱和
- 有留白
- 细线条
- 不现代卡通
- 不厚重国潮
- 不大面积金色或深红

每张插画必须满足：

- 适合手机竖屏全屏使用
- 有明确诗意场景
- 给诗文留出空白区域
- 不出现文字
- 不出现现代物件
- 人物不要太大，除非诗本身需要
- 画面不要太满

推荐生成提示词结构：

```text
Create a single 9:16 vertical portrait illustration for the Tang poem <诗名> by <作者>. No text anywhere.
Scene/backdrop: <诗意场景>
Subject: <主体元素>
Style/medium: refined Chinese picture-book illustration, 淡彩水墨 watercolor and ink wash on warm xuan paper, elegant airy composition, hand-painted texture, soft ink linework.
Composition/framing: vertical 9:16 mobile artwork, full-bleed portrait, generous negative space for overlaid poem text.
Lighting/mood: tranquil, spacious, poetic, heart-clearing.
Color palette: warm ivory paper, pale ink gray, celadon green, muted blue, light ochre.
Constraints: no Chinese characters, no English words, no watermark, no UI elements, no modern objects, no dense clutter, no saturated colors.
```

## 9. 技术建议

### 9.1 iOS 实现方案

建议用 SwiftUI 开发。

核心模块：

- `PoemReaderView`
- `PoemPageView`
- `PoemLibraryView`
- `PoemSearchView`
- `PoemSettingsView`
- `PoemDataStore`
- `FavoriteStore`

### 9.2 排版实现

如果保留横排诗文，SwiftUI 原生即可。

需要注意：

- 拼音可用自定义 Ruby 组件模拟
- 每个汉字和拼音组合成一个小单元
- 每行诗句使用 `HStack`
- 多行诗句使用 `VStack`
- 拼音字号和灰度要独立控制

### 9.3 数据存储

第一版：

- 诗词数据：本地 JSON
- 收藏：UserDefaults 或 SwiftData
- 设置：UserDefaults

后续：

- 精品插画资源本地内置
- 普通诗词页可以使用统一背景

## 10. 开发里程碑

### 阶段 1：技术原型

目标：把当前 HTML 原型迁移成 SwiftUI 可运行版本。

任务：

- 搭建 SwiftUI 项目
- 加载本地 JSON
- 实现一页一诗
- 实现横向翻页
- 实现拼音显示
- 实现注释显示
- 接入 5 张竖版插画

### 阶段 2：产品原型

目标：形成可体验的 MVP。

任务：

- 扩展到 20-30 首精品诗
- 建立 5 套版式模板
- 做目录页
- 做搜索页
- 做收藏
- 做设置

### 阶段 3：内容扩展

目标：让产品看起来完整。

任务：

- 补齐 300 首基础诗词
- 建立分类体系
- 普通诗页使用统一淡背景
- 精品诗页使用专属插画

### 阶段 4：上架打磨

目标：达到可上架质量。

任务：

- 适配主流 iPhone 尺寸
- 检查文字重叠
- 检查拼音准确性
- 检查插画风格统一性
- 准备 App Icon
- 准备 App Store 截图
- 准备隐私说明

## 11. 当前原型已完成

当前 HTML 原型已具备：

- 手机竖屏阅读器
- 317 首基础诗库
- 5 首精品画笺诗页
- 5 张竖版插画
- 横排诗文
- 带声调拼音
- 注释脚注
- 左右滑动翻页
- 目录缩略图
- 收藏状态
- 拼音开关
- 简注开关
- 页点

当前原型文件：

- `index.html`
- `styles.css`
- `app.js`
- `data/final/tang_poems_final.json`
- `data/poems.json`
- `唐诗三百首.json`
- `scripts/build_poems.py`
- `scripts/build_final_source.py`
- `scripts/clean_book_sources.py`
- `data/raw_sources/`
- `data/sources/`
- `assets/illustrations-portrait/`

## 12. 数据层设计

当前数据层采用“最终内容源 + 产品展示数据”的结构：

0. `data/final/tang_poems_final.json`  
   后续 App 应优先依赖的最终内容源，共 317 首。它整合书序、标准标题、简繁正文、注释、标签、英文译文和来源追踪。

   生成脚本为 `scripts/build_final_source.py`。字段说明见 `data/final/README.md`。

1. `唐诗三百首.json`  
   用户提供的基础源数据，共 317 首。保留原始 `title / author / dynasty / paragraphs / notes`。

2. `data/raw_sources/`  
   保存外部网页原始 HTML，当前包括：

- `chiuinan.html`：邱奕南整理版，繁体正文、章节、注释较完整。
- `ctext.html`：Chinese Text Project 版，带编号顺序、繁体正文和英文译文。

3. `data/sources/`  
   由 `scripts/clean_book_sources.py` 清洗生成：

- `chiuinan_clean.json`：320 首，含繁体、简体、章节、注释。
- `ctext_clean.json`：320 首，含繁体、简体、章节、编号、英文译文。
- `ctext_book_order.json`：从 CText 抽出的编号顺序索引。
- `source_match_report.json`：外部源与当前 317 首基础数据的匹配报告。

4. `data/poems.json`  
   原型实际使用的产品数据，由 `scripts/build_poems.py` 生成，并按 CText 清洗源中的《唐诗三百首》编号顺序排列。

生成脚本负责：

- 以 `data/sources/ctext_clean.json` 的 `bookOrder` 作为主书序
- 使用 `data/sources/chiuinan_clean.json` 作为繁体正文、注释和版本校验参考
- 将原始诗文拆成适合手机展示的短行
- 生成带声调拼音
- 推断基础分类
- 标记精品诗页
- 合并 5 首精品诗的插画、版式和精修简注
- 保留 `plainLines` 作为全文数据
- 保留 `notes` 作为原始注释数据

外部源清洗原则：

- 繁体原文不覆盖简体主数据，而是作为独立字段保留。
- 简体字段只用于搜索、匹配和产品展示候选。
- 英文译文先保留 CText 原始文本，并做轻量标点清洗；由于网页源码中英文空格已经丢失，不在清洗阶段强行补词。
- 两个外部源都抽到 320 首，当前基础源为 317 首，差异通过匹配报告暴露。
- `scripts/build_poems.py` 会为每首产品诗写入 `bookOrder / bookSequence / bookSection / orderSource / orderConfidence`，方便目录排序和后续校对。

当前产品数据字段：

```json
{
  "id": "jing-ye-si",
  "sourceIndex": 1,
  "bookOrder": 99,
  "bookSequence": 99,
  "bookSection": "五言绝句",
  "orderSource": "ctext",
  "orderConfidence": "high",
  "title": "静夜思",
  "sourceTitle": "静夜思",
  "author": "李白",
  "dynasty": "唐代",
  "theme": "思乡",
  "categories": ["思乡", "月夜"],
  "featured": true,
  "mood": "月夜",
  "image": "assets/illustrations-portrait/jing-ye-si.png",
  "layout": "layout-right",
  "composition": {
    "poemTop": "47%",
    "poemLeft": "46px",
    "poemRight": "46px",
    "poemAlign": "center",
    "poemSize": "23px",
    "poemMaxWidth": "320px",
    "noteBottom": "42px"
  },
  "lines": [
    [["床", "chuáng"], ["前", "qián"], ["明", "míng"], ["月", "yuè"], ["光", "guāng"], ["，", ""]]
  ],
  "plainLines": ["床前明月光，疑是地上霜。"],
  "noteTitle": "月光入室，乡心随起",
  "note": "夜里的月色像霜一样铺在床前，诗人抬头看月，又低头想起远方的故乡。",
  "notes": [],
  "source": "唐诗三百首.json"
}
```

## 13. 下一步建议

下一步不要急着扩 300 首。

建议先做：

1. 把当前 5 首做到非常稳定。
2. 再扩到 10 首，验证模板是否够用。
3. 再扩到 30 首，形成第一批精品画笺。
4. 最后再补 300 首基础诗库。

真正要守住的是体验：

> 打开 App 后，用户愿意安静地一页一页翻下去。
