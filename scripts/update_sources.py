#!/usr/bin/env python3
"""Independent public-source snapshots; never merge vote totals across publishers."""
import csv
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
ROOT = Path(__file__).resolve().parents[1]
AWANI = 'https://data.pru.astroawani.com/data/'
SPR = 'https://dashboard.spr.gov.my/api/v1/'
PARTIES = {'BN', 'PH', 'PN', 'BERSATU', 'BERSAMA', 'BEBAS', 'PUTRA'}
LINKS = {'awani': 'https://pru.astroawani.com/prn-melaka-2026/kawasan',
         'spr': 'https://dashboard.spr.gov.my/',
         'malaysiakini': 'https://www.malaysiakini.com/news/889120-live-d-day-for-malacca'}

def get(url, sse=False):
    with urlopen(Request(url, headers={'User-Agent': 'MelakaResultsDashboard/1.0', 'Accept': 'text/event-stream' if sse else 'application/json'}), timeout=35) as r:
        if not sse:
            return json.load(r)
        # Read a single SSE snapshot and close the stream, not a persistent subscription.
        chunks = []
        for i, line in enumerate(r):
            if i > 10000: raise ValueError('SSE snapshot too large')
            line = line.decode('utf-8').rstrip('\r\n')
            if line.startswith('data:'): chunks.append(line[5:].lstrip())
            if not line and chunks: return json.loads('\n'.join(chunks))
        if chunks: return json.loads('\n'.join(chunks))
        raise ValueError('No SSE data')

def vote(value):
    if value is None or value == '': return None
    if isinstance(value, bool): raise ValueError('Invalid vote')
    if isinstance(value, int) and value >= 0: return value
    if isinstance(value, str) and value.isdigit(): return int(value)
    raise ValueError('Invalid vote')

def validate(seats):
    if len(seats) != 28 or {s['code'] for s in seats} != {f'N.{n:02}' for n in range(1,29)}:
        raise ValueError('Incomplete DUN coverage')
    if sum(len(s['candidates']) for s in seats) != 79: raise ValueError('Incomplete candidate coverage')
    for s in seats:
        cs = s['candidates']
        if not 2 <= len(cs) <= 4 or len({c['id'] for c in cs}) != len(cs): raise ValueError('Invalid roster')
        if any(not c['name'] or c['party'] not in PARTIES for c in cs): raise ValueError('Unknown candidate/party')
        for c in cs: vote(c['votes'])
        if s['registered'] and sum(c['votes'] or 0 for c in cs) > s['registered']: raise ValueError('Votes exceed electorate')
    return sorted(seats, key=lambda s: s['code'])

def parse_awani(rows, parties):
    lookup = {p['id']: p['abbreviation'] for p in parties}
    seats = []
    for s in rows:
        if s['season_id'] != 21 or s['state'].lower() != 'melaka': raise ValueError('Wrong AWANI election')
        cs = []
        for c in s['candidates']:
            v = vote(c['vote'])
            # Nomination records use placeholder zeros. Count only published election-night records.
            if not s['official_result'] and c['status'] is None: v = None
            cs.append(dict(id=str(c['id']), name=c['name'], party=lookup[c['party']], votes=v))
        seats.append(dict(code='N.'+s['seat_id'][1:].zfill(2), name=s['seat_name'].title(),
                          registered=s['registered_voters'], candidates=cs,
                          official=s['official_result'], sourceUpdatedAt=s['last_published_at']))
    return validate(seats)

def parse_spr(payload):
    seats = {}
    for c in payload['data']:
        if c['Kod'] != '2026-03' or c['Negeri'] != 'MELAKA': raise ValueError('Wrong SPR election')
        code = 'N.'+c['KodDun'][-2:]
        s = seats.setdefault(code, dict(code=code, name=c['NamaDun'].title(), registered=None, candidates=[], official=True))
        s['candidates'].append(dict(id=c['KodDun']+'-'+c['NoCalon'], name=c['NamaUndiCalon'] or c['NamaCalon'],
                                    party=c['NamaSingkatanParti'], votes=vote(c['BilUndi'])))
    return validate(list(seats.values()))

def collect(key):
    if key == 'awani':
        season = get(AWANI+'seasons.json')['prn-melaka-2026']
        if season['id'] != 21 or season['name'] != 'PRN Melaka 2026': raise ValueError('AWANI election changed')
        return parse_awani(get(AWANI+'21/result_state_assembly.json'), get(AWANI+'party.json'))
    elections = get(SPR+'pilihanraya')
    if not any(e['Kod']=='2026-03' and e['NegeriPRK']=='MELAKA' and e['TarikhPengundian']=='2026-11-14' for e in elections):
        raise ValueError('SPR election changed')
    return parse_spr(get(SPR+'2026-03/calondun', sse=True))

def main(fixtures=None):
    path = ROOT/'data/sources.json'
    old = json.loads(path.read_text()) if path.exists() else {'sources': {}}
    now = datetime.now(timezone.utc).isoformat()
    result = {'checkedAt': now, 'sources': {}}
    def run(key):
        prior = old['sources'].get(key, {})
        entry = dict(prior, url=LINKS[key], attemptedAt=now)
        try:
            if fixtures:
                read = lambda n: json.loads((fixtures/n).read_text())
                seats = parse_awani(read('awani-results21.json'),read('awani-party.json')) if key=='awani' else parse_spr(read('spr-calondun.json'))
            else: seats = collect(key)
            if prior.get('seats'):
                roster = lambda ss: {s['code']: sorted(c['id'] for c in s['candidates']) for s in ss}
                if roster(prior['seats']) != roster(seats): raise ValueError('Roster changed; review required')
            entry.update(ok=True, checkedAt=now, seats=seats, message='Snapshot validated: 28 DUN / 79 candidates')
        except Exception as e:
            entry.update(ok=False, message='Refresh failed; last valid snapshot retained' if prior.get('seats') else 'Source unavailable; no validated snapshot')
            print(key, str(e), file=sys.stderr)
        return key, entry
    with ThreadPoolExecutor(max_workers=2) as pool:
        result['sources'].update(pool.map(run, ['awani','spr']))
    result['sources']['malaysiakini'] = dict(url=LINKS['malaysiakini'], ok=False,
        message='Live coverage link only. Automated widget retrieval returned HTTP 403; no vote feed connected.')
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    with (ROOT/'data/source-candidates.csv').open('w', newline='') as f:
        w=csv.writer(f); w.writerow(['Source','Checked at','DUN code','DUN name','Candidate name','Party','Votes','Official','Source URL'])
        for key, entry in result['sources'].items():
            for s in entry.get('seats',[]):
                for c in s['candidates']: w.writerow([key,entry['checkedAt'],s['code'],s['name'],c['name'],c['party'],c['votes'],s['official'],entry['url']])
    print({k: v['ok'] for k,v in result['sources'].items()})
if __name__ == '__main__':
    main(Path(sys.argv[2]) if len(sys.argv)==3 and sys.argv[1]=='--fixtures' else None)
