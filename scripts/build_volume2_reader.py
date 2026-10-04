#!/usr/bin/env python3
"""Prepare isolated volume-2 reader data and delivery copies, preserving originals."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess
from PIL import Image

try:
    from .volume2_narration_release import validate_volume2_release, MANIFEST_FILE
except ImportError:
    from volume2_narration_release import validate_volume2_release, MANIFEST_FILE

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'data/expansion/tang-second-volume'
OUT=ROOT/'data/reader-volume-2'
ASSETS=ROOT/'assets/volume-2/optimized'
SECTIONS=['五言绝句','七言绝句','五言律诗','七言律诗','五言古诗','七言古诗','杂言古诗','乐府']
FEATURED_ORDERS={6,8,11,13,15,18,23,24,62,66,73,74,81,83,87,88,89,100,276,285}
RECIPE={'version':1,'pageWidth':940,'pageQuality':83,'thumbnailWidth':240,'thumbnailQuality':83,'thumbnailCrop':'source-upper-square'}

def read(path): return json.loads(path.read_text())
def payload(value): return json.dumps(value,ensure_ascii=False,indent=2)+'\n'
def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+'.tmp')
    temporary.write_text(payload(value));temporary.replace(path)
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def asset_record(path):
    with Image.open(path) as image: size=image.size
    return {'file':path.relative_to(ROOT).as_posix(),'sha256':sha(path),'bytes':path.stat().st_size,'width':size[0],'height':size[1]}

def prepare_assets(poems,check=False):
    old=read(BASE/'delivery-assets.json') if (BASE/'delivery-assets.json').exists() else {}
    old_assets=old.get('poems',{})
    framing=read(BASE/'delivery-framing.json')['poems'] if (BASE/'delivery-framing.json').exists() else {}
    def prepare(p):
        source=ROOT/p['image']; receipt=read(ROOT/p['illustrationReceipt'])
        assert source.is_file() and sha(source)==receipt['sha256'], f'Original artwork changed: {p["id"]}'
        page=ASSETS/f'{p["id"]}-page.webp';thumb=ASSETS/f'{p["id"]}-thumb.webp'
        previous=old_assets.get(p['id'],{})
        framed=framing.get(p['id'],{})
        frame=framed.get('frame',{'x':0,'y':0,'side':1,'aspect':receipt['height']/receipt['width']})
        assert frame['aspect']==receipt['height']/receipt['width'] and 0<frame['side']<=1 and 0<=frame['x']<=1-frame['side']+0.000001 and 0<=frame['y']<=frame['aspect']-frame['side']+0.000001, f'Invalid directory crop: {p["id"]}'
        valid=old.get('recipe')==RECIPE and previous.get('sourceSHA256')==receipt['sha256'] and previous.get('thumbnailFrame')==frame
        valid=valid and all(path.is_file() and sha(path)==previous.get(kind,{}).get('sha256') for path,kind in [(page,'page'),(thumb,'thumbnail')])
        if not valid:
            assert not check, f'Delivery artwork missing or stale: {p["id"]}'
            ASSETS.mkdir(parents=True,exist_ok=True)
            temporary=page.with_suffix('.tmp.webp')
            subprocess.run(['cwebp','-quiet','-q',str(RECIPE['pageQuality']),'-resize','940','0',str(source),'-o',str(temporary)],check=True)
            temporary.replace(page)
            with Image.open(source) as original:
                # A conservative upper square retains the scene; individual crop review is separate.
                width,height=original.size
                cropped=original.convert('RGB').crop((round(frame['x']*width),round(frame['y']*width),round((frame['x']+frame['side'])*width),round((frame['y']+frame['side'])*width)))
                cropped.resize((240,240),Image.Resampling.LANCZOS).save(thumb,format='WEBP',quality=83,method=6)
        return p['id'], {'source':p['image'],'sourceSHA256':receipt['sha256'],'page':asset_record(page),'thumbnail':asset_record(thumb),'thumbnailFrame':frame,'cropReviewStatus':framed.get('status','initial-upper-square-needs-directory-review'),'cropReviewNote':framed.get('note','')}
    with ThreadPoolExecutor(max_workers=4) as pool: assets=dict(pool.map(prepare,poems))
    result={'schemaVersion':1,'recipe':RECIPE,'sourceBytes':sum((ROOT/p['image']).stat().st_size for p in poems),'pageBytes':sum(p['page']['bytes'] for p in assets.values()),'thumbnailBytes':sum(p['thumbnail']['bytes'] for p in assets.values()),'poems':assets}
    if check: assert read(BASE/'delivery-assets.json')==result, 'Delivery manifest stale'
    else: write(BASE/'delivery-assets.json',result)
    return result

def source_urls(poem):
    refs=[*poem.get('sourceRefs',[]),*poem['commentary']['basis'].get('sourceRefs',[]),*poem['commentary']['basis'].get('verificationRefs',[])]
    result=[]
    for ref in refs:
        value=ref if isinstance(ref,str) else ref.get('url',ref.get('href',''))
        if value.startswith(('https://','http://')) and value not in result: result.append(value)
    return result

def display_glyphs():
    mapping=read(BASE/'display-glyphs.json')['replacements']
    assert all(len(ch)==len(record['display'])==1 and record['evidenceURLs'] for ch,record in mapping.items()), 'Invalid display glyph mapping'
    return {ch:record['display'] for ch,record in mapping.items()}

def reader_entries(production,source,assets):
    poems=production['poems'];assert len(poems)==len({p['id'] for p in poems})==305
    original={p['id']:p for p in source['poems']};catalog=[];details={}
    assert set(original)=={p['id'] for p in poems}, 'Archival and production IDs differ'
    glyphs=display_glyphs()
    def display(text): return ''.join(glyphs.get(ch,ch) for ch in text)
    for p in poems:
        assert all(p.get(k) for k in ['displayTitle','displayDynasty','displayGenre','catalogSection']), f'Metadata not finalized: {p["id"]}'
        assert p['catalogSection'] in SECTIONS, f'Unclassified: {p["id"]}'
        title=display(p['displayTitle']);art=assets['poems'][p['id']];c=p['commentary'];o=original[p['id']]
        aliases=list(dict.fromkeys([title,p['title'],p.get('sourceTitle',p['title']),*p.get('aliases',[])]))
        catalog.append({'id':p['id'],'order':p['order'],'volume':'volume-2','title':title,'aliases':aliases,'author':display(p['author']),'dynasty':p['displayDynasty'],'section':p['catalogSection'],'genre':p['displayGenre'],'theme':p['displayGenre'],'featured':p['order'] in FEATURED_ORDERS,'dedicatedArt':True,'image':art['page']['file'],'thumbnail':art['thumbnail']['file'],'searchText':' '.join([*aliases,p['author'],p['displayDynasty'],p['displayGenre'],p['text']])})
        # Unicode scalar iteration preserves supplementary-plane characters as one token.
        lines=[[[ch,''] for ch in display(line)] for line in p['sentences']]
        assert ''.join(ch for line in lines for ch,_ in line)==display(''.join(p['sentences'])), p['id']
        detail={'id':p['id'],'title':title,'author':display(p['author']),'dynasty':p['displayDynasty'],'section':p['catalogSection'],'genre':p['displayGenre'],'sourceTitle':p['title'],'displaySourceTitle':display(p['title']),'originalEditionTitle':p.get('sourceTitle',p['title']),'rubyLines':lines,'noteTitle':'诗意','note':display(c['summary']),'interpretation':[display(x) for x in c['interpretation']],'annotations':[{'text':display(g['term']+'：'+g['text']),'source':'编辑释义'} for g in c['glossary']],'variants':[],'preface':[],'notes':[display(g['term']+'：'+g['text']) for g in c['glossary']],'editorialNotes':[display(x) for x in c['reviewNotes']],'sourceRefs':source_urls(p),'contentStatus':'editorial-draft','text':p['text'],'readingText':display(p['text']),'displayGlyphs':{ch:value for ch,value in glyphs.items() if ch in payload(p)},'layout':'center-low','pronunciationStatus':'not-prepared','sourceText':p.get('sourceText',o['text'])}
        assert detail['interpretation'] and detail['note'].strip(),p['id']
        details[p['id']]=detail
    ranks={s:i for i,s in enumerate(SECTIONS)};catalog.sort(key=lambda p:(ranks[p['section']],p['order']))
    result={'schemaVersion':1,'volume':'volume-2','title':'唐诗画笺 · 第二卷','subtitle':'撷英与补选 · 第二卷','coverPoemID':next(p['id'] for p in poems if p['order']==1),'narrationAvailable':False,'sections':[s for s in SECTIONS if any(p['section']==s for p in catalog)],'poems':catalog}
    result['narrationAvailable']=validate_volume2_release(ROOT,result,details)['available']
    return result,details

def build(check=False,assets_only=False):
    production=read(BASE/'production.json'); source=read(BASE/'poems.json')
    assert len(production['poems'])==305
    assets=prepare_assets(production['poems'],check)
    if assets_only: return {'poems':305,'sourceBytes':assets['sourceBytes'],'pageBytes':assets['pageBytes'],'thumbnailBytes':assets['thumbnailBytes']}
    catalog,details=reader_entries(production,source,assets)
    report={'schemaVersion':1,'volume':'volume-2','poems':305,'details':len(details),'productionSHA256':sha(BASE/'production.json'),'metadataSHA256':sha(BASE/'display-metadata.json'),'displayGlyphsSHA256':sha(BASE/'display-glyphs.json'),'sourceBytes':assets['sourceBytes'],'pageBytes':assets['pageBytes'],'thumbnailBytes':assets['thumbnailBytes'],'longPoems':sum(len(p['rubyLines'])>8 for p in details.values()),'longTitles':sum(len(p['title'])>14 for p in details.values()),'featuredPoems':sum(p['featured'] for p in catalog['poems']),'audioTracks':len(details) if catalog['narrationAvailable'] else 0,'publicationReady':False,'directoryCropReview':'assistant-reviewed' if all(a['cropReviewStatus']=='assistant-reviewed' for a in assets['poems'].values()) else 'pending','archivalPoemsSHA256':sha(BASE/'poems.json')}
    if catalog['narrationAvailable']: report['audioReleaseSHA256']=sha(ROOT/MANIFEST_FILE)
    expected={OUT/'catalog.json':catalog,OUT/'build-report.json':report,**{OUT/'poems'/f'{pid}.json':value for pid,value in details.items()}}
    if check:
        for path,value in expected.items(): assert path.is_file() and read(path)==value,f'Reader output missing or stale: {path}'
    else:
        for path,value in expected.items(): write(path,value)
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');parser.add_argument('--assets-only',action='store_true');args=parser.parse_args()
    print(json.dumps(build(args.check,args.assets_only),ensure_ascii=False))
