import json
from pathlib import Path
import subprocess
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import build_tang_second_volume as builder
from build_tang_yizhu import key
from build_tang_third_volume import duplicate_candidates

def read(p):return json.loads(p.read_text())

class SecondVolumeTest(unittest.TestCase):
    def test_only_repeated_poem_is_replaced_and_catalogue_remains_complete(self):
        doc=read(builder.OUT/'poems.json');poems=doc['poems'];source=read(builder.CATALOG)
        original=[p for e in source['entries'] for p in e.get('poems',[])]
        policy=read(builder.OUT/'selection-policy.json')
        self.assertEqual(len(original),305);self.assertEqual(len(poems),305)
        old={p['id'] for p in original};new={p['id'] for p in poems}
        self.assertEqual(old-new,{policy['replace']['poemId']})
        self.assertEqual(new-old,{policy['supplement']['poemId']})
        for p in poems:
            if p['id'] in old:self.assertEqual(p['text'],next(o['text'] for o in original if o['id']==p['id']))
        winter=next(p for p in original if p['id']==policy['replace']['poemId'])
        app=next(p for p in read(builder.APP)['poems'] if p['id']==policy['replace']['firstVolumePoemId'])
        self.assertEqual(key(winter['text']),key(app['text']))

    def test_supplement_provenance_and_reading(self):
        doc=read(builder.OUT/'poems.json');p=doc['poems'][-1]
        self.assertFalse(doc['importIntoApp']);self.assertFalse(doc['publicationReady'])
        self.assertEqual(p['title'],'早春寄王汉阳');self.assertEqual(p['author'],'李白')
        self.assertEqual(p['form']['proposedGenre'],'七言古诗')
        self.assertEqual(len(p['sentences']),8)
        self.assertIn('入武阳',p['sourceReading']['text']);self.assertIn('入武昌',p['text'])
        self.assertEqual(p['selection']['bookMembership'],'editorial-supplement-not-claimed-in-Xieying')
        self.assertTrue(p['text'].endswith('与君连日醉壶觞。'))

    def test_no_overlap_across_actual_four_volumes(self):
        second=read(builder.OUT/'poems.json')['poems'];app=read(builder.APP)['poems']
        third=read(ROOT/'data/expansion/tang-third-volume/poems.json')['poems']
        fourth=read(ROOT/'data/expansion/classical-fourth-volume/poems.json')['poems']
        self.assertEqual(duplicate_candidates(second,app+third+fourth),[])
        self.assertEqual(len({key(p['text']) for p in app+second+third+fourth}),1225)

    def test_rebuild_preserves_sources_and_is_deterministic(self):
        paths=[builder.CATALOG,builder.APP,builder.CORPUS]+[builder.OUT/p for p in ['poems.json','audit.json','CATALOG.md']]
        before={p:p.read_bytes() for p in paths}
        subprocess.run([sys.executable,str(ROOT/'scripts/build_tang_second_volume.py')],cwd=ROOT,check=True,capture_output=True)
        self.assertEqual(before,{p:p.read_bytes() for p in paths})

if __name__=='__main__':unittest.main()
