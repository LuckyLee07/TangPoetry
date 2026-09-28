#!/usr/bin/env python3
"""Guard collection identity, complete readings, provenance and non-import scope."""
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import build_tang_third_volume as builder
from build_tang_yizhu import key

OUT = ROOT / 'data/expansion/tang-third-volume'


def read(path):
    return json.loads(path.read_text())


class ThirdVolumeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = read(OUT / 'poems.json')
        cls.poems = cls.doc['poems']
        cls.by_id = {p['id']: p for p in cls.poems}
        cls.corpus = builder.load_corpus()
        cls.app = read(builder.APP)['poems']
        cls.xieying = [p for e in read(builder.XIEYING)['entries'] for p in e.get('poems', [])]
        cls.second = read(builder.SECOND_VOLUME)['poems']
        cls.audit = read(OUT / 'audit.json')

    def test_300_distinct_poems_and_all_prior_93_retained(self):
        self.assertEqual(len(self.poems), 300)
        self.assertEqual(len(self.by_id), 300)
        snapshot = read(OUT / 'sources/retained-93.json')['entries']
        self.assertEqual(len(snapshot), 93)
        expected = {(e['id'], e['retainedFrom']) for e in snapshot}
        actual = {(p['id'], p['selection']['retainedFrom']) for p in self.poems
                  if p['selection']['retainedFrom'] != 'expanded-to-300'}
        self.assertEqual(expected, actual)
        self.assertEqual(Counter(p['selection']['retainedFrom'] for p in self.poems),
                         Counter({'reader-selection-80': 80, 'earlier-recommendations-13': 13,
                                  'expanded-to-300': 207}))
        for p in self.poems:
            self.assertEqual(p['author'], self.corpus[p['id']]['author'])
            self.assertGreater(len(p['selection']['reason']), 20)

    def test_new_readings_do_not_erase_original_evidence(self):
        editions = {e['poemId']: e for e in read(OUT / 'sources/editions.json')['records']}
        self.assertEqual(len(editions), 7)
        for p in self.poems:
            original = self.corpus[p['id']]
            for field, value in p['sourceReading'].items():
                self.assertEqual(value, original[field])
            self.assertEqual(p['text'], '\n'.join(p['paragraphs']))
            self.assertEqual(p['textSha256'], hashlib.sha256(p['text'].encode()).hexdigest())
            self.assertEqual(p['sourceRecordIds'], original['sourceRecordIds'])
            self.assertEqual(p['witnesses'], original['witnesses'])
            if p['text'] != original['text'] or p['editorialDecisions']:
                self.assertIn(p['id'], editions)
                self.assertTrue(p['editorialDecisions'][0]['sourceUrl'].startswith('https://'))
            if p['id'] not in editions:
                self.assertEqual(p['paragraphs'], original['paragraphs'])

    def test_missing_couplet_and_known_character_errors_fixed(self):
        def poem(author, title):
            return next(p for p in self.poems if p['author'] == author and p['title'] == title)
        oriole = poem('李商隐', '流莺')
        self.assertEqual(len(oriole['sentences']), 8)
        self.assertTrue(oriole['text'].endswith('曾苦伤春不忍听，凤城何处有花枝。'))
        self.assertNotIn('曾苦伤春', oriole['sourceReading']['text'])
        horse = poem('李贺', '马诗二十三首·其五')
        self.assertTrue(horse['text'].startswith('大漠沙如雪'))
        self.assertTrue(horse['sourceReading']['text'].startswith('大漠山如雪'))
        self.assertTrue(poem('白居易', '遗爱寺')['text'].startswith('弄石'))
        self.assertIn('金陵驿路', poem('刘长卿', '送李判官之润州行营')['text'])
        self.assertIn('艰难愧深情', poem('杜甫', '羌村·其三')['text'])
        kuangfu = poem('杜甫', '狂夫')
        self.assertTrue(kuangfu['text'].startswith('万里桥西一草堂'))
        self.assertTrue(kuangfu['sourceReading']['text'].startswith('万里桥西一，草堂'))
        self.assertEqual(len(kuangfu['sentences']), 8)
        self.assertIn('元和十一年', poem('刘禹锡', '元和十年自朗州至京戏赠看花诸君子')['sourceTitle'])
        # Long narrative must remain a complete source reading, never a famous-line excerpt.
        qin = poem('韦庄', '秦妇吟')
        self.assertEqual((qin['form']['sentenceCount'], qin['form']['characterCount']), (238, 1666))
        self.assertIn('long-poem-collation-required', qin['review']['issues'])

    def test_no_overlap_with_actual_two_volume_baseline(self):
        self.assertEqual(len(self.app), 320)
        self.assertEqual(len(self.xieying), 305)
        baseline_texts = {key(p['text']) for p in self.app + self.second}
        self.assertEqual(len(baseline_texts), 625)
        new_texts = {key(p['text']) for p in self.poems}
        self.assertEqual(len(new_texts), 300)
        self.assertFalse(new_texts & baseline_texts)
        self.assertEqual(len(new_texts | baseline_texts), 925)
        baseline_source_ids = {i for p in self.app + self.second for i in p.get('sourceRecordIds', [])}
        for p in self.poems:
            self.assertFalse(set(p['sourceRecordIds']) & baseline_source_ids)
        self.assertEqual(self.audit['deduplication']['baselineCandidates'], [])
        self.assertEqual(self.audit['deduplication']['internalCandidates'], [])

    def test_dedup_detects_renamed_reassigned_and_variant_witness(self):
        a = {'id': 'one', 'author': '甲', 'title': '旧题',
             'text': '月落烏啼霜滿天，江楓漁火對愁眠。姑蘇城外寒山寺，夜半鐘聲到客船。'}
        b = {'id': 'two', 'author': '乙', 'title': '完全不同的新题',
             'text': '月落乌啼霜满天，江枫渔火对愁眠。姑苏城外寒山寺，夜半钟声入客船。'}
        self.assertEqual(len(builder.duplicate_candidates([a], [b])), 1)
        c = {'id': 'three', 'author': '丙', 'title': '另一题', 'text': '春草明年绿，王孙归不归。',
             'witnesses': [{'paragraphs': [a['text']]}]}
        self.assertEqual(builder.duplicate_candidates([c], [a])[0]['similarity'], 1)
        d = deepcopy(c)
        d['witnesses'] = []
        self.assertEqual(builder.duplicate_candidates([d], [a]), [])

    def test_attribution_and_book_membership_are_not_overclaimed(self):
        self.assertFalse(self.doc['publicationReady'])
        self.assertFalse(self.doc['importIntoApp'])
        emperor = next(p for p in self.poems if p['author'] == '太宗皇帝')
        self.assertEqual(emperor['authorDisplay'], '李世民（唐太宗）')
        self.assertTrue(any(n.get('sourceUrl') for n in emperor['editorialNotes']))
        for p in self.poems:
            self.assertFalse(p['form']['prosodyVerified'])
            self.assertFalse(p['review']['publicationReady'])
            self.assertEqual(set(p['selection']['bookMembership'].values()), {'not-verified'})
            self.assertEqual(p['enrichment'], self.corpus[p['id']]['enrichment'])
            self.assertTrue(p['sourceRefs'])

    def test_readable_catalog_and_fulltext_have_every_identity_once(self):
        catalog = (OUT / 'CATALOG.md').read_text()
        full = (OUT / 'POEMS.md').read_text()
        self.assertEqual(sum(self.doc['stats']['bySourceAuthor'].values()), 300)
        self.assertEqual(self.doc['catalogGrouping'], 'author')
        for p in self.poems:
            self.assertEqual(catalog.count(f'POEMS.md#{p["id"]}'), 1)
            self.assertEqual(full.count(f'<a id="{p["id"]}"></a>'), 1)
            self.assertIn('  \n'.join(p['paragraphs']), full)
            self.assertIn(p['selection']['reason'], full)

    def test_popularity_revision_is_traceable_without_theme_quotas(self):
        manifest = read(OUT / 'selection.json')
        for flag in ('themeQuotas', 'authorQuotas', 'countIsHardQuota'):
            self.assertFalse(manifest['selectionPolicy'][flag])
        self.assertNotIn('themes', manifest)
        self.assertTrue(all('theme' not in e for e in manifest['entries']))
        self.assertTrue(all('theme' not in p['selection'] for p in self.poems))
        previous = {e['id'] for e in read(OUT / 'sources/selection-before-popularity-review.json')['entries']}
        current = set(self.by_id)
        revision = read(OUT / 'sources/popularity-revision.json')
        self.assertEqual(revision['replacementCount'], 20)
        self.assertEqual(len(revision['replacements']), 20)
        self.assertEqual(previous - current, {e['previous']['id'] for e in revision['replacements']})
        self.assertEqual(current - previous, {e['replacement']['id'] for e in revision['replacements']})
        self.assertEqual(len(current - previous), 20)
        self.assertTrue(any(p['title'] == '夜宿山寺' for p in self.poems))
        extra = read(builder.ADDITIONAL)
        self.assertEqual(len(extra['records']), 15)
        upstream_ids = {p['id'] for p in read(builder.CORPUS)['poems']}
        added_ids = set(self.corpus) - upstream_ids
        self.assertEqual(len(added_ids), 15)
        self.assertTrue(added_ids <= current)
        for poem_id in added_ids:
            self.assertTrue(any(extra['repositoryCommit'] in ref['url']
                                for ref in self.by_id[poem_id]['sourceRefs']))

    def test_inputs_pinned_rebuild_deterministic_and_baselines_untouched(self):
        for item in self.audit['inputs']:
            path = ROOT / item['path']
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), item['sha256'])
        outputs = ['poems.json', 'audit.json', 'CATALOG.md', 'POEMS.md', 'REVIEW.md', 'REVISION.md']
        before = {n: (OUT / n).read_bytes() for n in outputs}
        protected = {p: p.read_bytes() for p in (builder.APP, builder.XIEYING, builder.SECOND_VOLUME, builder.CORPUS)}
        completed = subprocess.run([sys.executable, str(ROOT / 'scripts/build_tang_third_volume.py')],
                                   cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(before, {n: (OUT / n).read_bytes() for n in outputs})
        for path, value in protected.items():
            self.assertEqual(path.read_bytes(), value)


if __name__ == '__main__':
    unittest.main()
