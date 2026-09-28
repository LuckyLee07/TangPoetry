#!/usr/bin/env python3
"""Build an isolated, source-attributed expansion research corpus (never app data)."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re

from opencc import OpenCC

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/expansion/tang-yizhu'
COMMIT = 'b8594f81a89752241442f2ce267d6f66f96704ee'
REPO = f'https://github.com/chinese-poetry/chinese-poetry/blob/{COMMIT}/'
ACCESSED = '2026-09-28'
CC = OpenCC('t2s')
SC = OpenCC('s2t')
HAN = re.compile(r'[\u3400-\u9fff\U00020000-\U000323af]')
# For search/dedup only; the displayed texts retain their source readings.
FOLD = str.maketrans({'牀':'床','羣':'群','峯':'峰','迴':'回','閒':'闲','谿':'溪',
                     '鴈':'雁','鸎':'莺','詶':'酬','姪':'侄','隄':'堤','濬':'浚',
                     '脩':'修','霑':'沾','裴':'裴','荅':'答','盃':'杯','飜':'翻',
                     '昇':'升','爲':'为','竝':'并','氷':'冰','疎':'疏','烟':'烟'})
PREFIX = re.compile(r'^(?:相和歌辞|杂曲歌辞|横吹曲辞|鼓吹曲辞|琴曲歌辞|新乐府|清商曲辞|近代曲辞|舞曲歌辞)\s*')


def read(path):
    return json.loads(Path(path).read_text())


def write(name, obj):
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')


@lru_cache(maxsize=100000)
def simplified(value):
    return CC.convert(value)


@lru_cache(maxsize=100000)
def key(value):
    return ''.join(HAN.findall(simplified(value).translate(FOLD)))


def numeral(value):
    if value.isdigit():
        return int(value)
    digits = dict(zip('零一二三四五六七八九', range(10)))
    total = current = 0
    for c in value:
        if c in digits:
            current = digits[c]
        elif c in '十百':
            total += (current or 1) * {'十': 10, '百': 100}[c]
            current = 0
    return total + current


def title_parts(value):
    value = simplified(value)
    value = re.sub(r'[（(]其([一二三四五六七八九十百]+)[）)]', r' \1', value)
    value = re.sub(r'[（(].*?[）)]|\[[^\]]*\]', '', value)
    value = value.split('\t')[0].strip().replace('”', '')
    value = PREFIX.sub('', value)
    m = re.search(r'\s+([一二三四五六七八九十百]+)$', value)
    index = numeral(m[1]) if m else None
    group = value[:m.start()].strip() if m else None
    base = re.sub(r'[一二三四五六七八九十百]+首$', '', group or value)
    return value, group, index, key(base)


def import_sources(corpus_path, authors_path, qianjiashi_path):
    all_poems = read(corpus_path)
    aliases = read(OUT / 'selection-aliases.json')
    by_author = defaultdict(list)
    for p in all_poems:
        by_author[key(p['author'])].append(p)
    chosen, requests = {}, []
    for line in (OUT / 'selection.txt').read_text().splitlines():
        if not line or line.startswith('#'):
            continue
        author, titles = line.split('\t')
        for request in dict.fromkeys(titles.split('；')):
            subset = re.search(r'〔([0-9,]+)〕$', request)
            indices = set(map(int, subset[1].split(','))) if subset else None
            title = request[:subset.start()] if subset else request
            lookup = aliases['aliases'].get(f'{author}|{title}', title)
            explicit_ids = aliases.get('sourceIdSelections', {}).get(f'{author}|{title}')
            target = title_parts(lookup)[3]
            matches = []
            for p in by_author[key(author)]:
                clean, group, index, base = title_parts(p['title'])
                matched = p['id'] in explicit_ids if explicit_ids else (base == target or clean.startswith(lookup + ' ') or clean.endswith(' ' + lookup))
                if matched and (indices is None or index in indices):
                    matches.append(p)
            request_id = f'{author}|{request}'
            requests.append({'request': request_id, 'lookup': lookup,
                             'sourceIds': [p['id'] for p in matches],
                             'status': 'matched' if matches else 'unresolved',
                             'note': aliases['reviewNotes'].get(f'{author}|{title}') or
                                     aliases['unresolvedReasons'].get(f'{author}|{title}')})
            for p in matches:
                item = chosen.setdefault(p['id'], {
                    'raw': {k: p[k] for k in ('id', 'author', 'title', 'paragraphs')},
                    'file': '全唐诗/' + p['sourceFile'], 'index': p['sourceIndex'],
                    'requests': [], 'selectionNotes': []})
                if request_id not in item['requests']:
                    item['requests'].append(request_id)
                note = aliases['reviewNotes'].get(f'{author}|{title}')
                if note and note not in item['selectionNotes']:
                    item['selectionNotes'].append(note)
    write('sources/selected-qts.json', {'repositoryCommit': COMMIT, 'accessedOn': ACCESSED,
                                      'selectionRule': 'explicit-author-and-title; selected cycles expanded',
                                      'records': list(chosen.values())})
    write('selection-report.json', {'requests': requests})
    names = {key(p['raw']['author']) for p in chosen.values()}
    authors = [p for p in read(authors_path) if key(p['name']) in names]
    write('sources/authors-qts.json', {'file': '全唐诗/authors.tang.json',
                                     'repositoryCommit': COMMIT, 'records': authors})
    write('sources/qianjiashi.json', read(qianjiashi_path))


def source_ref(source_id, file=None, **extra):
    return {'sourceId': source_id, 'url': REPO + file if file else extra.pop('url'),
            'accessedOn': ACCESSED, **extra}


def score(a, b):
    return SequenceMatcher(None, a, b, autojunk=False).ratio()


def sentences(paragraphs):
    return [v.strip() for p in paragraphs
            for v in re.findall(r'[^，。！？；、\n]+[，。！？；、]?', p) if key(v)]


def shape(paragraphs, title, source_title):
    lines = sentences(paragraphs)
    counts = [len(HAN.findall(p)) for p in lines]
    uniform = counts[0] if counts and len(set(counts)) == 1 else None
    n = len(counts)
    guess = '杂言古诗'
    if uniform in (5, 6, 7):
        word = {5:'五言',6:'六言',7:'七言'}[uniform]
        guess = word + ('绝句' if n == 4 else '律诗' if n == 8 else '古诗')
    elif uniform:
        guess = f'{uniform}言诗'
    yuefu = bool(PREFIX.match(simplified(source_title)))
    return {'sentenceCount': n, 'characterCounts': counts, 'uniformLineLength': uniform,
            'characterCount': sum(counts), 'proposedGenre': '乐府' if yuefu else guess,
            'metricalShape': guess, 'status': 'source-yuefu-heading' if yuefu else 'shape-inferred',
            'basis': '来源乐府门类' if yuefu else '按分句字数与句数初分，未作平仄、押韵及体裁定本核验',
            'prosodyVerified': False}


def separate_annotations(paragraphs):
    """Keep bracketed supplied characters; remove notes across paragraph boundaries.

    QTS uses [欸] for an editorially supplied character, but [二] etc. in
    秦婦吟 for footnotes. Treating every bracket as a note would delete verse.
    The complete original remains in sources/selected-qts.json.
    """
    annotations, cleaned = [], []
    depth, note, start = 0, [], None
    for index, paragraph in enumerate(paragraphs):
        output = []
        for char in paragraph:
            if char in '（(':
                if depth == 0:
                    start = index
                depth += 1
                note.append(char)
            elif depth:
                note.append(char)
                if char in '）)':
                    depth -= 1
                    if depth == 0:
                        annotations.append({'kind': 'parenthetical-note', 'paragraphIndex': start,
                                            'endParagraphIndex': index, 'sourceText': ''.join(note)})
                        note = []
            else:
                output.append(char)
        if depth:
            note.append('\n')
        def square(match):
            inner = match[1]
            footnote = bool(re.fullmatch(r'[零一二三四五六七八九十百○0-9]+', inner))
            annotations.append({'kind': 'footnote-marker' if footnote else 'supplied-reading',
                                'paragraphIndex': index, 'sourceText': match[0],
                                'retainedText': '' if footnote else inner})
            return '' if footnote else inner
        value = re.sub(r'\[([^\]]*)\]', square, ''.join(output)).strip()
        if key(value):
            cleaned.append(value)
    if note:
        annotations.append({'kind': 'unclosed-parenthetical-note', 'paragraphIndex': start,
                            'endParagraphIndex': len(paragraphs)-1, 'sourceText': ''.join(note)})
    return cleaned, annotations


def make_record(raw, refs, selection_requests=None, selection_notes=None, traditional=True):
    title_raw = raw['title']
    title, group, position, _ = title_parts(title_raw)
    source_lines = list(raw['paragraphs'])
    clean, annotations = separate_annotations(source_lines)
    text_s = [simplified(p) for p in clean]
    digest = hashlib.sha256((raw.get('id') or raw['author'] + '|' + title_raw + '|' + ''.join(source_lines)).encode()).hexdigest()[:16]
    warnings = []
    original = ''.join(source_lines)
    if re.search(r'[□〓�]|缺字|缺[一二三四五六七八九十]字', original):
        warnings.append('source-missing-character')
    if re.search(r'[A-Za-z]|\{[^}]*\}|\[[^\]]*\]|[\ue000-\uf8ff]', ''.join(clean)):
        warnings.append('source-editorial-markers')
    if annotations:
        warnings.append('embedded-annotations-separated')
    if any(a['kind'] == 'unclosed-parenthetical-note' for a in annotations):
        warnings.append('unclosed-source-annotation')
    if any(a['kind'] == 'supplied-reading' for a in annotations):
        warnings.append('editorially-supplied-reading')
    if '并序' in title_raw or any(len(p) > 150 and '。' in p for p in clean):
        warnings.append('possible-preface-or-long-paragraph')
    form = shape(text_s, title, title_raw)
    if form['uniformLineLength'] is None:
        warnings.append('mixed-length-verse-review')
    if selection_notes:
        warnings.append('title-variant-review')
    return {'id': 'yizhu-' + digest, 'title': title, 'titleTraditional': SC.convert(title),
            'titleTraditionalOrigin': 'OpenCC-s2t-generated-not-edition',
            'sourceTitle': title_raw, 'author': simplified(raw['author']),
            'authorTraditional': raw['author'], 'dynasty': '唐',
            'dynastyBasis': '唐诗资料的选目范围，非单篇系年结论；跨唐五代作者尚待逐篇核验',
            'aliases': list(dict.fromkeys([simplified(title_raw)])),
            'group': {'title': group, 'position': position} if group else None,
            'paragraphs': text_s,
            'paragraphsTraditional': clean if traditional else [SC.convert(p) for p in clean],
            'traditionalTextOrigin': 'source' if traditional else 'OpenCC-s2t-generated-not-edition',
            'text': '\n'.join(text_s), 'sentences': sentences(text_s),
            'form': form, 'sourceAnnotations': annotations,
            'selection': {'basis': 'independent-curation', 'requests': selection_requests or [],
                          'notes': selection_notes or [], 'bookMembership': 'unconfirmed'},
            'sourceRefs': refs, 'witnesses': [],
            'variants': [], 'existingLibraryMatches': [],
            'review': {'status': 'collected-needs-editorial-review', 'issues': warnings},
            'enrichment': {'translation': None, 'wordNotes': None, 'appreciation': None,
                           'compositionYear': None, 'compositionPlace': None,
                           'pinyin': None, 'status': 'not-collected'},
            'sourceRecordIds': [raw.get('id')] if raw.get('id') else []}


def add_witness(record, raw, ref, genre=None):
    a = key(record['text'])
    b = key(''.join(separate_annotations(raw['paragraphs'])[0]))
    status = 'normalized-text-agrees' if a == b else 'text-variant'
    witness = {'title': raw['title'], 'author': raw['author'], 'paragraphs': raw['paragraphs'],
               'sourceRef': ref, 'comparison': status, 'similarity': round(score(a, b), 4)}
    record['witnesses'].append(witness)
    # A comparison anthology may renumber an excerpted cycle. Its title is a
    # witness title, never silently promoted to a canonical alternate title.
    ordinal = re.search(r'其([一二三四五六七八九十百]+)$', simplified(raw['title']))
    if ordinal and record['group'] and numeral(ordinal[1]) != record['group']['position']:
        witness['numberingStatus'] = 'differs-from-base-cycle'
        record['review']['issues'].append('witness-cycle-numbering-differs')
    if status == 'text-variant':
        edits = []
        for tag, i, j, x, y in SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
            if tag != 'equal':
                edits.append({'kind': tag, 'base': a[i:j], 'witness': b[x:y],
                              'baseOffset': i, 'witnessOffset': x})
        record['variants'].append({'sourceId': ref['sourceId'], 'sourceRef': ref, 'differences': edits,
                                   'comparisonBasis': '去标点、简体及检索字形归一后的汉字串；原始版本均保留'})
    expected = {'五言绝句': (4, 5), '七言绝句': (4, 7), '五言律诗': (8, 5), '七言律诗': (8, 7)}
    shape_ok = genre not in expected or (record['form']['sentenceCount'], record['form']['uniformLineLength']) == expected[genre]
    if genre and shape_ok:
        record['form'].update(proposedGenre=genre, status='reference-classification',
                              basis=ref['sourceId'])
    elif genre:
        record['review']['issues'].append('reference-genre-shape-conflict')


def best_match(raw, candidates):
    target = key(''.join(separate_annotations(raw['paragraphs'])[0]))
    author = key(raw['author'])
    possible = [p for p in candidates if key(p['author']) == author]
    result = None
    for p in possible:
        value = key(p['text'])
        # Trigram gate avoids expensive comparisons for unrelated long poems.
        if target[:8] != value[:8] and not set(target[i:i+3] for i in range(max(0, len(target)-2))) & set(value[i:i+3] for i in range(max(0, len(value)-2))):
            continue
        ratio = score(target, value)
        if ratio >= .84 and (result is None or ratio > result[0]):
            result = ratio, p
    return result[1] if result else None


def build():
    source = read(OUT / 'sources/selected-qts.json')
    records, merged = [], []
    for p in source['records']:
        raw = p['raw']
        ref = source_ref('chinese-poetry-qts', p['file'], recordId=raw['id'],
                         recordIndex=p['index'], repositoryCommit=COMMIT)
        record = make_record(raw, [ref], p['requests'], p['selectionNotes'])
        # Only merge same-author, same-opening, extremely similar versions.
        hit = next((v for v in records if key(v['author']) == key(record['author']) and
                    key(v['text'])[:12] == key(record['text'])[:12] and
                    score(key(v['text']), key(record['text'])) >= .94), None)
        if hit:
            add_witness(hit, raw, ref)
            hit['sourceRecordIds'].extend(record['sourceRecordIds'])
            hit['selection']['requests'] = list(dict.fromkeys(hit['selection']['requests'] + p['requests']))
            merged.append({'retainedId': hit['id'], 'mergedSourceId': raw['id'], 'title': raw['title']})
        else:
            records.append(record)
    # Explicitly reviewed pairs whose openings/numbering differ across copies.
    raw_by_id = {p['raw']['id']: p['raw'] for p in source['records']}
    for link in read(OUT / 'sources/version-links.json')['links']:
        retained = next((p for p in records if p['id'] == link['retainedId']), None)
        alternate = next((p for p in records if p['id'] == link['alternateId']), None)
        if retained is None or alternate is None:
            raise ValueError(f"Version link no longer resolves: {link}")
        raw = raw_by_id[alternate['sourceRecordIds'][0]]
        add_witness(retained, raw, alternate['sourceRefs'][0])
        retained['witnesses'].extend(alternate['witnesses'])
        retained['variants'].extend(alternate['variants'])
        retained['sourceRecordIds'].extend(alternate['sourceRecordIds'])
        retained['selection']['requests'] = list(dict.fromkeys(retained['selection']['requests'] + alternate['selection']['requests']))
        retained['selection']['notes'].append(link['basis'])
        records.remove(alternate)
        merged.append({'retainedId': retained['id'], 'mergedId': alternate['id'],
                       'mergedSourceIds': alternate['sourceRecordIds'], 'title': alternate['sourceTitle'],
                       'basis': 'reviewed-version-link'})
    # Cross-read only matching Tang entries from a second anthology; do not trust
    # its attribution or title automatically where it conflicts with the base.
    qian = read(OUT / 'sources/qianjiashi.json')
    qian_matches = 0
    for section in qian['content']:
        for i, p in enumerate(section['content']):
            if '唐' not in p['author']:
                continue
            children = p['paragraphs'] if p['paragraphs'] and isinstance(p['paragraphs'][0], dict) else [{'subchapter': '', 'paragraphs': p['paragraphs']}]
            for child in children:
                raw = {'author': re.sub(r'[（(].*?[）)]', '', p['author']).strip(),
                       'title': p['chapter'] + child['subchapter'], 'paragraphs': child['paragraphs']}
                hit = best_match(raw, records)
                if hit:
                    add_witness(hit, raw, source_ref('chinese-poetry-qianjiashi', '蒙学/qianjiashi.json',
                                section=section['type'], recordIndex=i, subchapter=child['subchapter']), simplified(section['type']))
                    qian_matches += 1
    book = read(OUT / 'sources/book-confirmed.json')
    for p in book['poems']:
        ref = source_ref('tangshi-xieying-public-preview', url=p['url'], chapterId=p['chapterId'])
        hit = best_match(p, records)
        if hit is None:
            hit = make_record(p, [ref], traditional=False)
            records.append(hit)
        add_witness(hit, p, ref, p['genre'])
        hit['selection'].update(basis='book-public-preview', bookMembership='confirmed',
                                bookChapterId=p['chapterId'], bookTitle=book['book']['title'])
    supplements_file = OUT / 'sources/supplements.json'
    if supplements_file.exists():
        for p in read(supplements_file)['poems']:
            ref = source_ref(p['sourceId'], url=p['url'])
            hit = best_match(p, records)
            if hit is None:
                hit = make_record(p, [ref], traditional=False)
                records.append(hit)
            else:
                add_witness(hit, p, ref)
            hit['aliases'] = list(dict.fromkeys(hit['aliases'] + p.get('aliases', [])))
            if p.get('genre'):
                hit['form'].update(proposedGenre=p['genre'], status='reference-classification', basis=p['url'])
            if p.get('reviewNote'):
                hit['review']['issues'].append('attribution-or-edition-review')
                hit['selection']['notes'].append(p['reviewNote'])
            if p.get('textualVariants'):
                hit['variants'].append({'sourceId': p['sourceId'], 'url': p['url'], 'reportedVariants': p['textualVariants']})
    # Resolve requests via supplementary witnesses as well as the base corpus.
    selection_report = read(OUT / 'selection-report.json')
    for request in selection_report['requests']:
        author, title = request['request'].split('|', 1)
        target = title_parts(title)[3]
        hits = [p for p in records if request['request'] in p['selection']['requests'] or
                (key(p['author']) == key(author) and target == title_parts(p['title'])[3])]
        request['resolvedPoemIds'] = [p['id'] for p in hits]
        request['finalStatus'] = 'resolved' if hits else 'unresolved'
        for p in hits:
            if request['request'] not in p['selection']['requests']:
                p['selection']['requests'].append(request['request'])
            if p['group'] is None and '〔' not in title and title not in p['aliases']:
                p['aliases'].append(title)
    write('selection-report.json', selection_report)
    existing_path = ROOT / 'data/final/tang_poems_final.json'
    existing = read(existing_path)['poems']
    # Title and text comparisons are both reported; cross-author copies are
    # retained in the review queue, never silently credited to a new author.
    for p in records:
        text_key = key(p['text'])
        possible = [e for e in existing if key(e['author']) == key(p['author']) or
                    key(e['text'])[:8] == text_key[:8] or title_parts(e['title'])[3] == title_parts(p['title'])[3]]
        for e in possible:
            other = key(e['text'])
            same_author = key(e['author']) == key(p['author'])
            ratio = score(text_key, other)
            if ratio >= .82 and (same_author or ratio >= .9):
                p['existingLibraryMatches'].append({'id': e['id'], 'title': e['title'], 'author': e['author'],
                    'similarity': round(ratio, 4), 'type': 'same-text' if text_key == other else 'same-work-text-variant',
                    'authorAgrees': same_author})
                if not same_author:
                    p['review']['issues'].append('existing-library-author-differs')
        if p['existingLibraryMatches']:
            p['collectionStatus'] = 'already-in-app'
        elif any(i in p['review']['issues'] for i in ('source-missing-character','source-editorial-markers','unclosed-source-annotation','possible-preface-or-long-paragraph','attribution-or-edition-review','title-variant-review','reference-genre-shape-conflict')):
            p['collectionStatus'] = 'review-before-inclusion'
        else:
            p['collectionStatus'] = 'new-candidate'
        p['review']['issues'] = list(dict.fromkeys(p['review']['issues']))
        p['textSha256'] = hashlib.sha256(p['text'].encode()).hexdigest()
    genre_order = {'五言绝句':0,'七言绝句':1,'六言绝句':2,'五言律诗':3,'七言律诗':4,
                   '五言排律':5,'七言排律':6,'五言古诗':7,'七言古诗':8,'乐府':9,'杂言古诗':10}
    records.sort(key=lambda p:(genre_order.get(p['form']['proposedGenre'], 99), p['author'], p['group']['title'] if p['group'] else p['title'], p['group']['position'] if p['group'] else 0, p['id']))
    for i, p in enumerate(records, 1):
        p['order'] = i
    authors_raw = read(OUT / 'sources/authors-qts.json')
    author_index = defaultdict(list)
    for p in records:
        author_index[p['author']].append(p)
    authors = []
    for name, poems in sorted(author_index.items()):
        biographies = [a for a in authors_raw['records'] if key(a['name']) == key(name)]
        authors.append({'id': 'author-' + hashlib.sha256(name.encode()).hexdigest()[:12],
                        'name': name, 'poemIds': [p['id'] for p in poems],
                        'poemCount': len(poems), 'newCandidateCount': sum(p['collectionStatus']=='new-candidate' for p in poems),
                        'biographies': [{'sourceTextTraditional': a.get('desc', ''),
                            'textSimplified': simplified(a.get('desc', '')),
                            'sourceRef': source_ref('chinese-poetry-qts-authors', '全唐诗/authors.tang.json', sourceAuthorName=a['name']),
                            'reviewStatus': 'historical-biography-not-modern-fact-check'} for a in biographies],
                        'birthYear': None, 'deathYear': None, 'datesStatus': 'not-verified'})
    groups_index = defaultdict(list)
    for p in records:
        if p['group']:
            groups_index[(p['author'], p['group']['title'])].append(p)
    groups = []
    for (author, title), entries in sorted(groups_index.items()):
        ordered = sorted(entries, key=lambda p: (p['group']['position'], p['id']))
        groups.append({'id': 'group-' + hashlib.sha256((author+'|'+title).encode()).hexdigest()[:12],
                       'author': author, 'title': title, 'poemIds': [p['id'] for p in ordered],
                       'collectedPositions': [p['group']['position'] for p in ordered],
                       'completeness': 'not-asserted', 'note': '底本题名与序号；部分组诗有意节选，不等于全组收齐。'})
    stats = {'recordCount': len(records), 'authorCount': len(authors),
             'selectedSourceRecordCount': len(source['records']),
             'newCandidateCount': sum(p['collectionStatus']=='new-candidate' for p in records),
             'reviewBeforeInclusionCount': sum(p['collectionStatus']=='review-before-inclusion' for p in records),
             'alreadyInAppCount': sum(p['collectionStatus']=='already-in-app' for p in records),
             'bookConfirmedCount': sum(p['selection']['bookMembership']=='confirmed' for p in records),
             'qianjiashiComparisonCount': qian_matches, 'sourceVersionsMerged': len(merged),
             'withWitnessCount': sum(bool(p['witnesses']) for p in records),
             'withTextVariantsCount': sum(bool(p['variants']) for p in records),
             'groupCount': len(groups),
             'selectionRequestCount': len(selection_report['requests']),
             'unresolvedRequestCount': sum(r['finalStatus']=='unresolved' for r in selection_report['requests']),
             'uniqueExistingAppPoemCount': len({m['id'] for p in records for m in p['existingLibraryMatches']}),
             'genreCounts': dict(Counter(p['form']['proposedGenre'] for p in records)),
             'issueCounts': dict(Counter(i for p in records for i in p['review']['issues']))}
    dataset = {'schemaVersion': '1.0.0', 'name': '唐诗遗珠候选资料库', 'collectedOn': ACCESSED,
               'status': 'research-corpus-not-production-edition',
               'scope': '独立选目，以《全唐诗》开放转录本为主；另记录可公开确认的《唐诗撷英》篇目。',
               'publicationReady': False,
               'bookCatalogComplete': False, 'book': book['book'], 'stats': stats,
               'existingLibrary': {'path': 'data/final/tang_poems_final.json', 'poemCount': len(existing),
                    'sha256': hashlib.sha256(existing_path.read_bytes()).hexdigest()},
               'poems': records}
    write('poems.json', dataset)
    write('authors.json', {'schemaVersion': '1.0.0', 'authors': authors})
    write('groups.json', {'schemaVersion': '1.0.0', 'groups': groups})
    write('audit.json', {'stats': stats, 'mergedVersions': merged,
          'existingMatches': [{'id': p['id'], 'title': p['title'], 'matches': p['existingLibraryMatches']} for p in records if p['existingLibraryMatches']],
          'reviewQueue': [{'id': p['id'], 'title': p['title'], 'author': p['author'], 'issues': p['review']['issues']} for p in records if p['review']['issues']]})
    write('new-candidates.json', {'schemaVersion': '1.0.0', 'note': '仅是去重后且未发现明显结构缺损的候选ID；仍需人工校订，不是可直接发布标记。',
                                'poemIds': [p['id'] for p in records if p['collectionStatus']=='new-candidate']})
    rows = ['# 唐诗遗珠候选篇目索引', '', '> 独立选目。只有明确标记“撷英已确认”的4首已证实收录于《唐诗撷英》；不是该书完整目录。体裁带“待核”者只按字数、句数初分。', '',
            '| 序 | 题名 | 作者 | 首句 | 体裁 / 初分 | 字数 | 收录状态 | 书目关系 |',
            '| --- | --- | --- | --- | --- | ---: | --- | --- |']
    status_labels = {'new-candidate':'新增候选','already-in-app':'已有，勿重复','review-before-inclusion':'待核后收录'}
    for p in records:
        genre = p['form']['proposedGenre'] + ('（待核）' if p['form']['status']=='shape-inferred' else '')
        rows.append(f"| {p['order']} | {p['title']} | {p['author']} | {p['sentences'][0]} | {genre} | {p['form']['characterCount']} | {status_labels[p['collectionStatus']]} | {'撷英已确认' if p['selection']['bookMembership']=='confirmed' else '独立候选'} |")
    (OUT / 'CATALOG.md').write_text('\n'.join(rows) + '\n')
    rows = ['# 去除现有诗库后的扩展目录', '',
            '> 按作者分组，保留首句以区分同名诗。这里只是扩展候选，尚未进入 App；体裁初分不等于格律定论。', '']
    for author, entries in sorted(author_index.items()):
        new = [p for p in entries if p['collectionStatus'] != 'already-in-app']
        if not new:
            continue
        rows.extend([f'## {author}（{len(new)}条）', '', '| 题名 | 首句 | 体裁 / 初分 | 状态 |',
                     '| --- | --- | --- | --- |'])
        for p in new:
            rows.append(f"| {p['title']} | {p['sentences'][0]} | {p['form']['proposedGenre']} | {status_labels[p['collectionStatus']]} |")
        rows.append('')
    (OUT / 'NEW_CANDIDATES.md').write_text('\n'.join(rows) + '\n')
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--import-corpus', type=Path)
    parser.add_argument('--authors', type=Path)
    parser.add_argument('--qianjiashi', type=Path)
    args = parser.parse_args()
    if args.import_corpus:
        if not args.authors or not args.qianjiashi:
            parser.error('--import-corpus requires --authors and --qianjiashi')
        import_sources(args.import_corpus, args.authors, args.qianjiashi)
    build()
