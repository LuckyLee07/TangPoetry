import json
import re
from difflib import SequenceMatcher
from pathlib import Path

from opencc import OpenCC
from pypinyin import Style, lazy_pinyin


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "唐诗三百首.json"
OUT = ROOT / "data" / "poems.json"
CTEXT_SOURCE = ROOT / "data" / "sources" / "ctext_clean.json"
CHIUINAN_SOURCE = ROOT / "data" / "sources" / "chiuinan_clean.json"


t2s = OpenCC("t2s")


FEATURED = {
    ("感遇十二首·其四", "张九龄"): {
        "id": "gan-yu-qi-yi",
        "title": "感遇其一",
        "theme": "山水",
        "categories": ["咏怀", "高洁"],
        "image": "assets/illustrations-portrait/lu-zhai.png",
        "mood": "开卷",
        "layout": "layout-opening",
        "composition": {
            "poemTop": "43%",
            "poemLeft": "42px",
            "poemRight": "42px",
            "poemAlign": "center",
            "poemSize": "22px",
            "poemMaxWidth": "330px",
            "noteBottom": "54px",
        },
        "noteTitle": "孤鸿入海，志在高远",
        "note": "开篇写孤鸿远来，不恋池潢，也不畏弋者。它像一个清醒自持的人，把高洁心志托在辽阔天海之间。",
    },
    ("静夜思", "李白"): {
        "id": "jing-ye-si",
        "title": "静夜思",
        "theme": "思乡",
        "categories": ["思乡", "月夜"],
        "image": "assets/illustrations-portrait/jing-ye-si.png",
        "mood": "月夜",
        "layout": "layout-right",
        "composition": {
            "poemTop": "47%",
            "poemLeft": "46px",
            "poemRight": "46px",
            "poemAlign": "center",
            "poemSize": "23px",
            "poemMaxWidth": "320px",
            "noteBottom": "42px",
        },
        "noteTitle": "月光入室，乡心随起",
        "note": "夜里的月色像霜一样铺在床前，诗人抬头看月，又低头想起远方的故乡。",
    },
    ("鹿柴", "王维"): {
        "id": "lu-zhai",
        "title": "鹿柴",
        "theme": "山水",
        "categories": ["山水", "空山"],
        "image": "assets/illustrations-portrait/lu-zhai.png",
        "mood": "空山",
        "layout": "layout-left",
        "composition": {
            "poemTop": "47%",
            "poemLeft": "38px",
            "poemRight": "86px",
            "poemAlign": "left",
            "poemSize": "22px",
            "poemMaxWidth": "300px",
            "noteBottom": "40px",
        },
        "noteTitle": "空山有声，斜光照苔",
        "note": "山中看不见人，只听见远处人声。夕阳返照进树林，又落在青青的苔痕上。",
    },
    ("春晓", "孟浩然"): {
        "id": "chun-xiao",
        "title": "春晓",
        "theme": "春日",
        "categories": ["春日", "清晨"],
        "image": "assets/illustrations-portrait/chun-xiao.png",
        "mood": "春晨",
        "layout": "layout-center",
        "composition": {
            "poemTop": "44%",
            "poemLeft": "92px",
            "poemRight": "34px",
            "poemAlign": "right",
            "poemSize": "22px",
            "poemMaxWidth": "300px",
            "noteBottom": "42px",
        },
        "noteTitle": "醒来听鸟，想起落花",
        "note": "春夜睡得香甜，不知不觉天已亮。醒来听见鸟鸣，想起昨夜风雨，不知吹落多少花。",
    },
    ("江雪", "柳宗元"): {
        "id": "jiang-xue",
        "title": "江雪",
        "theme": "山水",
        "categories": ["山水", "冬雪", "孤寂"],
        "image": "assets/illustrations-portrait/jiang-xue.png",
        "mood": "寒江",
        "layout": "layout-right",
        "composition": {
            "poemTop": "48%",
            "poemLeft": "50px",
            "poemRight": "50px",
            "poemAlign": "center",
            "poemSize": "23px",
            "poemMaxWidth": "310px",
            "noteBottom": "38px",
        },
        "noteTitle": "天地皆白，一人独钓",
        "note": "群山没有飞鸟，路上没有行人。大雪中的小船上，只有披蓑戴笠的老人独自垂钓。",
    },
    ("送元二使安西 / 渭城曲", "王维"): {
        "id": "song-yuan-er-shi-an-xi",
        "title": "送元二使安西",
        "theme": "送别",
        "categories": ["送别", "长亭"],
        "image": "assets/illustrations-portrait/song-yuan-er.png",
        "mood": "渭城",
        "layout": "layout-left",
        "composition": {
            "poemTop": "43%",
            "poemLeft": "38px",
            "poemRight": "78px",
            "poemAlign": "left",
            "poemSize": "21px",
            "poemMaxWidth": "314px",
            "noteBottom": "40px",
        },
        "noteTitle": "一杯酒里，都是远行",
        "note": "清晨小雨洗净尘土，客舍旁的柳色分外新。临别再饮一杯，因为出了阳关就难见故人了。",
    },
}


