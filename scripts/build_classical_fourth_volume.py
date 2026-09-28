#!/usr/bin/env python3
"""Build the fourth-volume research data offline; never write app resources."""
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

from build_tang_yizhu import key, separate_annotations, simplified, sentences
from build_tang_third_volume import duplicate_candidates

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/expansion/classical-fourth-volume'
BASELINES = [ROOT / 'data/final/tang_poems_final.json',
             ROOT / 'data/expansion/tang-second-volume/poems.json',
             ROOT / 'data/expansion/tang-third-volume/poems.json']
DATE = '2026-09-28'
PERIODS = ['先秦', '两汉', '魏晋', '南北朝', '隋代', '宋代', '金朝', '元代', '明代', '清代']
HAN = re.compile(r'[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\U00020000-\U000323af]')


def read(path):
    return json.loads(path.read_text())


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def write(name, value):
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2) + '\n'
    (OUT / name).write_text(text)


def fingerprint(path):
    return {'path': str(path.relative_to(ROOT)), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def clean_source(source):
    return separate_annotations(source['raw']['content'].splitlines())


def build_poem(entry, sources, order):
    refs = [sources[i] for i in entry['sourceIds']]
    source = refs[0]
    clean, annotations = clean_source(source)
    base = '\n'.join(clean)
    ex = entry['extraction']
    if sha(base) != ex['cleanedSourceSha256']:
        raise ValueError(f'Source changed: {entry["id"]}')
    if not 0 <= ex['start'] < ex['end'] <= len(base):
        raise ValueError(f'Invalid source boundary: {entry["id"]}')
    original = base[ex['start']:ex['end']]
    if original[:30] != ex['expectedOpening'] or original[-40:] != ex['expectedEnding']:
        raise ValueError(f'Poem boundary changed: {entry["id"]}')
    text = '\n'.join(simplified(re.sub(r'[ \t\u3000]+', '', line))
                     for line in original.splitlines() if line.strip())
    for edit in entry['edits']:
        if text.count(edit['old']) != 1:
            raise ValueError(f'Correction no longer applicable: {entry["id"]}')
        text = text.replace(edit['old'], edit['new'])
    if re.search(r'[A-Za-z\uFFFD]|——|版本[一二三]|原版|缺字', text):
        raise ValueError(f'Non-verse content remains: {entry["id"]}')
    for other in refs[1:]:
        other_clean, _ = clean_source(other)
        if key('\n'.join(other_clean)) != key(base):
            raise ValueError('Conflicting duplicate source readings require an editorial decision')
    paragraphs = text.splitlines()
    clauses = sentences(paragraphs)
    counts = [len(HAN.findall(v)) for v in clauses]
    uniform = counts[0] if len(set(counts)) == 1 else None
    form_label = '杂言诗' if uniform is None else {4: '四言诗', 5: '五言诗', 6: '六言诗', 7: '七言诗'}.get(uniform, f'{uniform}言诗')
    notes = deepcopy(entry['notes'])
    if len(clauses) > 40:
        notes.append('长篇须按可靠印本逐章逐句复核；本轮已收集全篇来源文本，不以名句节选代替全诗。')
    if entry['dynasty'] not in PERIODS or entry['literaryCategory'] not in {'诗', '诗经', '楚辞', '乐府/拟乐府'}:
        raise ValueError('Outside fourth-volume scope')
    return {
        'id': entry['id'], 'order': order, 'title': entry['title'], 'author': entry['author'],
        'authorDisplay': entry['authorDisplay'], 'dynasty': entry['dynasty'],
        'dynastyBasis': '编辑归类；不等同于已经考定写作年份，争议见 editorialNotes',
        'literaryCategory': entry['literaryCategory'],
        'aliases': list(dict.fromkeys([entry['title'], source['raw']['title']])),
        'text': text, 'paragraphs': paragraphs, 'sentences': clauses,
        'textSha256': sha(text), 'normalizedTextSha256': sha(key(text)),
        'form': {'lineLengthDescription': form_label, 'punctuationClauseCount': len(clauses),
                 'characterCount': len(HAN.findall(text)), 'clauseCharacterCounts': counts,
                 'status': 'length-description-only', 'prosodyVerified': False,
                 'note': '分句数不一定等于韵律诗行数；未按四句、八句机械判作绝句或律诗。'},
        'sourceReading': {'title': source['raw']['title'], 'author': source['raw']['author'],
                          'dynasty': source['raw']['dynasty'], 'text': original,
                          'textSha256': sha(original), 'extraction': ex,
                          'rawRecordRef': 'sources/selected-texts.json#' + source['id']},
        'sourceRefs': [{k: v for k, v in s.items() if k != 'raw'} for s in refs],
        'sourceNotes': annotations,
        'preface': entry.get('preface'),
        'fictionalSpeaker': '林黛玉' if entry['author'] == '曹雪芹' else None,
        'textProcessing': ['balanced parenthetical notes separated', 'explicit complete poem/version boundaries',
                           'OpenCC t2s simplified display; raw source unchanged', 'horizontal whitespace removed'],
        'editorialDecisions': deepcopy(entry['edits']), 'identityChecks': deepcopy(entry['checks']),
        'editorialNotes': notes,
        'selection': {'reason': entry['reason'], 'basis': 'familiar-poems-first-editorial-curation',
                      'bookMembershipStatus': 'not-verified-poem-by-poem',
                      'popularityMeasured': False},
        'review': {'publicationReady': False, 'status': 'collected-needs-print-edition-proofreading',
                   'wholePoemAgainstPrintEdition': False},
        'collectionStatus': 'fourth-volume-research-not-imported',
    }


def main():
    manifest = read(OUT / 'selection.json')
    source_doc = read(OUT / 'sources/selected-texts.json')
    sources = {s['id']: s for s in source_doc['records']}
    for s in sources.values():
        if sha(s['raw']['content']) != s['rawContentSha256']:
            raise ValueError(f'Raw source hash mismatch: {s["id"]}')
    poems = [build_poem(e, sources, i) for i, e in enumerate(manifest['entries'], 1)]
    if len({p['id'] for p in poems}) != len(poems):
        raise ValueError('Duplicate poem identities')
    app = read(BASELINES[0])['poems']
    xieying = read(BASELINES[1])['poems']
    third = read(BASELINES[2])['poems']
    baseline = app + xieying + third
    overlap = duplicate_candidates(poems, baseline)
    internal = duplicate_candidates(poems, poems, same_collection=True)
    if overlap or internal:
        raise ValueError(json.dumps({'baseline': overlap, 'internal': internal}, ensure_ascii=False))
    counts = Counter(p['dynasty'] for p in poems)
    stats = {'poems': len(poems), 'authorLabelsIncludingAnonymous': len({p['author'] for p in poems}),
             'anonymousPoems': sum(p['author'] == '佚名' for p in poems),
             'byPeriod': {d: counts[d] for d in PERIODS if counts[d]},
             'byLiteraryCategory': dict(Counter(p['literaryCategory'] for p in poems)),
             'sourceRecords': len(sources), 'textCorrections': sum(len(p['editorialDecisions']) for p in poems),
             'longPoemsOver40Clauses': sum(p['form']['punctuationClauseCount'] > 40 for p in poems)}
    inputs = [OUT/'selection.json', OUT/'sources/selected-texts.json', OUT/'sources/methodology.json',
              OUT/'sources/selection-review.json', *BASELINES]
    old_unique = {key(p['text']) for p in baseline}
    audit = {'checkedOn': DATE, 'inputs': [fingerprint(p) for p in inputs], 'stats': stats,
             'deduplication': {'normalization': 'simplified + punctuation removed + explicit glyph folding',
                              'algorithm': 'SequenceMatcher, threshold 0.70; all available baseline text witnesses',
                              'groupHandling': 'compare extracted complete members, not entire source cycles',
                              'baselineCandidates': overlap, 'internalCandidates': internal},
             'releasePlan': {'volume1': len(app), 'volume2Gross': len(xieying), 'volume3': len(third),
                             'firstThreeUnique': len(old_unique), 'volume4NetNew': len(poems),
                             'fourVolumeUnique': len(old_unique | {key(p['text']) for p in poems}),
                             'status': 'research plan; App remains unchanged'}, 'publicationReady': False}
    write('poems.json', {'schemaVersion': 1, 'name': manifest['name'], 'selectedOn': DATE,
                         'publicationReady': False, 'importIntoApp': False, 'stats': stats,
                         'selectionPolicy': manifest['selectionPolicy'],
                         'methodologyRef': 'sources/methodology.json', 'auditRef': 'audit.json', 'poems': poems})
    write('audit.json', audit)
    catalog = ['# 第四卷：唐以外古典诗歌 300 首初选', '',
               '只收诗，不收唐诗、宋词、元曲。组诗按单首计数，异本不重复计数。暂不导入 App。', '',
               '这是一份编辑初选，并非知名度排名；未逐首核实参考选本收录关系。', '',
               '[说明](README.md) · [完整诗文](POEMS.md) · [结构化数据](poems.json) · [校订与待核](REVIEW.md)', '']
    full = ['# 第四卷：完整诗文工作稿', '',
            '300 首，采用每首完整读法；来源中的组诗、不同版本和小序分别保存。尚未逐字对校印本。', '',
            '[目录](CATALOG.md) · [说明](README.md) · [校订与待核](REVIEW.md)', '']
    review = ['# 校订与待核', '',
              '所有 300 首均需出版前定本校对；以下列出当前已识别的额外事项。', '',
              '“核对”只表示其后注明的篇次、身份或字句核对，不等同于已校完整部选集。', '']
    for period in stats['byPeriod']:
        catalog += [f'## {period}（{counts[period]} 首）', '',
                    '| 编号 | 作者 | 诗题 | 起句 | 收录考虑 |', '| --- | --- | --- | --- | --- |']
        for p in poems:
            if p['dynasty'] == period:
                incipit = ''.join(p['sentences'][:2])
                catalog.append(f'| {p["order"]:03} | {p["authorDisplay"]} | [{p["title"]}](POEMS.md#{p["id"]}) | {incipit} | {p["selection"]["reason"]} |')
        catalog.append('')
    for p in poems:
        full += [f'<a id="{p["id"]}"></a>', '', f'## {p["order"]:03}　{p["title"]}', '',
                 f'{p["dynasty"]} · {p["authorDisplay"]}', '', '\\\n'.join(p['paragraphs']), '',
                 f'收录考虑：{p["selection"]["reason"]}', '',
                 f'[正文来源]({p["sourceRefs"][0]["url"]})；来源原题《{p["sourceReading"]["title"]}》。']
        if p['preface']:
            full += ['', '<details><summary>原序（不计入诗歌正文）</summary>', '', p['preface'], '', '</details>']
        if p['editorialNotes'] or p['editorialDecisions'] or p['identityChecks']:
            review += [f'## {p["order"]:03}　{p["title"]} · {p["authorDisplay"]}', '']
            for note in p['editorialNotes']:
                review.append(f'- {note}')
            for check in [*p['identityChecks'], *p['editorialDecisions']]:
                review.append(f'- {check["note"]} [核对来源]({check["url"]})')
            review.append('')
            full += ['', f'编辑事项见 [校订与待核](REVIEW.md)，结构化详情见记录 `{p["id"]}`。']
        full.append('')
    write('CATALOG.md', '\n'.join(catalog))
    write('POEMS.md', '\n'.join(full))
    write('REVIEW.md', '\n'.join(review))
    print(json.dumps({'stats': stats, 'releasePlan': audit['releasePlan']}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
