#!/usr/bin/env python3
"""Resolve user-transcribed album titles against preserved public poetry sources.

This builds a separate catalog and candidate-text collection, never app data.
Ambiguous titles/cycle selections remain unselected until confirmed.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re

import build_tang_yizhu as base

ROOT = base.ROOT
OUT = ROOT / 'data/expansion/tang-yizhu/xieying'
ALBUM = 'https://www.ximalaya.com/album/81955629'
GENRES = {'五古': (None, 5), '七古': (None, 7), '五律': (8, 5),
          '七律': (8, 7), '五绝': (4, 5), '七绝': (4, 7)}


def load(path):
    return json.loads(Path(path).read_text())


def write(name, data):
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def parse_catalog(text):
    entries, section, occurrence = [], None, Counter()
    for raw in text.splitlines():
        if not raw.strip():
            continue
        title = re.sub(r'\d*20\d{2}-\d{2}$', '', raw.strip())
        tag = re.match(r'^【([^】]+)】', title)
        if tag:
            section = tag[1]
            occurrence[section] += 1
            title = title[tag.end():]
        i = len(entries) + 1
        entries.append({'id': f'xieying-track-{i:03}', 'order': i, 'rawInput': raw,
                        'title': title, 'section': section,
                        'sectionOccurrence': occurrence[section] if section else None,
                        'kind': 'preface' if '序言' in title else 'poem-entry',
                        'albumPage': (i-1)//30+1, 'sourceUrl': ALBUM})
    return entries


def title_identity(title):
    value = base.simplified(title)
    # Search normalization only: source text and display title stay untouched.
    value = value.translate(str.maketrans({'劒': '剑', '䜩': '宴', '脁': '朓'}))
    value = re.sub(r'\[[^\]]*\]|[（(](?!其)[^）)]*[）)]', '', value)
    value = re.sub(r'[（(]其([一二三四五六七八九十百]+)[）)]', r'·其\1', value)
    value = value.split('\t')[0].strip()
    value = base.PREFIX.sub('', value)
    value = re.sub(r'^杂歌谣辞\s*', '', value)
    index_match = re.search(r'(?:[·・]?其|\s+)([一二三四五六七八九十百]+)$', value)
    index = base.numeral(index_match[1]) if index_match else None
    if index_match:
        value = value[:index_match.start()].strip()
    count = re.search(r'([一二三四五六七八九十百]+)(?:首|绝句|绝)$', value)
    if count:
        value = value[:count.start()].strip()
    return base.key(value), index


def compatible(entry, record):
    """Use explicit absolute/regulated section shapes; retain ancient mixed meter."""
    section = entry['section']
    if section not in ('五绝', '七绝', '五律', '七律'):
        return True
    shape = record['form']
    return (shape['sentenceCount'], shape['uniformLineLength']) == GENRES[section]


def apply_confirmations(entries, records, document):
    """Apply explicit user choices without discarding the original candidate trail."""
    by_entry = {e['id']: e for e in entries}
    by_poem = {p['id']: p for p in records}
    seen = set()
    for batch in document['batches']:
        for choice in batch['selections']:
            entry = by_entry[choice['catalogEntryId']]
            if entry['id'] in seen:
                raise ValueError(f"Duplicate user confirmation: {entry['id']}")
            seen.add(entry['id'])
            if entry['title'] != choice['expectedTitle'] or entry['section'] != choice['expectedSection']:
                raise ValueError(f"Confirmation no longer matches catalog: {entry['id']}")
            selected = choice['selectedPoemIds']
            if not selected or len(selected) != len(set(selected)) or not set(selected).issubset(entry['candidateIds']):
                raise ValueError(f"Invalid confirmed poem IDs for {entry['id']}: {selected}")
            if any(by_poem[i]['author'] != choice['author'] for i in selected):
                raise ValueError(f"Confirmed author mismatch: {entry['id']}")
            if choice.get('wholeGroupConfirmed'):
                groups = [by_poem[i]['group'] for i in selected]
                group_titles = {g['title'] for g in groups if g}
                count = re.search(r'([一二三四五六七八九十百]+)首$', next(iter(group_titles), ''))
                if (not all(groups) or len(group_titles) != 1 or not count or
                    sorted(g['position'] for g in groups) != list(range(1, base.numeral(count[1]) + 1))):
                    raise ValueError(f"Incomplete whole-group confirmation: {entry['id']}")
            entry.update(status='user-confirmed-selection', selectedPoemIds=selected[:],
                         selectionBasis='explicit-user-confirmation',
                         userConfirmation={'batchId':batch['id'], 'confirmedOn':batch['confirmedOn'],
                            'scope':'work-identity-and-selected-members', 'note':choice['note'],
                            'sourceRef':{'sourceId':'user-confirmation', 'file':'sources/user-confirmations.json',
                                         'batchId':batch['id'], 'catalogEntryId':entry['id']}})
            if choice.get('wholeGroupConfirmed'):
                entry['userConfirmation']['wholeGroupConfirmed'] = True


def import_sources(corpus):
    entries = parse_catalog((OUT / 'catalog-input.txt').read_text())
    overrides_path = OUT / 'title-overrides.json'
    overrides = load(overrides_path) if overrides_path.exists() else {}
    alias_map = load(base.OUT / 'selection-aliases.json')['aliases']
    reverse_aliases = defaultdict(set)
    for request, target in alias_map.items():
        author, title = request.split('|', 1)
        reverse_aliases[(base.key(author), title_identity(target)[0])].add(title_identity(title)[0])
    by_title = defaultdict(list)
    for raw in load(corpus):
        k, index = title_identity(raw['title'])
        keys = {k} | reverse_aliases[(base.key(raw['author']), k)]
        # Named sub-poems in collections: 輞川集 辛夷塢 etc.
        tail = base.simplified(raw['title']).split('\t')[0].split(' ')[-1]
        if not re.fullmatch(r'[一二三四五六七八九十百]+', tail):
            keys.add(title_identity(tail)[0])
        for key in keys:
            by_title[key].append((raw, index))
    corpus_by_id = {p['id']: p for p in load(corpus)}
    selected, requests = {}, []
    for entry in entries:
        if entry['kind'] != 'poem-entry':
            continue
        rule = overrides.get(str(entry['order']), {})
        k, index = title_identity(rule.get('lookupTitle', entry['title']))
        matched = list(by_title[k])
        for alias in rule.get('additionalTitles', []):
            other_key, other_index = title_identity(alias)
            matched += [(p, i) for p, i in by_title[other_key] if other_index is None or i == other_index]
        if rule.get('author'):
            matched = [(p, i) for p, i in matched if base.key(p['author']) == base.key(rule['author'])]
        if rule.get('sourceIds'):
            matched = [(corpus_by_id[i], title_identity(corpus_by_id[i]['title'])[1]) for i in rule['sourceIds']]
        if index is not None and not rule.get('sourceIds'):
            matched = [(p, i) for p, i in matched if i == index]
        ids = []
        for p, _ in matched:
            if p['id'] in ids:
                continue
            ids.append(p['id'])
            chosen = selected.setdefault(p['id'], {'raw': {k: p[k] for k in ('id','author','title','paragraphs')},
                      'file': '全唐诗/' + p['sourceFile'], 'index': p['sourceIndex'], 'catalogEntryIds': []})
            chosen['catalogEntryIds'].append(entry['id'])
        requests.append({'catalogEntryId': entry['id'], 'rawSourceIds': ids})
    write('sources/qts-candidates.json', {'repositoryCommit': base.COMMIT, 'records': list(selected.values())})
    write('sources/title-matches.json', requests)


def build():
    entries = parse_catalog((OUT / 'catalog-input.txt').read_text())
    sources = load(OUT / 'sources/qts-candidates.json')['records']
    overrides = load(OUT / 'title-overrides.json') if (OUT / 'title-overrides.json').exists() else {}
    editions = load(OUT / 'sources/editions.json')['poems']
    edition_by_source = {source_id: e for e in editions for source_id in e.get('sourceRecordIds', [])}
    # Carry forward only explicitly reviewed work/version links, never title-only guesses.
    prior = load(base.OUT / 'poems.json')['poems']
    prior_by_source = {i: p for p in prior for i in p['sourceRecordIds']}
    records, source_to_record = [], {}
    for item in sources:
        raw = item['raw']
        ref = base.source_ref('chinese-poetry-qts', item['file'], recordId=raw['id'],
                              recordIndex=item['index'], repositoryCommit=base.COMMIT)
        p = base.make_record(raw, [ref])
        p['selection']['basis'] = 'album-title-candidate'
        p['selection']['bookMembership'] = 'unverified-from-album'
        edition = edition_by_source.get(raw['id'])
        if edition:
            edition_ref = base.source_ref(edition['sourceId'], url=edition['url'])
            complete = base.make_record(edition, [edition_ref, ref], traditional=False)
            # Stable ID and original source identity survive a documented edition choice.
            complete.update(id=p['id'], sourceRecordIds=p['sourceRecordIds'], sourceTitle=p['sourceTitle'],
                            selection=p['selection'], aliases=list(dict.fromkeys(p['aliases']+[edition['title']])))
            complete['editionDecision'] = {'basis':edition['note'], 'sourceRef':edition_ref}
            base.add_witness(complete, raw, ref)
            p = complete
        # Merge only highly similar copies of the same title, author and cycle
        # index. Contradictory cycle numbering remains visible for confirmation.
        prior_work = prior_by_source.get(raw['id'])
        hit = next((q for q in records if q['author'] == p['author'] and (
                    (title_identity(q['title']) == title_identity(p['title']) and
                     base.score(base.key(q['text']),base.key(p['text'])) >= .94) or
                    (prior_work and set(q['sourceRecordIds']) & set(prior_work['sourceRecordIds'])))), None)
        if hit:
            base.add_witness(hit, raw, ref)
            hit['sourceRecordIds'].extend(p['sourceRecordIds'])
        else:
            hit = p
            records.append(hit)
        source_to_record[raw['id']] = hit
    raw_by_source = {item['raw']['id']:item['raw'] for item in sources}
    for link in load(OUT/'sources/version-links.json')['links']:
        retained = next(p for p in records if p['id'] == link['retainedId'])
        alternate = next(p for p in records if p['id'] == link['alternateId'])
        raw = raw_by_source[alternate['sourceRecordIds'][0]]
        base.add_witness(retained, raw, alternate['sourceRefs'][0])
        retained['witnesses'] += alternate['witnesses']
        retained['variants'] += alternate['variants']
        retained['sourceRecordIds'] += alternate['sourceRecordIds']
        retained['selection']['notes'].append(link['basis'])
        for source_id in alternate['sourceRecordIds']:
            source_to_record[source_id] = retained
        records.remove(alternate)
    # Bring across already collected ancient-text witnesses and source links.
    # Modern commentary and translations are not copied into this collection.
    for p in records:
        earlier = {prior_by_source[i]['id']:prior_by_source[i] for i in p['sourceRecordIds'] if i in prior_by_source}
        for old in earlier.values():
            p.setdefault('relatedResearchIds', []).append(old['id'])
            p['existingLibraryMatches'] += old.get('existingLibraryMatches', [])
            for w in old['witnesses']:
                if w['sourceRef'] not in p['sourceRefs'] and w['sourceRef'] not in [x['sourceRef'] for x in p['witnesses']]:
                    base.add_witness(p,w,w['sourceRef'])
            if old['selection'].get('bookMembership') == 'confirmed':
                p['selection'].update(old['selection'])
            for issue in old['review']['issues']:
                if issue not in p['review']['issues']:
                    p['review']['issues'].append(issue)
    # Previously verified supplemental sources (public-domain poem text only).
    supplemental = load(base.OUT / 'sources/supplements.json')['poems']
    supplemental_file = OUT / 'sources/supplements.json'
    if supplemental_file.exists():
        supplemental += load(supplemental_file)['poems']
    for raw in supplemental:
        related = [e for e in entries if title_identity(e['title']) == title_identity(raw['title'])]
        if not related:
            continue
        hit = base.best_match(raw, records)
        ref = base.source_ref(raw['sourceId'], url=raw['url'])
        if hit:
            base.add_witness(hit,raw,ref)
        else:
            hit = base.make_record(raw,[ref],traditional=False)
            if raw.get('genre'):
                hit['form'].update(proposedGenre=raw['genre'],status='reference-classification',basis=raw['url'])
            records.append(hit)
        if raw.get('reviewNote'):
            hit['review']['issues'].append('attribution-or-edition-review')
            hit['selection']['notes'].append(raw['reviewNote'])
    track_file = OUT / 'sources/album-first-100.json'
    tracks = load(track_file)['data'] if track_file.exists() else []
    imported = {r['catalogEntryId']:r for r in load(OUT / 'sources/title-matches.json')}
    by_id = {p['id']:p for p in records}
    for entry in entries:
        entry['originalTitleOnly'] = entry['title']
        entry['sourceRefs'] = [{'sourceId':'user-transcription','file':'catalog-input.txt','line':entry['order']},
                               {'sourceId':'ximalaya-album','url':ALBUM}]
        if entry['order'] <= len(tracks):
            track = tracks[entry['order']-1]
            track_title = re.sub(r'^【[^】]+】', '', track['trackName'])
            if base.key(track_title) != base.key(entry['title']):
                raise ValueError(f"Album track/transcript mismatch: {entry['order']}")
            entry['trackId'] = track['trackId']
            entry['sourceUrl'] = 'https://www.ximalaya.com' + track['uri']
            entry['sourceRefs'].append({'sourceId':'ximalaya-public-track-list','url':entry['sourceUrl'],
                                       'trackId':track['trackId']})
        if entry['kind'] == 'preface':
            entry.update(status='excluded-preface',candidateIds=[],selectedPoemIds=[])
            continue
        rule = overrides.get(str(entry['order']), {})
        ids = {source_to_record[i]['id'] for i in imported[entry['id']]['rawSourceIds']}
        for p in records:
            if not p['sourceRecordIds'] and title_identity(p['title']) == title_identity(entry['title']):
                ids.add(p['id'])
        all_candidates = sorted((by_id[i] for i in ids), key=lambda p:(p['author'],
                                title_identity(p['title'])[0], title_identity(p['title'])[1] or 0,p['title'],p['id']))
        candidates = [p for p in all_candidates if compatible(entry,p)]
        entry['filteredOutCandidates'] = [
            {'title':p['title'],'author':p['author'],'opening':p['paragraphs'][0],
             'form':p['form'],'sourceRecordIds':p['sourceRecordIds'],
             'reason':'句数或每句字数不符合目录所标绝句/律诗栏目；不是作品不存在的判断。'}
            for p in all_candidates if p not in candidates]
        entry['candidateIds'] = [p['id'] for p in candidates]
        if not candidates and all_candidates:
            candidates = all_candidates
            entry['candidateIds'] = [p['id'] for p in candidates]
            entry['sectionConflict'] = True
            entry['filteredOutCandidates'] = []
        entry['selectedPoemIds'] = []
        if not candidates:
            entry['status'] = 'source-needed'
        elif len(candidates) == 1 and not rule.get('forceConfirm') and (not entry.get('sectionConflict') or rule.get('allowSectionConflict')):
            entry['status'] = 'matched-single-candidate'
            entry['selectedPoemIds'] = entry['candidateIds'][:]
        else:
            entry['status'] = 'needs-confirmation'
        if rule:
            entry['matchingNote'] = rule.get('note')
            entry['matchingEvidenceUrls'] = rule.get('evidenceUrls', [])
            if rule.get('titleReview'):
                entry['titleReview'] = rule['titleReview']
        entry['selectionBasis'] = ('unique-among-collected-candidates-not-user-confirmed'
                                   if entry['selectedPoemIds'] else 'awaiting-user-choice')
    confirmations_path = OUT/'sources/user-confirmations.json'
    if confirmations_path.exists():
        apply_confirmations(entries, records, load(confirmations_path))
    used_ids = {i for e in entries for i in e['candidateIds']}
    records = [p for p in records if p['id'] in used_ids]
    existing_path = ROOT/'data/final/tang_poems_final.json'
    existing = load(existing_path)['poems']
    for p in records:
        p['catalogEntryIds'] = [e['id'] for e in entries if p['id'] in e['candidateIds']]
        p['provisionallyMatchedEntryIds'] = [e['id'] for e in entries if
            e['status']=='matched-single-candidate' and p['id'] in e['selectedPoemIds']]
        p['userConfirmedEntryIds'] = [e['id'] for e in entries if
            e['status']=='user-confirmed-selection' and p['id'] in e['selectedPoemIds']]
        p['textSha256'] = hashlib.sha256(p['text'].encode()).hexdigest()
        p['scopeNote'] = '唐诗来源库的检索候选，不保证所有同名作者都属于唐代；入选身份和文本定本分别核验。'
        if p['author'] == '曹修古':
            p['dynasty'] = '宋'
            p['dynastyBasis'] = '宋史卷二九七曹修古传：https://zh.wikisource.org/zh-hans/宋史/卷297；保留同名检索结果，非唐诗入选依据。'
            p['review']['issues'].append('out-of-tang-scope-candidate')
        p['existingLibraryMatches'] = []
        key = base.key(p['text'])
        for app_poem in existing:
            other = base.key(app_poem['text'])
            same_author = base.key(app_poem['author']) == base.key(p['author'])
            if not same_author and key[:8] != other[:8]:
                continue
            similarity = base.score(key, other)
            if similarity >= (.82 if same_author else .9):
                p['existingLibraryMatches'].append({'id':app_poem['id'], 'title':app_poem['title'],
                    'author':app_poem['author'],'similarity':round(similarity,4),'authorAgrees':same_author,
                    'type':'same-text' if key==other else 'probable-same-work-variant'})
        p['review']['issues'] = list(dict.fromkeys(p['review']['issues']))
    stats = {'catalogEntryCount':len(entries), 'poemEntryCount':sum(e['kind']=='poem-entry' for e in entries),
             'statuses':dict(Counter(e['status'] for e in entries)),
             'candidateTextCount':len(records), 'candidateAuthorCount':len({p['author'] for p in records})}
    stats['entriesWithCandidateText'] = sum(bool(e['candidateIds']) for e in entries)
    stats['selectedUniquePoemCount'] = len({i for e in entries for i in e['selectedPoemIds']})
    stats['selectedEntryCount'] = sum(bool(e['selectedPoemIds']) for e in entries)
    stats['userConfirmedEntryCount'] = sum(e['status']=='user-confirmed-selection' for e in entries)
    stats['userConfirmedPoemCount'] = len({i for e in entries if e['status']=='user-confirmed-selection' for i in e['selectedPoemIds']})
    stats['provisionallyMatchedEntriesWithAppDuplicate'] = sum(
        any(by_id[i]['existingLibraryMatches'] for i in e['selectedPoemIds'])
        for e in entries if e['status']=='matched-single-candidate')
    stats['selectedEntriesWithAppDuplicate'] = sum(
        any(by_id[i]['existingLibraryMatches'] for i in e['selectedPoemIds']) for e in entries)
    stats['sections'] = dict(Counter(e['section'] for e in entries if e['kind']=='poem-entry'))
    write('catalog.json',{'schemaVersion':'1.1.0','sourceUrl':ALBUM,'sourceType':'user-transcribed-album-catalog',
                         'bookPrintTocVerified':False,'stats':stats,'entries':entries})
    write('poems.json',{'schemaVersion':'1.1.0','publicationReady':False,
                       'notice':'候选全文包含未选中的同名诗。catalog.entries[].selectedPoemIds 按状态区分暂定对应与用户已确认选篇；仍需定本校订。',
                       'existingLibrary':{'path':'data/final/tang_poems_final.json','poemCount':len(existing),
                                          'sha256':hashlib.sha256(existing_path.read_bytes()).hexdigest()},
                       'poems':records})
    write('pending.json',{'entries':[{**e,'candidates':[{'id':p['id'],'title':p['title'],'author':p['author'],
                           'opening':p['paragraphs'][0],'form':p['form']['proposedGenre']} for i in e['candidateIds'] for p in [by_id[i]]]} for e in entries if e['status'] in ('source-needed','needs-confirmation')]})
    write_views(entries, records, stats)
    print(json.dumps(stats,ensure_ascii=False,indent=2))


def write_views(entries, records, stats):
    """Reader-friendly full texts and explicit unresolved choices, plus indexes."""
    poems = {p['id']:p for p in records}
    matched = [e for e in entries if e['selectedPoemIds']]
    pending = [e for e in entries if e['status'] == 'needs-confirmation']
    matched_rows = [{**e, 'poems':[poems[i] for i in e['selectedPoemIds']]} for e in matched]
    write('matched-poems.json', {'schemaVersion':'1.1.0','publicationReady':False,
                                'status':'selected-identities-see-entry-status-not-book-text-verification',
                                'entries':matched_rows})
    catalog = ['# 《唐诗撷英》音频目录整理', '',
               f"原目录 {len(entries)} 条：序言 1 条，诗歌条目 {stats['poemEntryCount']} 条。",
               f"用户已确认 {stats['userConfirmedEntryCount']} 条目录、{stats['userConfirmedPoemCount']} 首诗；暂定对应 {stats['statuses'].get('matched-single-candidate',0)} 条；待确认 {len(pending)} 条。候选全文记录 {len(records)} 条，不能理解为本书收了这么多首。", '',
               '目录依据用户提供的喜马拉雅标题，不宣称已核对纸书完整目录或纸书用字。', '',
               '|序号|栏目|目录题名|对应作者 / 候选作者|状态|', '|---:|---|---|---|---|']
    for e in entries:
        names = list(dict.fromkeys(poems[i]['author'] for i in (e['selectedPoemIds'] or e['candidateIds'])))
        state = ('序言，不采集正文' if e['kind']=='preface' else
                 f"用户已确认（{len(e['selectedPoemIds'])} 首）" if e['status']=='user-confirmed-selection' else
                 '暂定对应' if e['selectedPoemIds'] else '待确认')
        catalog.append(f"|{e['order']}|{e['section'] or '—'}|{e['title']}|{'、'.join(names) or '—'}|{state}|")
    (OUT/'CATALOG.md').write_text('\n'.join(catalog)+'\n')
    full = ['# 已对应诗歌全文', '',
            f"共 {len(matched)} 个目录条目、{stats['selectedUniquePoemCount']} 首诗。用户已确认 {stats['userConfirmedEntryCount']} 条目录、{stats['userConfirmedPoemCount']} 首诗；其余为暂定对应。选篇确认不等于出版级文本定本。", '',
            '同名或选篇不明的条目另见 [待确认清单](REVIEW.md)，所有候选全文见 [CANDIDATE_TEXTS.md](CANDIDATE_TEXTS.md)。', '']
    for e in matched:
        names = '、'.join(dict.fromkeys(poems[i]['author'] for i in e['selectedPoemIds']))
        state = '用户已确认选篇' if e['status']=='user-confirmed-selection' else '暂定对应'
        full += [f"## {e['order']:03}. {e['title']} · {names}", '', f"栏目：{e['section']}。状态：{state}。", '']
        if e.get('userConfirmation'):
            full += [f"确认说明：{e['userConfirmation']['note']}", '']
        if e.get('matchingNote'):
            full += [f"对应说明：{e['matchingNote']}", '']
        if e.get('matchingEvidenceUrls'):
            full += [' · '.join(f'[题名核对来源 {i}]({url})' for i, url in enumerate(e['matchingEvidenceUrls'],1)), '']
        for pid in e['selectedPoemIds']:
            p = poems[pid]
            full += [f"### {p['title']}", '', f"来源题名：{p['sourceTitle']}。", '']
            full += [s+'  ' for s in p['sentences']] + ['']
            if p.get('editionDecision'):
                full += [f"文本说明：{p['editionDecision']['basis']}", '']
            full += [f"[诗文来源]({p['sourceRefs'][0]['url']}) · [目录来源]({e['sourceUrl']})", '']
    (OUT/'MATCHED_POEMS.md').write_text('\n'.join(full)+'\n')
    review = ['# 待确认条目', '',
              f'共 {len(pending)} 条。正文均已收集，未替你确定选篇。回复“目录序号 + 作者 + 首句”即可；组诗也可回复“全组”或具体篇次。', '',
              '同名诗按作者和首句辨认；括号内为来源全题。目录位置只能作线索，未据此自动选择作者。', '',
              '下列序号是原始 297 条目录中的序号，含第 1 条序言，因此第 2 条是《春江花月夜》。', '']
    if not pending:
        review = ['# 待确认条目', '', '当前待用户确认的选篇为 **0 条**。此前的同名、作者及组诗选篇已按用户回复处理。', '',
                  f"全部 {stats['poemEntryCount']} 条诗歌目录均已对应作者与正文，共 {stats['selectedUniquePoemCount']} 首诗；其中 {stats['userConfirmedEntryCount']} 条经用户确认，其余为唯一候选的暂定对应。", '',
                  '完整内容见 [已对应诗歌全文](MATCHED_POEMS.md)。正文定本、署名异议及纸书版本差异仍保留各自说明；选篇清单清零不代表所有版本疑点消失。', '',
                  '第 263 条于鹄已按用户确认统一采用《江南曲》。此前报告的纸书题名《江南春》仅作来源差异留档，题名选择已完成；详见全文第 263 条与 `catalog.json` 的 `titleReview`。', '']
    for e in pending:
        review += [f"## {e['order']:03}. {e['title']}（{e['section']}）", '']
        if e.get('matchingNote'):
            review += [e['matchingNote'], '']
        if e.get('sectionConflict'):
            review += ['目录栏目与正文句式不一致，请一并核对。', '']
        for idx, pid in enumerate(e['candidateIds'], 1):
            p = poems[pid]
            review.append(f"{idx}. **{p['author']}**｜{p['paragraphs'][0]}（《{p['title']}》） [全文](CANDIDATE_TEXTS.md#{pid})")
        review += ['', f"[专辑条目来源]({e['sourceUrl']})", '']
    (OUT/'REVIEW.md').write_text('\n'.join(review)+'\n')
    text_pages = ['# 全部候选诗文', '',
                  f'{len(records)} 条来源作品记录，包含同名候选、组诗候选。不是确认收录清单。', '']
    for p in records:
        text_pages += [f'<a id="{p["id"]}"></a>',f"## {p['title']} · {p['author']}", '',
                       '关联目录：'+ '、'.join(i.rsplit('-',1)[-1] for i in p['catalogEntryIds'])+'。', '']
        text_pages += [s+'  ' for s in p['sentences']] + ['',f"[诗文来源]({p['sourceRefs'][0]['url']})", '']
    (OUT/'CANDIDATE_TEXTS.md').write_text('\n'.join(text_pages)+'\n')
    grouped = defaultdict(list)
    for p in records:
        grouped[p['author']].append(p)
    author_source_file = OUT/'sources/authors-qts.json'
    author_sources = load(author_source_file)['records'] if author_source_file.exists() else []
    author_data = []
    for name, items in sorted(grouped.items()):
        authors = [a for a in author_sources if base.key(a['name']) == base.key(name)]
        author_data.append({'id':'author-'+hashlib.sha256(name.encode()).hexdigest()[:12], 'name':name,
                            'sourceBiographies': [{'sourceText':a['desc'],'sourceAuthorId':a['id'],
                             'sourceUrl':base.REPO+'全唐诗/authors.tang.json'} for a in authors],
                            'poemIds':[p['id'] for p in items],
                            'provisionallyMatchedPoemIds':[p['id'] for p in items if p['provisionallyMatchedEntryIds']],
                            'userConfirmedPoemIds':[p['id'] for p in items if p['userConfirmedEntryIds']],
                            'birthYear':None, 'deathYear':None,
                            'notice':'姓名与小传保留来源；未逐位统一别称或抽取未经验证的生卒年。'})
    write('authors.json', {'schemaVersion':'1.0.0','authors':author_data})
    cycles = defaultdict(list)
    for p in records:
        if p['group']:
            cycles[(p['author'],p['group']['title'])].append(p)
    whole_groups = {(poems[i]['author'],poems[i]['group']['title']) for e in entries
                    if e.get('userConfirmation',{}).get('wholeGroupConfirmed') for i in e['selectedPoemIds']}
    write('groups.json',{'groups':[{'author':a,'title':t,'positions':[p['group']['position'] for p in ps],
                         'poemIds':[p['id'] for p in ps], 'wholeGroupConfirmed':(a,t) in whole_groups,
                         'userConfirmedPoemIds':[p['id'] for p in ps if p['userConfirmedEntryIds']]}
                         for (a,t),ps in sorted(cycles.items())]})
    # Exact normalized text, cross-author homonyms and explicit text review issues.
    text_buckets = defaultdict(list)
    for p in records:
        text_buckets[base.key(p['text'])].append(p)
    write('audit.json', {'stats':stats,
                         'duplicateCatalogTitles':[{ 'title':t,'orders':[e['order'] for e in entries if e['title']==t]}
                            for t,n in Counter(e['title'] for e in entries).items() if n>1],
                         'crossAuthorSameText':[{'poemIds':[p['id'] for p in ps],'authors':[p['author'] for p in ps]}
                            for ps in text_buckets.values() if len({p['author'] for p in ps})>1],
                         'textReview':[{'poemId':p['id'],'issues':p['review']['issues']}
                            for p in records if p['review']['issues']],
                         'editionDecisions':[{'poemId':p['id'],**p['editionDecision']}
                            for p in records if p.get('editionDecision')],
                         'titleReviews':[{'catalogEntryId':e['id'],**e['titleReview']}
                            for e in entries if e.get('titleReview')],
                         'unresolvedEntryIds':[e['id'] for e in pending]})


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--import-corpus',type=Path)
    args=parser.parse_args()
    if args.import_corpus:
        import_sources(args.import_corpus)
    build()