TEMPLATES = {
    "思乡": {
        "image": "assets/illustrations-portrait/jing-ye-si.png",
        "layout": "layout-center",
        "mood": "思乡",
        "composition": {
            "poemTop": "47%",
            "poemLeft": "44px",
            "poemRight": "44px",
            "poemAlign": "center",
            "poemSize": "21px",
            "poemMaxWidth": "320px",
            "noteBottom": "40px",
        },
    },
    "山水": {
        "image": "assets/illustrations-portrait/lu-zhai.png",
        "layout": "layout-left",
        "mood": "山水",
        "composition": {
            "poemTop": "46%",
            "poemLeft": "38px",
            "poemRight": "80px",
            "poemAlign": "left",
            "poemSize": "20px",
            "poemMaxWidth": "318px",
            "noteBottom": "40px",
        },
    },
    "春日": {
        "image": "assets/illustrations-portrait/chun-xiao.png",
        "layout": "layout-center",
        "mood": "春日",
        "composition": {
            "poemTop": "44%",
            "poemLeft": "74px",
            "poemRight": "36px",
            "poemAlign": "right",
            "poemSize": "20px",
            "poemMaxWidth": "318px",
            "noteBottom": "40px",
        },
    },
    "送别": {
        "image": "assets/illustrations-portrait/song-yuan-er.png",
        "layout": "layout-left",
        "mood": "送别",
        "composition": {
            "poemTop": "43%",
            "poemLeft": "38px",
            "poemRight": "78px",
            "poemAlign": "left",
            "poemSize": "20px",
            "poemMaxWidth": "318px",
            "noteBottom": "40px",
        },
    },
    "边塞": {
        "image": "assets/illustrations-portrait/jiang-xue.png",
        "layout": "layout-center",
        "mood": "边塞",
        "composition": {
            "poemTop": "47%",
            "poemLeft": "44px",
            "poemRight": "44px",
            "poemAlign": "center",
            "poemSize": "20px",
            "poemMaxWidth": "320px",
            "noteBottom": "40px",
        },
    },
}


PINYIN_OVERRIDES = {
    ("静夜思", "床前明月光，"): ["chuáng", "qián", "míng", "yuè", "guāng"],
    ("静夜思", "疑是地上霜。"): ["yí", "shì", "dì", "shàng", "shuāng"],
    ("静夜思", "举头望明月，"): ["jǔ", "tóu", "wàng", "míng", "yuè"],
    ("静夜思", "低头思故乡。"): ["dī", "tóu", "sī", "gù", "xiāng"],
    ("鹿柴", "空山不见人，"): ["kōng", "shān", "bú", "jiàn", "rén"],
    ("送元二使安西", "渭城朝雨浥轻尘，"): ["wèi", "chéng", "zhāo", "yǔ", "yì", "qīng", "chén"],
    ("送元二使安西", "劝君更尽一杯酒，"): ["quàn", "jūn", "gèng", "jìn", "yì", "bēi", "jiǔ"],
}


def slugify(text):
    pinyin = lazy_pinyin(re.sub(r"[^\u4e00-\u9fff]", "", text), style=Style.NORMAL)
    return "-".join(pinyin)[:80] or "poem"


def base_title(title):
    return re.split(r"\s*/\s*|·", title)[0]


def compact_key(text):
    text = t2s.convert(text or "")
    return re.sub(r"[^\u4e00-\u9fff]", "", text)


