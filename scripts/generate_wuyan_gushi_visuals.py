#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import random
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "final" / "tang_poems_final.json"
OUT_DIR = ROOT / "assets" / "illustrations-wuyan-gushi"
WIDTH = 941
HEIGHT = 1672
SECTION = "五言古诗"
STYLE_TEMPLATES = {
    "spring": ROOT / "assets" / "illustrations-portrait" / "chun-xiao.png",
    "snow_water": ROOT / "assets" / "illustrations-portrait" / "jiang-xue.png",
    "moon_room": ROOT / "assets" / "illustrations-portrait" / "jing-ye-si.png",
    "forest": ROOT / "assets" / "illustrations-portrait" / "lu-zhai.png",
    "willow_farewell": ROOT / "assets" / "illustrations-portrait" / "song-yuan-er.png",
}

STYLE_NOTE = "竖版淡彩水墨，宣纸质感，低饱和留白，与现有五张阅读页插图保持一致"


VISUALS = {
    "tang-001-gan-yu-qi-yi": {
        "coreImagery": ["孤鸿", "沧海", "翠鸟", "珠树"],
        "mood": ["清高", "警觉", "孤远"],
        "palette": ["雾青", "浅赭", "墨灰", "淡金"],
        "composition": "孤鸿掠过辽阔水面，远处一枝珠树隐在雾色里，画面上半部保留大面积空白。",
        "motifs": ["sea", "bird", "tree", "mist"],
    },
    "tang-002-gan-yu-qi-er": {
        "coreImagery": ["兰叶", "桂花", "春风", "秋露"],
        "mood": ["澄明", "自持", "幽香"],
        "palette": ["兰青", "桂金", "米白", "浅绿"],
        "composition": "兰叶自下舒展，桂枝在上方轻垂，春秋之气交汇成清淡花雾。",
        "motifs": ["orchid", "osmanthus", "mist"],
    },
    "tang-003-gan-yu-qi-san": {
        "coreImagery": ["幽人", "高鸟", "孤云"],
        "mood": ["孤清", "高远", "不合流俗"],
        "palette": ["云灰", "松绿", "淡青", "墨色"],
        "composition": "山坳中一位幽人远望，高鸟从云隙飞过，人与天地之间留出疏朗距离。",
        "motifs": ["mountain", "figure", "bird", "cloud"],
    },
    "tang-004-gan-yu-qi-si": {
        "coreImagery": ["江南丹橘", "岁寒", "绿叶", "嘉树"],
        "mood": ["坚贞", "温厚", "自守"],
        "palette": ["橘红", "苔绿", "暖纸", "淡墨"],
        "composition": "一株丹橘立在江南薄雾中，枝叶丰润，橘果只作点睛。",
        "motifs": ["orange_tree", "river", "mist"],
    },
    "tang-005-xia-zhong-nan-shan-guo-hu-si-shan-ren-su-zhi-jiu": {
        "coreImagery": ["终南山", "松风", "绿竹", "山人夜酒"],
        "mood": ["闲适", "酣畅", "入山"],
        "palette": ["山青", "竹绿", "酒褐", "月白"],
        "composition": "终南山层层退远，竹径引向一间灯火小屋，月色与松风笼住夜饮。",
        "motifs": ["mountain", "bamboo", "house", "moon"],
    },
    "tang-006-yue-xia-du-zhuo": {
        "coreImagery": ["花间酒", "明月", "身影", "独酌"],
        "mood": ["孤独", "旷达", "微醺"],
        "palette": ["月白", "花粉", "酒金", "夜青"],
        "composition": "花影低垂，一壶酒置于月下，人物与影子相对而坐。",
        "motifs": ["moon", "flowers", "wine", "figure"],
    },
    "tang-007-chun-si": {
        "coreImagery": ["燕草", "秦桑", "罗帏", "春风"],
        "mood": ["相思", "柔婉", "春怨"],
        "palette": ["桑绿", "浅粉", "帘白", "春青"],
        "composition": "帘幕半卷，桑叶与远草在春风里相望，室内留一角静空。",
        "motifs": ["curtain", "mulberry", "grass", "wind"],
    },
    "tang-008-wang-yue": {
        "coreImagery": ["泰山", "层云", "归鸟", "日色"],
        "mood": ["壮阔", "昂扬", "开张"],
        "palette": ["岱青", "云白", "日金", "深墨"],
        "composition": "泰山自画面底部拔起，层云从峰腰裂开，归鸟穿过日光。",
        "motifs": ["mountain", "cloud", "bird", "sun"],
    },
    "tang-009-zeng-wei-ba-chu-shi": {
        "coreImagery": ["灯烛", "老友", "夜雨", "春韭"],
        "mood": ["温厚", "久别", "人间烟火"],
        "palette": ["烛金", "雨青", "韭绿", "暖褐"],
        "composition": "雨夜小屋透出暖灯，案上春韭与酒盏，窗外雨线细密。",
        "motifs": ["house", "rain", "lantern", "grass"],
    },
    "tang-010-jia-ren": {
        "coreImagery": ["空谷", "佳人", "修竹", "寒袖"],
        "mood": ["清冷", "哀婉", "孤贞"],
        "palette": ["竹青", "冷白", "淡墨", "苍绿"],
        "composition": "空谷修竹间，一位女子侧身独立，衣袖被寒风轻轻吹起。",
        "motifs": ["bamboo", "figure", "valley", "wind"],
    },
    "tang-011-meng-li-bai-zhi-yi": {
        "coreImagery": ["梦魂", "落月", "江南瘴疠", "浮云"],
        "mood": ["深切", "忧惧", "牵挂"],
        "palette": ["月灰", "雾青", "冷紫", "淡墨"],
        "composition": "残月低斜，水雾与云气在江面漂浮，远处人影如梦中归来。",
        "motifs": ["moon", "river", "cloud", "figure"],
    },
    "tang-012-meng-li-bai-zhi-er": {
        "coreImagery": ["浮云", "游子", "落月", "梦归"],
        "mood": ["寂寞", "怅惘", "不安"],
        "palette": ["云灰", "夜青", "月白", "苍墨"],
        "composition": "浮云压着远山，游子背影在月光下渐远，画面边缘像梦境散开。",
        "motifs": ["cloud", "mountain", "moon", "traveler"],
    },
    "tang-013-song-bie": {
        "coreImagery": ["下马饮酒", "南山", "白云", "归隐"],
        "mood": ["送别", "淡泊", "释然"],
        "palette": ["山青", "云白", "酒褐", "草绿"],
        "composition": "山脚两人下马对饮，南山与白云在远处静静铺开。",
        "motifs": ["mountain", "horse", "wine", "cloud"],
    },
    "tang-014-song-qi-wu-qian-luo-di-huan-xiang": {
        "coreImagery": ["落第归乡", "长安道", "桂棹", "孤城落晖"],
        "mood": ["慰勉", "失意", "远行"],
        "palette": ["落晖金", "道尘灰", "水青", "城墨"],
        "composition": "长安城在落日中后退，一叶归舟与长路构成离开的方向。",
        "motifs": ["city", "sun", "boat", "road"],
    },
    "tang-015-qing-xi": {
        "coreImagery": ["青溪", "乱石", "松林", "菱荇"],
        "mood": ["清幽", "自在", "澄澈"],
        "palette": ["溪青", "松绿", "石灰", "水白"],
        "composition": "溪水绕乱石流过，松影落在水面，菱荇在前景轻轻漂浮。",
        "motifs": ["stream", "rocks", "pine", "water_plants"],
    },
    "tang-016-wei-chuan-tian-jia": {
        "coreImagery": ["渭川田家", "牛羊归", "麦苗", "蚕眠"],
        "mood": ["田园", "羡闲", "安稳"],
        "palette": ["麦绿", "暮金", "土褐", "烟白"],
        "composition": "暮色中的田畴低平展开，牛羊沿小径归来，村烟在远处升起。",
        "motifs": ["field", "animals", "village", "sun"],
    },
    "tang-017-xi-shi-yong": {
        "coreImagery": ["越溪女", "吴宫", "罗衣", "香粉"],
        "mood": ["盛衰", "怜惜", "幽叹"],
        "palette": ["胭脂粉", "宫墙红", "溪青", "旧金"],
        "composition": "溪边女子与远处宫墙形成对照，华丽色彩被水雾冲淡。",
        "motifs": ["river", "figure", "palace", "flowers"],
    },
    "tang-018-qiu-deng-lan-shan-ji-zhang-wu": {
        "coreImagery": ["北山白云", "秋雁", "沙行渡头", "月洲"],
        "mood": ["秋兴", "邀约", "清旷"],
        "palette": ["秋金", "云白", "水蓝", "沙褐"],
        "composition": "秋山与白云高远，雁阵经过渡头，水洲映出淡月。",
        "motifs": ["mountain", "cloud", "geese", "river"],
    },
    "tang-019-xia-ri-nan-ting-huai-xin-da": {
        "coreImagery": ["南亭", "荷风", "竹露", "月池"],
        "mood": ["清凉", "怀友", "舒展"],
        "palette": ["荷绿", "月白", "竹青", "水蓝"],
        "composition": "南亭临水，荷叶与竹影分置两侧，月色落在池心。",
        "motifs": ["pavilion", "lotus", "bamboo", "moon"],
    },
    "tang-020-su-ye-shi-shan-fang-dai-ding-da-bu-zhi": {
        "coreImagery": ["西岭夕阳", "松月", "风泉", "孤琴"],
        "mood": ["静候", "幽寂", "失约"],
        "palette": ["夕金", "松墨", "泉白", "夜青"],
        "composition": "山房前有空席与孤琴，夕光将尽，松间泉声化成淡线。",
        "motifs": ["mountain", "house", "pine", "zither"],
    },
    "tang-021-tong-cong-di-nan-zhai-wan-yue-yi-shan-yin-cui-shao-fu": {
        "coreImagery": ["南斋", "明月", "清辉水木", "越吟"],
        "mood": ["皎洁", "怀人", "清雅"],
        "palette": ["月白", "水青", "木绿", "夜蓝"],
        "composition": "书斋临水，月光穿过树影铺在岸边，远处留出怀人的空白。",
        "motifs": ["house", "moon", "water", "trees"],
    },
    "tang-022-xun-xi-shan-yin-zhe-bu-yu": {
        "coreImagery": ["绝顶茅茨", "柴车", "秋水", "松声"],
        "mood": ["寻隐", "怅然", "清寒"],
        "palette": ["秋褐", "松绿", "水灰", "茅草黄"],
        "composition": "山顶茅屋空寂，柴车停在路旁，秋水从石间转出。",
        "motifs": ["mountain", "hut", "cart", "pine"],
    },
    "tang-023-chun-fan-ruo-ye-xi": {
        "coreImagery": ["若耶溪", "晚风行舟", "花路", "月潭"],
        "mood": ["幽意", "随缘", "清游"],
        "palette": ["溪青", "花粉", "月白", "暮紫"],
        "composition": "小舟沿花岸入溪，远处月影落潭，水路弯向画面深处。",
        "motifs": ["boat", "stream", "flowers", "moon"],
    },
    "tang-024-su-wang-chang-ling-yin-ju": {
        "coreImagery": ["清溪", "孤云", "松月", "隐居"],
        "mood": ["清寂", "怀友", "幽深"],
        "palette": ["溪青", "松绿", "云白", "月灰"],
        "composition": "隐居小屋被松影掩映，孤云在溪上停住，月光淡淡。",
        "motifs": ["house", "stream", "pine", "moon"],
    },
    "tang-025-yu-gao-shi-xue-ju-deng-ci-en-si-fu-tu": {
        "coreImagery": ["慈恩寺浮图", "高塔", "天宫", "长安"],
        "mood": ["登临", "苍茫", "肃穆"],
        "palette": ["塔灰", "天青", "城褐", "云白"],
        "composition": "高塔贯穿画面纵轴，长安城低伏在云雾下，视线向天际提升。",
        "motifs": ["pagoda", "city", "cloud", "sun"],
    },
    "tang-026-zei-tui-shi-guan-li-bing-xu": {
        "coreImagery": ["贼退", "荒村", "官吏", "山林"],
        "mood": ["沉痛", "讽谕", "荒寒"],
        "palette": ["土灰", "枯黄", "墨黑", "冷白"],
        "composition": "荒村空路与远山相接，残破篱落前只有冷风与稀疏树影。",
        "motifs": ["village", "bare_tree", "road", "mountain"],
    },
    "tang-027-jun-zhai-yu-zhong-yu-zhu-wen-shi-yan-ji": {
        "coreImagery": ["郡斋雨", "画戟", "文士宴", "海风"],
        "mood": ["清雅", "从容", "雨意"],
        "palette": ["雨青", "墨灰", "酒金", "苔绿"],
        "composition": "郡斋檐下雨线不断，室内几案雅集，窗外海风吹开竹影。",
        "motifs": ["house", "rain", "lantern", "bamboo"],
    },
    "tang-028-chu-fa-yang-zi-ji-yuan-da-xiao-shu": {
        "coreImagery": ["扬子江雾", "归棹", "残钟", "广陵树"],
        "mood": ["离别", "茫然", "清远"],
        "palette": ["江青", "雾白", "钟铜", "树绿"],
        "composition": "雾中归棹渐远，岸边树影和钟声都被江色化淡。",
        "motifs": ["river", "boat", "mist", "trees"],
    },
    "tang-029-ji-quan-jiao-shan-zhong-dao-shi": {
        "coreImagery": ["山中道士", "涧底荆薪", "白石", "郡斋冷"],
        "mood": ["清寒", "挂念", "幽远"],
        "palette": ["石白", "涧青", "松绿", "冷灰"],
        "composition": "涧底白石与荆薪在前，山路消失在雾里，似有道士未归。",
        "motifs": ["stream", "rocks", "pine", "path"],
    },
    "tang-030-chang-an-yu-feng-zhu": {
        "coreImagery": ["灞陵雨", "客衣", "长安相逢"],
        "mood": ["萧瑟", "问候", "旅况"],
        "palette": ["雨灰", "城褐", "衣青", "柳绿"],
        "composition": "长安雨中，两位旅人隔着湿润街道相逢，远处城门低隐。",
        "motifs": ["rain", "city", "figures", "road"],
    },
    "tang-031-xi-ci-xu-yi-xian": {
        "coreImagery": ["淮镇孤驿", "风波", "暗山", "芦洲雁"],
        "mood": ["羁旅", "乡思", "凄清"],
        "palette": ["芦白", "水灰", "山青", "暮紫"],
        "composition": "孤驿临水，芦洲雁影掠过暗山，风波使江面略带不安。",
        "motifs": ["river", "geese", "reeds", "house"],
    },
    "tang-032-dong-jiao": {
        "coreImagery": ["东郊", "杨柳", "青山", "微雨", "春鸠"],
        "mood": ["疏朗", "释怀", "春晴"],
        "palette": ["柳绿", "山青", "雨白", "土黄"],
        "composition": "东郊雨后，柳色明净，青山在远处展开，春鸠点在空中。",
        "motifs": ["willow", "mountain", "rain", "bird"],
    },
    "tang-033-song-yang-shi-nv": {
        "coreImagery": ["杨氏女", "大江轻舟", "幼女出嫁", "慈父"],
        "mood": ["不舍", "温柔", "怜爱"],
        "palette": ["江青", "嫁衣粉", "暖褐", "云白"],
        "composition": "江边轻舟将发，父女身影被留在柔和晨雾中，岸线低而安静。",
        "motifs": ["river", "boat", "figures", "mist"],
    },
    "tang-034-chen-yi-chao-shi-yuan-du-chan-jing": {
        "coreImagery": ["禅院", "汲井", "贝叶经", "晨光"],
        "mood": ["清净", "悟道", "澄澈"],
        "palette": ["晨金", "井青", "寺灰", "叶绿"],
        "composition": "晨光入禅院，井栏、经卷与疏竹各安其位，气息极静。",
        "motifs": ["temple", "well", "bamboo", "sun"],
    },
    "tang-035-xi-ju": {
        "coreImagery": ["溪居", "农圃", "山林客", "耕钓"],
        "mood": ["闲适", "释然", "自得"],
        "palette": ["溪青", "田绿", "山灰", "纸白"],
        "composition": "溪边小居与菜圃相邻，远山淡退，一竿钓影落在水边。",
        "motifs": ["stream", "field", "hut", "fishing"],
    },
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def rgba(color: tuple[int, int, int], alpha: int) -> tuple[int, int, int, int]:
    return color[0], color[1], color[2], alpha


def paper_background(seed: int) -> Image.Image:
    rng = random.Random(seed)
    img = Image.new("RGB", (WIDTH, HEIGHT), (236, 230, 212))
    pixels = img.load()
    for y in range(HEIGHT):
        wash = int(8 * math.sin(y / 210) + 4 * math.sin(y / 53))
        for x in range(WIDTH):
            n = rng.randint(-7, 6)
            base = 235 + n + wash
            pixels[x, y] = (
                max(205, min(250, base + 2)),
                max(200, min(244, base - 3)),
                max(185, min(235, base - 16)),
            )
    return img.filter(ImageFilter.GaussianBlur(0.28)).convert("RGBA")


def choose_template(motifs: set[str]) -> Path:
    if {"curtain", "moon", "zither", "well"} & motifs and not {"boat", "river", "stream"} & motifs:
        return STYLE_TEMPLATES["moon_room"]
    if {"willow", "road", "city", "figures", "horse", "cart"} & motifs:
        return STYLE_TEMPLATES["willow_farewell"]
    if {"boat", "river", "sea", "reeds", "geese", "fishing"} & motifs:
        return STYLE_TEMPLATES["snow_water"]
    if {"flowers", "orchid", "osmanthus", "orange_tree", "mulberry", "field", "animals"} & motifs:
        return STYLE_TEMPLATES["spring"]
    return STYLE_TEMPLATES["forest"]


def template_background(motifs: set[str], seed: int) -> Image.Image:
    template = Image.open(choose_template(motifs)).convert("RGBA").resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
    paper = paper_background(seed)
    img = Image.blend(template, paper, 0.16)

    veil = Image.new("RGBA", (WIDTH, HEIGHT), (236, 230, 212, 0))
    d = ImageDraw.Draw(veil, "RGBA")
    d.rectangle((0, 0, WIDTH, HEIGHT), fill=(236, 230, 212, 34))
    d.rectangle((0, int(HEIGHT * 0.30), WIDTH, int(HEIGHT * 0.76)), fill=(236, 230, 212, 24))
    img.alpha_composite(veil.filter(ImageFilter.GaussianBlur(18)))
    return img


def add_wash(layer: Image.Image, bbox: tuple[int, int, int, int], color: tuple[int, int, int], alpha: int) -> None:
    wash = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    d = ImageDraw.Draw(wash, "RGBA")
    d.ellipse(bbox, fill=rgba(color, alpha))
    layer.alpha_composite(wash.filter(ImageFilter.GaussianBlur(58)))


def draw_mountains(draw: ImageDraw.ImageDraw, rng: random.Random, y: int, color=(75, 99, 95), alpha=78) -> None:
    for band in range(3):
        points = [(-80, HEIGHT)]
        step = 130
        for x in range(-60, WIDTH + 160, step):
            peak = y + band * 70 + rng.randint(-70, 56)
            points.append((x, peak))
            points.append((x + step // 2, peak - rng.randint(40, 120)))
        points.extend([(WIDTH + 80, HEIGHT), (-80, HEIGHT)])
        draw.polygon(points, fill=rgba(color, max(24, alpha - band * 20)))


def draw_water(draw: ImageDraw.ImageDraw, rng: random.Random, top: int, color=(74, 125, 135)) -> None:
    draw.rectangle((0, top, WIDTH, HEIGHT), fill=rgba(color, 26))
    for i in range(28):
        y = top + i * rng.randint(18, 35) + rng.randint(-8, 8)
        x0 = rng.randint(-50, WIDTH - 120)
        x1 = min(WIDTH + 40, x0 + rng.randint(120, 430))
        draw.arc((x0, y, x1, y + rng.randint(14, 34)), 185, 355, fill=rgba((72, 98, 105), rng.randint(18, 42)), width=2)


def draw_tree(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float, color=(50, 94, 74), kind="pine") -> None:
    trunk = rgba((82, 67, 48), 105)
    draw.line((x, y, x + int(10 * scale), y - int(260 * scale)), fill=trunk, width=max(2, int(7 * scale)))
    if kind == "willow":
        for i in range(16):
            dx = int((i - 8) * 12 * scale)
            draw.line((x + dx, y - int(245 * scale), x + dx + int(18 * scale), y - int(60 * scale)), fill=rgba(color, 70), width=2)
    else:
        for i in range(8):
            yy = y - int((70 + i * 26) * scale)
            span = int((120 - i * 8) * scale)
            draw.line((x - span, yy, x + span, yy - int(25 * scale)), fill=rgba(color, 72), width=max(2, int(5 * scale)))


def draw_bamboo(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float) -> None:
    for stem in range(7):
        sx = x + int((stem - 3) * 22 * scale)
        top = y - int((330 + stem * 9) * scale)
        draw.line((sx, y, sx + int(25 * scale), top), fill=rgba((48, 108, 76), 92), width=max(2, int(5 * scale)))
        for j in range(8):
            yy = y - int((42 + j * 38) * scale)
            draw.line((sx + int(4 * j * scale), yy, sx + int(65 * scale), yy - int(20 * scale)), fill=rgba((57, 126, 82), 62), width=2)


def draw_house(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float, temple=False) -> None:
    w = int(190 * scale)
    h = int(110 * scale)
    roof = rgba((83, 72, 58), 96)
    wall = rgba((232, 221, 195), 135)
    draw.polygon([(x - w // 2, y - h), (x, y - h - int(72 * scale)), (x + w // 2, y - h)], fill=roof)
    draw.rectangle((x - w // 2 + int(18 * scale), y - h, x + w // 2 - int(18 * scale), y), fill=wall)
    draw.rectangle((x - int(24 * scale), y - int(58 * scale), x + int(24 * scale), y), fill=rgba((80, 63, 43), 90))
    if temple:
        draw.arc((x - w // 2, y - h - int(94 * scale), x + w // 2, y - h - int(35 * scale)), 190, 350, fill=roof, width=max(2, int(5 * scale)))


def draw_boat(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float) -> None:
    hull = rgba((75, 63, 47), 112)
    draw.pieslice((x - int(110 * scale), y - int(35 * scale), x + int(130 * scale), y + int(45 * scale)), 0, 180, fill=hull)
    draw.line((x - int(25 * scale), y - int(25 * scale), x + int(30 * scale), y - int(145 * scale)), fill=rgba((70, 62, 52), 90), width=max(2, int(5 * scale)))
    draw.polygon(
        [(x + int(30 * scale), y - int(145 * scale)), (x + int(92 * scale), y - int(45 * scale)), (x - int(5 * scale), y - int(52 * scale))],
        fill=rgba((225, 218, 196), 98),
    )


def draw_figure(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float, pair=False) -> None:
    for offset in ([0, int(45 * scale)] if pair else [0]):
        sx = x + offset
        draw.ellipse((sx - int(12 * scale), y - int(92 * scale), sx + int(12 * scale), y - int(68 * scale)), fill=rgba((58, 50, 44), 100))
        draw.line((sx, y - int(66 * scale), sx - int(20 * scale), y), fill=rgba((55, 64, 65), 115), width=max(3, int(9 * scale)))
        draw.line((sx, y - int(50 * scale), sx + int(26 * scale), y - int(8 * scale)), fill=rgba((55, 64, 65), 90), width=max(2, int(5 * scale)))


def draw_birds(draw: ImageDraw.ImageDraw, rng: random.Random, count: int, y: int) -> None:
    for _ in range(count):
        x = rng.randint(80, WIDTH - 100)
        yy = y + rng.randint(-130, 130)
        s = rng.randint(14, 30)
        draw.arc((x - s, yy - s // 2, x, yy + s // 2), 200, 340, fill=rgba((46, 49, 47), 94), width=2)
        draw.arc((x, yy - s // 2, x + s, yy + s // 2), 200, 340, fill=rgba((46, 49, 47), 94), width=2)


def draw_flowers(draw: ImageDraw.ImageDraw, rng: random.Random, x: int, y: int, color=(196, 122, 116)) -> None:
    for _ in range(42):
        px = x + rng.randint(-150, 150)
        py = y + rng.randint(-150, 120)
        r = rng.randint(3, 8)
        draw.ellipse((px - r, py - r, px + r, py + r), fill=rgba(color, rng.randint(45, 86)))


def draw_pagoda(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float) -> None:
    for level in range(7):
        yy = y - int(level * 95 * scale)
        w = int((180 - level * 12) * scale)
        draw.rectangle((x - w // 3, yy - int(68 * scale), x + w // 3, yy), fill=rgba((112, 100, 86), 82))
        draw.polygon([(x - w // 2, yy - int(64 * scale)), (x, yy - int(103 * scale)), (x + w // 2, yy - int(64 * scale))], fill=rgba((78, 72, 64), 104))
    draw.line((x, y - int(760 * scale), x, y - int(850 * scale)), fill=rgba((78, 72, 64), 80), width=2)


def draw_fields(draw: ImageDraw.ImageDraw, rng: random.Random, top: int) -> None:
    for i in range(6):
        y = top + i * 72
        draw.line((0, y, WIDTH, y + rng.randint(-30, 35)), fill=rgba((104, 132, 82), 50), width=3)
    for x in range(-100, WIDTH, 90):
        draw.line((x, top, x + rng.randint(40, 160), HEIGHT), fill=rgba((126, 118, 76), 36), width=2)


def draw_asset(poem_id: str, filename: str, visual: dict, index: int) -> None:
    target = OUT_DIR / filename
    if poem_id == "tang-001-gan-yu-qi-yi" and target.exists():
        img = Image.open(target).convert("RGBA")
        if img.size != (WIDTH, HEIGHT):
            img = img.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
        img.save(target)
        return

    seed = 7300 + index * 97
    rng = random.Random(seed)
    motifs = set(visual["motifs"])
    img = template_background(motifs, seed)
    layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer, "RGBA")

    add_wash(layer, (-160, 120, 780, 980), (132, 159, 154), 18)
    add_wash(layer, (240, 680, 1160, 1530), (197, 170, 119), 14)
    if {"moon", "night"} & motifs:
        add_wash(layer, (180, 80, 760, 660), (126, 149, 170), 18)
    if "sun" in motifs:
        add_wash(layer, (520, 120, 900, 500), (218, 170, 83), 20)

    if "mountain" in motifs or "valley" in motifs:
        draw_mountains(draw, rng, rng.randint(640, 860), alpha=82)
    if "river" in motifs or "stream" in motifs or "sea" in motifs or "water" in motifs:
        draw_water(draw, rng, rng.randint(1010, 1210), color=(62, 123, 137))
    if "field" in motifs:
        draw_fields(draw, rng, 1000)
    if "road" in motifs or "path" in motifs:
        draw.polygon([(390, HEIGHT), (540, HEIGHT), (490, 980), (450, 980)], fill=rgba((152, 134, 92), 32))

    if "moon" in motifs:
        mx, my = rng.randint(575, 760), rng.randint(210, 395)
        draw.ellipse((mx - 58, my - 58, mx + 58, my + 58), fill=rgba((247, 241, 215), 118))
    if "sun" in motifs:
        sx, sy = rng.randint(620, 790), rng.randint(260, 470)
        draw.ellipse((sx - 70, sy - 70, sx + 70, sy + 70), fill=rgba((221, 168, 76), 76))

    if "pagoda" in motifs:
        draw_pagoda(draw, 505, 1245, 0.82)
    if "city" in motifs or "palace" in motifs:
        base = 1160
        draw.rectangle((95, base - 120, 835, base), fill=rgba((102, 82, 67), 58))
        for x in range(130, 800, 110):
            draw.rectangle((x, base - 180, x + 58, base - 118), fill=rgba((104, 80, 64), 55))

    if "house" in motifs or "hut" in motifs or "village" in motifs or "temple" in motifs:
        draw_house(draw, rng.randint(295, 650), rng.randint(1070, 1290), rng.uniform(0.62, 0.86), temple="temple" in motifs)
    if "well" in motifs:
        x, y = 360, 1210
        draw.ellipse((x - 62, y - 22, x + 62, y + 22), outline=rgba((88, 92, 78), 90), width=4)
        draw.rectangle((x - 56, y - 6, x + 56, y + 70), outline=rgba((88, 92, 78), 70), width=3)
    if "boat" in motifs:
        draw_boat(draw, rng.randint(310, 630), rng.randint(1170, 1390), rng.uniform(0.62, 0.9))
    if "horse" in motifs or "cart" in motifs:
        x, y = 560, 1260
        draw.line((x - 80, y, x + 110, y), fill=rgba((72, 62, 50), 95), width=8)
        draw.ellipse((x - 58, y + 10, x - 18, y + 50), outline=rgba((72, 62, 50), 90), width=4)
        draw.ellipse((x + 58, y + 10, x + 98, y + 50), outline=rgba((72, 62, 50), 90), width=4)

    if "bamboo" in motifs:
        draw_bamboo(draw, rng.randint(165, 310), rng.randint(1280, 1470), rng.uniform(0.85, 1.16))
    if "pine" in motifs or "trees" in motifs or "tree" in motifs:
        for _ in range(2 if "pine" in motifs else 1):
            draw_tree(draw, rng.randint(120, 820), rng.randint(1200, 1510), rng.uniform(0.7, 1.05), kind="pine")
    if "willow" in motifs:
        draw_tree(draw, 220, 1380, 1.12, color=(83, 136, 79), kind="willow")
    if "bare_tree" in motifs:
        x, y = 250, 1360
        draw.line((x, y, x + 18, y - 310), fill=rgba((78, 64, 54), 82), width=6)
        for i in range(11):
            yy = y - 80 - i * 21
            draw.line((x + 6, yy, x + rng.randint(-85, 90), yy - rng.randint(35, 86)), fill=rgba((78, 64, 54), 58), width=2)
    if "orange_tree" in motifs:
        draw_tree(draw, 610, 1335, 0.9, color=(57, 113, 72), kind="pine")
        for _ in range(18):
            px, py = rng.randint(505, 740), rng.randint(960, 1260)
            draw.ellipse((px - 10, py - 10, px + 10, py + 10), fill=rgba((207, 102, 48), 82))
    if "orchid" in motifs or "grass" in motifs or "water_plants" in motifs:
        for _ in range(36):
            x = rng.randint(80, WIDTH - 80)
            y = rng.randint(1250, 1580)
            draw.line((x, y, x + rng.randint(-22, 22), y - rng.randint(45, 150)), fill=rgba((73, 126, 84), rng.randint(34, 72)), width=2)
    if "osmanthus" in motifs:
        draw_tree(draw, 700, 1180, 0.7, color=(94, 123, 72), kind="pine")
        for _ in range(34):
            px, py = rng.randint(590, 810), rng.randint(780, 1040)
            draw.ellipse((px - 5, py - 5, px + 5, py + 5), fill=rgba((211, 162, 64), 74))
    if "mulberry" in motifs:
        draw_tree(draw, 660, 1340, 0.8, color=(77, 127, 78), kind="pine")
    if "lotus" in motifs:
        for _ in range(16):
            x, y = rng.randint(90, 840), rng.randint(1190, 1490)
            draw.ellipse((x - 32, y - 14, x + 32, y + 14), fill=rgba((88, 139, 100), 58))
            if rng.random() > 0.55:
                draw.ellipse((x - 8, y - 26, x + 8, y - 8), fill=rgba((198, 126, 139), 60))
    if "flowers" in motifs:
        draw_flowers(draw, rng, rng.randint(220, 700), rng.randint(980, 1330))
    if "curtain" in motifs:
        draw.rectangle((72, 250, 225, 1110), fill=rgba((219, 202, 180), 44))
        for x in range(82, 220, 32):
            draw.line((x, 250, x + rng.randint(-18, 24), 1110), fill=rgba((152, 116, 99), 30), width=3)

    if "rain" in motifs:
        for _ in range(105):
            x, y = rng.randint(0, WIDTH), rng.randint(150, HEIGHT - 150)
            draw.line((x, y, x + rng.randint(-8, 8), y + rng.randint(45, 95)), fill=rgba((96, 118, 124), rng.randint(22, 48)), width=1)
    if "reeds" in motifs:
        for x in range(60, WIDTH, 34):
            y = rng.randint(1320, 1590)
            draw.line((x, HEIGHT, x + rng.randint(-35, 28), y), fill=rgba((134, 124, 82), 60), width=2)
    if "zither" in motifs:
        draw.polygon([(330, 1260), (620, 1230), (650, 1260), (350, 1300)], fill=rgba((91, 65, 43), 80))
        for i in range(5):
            draw.line((350, 1262 + i * 7, 630, 1240 + i * 6), fill=rgba((230, 221, 190), 70), width=1)
    if "wine" in motifs:
        x, y = rng.randint(400, 560), rng.randint(1150, 1320)
        draw.rectangle((x - 16, y - 74, x + 16, y - 18), fill=rgba((104, 83, 55), 86))
        draw.ellipse((x - 28, y - 20, x + 28, y + 12), fill=rgba((104, 83, 55), 80))
        draw.ellipse((x + 60, y - 8, x + 94, y + 20), outline=rgba((104, 83, 55), 72), width=3)
    if "lantern" in motifs:
        x, y = rng.randint(560, 700), rng.randint(920, 1080)
        draw.ellipse((x - 26, y - 38, x + 26, y + 38), fill=rgba((223, 151, 73), 86))
        add_wash(layer, (x - 150, y - 150, x + 150, y + 150), (226, 168, 86), 38)

    if "figure" in motifs or "traveler" in motifs or "figures" in motifs:
        draw_figure(draw, rng.randint(330, 650), rng.randint(1220, 1430), rng.uniform(0.72, 1.04), pair="figures" in motifs)
    if "animals" in motifs:
        for x in (360, 430, 520):
            y = rng.randint(1290, 1390)
            draw.ellipse((x - 35, y - 15, x + 35, y + 15), fill=rgba((86, 78, 62), 70))
            draw.line((x - 25, y + 12, x - 34, y + 48), fill=rgba((86, 78, 62), 70), width=3)
            draw.line((x + 25, y + 12, x + 32, y + 48), fill=rgba((86, 78, 62), 70), width=3)
    if "bird" in motifs:
        draw_birds(draw, rng, 5, rng.randint(390, 650))
    if "geese" in motifs:
        draw_birds(draw, rng, 8, rng.randint(520, 780))
    if "fishing" in motifs:
        x, y = 600, 1300
        draw_figure(draw, x - 40, y, 0.68)
        draw.line((x, y - 70, x + 180, y - 160), fill=rgba((74, 63, 46), 90), width=2)

    if "mist" in motifs or "cloud" in motifs:
        for _ in range(7):
            y = rng.randint(500, 1260)
            x0 = rng.randint(-180, 720)
            x1 = rng.randint(360, 1120)
            if x1 < x0:
                x0, x1 = x1, x0
            add_wash(layer, (x0, y, x1, y + rng.randint(115, 230)), (232, 230, 214), rng.randint(12, 28))

    softened = layer.filter(ImageFilter.GaussianBlur(0.35))
    img.alpha_composite(softened)
    vignette = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    vd = ImageDraw.Draw(vignette, "RGBA")
    vd.rectangle((0, 0, WIDTH, HEIGHT), outline=rgba((91, 78, 58), 36), width=20)
    img.alpha_composite(vignette.filter(ImageFilter.GaussianBlur(24)))
    img.convert("RGB").save(target, quality=94)


def prompt_for(poem: dict, visual: dict) -> str:
    return (
        f"{poem['title']}，{poem['author']}。核心意象：{'、'.join(visual['coreImagery'])}；"
        f"情绪：{'、'.join(visual['mood'])}。{visual['composition']}。"
        "竖版 941x1672，淡彩水墨，中国宣纸肌理，大面积留白，色彩低饱和，"
        "画面清透安静，适合上层叠加诗文与注释，不出现文字。"
    )


def build() -> None:
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    poems = [poem for poem in data.get("poems", []) if poem.get("section") == SECTION]
    if len(poems) != len(VISUALS):
        raise SystemExit(f"Expected {len(VISUALS)} {SECTION} poems, found {len(poems)}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    generated_at = now_iso()

    for index, poem in enumerate(poems, 1):
        visual = VISUALS.get(poem["id"])
        if not visual:
            raise SystemExit(f"Missing visual metadata for {poem['id']}")

        filename = f"{poem['order']:03d}-{poem['id']}.png"
        draw_asset(poem["id"], filename, visual, index)
        poem["visual"] = {
            "image": f"assets/illustrations-wuyan-gushi/{filename}",
            "coreImagery": visual["coreImagery"],
            "mood": visual["mood"],
            "palette": visual["palette"],
            "composition": visual["composition"],
            "style": STYLE_NOTE,
            "prompt": prompt_for(poem, visual),
            "generatedAt": generated_at,
            "generator": "imagegen" if poem["id"] == "tang-001-gan-yu-qi-yi" else "procedural-watercolor",
        }

    data.setdefault("stats", {})["wuyanGushiVisuals"] = len(poems)
    data.setdefault("sourcePolicy", {})["visuals"] = (
        "五言古诗插图使用竖版淡彩水墨风格；每首诗在 visual 字段保留核心意象、情绪、构图与资产路径。"
    )
    write_json(SOURCE, data)

    print(f"Wrote {len(poems)} {SECTION} visual records")
    print(f"Wrote assets to {OUT_DIR.relative_to(ROOT)}")


if __name__ == "__main__":
    build()
