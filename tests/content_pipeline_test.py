"""Regressions from the imported HTML notes, separate from text-source fidelity."""
import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("reader", Path(__file__).resolve().parents[1] / "scripts/build_reader.py")
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)


class ReadingNotesTests(unittest.TestCase):
    def test_numbered_html_line_wraps_and_variants(self):
        poem = {"notes": [
            {"source": "唐诗三百首.json", "text": "客思深--一作 ：客思侵"},
            {"source": "chiuinan", "text": '1.西陆：秋天。隋书天文志："日循黄道东行，'},
            {"source": "chiuinan", "text": '行西陆谓之秋"。'},
            {"source": "chiuinan", "text": "2.玄鬓影：指年当盛壮。"},
        ], "variants": [{"text": "又作溪", "source": "ctext"}]}
        annotations, variants = reader.reading_notes(poem, {})
        self.assertEqual(len(annotations), 2)
        self.assertIn('行西陆谓之秋"。', annotations[0]["text"])
        self.assertEqual(len(variants), 2)
        self.assertTrue(all("一作" not in n["text"] for n in annotations))

    def test_missing_character_and_repeated_headword(self):
        poem = {"corrections": [{"original": "□", "replacement": "藁"}], "notes": [
            {"source": "chiuinan", "text": "1.□砧：喻丈夫。"},
            {"source": "chiuinan", "text": "2.蟢子：蜘蛛。"},
        ]}
        annotations, _ = reader.reading_notes(poem, {"glossary": [{"term": "蟢子", "text": "一种小蜘蛛，旧时被视作喜兆。"}]})
        self.assertEqual(len(annotations), 2)
        self.assertEqual(annotations[1]["text"], "藁砧：喻丈夫。")
        self.assertEqual(sum(n["text"].startswith("蟢子") for n in annotations), 1)

    def test_mixed_variant_note_keeps_the_definition_in_word_explanations(self):
        annotations, variants = reader.reading_notes({"notes": [
            {"source": "唐诗三百首.json", "text": '挂帆席--一作 “洞庭去”， 扬帆驶船。'}
        ]}, {})
        self.assertEqual(annotations[0]["text"], "挂帆席：扬帆驶船。")
        self.assertEqual(variants[0]["text"], "挂帆席，一作“洞庭去”。")


if __name__ == "__main__":
    unittest.main()
