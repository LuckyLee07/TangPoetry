#!/usr/bin/env python3
"""Protect poem identity, complete versions, provenance, and the App boundary."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import build_classical_fourth_volume as builder
from build_tang_yizhu import key

OUT = builder.OUT

def read(path):
    return json.loads(path.read_text())


class FourthVolumeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = read(OUT/'poems.json')
        cls.poems = cls.doc['poems']
        cls.audit = read(OUT/'audit.json')
        cls.sources = {s['id']: s for s in read(OUT/'sources/selected-texts.json')['records']}

    def poem(self, author, title):
        return next(p for p in self.poems if p['author'] == author and p['title'] == title)

    def test_scope_and_unique_single_poem_count(self):
        self.assertEqual(len(self.poems), 300)
        self.assertEqual(len({p['id'] for p in self.poems}), 300)
        self.assertEqual(len({key(p['text']) for p in self.poems}), 300)
        self.assertFalse(self.doc['importIntoApp'])
        for p in self.poems:
            self.assertIn(p['dynasty'], builder.PERIODS)
            self.assertNotIn(p['literaryCategory'], ['词', '曲'])
            self.assertTrue(p['selection']['reason'].strip())
        self.assertFalse(any(p['title'] == '风入松' for p in self.poems))
        self.assertEqual(self.poem('佚名', '西洲曲')['literaryCategory'], '乐府/拟乐府')

    def test_multiple_versions_never_concatenated(self):
        for author, title, count in [('王冕', '墨梅', 4), ('曹植', '七步诗（四句本）', 4),
                                      ('唐寅', '桃花庵歌', 20), ('钱福', '明日歌', 10),
                                      ('曹雪芹', '葬花吟', 52)]:
            p = self.poem(author, title)
            self.assertEqual(len(p['sentences']), count)
            self.assertEqual(p['sourceReading']['extraction']['kind'], 'complete-version')
            self.assertNotRegex(p['text'], '版本|通行本|校本|弘治|甲戌')
        self.assertNotIn('探虎穴', self.poem('荆轲', '易水歌')['text'])

    def test_cycle_boundaries_and_complete_long_poems(self):
        for title, count in [('雨中登岳阳楼望君山·其一', 4), ('雨中登岳阳楼望君山·其二', 4)]:
            self.assertEqual(len(self.poem('黄庭坚', title)['sentences']), count)
        self.assertEqual(len(self.poem('苏轼', '六月二十七日望湖楼醉书·其一')['sentences']), 4)
        self.assertEqual(len(self.poem('王安石', '书湖阴先生壁·其一')['sentences']), 4)
        self.assertNotIn('明妃初嫁', self.poem('王安石', '明妃曲·其一')['text'])
        self.assertTrue(self.poem('屈原', '九歌·湘君')['text'].endswith('聊逍遥兮容与。'))
        self.assertTrue(self.poem('屈原', '九歌·山鬼')['text'].endswith('思公子兮徒离忧。'))
        self.assertTrue(self.poem('屈原', '九章·橘颂')['text'].endswith('置以为像兮。'))
        kong = self.poem('佚名', '孔雀东南飞')
        self.assertTrue(kong['text'].startswith('孔雀东南飞，五里一徘徊。'))
        self.assertTrue(kong['text'].endswith('多谢后世人，戒之慎勿忘。'))
        self.assertGreater(kong['form']['characterCount'], 1700)
        self.assertIn('汉末建安中', kong['preface'])
        zheng = self.poem('文天祥', '正气歌')
        self.assertEqual(zheng['form']['characterCount'], 300)
        self.assertIn('余囚北庭', zheng['preface'])
        self.assertTrue(self.poem('屈原', '离骚')['text'].endswith('吾将从彭咸之所居！'))
        self.assertGreater(self.poem('屈原', '离骚')['form']['characterCount'], 2400)

    def test_sources_and_editorial_changes_are_traceable(self):
        for s in self.sources.values():
            self.assertEqual(builder.sha(s['raw']['content']), s['rawContentSha256'])
            self.assertTrue(s['url'].startswith('https://'))
            self.assertFalse({'translation', 'shangxi', 'audioUrl'} & s['raw'].keys())
            if 'repositoryCommit' in s:
                self.assertEqual(len(s['repositoryCommit']), 40)
                self.assertIn(s['repositoryCommit'], s['url'])
        entries = read(OUT/'selection.json')['entries']
        for e, p in zip(entries, self.poems):
            self.assertEqual(builder.build_poem(e, self.sources, p['order']), p)
            self.assertEqual(builder.sha(p['text']), p['textSha256'])
        p = self.poem('黄景仁', '杂感')
        self.assertIn('百无—用', p['sourceReading']['text'])
        self.assertIn('百无一用', p['text'])
        self.assertTrue(p['editorialDecisions'][0]['url'].startswith('https://'))
        self.assertEqual(self.poem('龚自珍', '己亥杂诗·其一百二十五')['sourceReading']['title'], '己亥杂诗·其二百二十')
        self.assertEqual(self.poem('陶渊明', '饮酒·其七')['sourceReading']['title'], '饮酒·其四')

    def test_no_unearned_authorship_or_book_membership_certainty(self):
        self.assertFalse(self.doc['publicationReady'])
        for p in self.poems:
            self.assertFalse(p['review']['publicationReady'])
            self.assertFalse(p['review']['wholePoemAgainstPrintEdition'])
            self.assertEqual(p['selection']['bookMembershipStatus'], 'not-verified-poem-by-poem')
            self.assertFalse(p['form']['prosodyVerified'])
        self.assertIn('存疑', self.poem('苏武', '留别妻')['authorDisplay'])
        self.assertIn('存疑', self.poem('卓文君', '白头吟')['authorDisplay'])
        self.assertIn('待核', self.poem('朱熹', '偶成')['authorDisplay'])
        self.assertEqual(self.poem('佚名', '陌上桑')['sourceReading']['author'], '乐府诗集')
        self.assertEqual(self.poem('曹雪芹', '葬花吟')['fictionalSpeaker'], '林黛玉')

    def test_no_overlap_with_first_three_volumes(self):
        app, xieying, third = [read(p) for p in builder.BASELINES]
        baseline = app['poems'] + xieying['poems'] + third['poems']
        prior = {key(p['text']) for p in baseline}
        self.assertEqual(len(prior), 925)
        current = {key(p['text']) for p in self.poems}
        self.assertFalse(prior & current)
        self.assertEqual(len(prior | current), 1225)
        self.assertEqual(self.audit['deduplication']['baselineCandidates'], [])
        self.assertEqual(self.audit['deduplication']['internalCandidates'], [])

    def test_build_is_reproducible_and_does_not_touch_app_or_baselines(self):
        paths = [OUT/n for n in ['poems.json', 'audit.json', 'CATALOG.md', 'POEMS.md', 'REVIEW.md']]
        watched = paths + builder.BASELINES
        before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in watched}
        subprocess.run([sys.executable, str(ROOT/'scripts/build_classical_fourth_volume.py')],
                       cwd=ROOT, check=True, capture_output=True)
        self.assertEqual(before, {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in watched})
        for f in self.audit['inputs']:
            self.assertEqual(f['sha256'], hashlib.sha256((ROOT/f['path']).read_bytes()).hexdigest())


if __name__ == '__main__':
    unittest.main()
