import importlib.util
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location("generate_audio", Path(__file__).resolve().parents[1] / "scripts/generate_audio.py")
audio = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audio)


class NarrationTextTests(unittest.TestCase):
    def test_verse_pauses_do_not_change_displayed_content_or_include_commentary(self):
        poem = {"id": "tang-224-lu-chai", "title": "鹿柴", "author": "王维",
                "rubyLines": [[["空", "kōng"], ["山", "shān"], ["，", ""]],
                              [["问", "wèn"], ["？", ""]]], "note": "不读这段"}
        text = audio.narration_text(poem)
        self.assertEqual(text, "鹿寨。\n唐代，王维。\n空山。\n问？")
        self.assertEqual(poem["title"], "鹿柴")
        self.assertEqual(poem["rubyLines"][0][-1][0], "，")
        self.assertNotIn("kōng", text)
        self.assertNotIn("不读这段", text)

    def test_blank_lines_are_omitted_but_last_unpunctuated_verse_is_kept(self):
        poem = {"id": "sample", "title": "示例", "author": "作者",
                "rubyLines": [[], [["山", ""]], [["水", ""], ["；", ""]]]}
        self.assertTrue(audio.narration_text(poem).endswith("山。\n水。"))


if __name__ == "__main__":
    unittest.main()
