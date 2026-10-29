import unittest
from season_forecast import project_game,select_field,build_forecast

class ForecastTests(unittest.TestCase):
    def test_margin_home_neutral_and_no_ties(self):
        games=[{'homeTeam':'A','awayTeam':'B','homePoints':30,'awayPoints':20}]
        g={'homeTeam':'A','awayTeam':'B','neutralSite':False}
        p=project_game(g,games,{'A':4,'B':1},2)
        self.assertEqual(p['projectedHomeMargin'],5)
        self.assertLessEqual(abs(p['homePoints']-p['awayPoints']-5),1)
        self.assertEqual(project_game(dict(g,neutralSite=True),games,{'A':4,'B':1},2)['projectedHomeMargin'],3)
        tied=project_game(g,games,{'A':0,'B':0},0)
        self.assertNotEqual(tied['homePoints'],tied['awayPoints'])
        self.assertNotIn('projected',g)
    def test_2026_group_bid_need_not_be_champion(self):
        teams=['T'+str(i) for i in range(16)]
        rows=[{'Team':t,'Rank':i+1} for i,t in enumerate(teams)]
        meta=[{'team':t,'conference':'SEC' if i<13 else 'Sun Belt'} for i,t in enumerate(teams)]
        f=select_field(rows,meta,{'SEC':'T12','Sun Belt':'T15'})
        self.assertEqual(len(f),12)
        self.assertIn('T12',[r['Team'] for r in f])
        self.assertIn('T13',[r['Team'] for r in f])
        self.assertNotIn('T15',[r['Team'] for r in f])
        self.assertEqual([r['seed'] for r in f],list(range(1,13)))
    def test_bracket_progression_and_input_immutability(self):
        meta=[{'team':str(i),'conference':c} for i,c in enumerate(['ACC']*4+['SEC']*4+['Sun Belt']*4)]
        completed=[{'id':i,'week':1,'homeTeam':str(i),'awayTeam':str(i+1),'homePoints':28,'awayPoints':14,'neutralSite':False,'completed':True} for i in range(0,12,2)]
        future={'id':99,'week':2,'homeTeam':'0','awayTeam':'4','completed':False,'neutralSite':False,'startDate':None}
        f=build_forecast(completed+[future],completed,meta,{str(i):12-i for i in range(12)},2,lambda *args:0)
        self.assertEqual([len(r['games']) for r in f['rounds']],[4,4,2,1])
        self.assertEqual(len(f['weeklyFields']),3)
        self.assertEqual(len(completed),6)
        self.assertFalse(future['completed'])
        self.assertEqual(f['champion'],f['rounds'][-1]['games'][0]['winner'])
        first={g['winner'] for g in f['rounds'][0]['games']}
        quarter={t for g in f['rounds'][1]['games'] for t in (g['homeTeam'],g['awayTeam'])}
        self.assertTrue(first<=quarter)
if __name__=='__main__':unittest.main()
