"""Album transcription and poem identity regressions; offline, no App changes."""
import hashlib
import json
import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import collect_xieying_catalog as builder

DATA = ROOT/'data/expansion/tang-yizhu/xieying'


def read(name):
    return json.loads((DATA/name).read_text())


class CatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = read('catalog.json')
        cls.entries = cls.catalog['entries']
        cls.dataset = read('poems.json')
        cls.poems = {p['id']:p for p in cls.dataset['poems']}

    def candidates(self, order):
        return [self.poems[i] for i in self.entries[order-1]['candidateIds']]

    def test_original_transcription_and_duplicate_positions_are_preserved(self):
        original = (DATA/'catalog-input.txt').read_text().splitlines()
        self.assertEqual(len(original),297)
        self.assertEqual([e['rawInput'] for e in self.entries],original)
        self.assertEqual([e['order'] for e in self.entries],list(range(1,298)))
        self.assertEqual([e['order'] for e in self.entries if e['title']=='野望'],[36,171])
        self.assertEqual([e['order'] for e in self.entries if e['title']=='咏风'],[130,189])
        self.assertEqual(self.entries[0]['status'],'excluded-preface')

    def test_title_noise_and_real_cycle_number_are_separated(self):
        parsed = builder.parse_catalog('【七绝】不第后赋菊32024-06\n南园十三首02024-06\n秋兴·其一222024-05\n长安古意')
        self.assertEqual([e['title'] for e in parsed],['不第后赋菊','南园十三首','秋兴·其一','长安古意'])
        self.assertEqual(builder.title_identity('江畔獨步尋花七絕句 六'),('江畔独步寻花',6))
        self.assertEqual(builder.title_identity('池上二絕 二'),('池上',2))

    def test_every_poem_entry_has_sourced_candidates_and_pending_stays_unselected(self):
        self.assertEqual(len(self.poems),len(self.dataset['poems']))
        for e in self.entries[1:]:
            self.assertTrue(e['candidateIds'])
            self.assertTrue(set(e['candidateIds']).issubset(self.poems))
            self.assertTrue(set(e['selectedPoemIds']).issubset(e['candidateIds']))
            if e['status']=='needs-confirmation':
                self.assertEqual(e['selectedPoemIds'],[])
            elif e['status']=='user-confirmed-selection':
                self.assertTrue(e['selectedPoemIds'])
                self.assertEqual(e['selectionBasis'],'explicit-user-confirmation')
                self.assertTrue(e['userConfirmation']['sourceRef'])
            else:
                self.assertEqual(len(e['candidateIds']),1)
                self.assertEqual(e['selectedPoemIds'],e['candidateIds'])
        self.assertFalse(self.catalog['bookPrintTocVerified'])
        self.assertFalse(self.dataset['publicationReady'])

    def test_aliases_do_not_omit_the_familiar_work(self):
        self.assertIn('杜牧',{p['author'] for p in self.candidates(88)})
        self.assertIn('白居易',{p['author'] for p in self.candidates(240)})
        self.assertIn('陈子昂',{p['author'] for p in self.candidates(6)})
        self.assertEqual({p['author'] for p in self.candidates(215)},{'赵嘏'})
        self.assertEqual({p['author'] for p in self.candidates(194)},{'齐己'})

    def test_original_cycles_and_conflicting_attribution_candidates_are_preserved(self):
        for order, count in [(254,2),(258,7),(267,5),(282,13)]:
            self.assertEqual(len(self.candidates(order)),count)
            self.assertEqual(self.entries[order-1]['status'],'user-confirmed-selection')
        self.assertEqual({p['author'] for p in self.candidates(68)},{'钱起','钱珝'})
        self.assertIn('attribution-or-edition-review',self.candidates(244)[0]['review']['issues'])

    def test_explicit_ordinals_remain_bound_to_the_requested_member(self):
        for order, ordinal in [(22,4),(49,1),(58,2),(77,2),(94,1),(108,3),(110,6),(234,3),(288,2)]:
            self.assertEqual({p['group']['position'] for p in self.candidates(order)},{ordinal})

    def test_source_records_and_edition_history_remain_recoverable(self):
        raw = {p['raw']['id']:p for p in read('sources/qts-candidates.json')['records']}
        represented = set()
        for p in self.poems.values():
            represented.update(p['sourceRecordIds'])
            refs = p['sourceRefs']+[w['sourceRef'] for w in p['witnesses']]
            ids = {r.get('recordId') for r in refs}
            self.assertTrue(set(p['sourceRecordIds']).issubset(ids))
            self.assertTrue(all(r['url'].startswith('https://') for r in refs))
            self.assertEqual(p['text'],'\n'.join(p['paragraphs']))
            self.assertEqual(p['textSha256'],hashlib.sha256(p['text'].encode()).hexdigest())
            self.assertEqual(p['form']['sentenceCount'],len(p['sentences']))
        for e in self.entries:
            for p in e.get('filteredOutCandidates',[]):
                represented.update(p['sourceRecordIds'])
        self.assertEqual(represented,set(raw))

    def test_missing_couplet_completed_from_an_explicit_source(self):
        p = next(p for p in self.candidates(137) if p['author']=='上官昭容')
        self.assertEqual(p['form']['sentenceCount'],8)
        self.assertEqual(p['paragraphs'][-1],'借问桃将李，相乱欲何如。')
        self.assertTrue(p['editionDecision'])
        self.assertTrue(any(len(w['paragraphs'])==3 for w in p['witnesses']))

    def test_only_verified_track_ids_are_emitted(self):
        tracks = read('sources/album-first-100.json')['data']
        self.assertEqual(len(tracks),100)
        for e,t in zip(self.entries,tracks):
            self.assertEqual(e['trackId'],t['trackId'])
            self.assertEqual(e['sourceUrl'],'https://www.ximalaya.com'+t['uri'])
        self.assertTrue(all('trackId' not in e for e in self.entries[100:]))

    def test_matched_export_and_indexes_have_no_orphans(self):
        matched = read('matched-poems.json')['entries']
        self.assertEqual({e['id'] for e in matched},{e['id'] for e in self.entries if e['selectedPoemIds']})
        authors = read('authors.json')['authors']
        self.assertEqual({i for a in authors for i in a['poemIds']},set(self.poems))
        for g in read('groups.json')['groups']:
            self.assertTrue(set(g['poemIds']).issubset(self.poems))
        app_file = ROOT/self.dataset['existingLibrary']['path']
        self.assertEqual(self.dataset['existingLibrary']['sha256'],hashlib.sha256(app_file.read_bytes()).hexdigest())

    def test_first_batch_choices_remain_selected(self):
        confirmed = {2:'张若虚',6:'陈子昂',8:'王维',16:'贺知章',17:'王昌龄',18:'李白',
                     20:'刘禹锡',21:'刘禹锡',23:'杜牧',24:'杜牧',25:'罗隐',33:'李贺',
                     36:'王绩',39:'王维',40:'李白',47:'李商隐'}
        pending_ids = {e['id'] for e in read('pending.json')['entries']}
        for order, author in confirmed.items():
            e = self.entries[order-1]
            self.assertEqual(e['status'],'user-confirmed-selection')
            self.assertEqual({self.poems[i]['author'] for i in e['selectedPoemIds']},{author})
            self.assertNotIn(e['id'],pending_ids)
            for pid in e['selectedPoemIds']:
                self.assertIn(e['id'],self.poems[pid]['userConfirmedEntryIds'])
                self.assertNotIn(e['id'],self.poems[pid]['provisionallyMatchedEntryIds'])
        for order, opening in [(18,'日照香炉生紫烟'),(21,'杨柳青青江水平')]:
            self.assertTrue(self.poems[self.entries[order-1]['selectedPoemIds'][0]]['text'].startswith(opening))

    def test_two_poem_selection_is_preserved_in_json_and_readable_export(self):
        e = self.entries[16]
        selected = [self.poems[i] for i in e['selectedPoemIds']]
        self.assertEqual([p['group']['position'] for p in selected],[4,5])
        self.assertEqual([p['paragraphs'][0] for p in selected],
                         ['青海长云暗雪山，孤城遥望雁门关。','大漠风尘日色昏，红旗半卷出辕门。'])
        exported = next(e for e in read('matched-poems.json')['entries'] if e['order']==17)
        self.assertEqual([p['id'] for p in exported['poems']],e['selectedPoemIds'])
        section = (DATA/'MATCHED_POEMS.md').read_text().split('## 017. ')[1].split('\n## ')[0]
        for p in selected:
            for line in p['sentences']:
                self.assertIn(line,section)
        confirmations = [c for b in read('sources/user-confirmations.json')['batches'] for c in b['selections']]
        self.assertEqual(self.catalog['stats']['userConfirmedEntryCount'],len(confirmations))
        self.assertEqual(self.catalog['stats']['userConfirmedPoemCount'],len({i for c in confirmations for i in c['selectedPoemIds']}))
        self.assertEqual(self.catalog['stats']['statuses'].get('needs-confirmation',0),len(read('pending.json')['entries']))

    def test_second_batch_choices_remain_selected(self):
        expected = {
            50:('杜甫','朝回日日典春衣'), 55:('白居易','赠君一法决狐疑'),
            62:('虞世南','垂緌饮清露'), 65:('李白','众鸟高飞尽'),
            66:('杜甫','迟日江山丽'), 67:('贾岛','十年磨一剑'),
            68:('钱珝','咫尺愁风雨'), 72:('高适','十里黄云白日曛'),
            81:('韩愈','新年都未有芳华'), 83:('刘禹锡','九曲黄河万里沙'),
            86:('刘禹锡','自古逢秋悲寂寥'), 88:('杜牧','千里莺啼绿映江'),
            103:('王昌龄','奸雄乃得志'), 107:('李白','明朝驿使发'),
            117:('孟郊','南山塞天地'), 123:('李白','去年战桑干源'),
            129:('李贺','瑠璃钟'), 130:('王勃','肃肃凉景生'),
            133:('陈子昂','故人洞庭去'), 137:('上官昭容','密叶因裁吐')}
        pending_ids = {e['id'] for e in read('pending.json')['entries']}
        for order, (author, opening) in expected.items():
            e = self.entries[order-1]
            self.assertEqual(e['status'],'user-confirmed-selection')
            self.assertEqual(len(e['selectedPoemIds']),1)
            p = self.poems[e['selectedPoemIds'][0]]
            self.assertEqual(p['author'],author)
            self.assertTrue(p['text'].startswith(opening))
            self.assertIn(e['id'],p['userConfirmedEntryIds'])
            self.assertNotIn(e['id'],pending_ids)
        self.assertTrue(self.poems[self.entries[106]['selectedPoemIds'][0]]['title'].endswith('冬歌'))

    def test_third_batch_resolves_authors_openings_and_repeated_titles(self):
        expected = {
            142:('王昌龄','城南虏已合'), 146:('王维','寂寞掩柴扉'),
            160:('李白','见说蚕丛路'), 171:('杜甫','清秋望不极'),
            174:('杜甫','四更山吐月'), 178:('张巡','岧嶤试一临'),
            179:('丁仙芝','桂檝中流望'), 189:('张祜','摇摇歌扇举'),
            192:('杜荀鹤','君到姑苏见'), 193:('翁宏','又是春残也'),
            200:('杜甫','露下天高秋水清'), 217:('皮日休','白纶巾下髪如丝'),
            219:('崔涂','水流花谢两无情'), 222:('李远','秋风吹却九臯禽'),
            227:('李峤','解落三秋叶'), 230:('韦承庆','万里人南去'),
            231:('韦承庆','澹澹长江水'), 235:('王维','荆溪白石出'),
            236:('高适','尚有绨袍赠'), 237:('丘为','冷艳全欺雪'),
            240:('白居易','小娃撑小艇')}
        pending_ids = {e['id'] for e in read('pending.json')['entries']}
        for order, (author, opening) in expected.items():
            e = self.entries[order-1]
            self.assertEqual(e['status'],'user-confirmed-selection')
            self.assertEqual(e['userConfirmation']['batchId'],'user-confirmation-2026-09-28-03')
            self.assertEqual(len(e['selectedPoemIds']),1)
            p = self.poems[e['selectedPoemIds'][0]]
            self.assertEqual(p['author'],author)
            self.assertTrue(p['text'].startswith(opening))
            self.assertIn(e['id'],p['userConfirmedEntryIds'])
            self.assertNotIn(e['id'],pending_ids)
        for order, author in [(36,'王绩'),(130,'王勃')]:
            self.assertEqual(self.poems[self.entries[order-1]['selectedPoemIds'][0]]['author'],author)

    def test_saixiaqu_and_qiuxing_export_only_requested_members_in_order(self):
        for order, author, positions in [(159,'李白',[3,5]),(198,'杜甫',[3,4,7])]:
            e = self.entries[order-1]
            selected = [self.poems[i] for i in e['selectedPoemIds']]
            self.assertEqual(e['status'],'user-confirmed-selection')
            self.assertEqual({p['author'] for p in selected},{author})
            self.assertEqual([p['group']['position'] for p in selected],positions)
            exported = next(e for e in read('matched-poems.json')['entries'] if e['order']==order)
            self.assertEqual([p['id'] for p in exported['poems']],e['selectedPoemIds'])
            section = (DATA/'MATCHED_POEMS.md').read_text().split(f'## {order:03d}. ')[1].split('\n## ')[0]
            for p in selected:
                for line in p['sentences']:
                    self.assertIn(line,section)
        self.assertEqual(len(self.candidates(198)),8)
        for order in [40,49]:
            self.assertEqual([self.poems[i]['group']['position'] for i in self.entries[order-1]['selectedPoemIds']],[1])

    def test_cuitu_luhuai_alias_recovers_complete_sourced_text(self):
        entry = self.entries[218]
        p = self.poems[entry['selectedPoemIds'][0]]
        self.assertEqual(entry['title'],'旅怀')
        self.assertEqual((p['author'],p['sourceTitle']),('崔涂','春夕'))
        self.assertEqual(p['form']['sentenceCount'],8)
        self.assertEqual(p['paragraphs'][-1],'自是不归归便得，五湖烟景有谁争。')
        source_id = '1f8c69c3-6ae6-48ff-bf8c-1e18b0f42133'
        self.assertIn(source_id,p['sourceRecordIds'])
        rule = read('title-overrides.json')['219']
        self.assertIn(source_id,rule['sourceIds'])
        self.assertTrue(rule['evidenceUrls'])
        self.assertTrue(any(a['name']=='崔涂' and a['sourceBiographies'] for a in read('authors.json')['authors']))

    def test_final_batch_singles_and_full_jingwuyin_are_selected(self):
        expected = {
            244:('薛郧、薛涛（传）','庭除一古桐'),
            248:('王昌龄','荷叶罗裙一色裁'), 249:('张谓','一树寒梅白玉条'),
            250:('贾至','草色青青柳色黄'), 263:('于鹄','偶向江边采白苹'),
            265:('李益','露湿晴花宫殿香'), 268:('张籍','洛阳城里见秋风'),
            271:('刘禹锡','春江月出大堤平'), 289:('韩偓','清江碧草两悠悠'),
            290:('陆龟蒙','素蘤多蒙别艳欺'), 293:('韦庄','晴烟漠漠柳毵毵'),
            296:('章谒','竹帛烟消帝业虚')}
        for order, (author, opening) in expected.items():
            e = self.entries[order-1]
            self.assertEqual(e['status'],'user-confirmed-selection')
            self.assertEqual(len(e['selectedPoemIds']),1)
            p = self.poems[e['selectedPoemIds'][0]]
            self.assertEqual(p['author'],author)
            self.assertTrue(p['text'].startswith(opening))
        p = self.poems[self.entries[243]['selectedPoemIds'][0]]
        self.assertEqual(p['sentences'],['庭除一古桐，','耸干入云中。','枝迎南北鸟，','叶送往来风。'])
        self.assertEqual((p['form']['sentenceCount'],p['form']['uniformLineLength']),(4,5))
        self.assertEqual(read('pending.json')['entries'],[])
        self.assertEqual(self.catalog['stats']['selectedEntryCount'],296)
        self.assertEqual(self.catalog['stats']['selectedUniquePoemCount'],305)

    def test_final_batch_cycles_distinguish_full_group_from_excerpts(self):
        for order, author, positions in [(254,'岑参',[1,2]),(258,'杜甫',[5,6]),
                                         (267,'韩愈',[2,5]),(282,'李贺',[5,6])]:
            e = self.entries[order-1]
            selected = [self.poems[i] for i in e['selectedPoemIds']]
            self.assertEqual({p['author'] for p in selected},{author})
            self.assertEqual([p['group']['position'] for p in selected],positions)
            exported = next(e for e in read('matched-poems.json')['entries'] if e['order']==order)
            self.assertEqual([p['id'] for p in exported['poems']],e['selectedPoemIds'])
            section = (DATA/'MATCHED_POEMS.md').read_text().split(f'## {order:03d}. ')[1].split('\n## ')[0]
            for p in selected:
                for line in p['sentences']:
                    self.assertIn(line,section)
            group = next(g for g in read('groups.json')['groups'] if g['author']==author and g['title']==selected[0]['group']['title'])
            self.assertEqual(group['wholeGroupConfirmed'],order==254)

    def test_reported_book_title_is_kept_separate_from_verified_title(self):
        e = self.entries[262]
        p = self.poems[e['selectedPoemIds'][0]]
        self.assertEqual((e['title'],p['title'],p['author']),('江南曲','江南曲','于鹄'))
        self.assertEqual(e['titleReview']['reportedBookTitle'],'江南春')
        self.assertFalse(e['titleReview']['bookPageIndependentlyChecked'])
        self.assertNotIn('江南春',p['aliases'])
        self.assertTrue(e['matchingEvidenceUrls'])
        exported = next(e for e in read('matched-poems.json')['entries'] if e['order']==263)
        self.assertEqual(exported['titleReview'],e['titleReview'])
        self.assertTrue(any(r['catalogEntryId']==e['id'] for r in read('audit.json')['titleReviews']))
        dup = self.poems[self.entries[87]['selectedPoemIds'][0]]
        self.assertEqual(dup['author'],'杜牧')
        self.assertNotEqual(p['id'],dup['id'])

    def test_partial_group_cannot_be_declared_complete(self):
        confirmation = read('sources/user-confirmations.json')
        choice = next(c for b in confirmation['batches'] for c in b['selections'] if c['catalogEntryId']=='xieying-track-254')
        choice['selectedPoemIds'] = choice['selectedPoemIds'][:1]
        with self.assertRaisesRegex(ValueError,'Incomplete whole-group confirmation'):
            builder.apply_confirmations(copy.deepcopy(self.entries),list(self.poems.values()),confirmation)

    def test_qiupuge_exports_both_requested_members_in_order(self):
        entry = self.entries[63]
        self.assertEqual(entry['status'],'user-confirmed-selection')
        selected = [self.poems[i] for i in entry['selectedPoemIds']]
        self.assertEqual([p['group']['position'] for p in selected],[14,15])
        self.assertEqual([p['paragraphs'][0] for p in selected],
                         ['炉火照天地，红星乱紫烟。','白发三千丈，缘愁似个长。'])
        exported = next(e for e in read('matched-poems.json')['entries'] if e['order']==64)
        self.assertEqual([p['id'] for p in exported['poems']],entry['selectedPoemIds'])
        section = (DATA/'MATCHED_POEMS.md').read_text().split('## 064. ')[1].split('\n## ')[0]
        for p in selected:
            for line in p['sentences']:
                self.assertIn(line,section)

    def test_invalid_confirmation_cannot_silently_select_unrelated_poem(self):
        confirmation = read('sources/user-confirmations.json')
        confirmation['batches'][0]['selections'][0]['selectedPoemIds'] = self.entries[16]['selectedPoemIds'][:]
        with self.assertRaisesRegex(ValueError,'Invalid confirmed poem IDs'):
            builder.apply_confirmations(copy.deepcopy(self.entries),list(self.poems.values()),confirmation)
        confirmation = read('sources/user-confirmations.json')
        confirmation['batches'][0]['selections'][0]['expectedTitle'] = '错题'
        with self.assertRaisesRegex(ValueError,'Confirmation no longer matches catalog'):
            builder.apply_confirmations(copy.deepcopy(self.entries),list(self.poems.values()),confirmation)


if __name__=='__main__':
    unittest.main()
