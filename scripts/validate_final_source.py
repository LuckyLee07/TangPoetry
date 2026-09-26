#!/usr/bin/env python3
"""Check the canonical anthology and its lossless structural cleanup."""
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FINAL = ROOT / "data/final/tang_poems_final.json"
AUDIT = ROOT / "data/final/content_audit.json"
FIXED_FORMS = {"五言绝句": (4, 5), "七言绝句": (4, 7), "五言律诗": (8, 5), "七言律诗": (8, 7)}


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def verse_lines(poem):
    return [part for paragraph in poem["lines"]
            for part in re.findall(r"[^，。！？；]+[，。！？；]?", paragraph) if part.strip()]


def han_count(text):
    # Includes the extension characters present in this edition, e.g. 坎𡒄.
    return len(re.findall(r"[\u3400-\u9fff\U00020000-\U0003134f]", text))


def validate():
    final = json.loads(FINAL.read_text(encoding="utf-8"))
    poems = final["poems"]
    source = {p["bookOrder"]: p for p in read("data/sources/ctext_clean.json")}
    corrections = read("data/content-corrections.json")
    ids = {poem["id"] for poem in poems}
    assert len(poems) == len(ids) == 320
    assert [poem["order"] for poem in poems] == list(range(1, 321))
    assert final["stats"]["missingCtextOrders"] == []
    assert sum(poem["sourceRefs"]["base"]["supplemented"] for poem in poems) == 3
    original_identities = {poem["id"]: poem["order"] for poem in poems
                           if not poem["sourceRefs"]["base"]["supplemented"]}
    identity_hash = hashlib.sha256(json.dumps(original_identities, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    assert len(original_identities) == corrections["identityBaseline"]["poemCount"] == 317
    assert identity_hash == corrections["identityBaseline"]["sha256"], "Original poem IDs/orders changed"
    by_id = {poem["id"]: poem for poem in poems}
    for supplement in corrections["supplements"]:
        assert by_id[supplement["id"]]["order"] == supplement["order"]

    fixed_form_results, structural_results = [], []
    for poem in poems:
        assert len(poem["lines"]) == len(poem["linesTraditional"]), poem["id"]
        assert poem["text"] == "".join(poem["lines"]), poem["id"]
        assert poem["textTraditional"] == "".join(poem["linesTraditional"]), poem["id"]
        assert "".join(pair[0] for line in poem["rubyLines"] for pair in line) == poem["text"], poem["id"]
        assert not any(line.strip().startswith("又作") for line in poem["lines"]), poem["id"]
        assert "□" not in poem["text"], poem["id"]
        if "并序" in poem["title"]:
            assert poem["preface"], f"Preface still mixed into verse: {poem['id']}"
        for field, correction in poem["metadataCorrections"].items():
            assert poem[field] == correction["replacement"]
            assert poem[f"{field}Traditional"] == correction["replacementTraditional"]

        # Recompose the original CText text, undoing only documented replacements.
        # This proves no prose or variant text vanished when leaving the verse area.
        restored = "".join(poem["preface"] + poem["lines"])
        restored_traditional = "".join(poem["prefaceTraditional"] + poem["linesTraditional"])
        for replacement in reversed(poem["corrections"]):
            restored = restored.replace(replacement["replacement"], replacement["original"])
            restored_traditional = restored_traditional.replace(
                replacement.get("replacementTraditional", replacement["replacement"]),
                replacement.get("originalTraditional", replacement["original"]))
        restored += "".join(variant["originalLine"] for variant in poem["variants"])
        restored_traditional += "".join(variant["originalLineTraditional"] for variant in poem["variants"])
        assert restored == source[poem["order"]]["textSimplified"], poem["id"]
        assert restored_traditional == source[poem["order"]]["textTraditional"], poem["id"]

        lines = verse_lines(poem)
        if poem["section"] in FIXED_FORMS:
            count, length = FIXED_FORMS[poem["section"]]
            lengths = [han_count(line) for line in lines]
            assert len(lines) == count, (poem["id"], len(lines), count)
            assert all(value == length for value in lengths), (poem["id"], lengths, length)
            fixed_form_results.append({"id": poem["id"], "title": poem["title"], "section": poem["section"],
                                       "lineCount": len(lines), "charactersPerLine": length, "status": "passed"})
        if poem["preface"] or poem["variants"] or poem["corrections"]:
            structural_results.append({"id": poem["id"], "title": poem["title"], "verseLineCount": len(lines),
                                       "prefaceParagraphCount": len(poem["preface"]),
                                       "variantSourceLineCount": len(poem["variants"]),
                                       "originalTextReconstructed": True})

    assert len(by_id["tang-093-zai-yu-yong-chan-bing-xu"]["preface"]) == 20
    assert len(verse_lines(by_id["tang-093-zai-yu-yong-chan-bing-xu"])) == 8
    assert sum(bool(poem["preface"]) for poem in poems) == 6
    assert sum(bool(poem["variants"]) for poem in poems) == 18
    assert by_id["tang-243-yu-tai-ti"]["lines"][-1] == "铅华不可弃，莫是藁砧归。"
    index = read("data/final/poems/index.json")
    assert index["poemCount"] == 320
    assert {item["id"] for item in index["poems"]} == ids
    for entry in index["poems"]:
        assert read("data/final/" + entry["path"])["poem"] == by_id[entry["id"]]

    report = {
        "schemaVersion": "1.0.0", "status": "passed", "sourceGeneratedAt": final["generatedAt"],
        "scope": "全320首结构、简繁正文回溯、单诗同步；213首固定体裁的句数与汉字数。该检查不等同于逐字版本学定本。",
        "poemCount": len(poems), "sourceOrdersComplete": True, "archivedTextReconstructed": len(poems),
        "legacyIdentitiesPreserved": len(original_identities), "legacyIdentitySHA256": identity_hash,
        "prefacePoemCount": sum(bool(poem["preface"]) for poem in poems),
        "correctedTextPassages": sum(len(poem["corrections"]) for poem in poems),
        "metadataCorrectionCount": sum(len(poem["metadataCorrections"]) for poem in poems),
        "genreCounts": dict(Counter(poem["section"] for poem in poems)),
        "fixedFormCount": len(fixed_form_results), "fixedFormResults": fixed_form_results,
        "structuralResults": structural_results,
        "knownSourceLimitations": [
            "CText尾部又作说明未指明对应字句，保留原行而不推断替换位置。",
            "古体与乐府不强制套用固定句数和字数；保留选本异文。",
            "归档英译存在英文空格丢失，仍只供资料追溯。",
        ],
    }
    AUDIT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Validated {len(poems)} poems, {len(fixed_form_results)} fixed forms; all source text reconstructed; wrote {AUDIT.relative_to(ROOT)}")


if __name__ == "__main__":
    validate()