def title_variants(title):
    variants = []
    for part in re.split(r"\s*/\s*", t2s.convert(title or "")):
        part = part.strip()
        if not part:
            continue
        variants.append(part)
        variants.append(re.split(r"·", part)[0])
        variants.append(re.sub(r"(二|三|四|五)首[·之]?其?", "", part))
        variants.append(re.sub(r"其([一二三四五六七八九十])$", r"之\1", part))
        variants.append(re.sub(r"之([一二三四五六七八九十])$", r"其\1", part))
    seen = []
    for variant in variants:
        normalized = compact_key(variant)
        if normalized and normalized not in seen:
            seen.append(normalized)
    return seen


def text_similarity(left, right):
    left = compact_key(left)
    right = compact_key(right)
    if not left or not right:
        return 0
    if left == right:
        return 1
    if min(len(left), len(right)) >= 20 and (left in right or right in left):
        return 0.97
    if len(left) > 80 or len(right) > 80:
        left = left[:160] + left[-80:]
        right = right[:160] + right[-80:]
    return SequenceMatcher(None, left, right).ratio()


def same_author(left, right):
    aliases = {
        "丘为": "邱为",
        "皎然": "僧皎然",
        "刘昚虚": "刘脊虚",
        "李白": "李白",
    }
    left = aliases.get(compact_key(left), compact_key(left))
    right = aliases.get(compact_key(right), compact_key(right))
    return left == right


def load_order_sources():
    sources = []
    if CTEXT_SOURCE.exists():
        sources.append(("ctext", json.loads(CTEXT_SOURCE.read_text(encoding="utf-8"))))
    if CHIUINAN_SOURCE.exists():
        sources.append(("chiuinan", json.loads(CHIUINAN_SOURCE.read_text(encoding="utf-8"))))
    return sources


def order_match_score(source, candidate):
    author_score = 1 if same_author(source["author"], candidate["authorSimplified"]) else 0
    local_titles = title_variants(source["title"])
    candidate_title = compact_key(candidate["titleSimplified"])
    title_score = max([text_similarity(title, candidate_title) for title in local_titles] or [0])
    local_text = "".join(source["paragraphs"])
    candidate_text = candidate.get("textSimplified") or "".join(candidate.get("linesSimplified", []))
    body_score = text_similarity(local_text, candidate_text)
    score = body_score * 0.78 + title_score * 0.17 + author_score * 0.05

    if author_score and title_score >= 0.96:
        score = max(score, 0.9)
    return score, body_score, title_score, author_score


def best_order_match(source, order_sources):
    manual = {
        ("赠别二首", "杜牧"): ("ctext", 295),
        ("赠别", "杜牧"): ("ctext", 296),
        ("长信怨", "王昌龄"): ("ctext", 314),
        ("金陵图", "韦庄"): ("ctext", 308),
        ("咏蝉 / 在狱咏蝉", "骆宾王"): ("ctext", 93),
    }
    override = manual.get((source["title"], source["author"]))
    if override:
        source_name, order = override
        for current_source_name, candidates in order_sources:
            if current_source_name != source_name:
                continue
            for candidate in candidates:
                if candidate["bookOrder"] == order:
                    return {
                        "bookOrder": candidate["bookOrder"],
                        "bookSequence": candidate.get("sequence"),
                        "bookSection": candidate["sectionSimplified"],
                        "orderSource": current_source_name,
                        "orderConfidence": "manual",
                        "orderScore": 1,
                        "externalTitle": candidate["titleSimplified"],
                        "externalAuthor": candidate["authorSimplified"],
                    }

    best_overall = None
    for source_name, candidates in order_sources:
        best_for_source = None
        for candidate in candidates:
            score, body_score, title_score, author_score = order_match_score(source, candidate)
            if best_for_source is None or score > best_for_source["orderScore"]:
                best_for_source = {
                    "bookOrder": candidate["bookOrder"],
                    "bookSequence": candidate.get("sequence"),
                    "bookSection": candidate["sectionSimplified"],
                    "orderSource": source_name,
                    "orderConfidence": "high" if score >= 0.82 else "review",
                    "orderScore": round(score, 4),
                    "bodyScore": round(body_score, 4),
                    "titleScore": round(title_score, 4),
                    "authorScore": author_score,
                    "externalTitle": candidate["titleSimplified"],
                    "externalAuthor": candidate["authorSimplified"],
                }

        if best_for_source and (
            best_overall is None or best_for_source["orderScore"] > best_overall["orderScore"]
        ):
            best_overall = best_for_source

        # CText is the primary source because it carries the explicit 1-320 sequence.
        # Chiuinan is used only when CText cannot provide a credible match.
        if source_name == "ctext" and best_for_source and best_for_source["orderScore"] >= 0.7:
            return best_for_source

    if best_overall and best_overall["orderScore"] >= 0.7:
        return best_overall
    return {
        "bookOrder": 9000,
        "bookSequence": None,
        "bookSection": "待校对",
        "orderSource": "unmatched",
        "orderConfidence": "unmatched",
        "orderScore": round(best_overall["orderScore"], 4) if best_overall else 0,
        "externalTitle": best_overall["externalTitle"] if best_overall else "",
        "externalAuthor": best_overall["externalAuthor"] if best_overall else "",
    }


