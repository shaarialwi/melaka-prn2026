import json, unittest
from pathlib import Path
from update_results import parse, ROOT
class ResultsTest(unittest.TestCase):
    def test_snapshot_map_and_roster(self):
        d=json.loads((ROOT/'data/results.json').read_text());g=json.loads((ROOT/'data/melaka.geojson').read_text())
        self.assertEqual(len(g['features']),28)
        for seats in d['modes'].values():
            self.assertEqual(len(seats),28);self.assertEqual(sum(len(s['candidates']) for s in seats),79)
            self.assertEqual({s['code'] for s in seats},{f['properties']['code_dun'] for f in g['features']})
            for s in seats:
                for c in s['candidates']:self.assertTrue(c['votes'] is None or isinstance(c['votes'],int) and c['votes']>=0)
    def test_rejects_incomplete_response(self):
        for page in ['','<h1>PRN Melaka 2026</h1>','<h1>PRN Melaka 2021</h1>']:
            with self.assertRaises(ValueError):parse(page)
    def test_no_old_results_parsed(self):
        if not Path('/tmp/melaka.html').exists():return
        p=Path('/tmp/melaka.html').read_text();seats=parse(p)
        self.assertTrue(all(c['votes'] is None for s in seats for c in s['candidates']))
        p=p.replace('<span>Undi</span><strong>-</strong>','<span>Undi</span><strong>1,234</strong>',1)
        self.assertEqual(parse(p)[0]['candidates'][0]['votes'],1234)
        p=p.replace('<span>Undi</span><strong>1,234</strong>','<span>Undi</span><strong>999,999</strong>',1)
        with self.assertRaises(ValueError):parse(p)
if __name__=='__main__':unittest.main()
