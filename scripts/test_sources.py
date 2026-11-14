import copy
import unittest
from update_sources import parse_awani, parse_spr, vote

class SourcesTest(unittest.TestCase):
    def awani(self):
        # 23 three-way seats and 5 two-way seats = 79 candidates.
        return [dict(state='Melaka',season_id=21,seat_id=f'N{i:02}',seat_name=f'Seat {i}',registered_voters=10000,official_result=False,last_published_at='2026-11-14T10:00:00Z',candidates=[dict(id=f'{i}-{j}',name=f'Candidate {j}',party=1,vote=0,status=None) for j in range(3 if i<=23 else 2)]) for i in range(1,29)]
    def test_nomination_zeros_are_missing(self):
        self.assertIsNone(parse_awani(self.awani(),[dict(id=1,abbreviation='BN')])[0]['candidates'][0]['votes'])
    def test_published_zero_and_partial_count(self):
        rows=self.awani();rows[0]['candidates'][0].update(status='win',vote=122);rows[0]['candidates'][1].update(status='lose',vote=0)
        cs=parse_awani(rows,[dict(id=1,abbreviation='BN')])[0]['candidates'];self.assertEqual([c['votes'] for c in cs],[122,0,None])
    def test_reject_wrong_election_and_incomplete(self):
        for rows in [self.awani()[:-1],self.awani()]:
            rows[0]['season_id']=19
            with self.assertRaises(ValueError):parse_awani(rows,[dict(id=1,abbreviation='BN')])
    def test_reject_negative_fractional_and_boolean(self):
        for n in [-1,1.5,True,'unknown']:
            with self.assertRaises(ValueError):vote(n)
    def test_spr_votes_not_turnout(self):
        records=[]
        for s in self.awani():
            for c in s['candidates']:
                records.append(dict(Kod='2026-03',Negeri='MELAKA',KodDun='134'+s['seat_id'][1:],NamaDun=s['seat_name'],NoCalon=c['id'],NamaUndiCalon=c['name'],NamaCalon=c['name'],NamaSingkatanParti='BN',BilUndi=None,Kehadiran=999))
        self.assertTrue(all(c['votes'] is None for s in parse_spr(dict(data=records)) for c in s['candidates']))
        records[0]['BilUndi']='123';self.assertEqual(parse_spr(dict(data=records))[0]['candidates'][0]['votes'],123)
        records[0]['Kod']='2021-01'
        with self.assertRaises(ValueError):parse_spr(dict(data=records))
if __name__=='__main__': unittest.main()
