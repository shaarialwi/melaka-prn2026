#!/usr/bin/env python3
"""Fetch one whole snapshot per mode. Fail closed on changed markup/roster."""
import csv, html, json, re, sys, time
from pathlib import Path
from datetime import datetime, timezone
from urllib.request import Request, urlopen
ROOT=Path(__file__).resolve().parents[1]
BASE='https://election.bernama.com/prn/melaka/2026/keputusan/'
def clean(s): return html.unescape(re.sub('<[^>]*>',' ',s)).strip()
def parse(page):
    if 'PRN Melaka 2026' not in page: raise ValueError('Wrong election')
    seats=[]
    for section in re.findall(r'<section\b[^>]*>(.*?)</section>',page,re.S):
        header=re.search(r'<header\b[^>]*>(.*?)</header>',section,re.S)
        if not header: continue
        m=re.search(r'(N\.\d{2})\s*[—–-]\s*([^<]+)',header[1])
        if not m: continue
        reg=re.search(r'Pengundi berdaftar:\s*([\d,]+)',header[1])
        candidates=[]
        for a in re.findall(r'<article\b[^>]*>(.*?)</article>',section,re.S):
            name=re.search(r'<h2\b[^>]*>(.*?)</h2>',a,re.S)
            party=re.search(r'href="[^\"]*/parti/[^\"]*"[^>]*>(.*?)</a>',a,re.S)
            vote=re.search(r'<span>Undi</span>\s*<strong>(.*?)</strong>',a,re.S)
            ident=re.search(r'/calon/([^/]+)/',a)
            if not all([name,party,vote,ident]): raise ValueError('Candidate markup changed')
            raw=clean(vote[1]).replace(',','')
            if raw not in ('-','–','—','') and not raw.isdigit(): raise ValueError('Unrecognised vote value')
            candidates.append(dict(id=ident[1],name=clean(name[1]),party=clean(party[1]),votes=int(raw) if raw.isdigit() else None))
        if not 2<=len(candidates)<=4: raise ValueError('Incomplete seat')
        seats.append(dict(code=m[1],name=clean(m[2]).title(),registered=int(reg[1].replace(',','')) if reg else None,candidates=candidates))
    if len(seats)!=28 or sum(len(s['candidates']) for s in seats)!=79: raise ValueError('Incomplete election snapshot')
    if {s['code'] for s in seats}!={f'N.{i:02}' for i in range(1,29)}: raise ValueError('Duplicate/missing DUN')
    for s in seats:
        ids=[c['id'] for c in s['candidates']]
        if len(set(ids))!=len(ids): raise ValueError('Duplicate candidate')
        if s['registered'] and sum(c['votes'] or 0 for c in s['candidates'])>s['registered']: raise ValueError('Votes exceed electorate')
    return seats

def fetch(url):
    for attempt in range(3):
        try:
            with urlopen(Request(url,headers={'User-Agent':'MelakaResultsDashboard/1.0 (public election results)'}),timeout=40) as r: return r.read().decode('utf-8')
        except Exception:
            if attempt==2: raise
            time.sleep(2**attempt)

def main():
    p=ROOT/'data/results.json'; old=json.loads(p.read_text()) if p.exists() else None
    now=datetime.now(timezone.utc).isoformat()
    modes={}
    for mode in ('unofficial','official'):
        fixture=Path(f'/tmp/melaka{"-official" if mode=="official" else ""}.html')
        page=fixture.read_text() if '--fixtures' in sys.argv else fetch(BASE+'?mode='+mode)
        seats=parse(page)
        if old:
            prior={s['code']:{c['id'] for c in s['candidates']} for s in old['modes'][mode]}
            if any(prior.get(s['code'])!={c['id'] for c in s['candidates']} for s in seats): raise ValueError('Roster changed; requires review')
        modes[mode]=seats
    if [{s['code']: {c['id'] for c in s['candidates']} for s in modes[k]} for k in modes][0] != [{s['code']: {c['id'] for c in s['candidates']} for s in modes[k]} for k in modes][1]: raise ValueError('Mode roster mismatch')
    changed=not old or old['modes']!=modes
    data=dict(election='PRN Melaka 2026',pollingDate='2026-11-14',checkedAt=now,changedAt=now if changed else old['changedAt'],source=BASE,modes=modes)
    p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    (ROOT/'data/status.json').write_text(json.dumps(dict(ok=True,attemptAt=now,message='Source fetched and validated'))+'\n')
    with (ROOT/'data/candidates.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['DUN code','DUN name','Candidate name','Party / coalition','Unofficial votes','Official votes'])
        official={c['id']:c['votes'] for s in modes['official'] for c in s['candidates']}
        for s in modes['unofficial']:
            for c in s['candidates']:w.writerow([s['code'],s['name'],c['name'],c['party'],c['votes'],official[c['id']]])
    print('Validated 28 seats / 79 candidates; changed:',changed)
if __name__=='__main__':
    try:main()
    except Exception as e:
        (ROOT/'data/status.json').write_text(json.dumps(dict(ok=False,attemptAt=datetime.now(timezone.utc).isoformat(),message='Source unavailable or validation failed; last good snapshot retained'))+'\n')
        print(str(e),file=sys.stderr);sys.exit(1)