def infer_theme(title, author, paragraphs):
    text = title + " ".join(paragraphs)
    if any(word in text for word in ["送", "别", "赠", "辞"]):
        return "送别"
    if any(word in text for word in ["塞", "凉州", "从军", "玉门", "阴山", "胡马"]):
        return "边塞"
    if any(word in text for word in ["春", "花", "柳", "莺", "雨"]):
        return "春日"
    if any(word in text for word in ["乡", "思", "忆", "故园", "故国"]):
        return "思乡"
    if any(word in text for word in ["山", "江", "楼", "瀑", "水", "月", "雪", "云", "舟"]):
        return "山水"
    return "山水"


def chars_only(line):
    return [char for char in line if re.match(r"[\u4e00-\u9fff]", char)]


def line_to_ruby(title, line):
    punctuation = set("，。！？；：、,.!?;:（）()《》“”‘’")
    clean_title = base_title(title)
    override = PINYIN_OVERRIDES.get((clean_title, line))
    pinyin = override or lazy_pinyin("".join(chars_only(line)), style=Style.TONE)
    index = 0
    cells = []
    for char in line:
        if char in punctuation or char.strip() == "":
            cells.append([char, ""])
        else:
            cells.append([char, pinyin[index] if index < len(pinyin) else ""])
            index += 1
    return cells


def display_lines(paragraphs, limit=4):
    lines = []
    for paragraph in paragraphs:
        for line in re.findall(r"[^，。！？；]+[，。！？；]?", paragraph):
            if line.strip():
                lines.append(line)
    return lines[:limit]


def note_from_source(source):
    notes = source.get("notes") or []
    if notes:
        return "；".join(notes[:2])
    return "这首诗已收入基础诗库，后续会继续补充更适合阅读页的简注和诗意。"


def build_poem(source, index, order_info):
    key = (source["title"], source["author"])
    featured = FEATURED.get(key)
    title = featured["title"] if featured else order_info["externalTitle"] or base_title(source["title"])
    theme = featured["theme"] if featured else infer_theme(title, source["author"], source["paragraphs"])
    template = TEMPLATES.get(theme, TEMPLATES["山水"])

    return {
        "id": featured["id"] if featured else f"{slugify(title)}-{index:03d}",
        "sourceIndex": index + 1,
        "bookOrder": order_info["bookOrder"],
        "bookSequence": order_info["bookSequence"],
        "bookSection": order_info["bookSection"],
        "bookTitle": order_info["externalTitle"] or title,
        "orderSource": order_info["orderSource"],
        "orderConfidence": order_info["orderConfidence"],
        "orderScore": order_info["orderScore"],
        "externalTitle": order_info["externalTitle"],
        "externalAuthor": order_info["externalAuthor"],
        "title": title,
        "sourceTitle": source["title"],
        "author": source["author"],
        "dynasty": source.get("dynasty", "唐代"),
        "theme": theme,
        "categories": featured["categories"] if featured else [theme],
        "featured": bool(featured),
        "mood": featured["mood"] if featured else template["mood"],
        "image": featured["image"] if featured else template["image"],
        "layout": featured["layout"] if featured else template["layout"],
        "composition": featured["composition"] if featured else template["composition"],
        "lines": [line_to_ruby(title, line) for line in display_lines(source["paragraphs"])],
        "plainLines": source["paragraphs"],
        "noteTitle": featured["noteTitle"] if featured else "基础诗库",
        "note": featured["note"] if featured else note_from_source(source),
        "notes": source.get("notes", []),
        "source": "唐诗三百首.json",
    }


def build():
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    order_sources = load_order_sources()
    poems = [
        build_poem(item, index, best_order_match(item, order_sources))
        for index, item in enumerate(source)
    ]
    poems.sort(key=lambda poem: (poem["bookOrder"], poem["sourceIndex"]))

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(poems, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(poems)} poems to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    build()
