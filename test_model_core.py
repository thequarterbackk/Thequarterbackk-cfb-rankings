import unittest
from model_core import colley,fit_power,resume_rankings,walk_forward
from test_rankings import game,penalty

class ModelCoreTests(unittest.TestCase):
    def test_colley_equations(self):
        ratings=colley([game(1,1,'A','B',87,3)],['A','B','Idle'])
        self.assertAlmostEqual(ratings['A'],0.625)
        self.assertAlmostEqual(ratings['B'],0.375)
        self.assertEqual(ratings['Idle'],0.5)
        self.assertEqual(ratings,colley([game(1,1,'A','B',7,3)],['A','B','Idle']))

    def test_blowouts_saturate_and_neutral_symmetry(self):
        close=game(1,1,'A','B',40,0);close['neutralSite']=True
        huge=game(1,1,'A','B',400,0);huge['neutralSite']=True
        p,h=fit_power([close],['A','B']);q,_=fit_power([huge],['A','B'])
        self.assertEqual(h,0)
        self.assertAlmostEqual(p['A'],-p['B'])
        self.assertLess(q['A']-p['A'],3)

    def test_name_and_conference_invariance(self):
        games=[game(1,1,'A','B',20,7),game(2,1,'C','D',20,7),game(3,2,'A','D',7,20),game(4,2,'B','C',14,10)]
        names=['A','B','C','D'];mapping={'A':'Z','B':'Y','C':'X','D':'W'}
        changed=[dict(g,homeTeam=mapping[g['homeTeam']],awayTeam=mapping[g['awayTeam']],conference='Fictional') for g in games]
        a=resume_rankings(games,names,penalty)[0];b=resume_rankings(changed,list(mapping.values()),penalty)[0]
        scores={r['Team']:r for r in b}
        for r in a:
            self.assertAlmostEqual(r['Final Rating'],scores[mapping[r['Team']]]['Final Rating'],places=3)
            self.assertEqual(r['Loss Penalty'],scores[mapping[r['Team']]]['Loss Penalty'])

    def test_history_and_score_accounting(self):
        names=['A','B','C','D'];games=[game(1,1,'A','B',20,7),game(2,1,'C','D',13,7),game(3,2,'A','D',7,20)]
        rows=resume_rankings(games,names,penalty)[0]
        future=resume_rankings(games+[game(4,3,'D','B',60,0)],names,penalty)[0]
        self.assertEqual(next(r for r in rows if r['Team']=='A')['Loss Details'],next(r for r in future if r['Team']=='A')['Loss Details'])
        for r in rows:self.assertAlmostEqual(r['Final Rating'],r['Base Rating']+r['Dynamic Validation']-r['Loss Penalty'],places=3)
        self.assertEqual(rows,resume_rankings(list(reversed(games)),names,penalty)[0])

    def test_walkforward_never_uses_test_week_scores_for_selection(self):
        games=[game(w,w,'A','B',20+w,7) for w in range(1,6)]
        _,_,first=walk_forward(games,['A','B'])
        altered=[dict(g,homePoints=200) if g['week']==5 else g for g in games]
        _,_,second=walk_forward(altered,['A','B'])
        self.assertEqual(first['weeks'][-1]['parameters'],second['weeks'][-1]['parameters'])
        self.assertEqual(first['weeks'][:-1],second['weeks'][:-1])

if __name__=='__main__':unittest.main()
