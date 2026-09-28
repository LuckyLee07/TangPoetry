#!/usr/bin/env python3
"""Prepare built-in imagegen prompts only; this script never calls an image API."""
import argparse,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'data/expansion/tang-second-volume'
def jobs(first,last,missing=True):
    config=json.loads((BASE/'illustrations/style.json').read_text())
    commentary={}
    for p in sorted((BASE/'commentary').glob('*.json')):
        commentary.update(json.loads(p.read_text())['poems'])
    output=[]
    for p in json.loads((BASE/'poems.json').read_text())['poems']:
        n=p['order']
        if not first<=n<=last: continue
        receipt=BASE/'illustrations/receipts'/f'{n:03d}.json'
        if missing and receipt.exists(): continue
        scene=commentary.get(p['id'],{}).get('artDirection') or config['initialDirections'].get(str(n))
        if not isinstance(scene,str) or not scene.strip(): raise ValueError(f'Missing individual scene: {n}')
        prompt=(config['stylePrompt']+'\nSpecific scene: '+scene+'\nPoem (semantic reference only, do not paint words): '
                +p['title']+' — '+p['author']+'\n'+p['text'])
        output.append({'order':n,'id':p['id'],'title':p['title'],'author':p['author'],'prompt':prompt})
    return output
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--from',dest='first',type=int,required=True)
    parser.add_argument('--to',dest='last',type=int,required=True);parser.add_argument('--include-existing',action='store_true')
    args=parser.parse_args(); print(json.dumps(jobs(args.first,args.last,not args.include_existing),ensure_ascii=False))
