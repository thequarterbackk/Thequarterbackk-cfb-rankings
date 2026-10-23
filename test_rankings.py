"""Offline checks for historical-rank penalties; no API credentials or calls."""
import ast
import unittest
from pathlib import Path

tree = ast.parse(Path(__file__).with_name('update_rankings.py').read_text())
functions = ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef)], type_ignores=[])
model = {}
exec(compile(functions, 'update_rankings.py', 'exec'), model)
compute = model['compute_rankings']
penalty = model['loss_penalty']

def game(i, week, home, away, hp, ap):
    return dict(id=i, week=week, homeTeam=home, awayTeam=away, homePoints=hp, awayPoints=ap)

class RankPenaltyTests(unittest.TestCase):
    def test_upset_and_margin_severity(self):
        self.assertGreater(penalty(1, 70, 31, 34), penalty(1, 5, 31, 34))
        self.assertGreater(penalty(1, 70, 3, 34), penalty(1, 70, 31, 34))
        self.assertEqual(penalty(1, 70, 31, 34), 194)
        self.assertEqual(penalty(1, 70, 34, 31), 0)

    def test_no_invented_opening_rank_and_accounting(self):
        rows, _, _ = compute([game(1, 1, 'A', 'B', 10, 20)], ['A', 'B', 'Idle'])
        a = next(r for r in rows if r['Team'] == 'A')
        self.assertIsNone(a['Loss Details'][0]['teamRankAtGame'])
        self.assertIsNone(a['Loss Details'][0]['opponentRankAtGame'])
        self.assertEqual(a['Loss Penalty'], 70)
        for r in rows:
            self.assertAlmostEqual(r['Final Rating'], r['Base Rating'] + r['Dynamic Validation'] - r['Loss Penalty'], places=3)

    def test_freeze_history_and_same_week_order(self):
        names = ['A', 'B', 'C', 'D']
        games = [game(1, 1, 'A', 'C', 60, 0), game(2, 1, 'B', 'D', 10, 7),
                 game(3, 2, 'A', 'D', 17, 20), game(4, 2, 'B', 'C', 30, 0)]
        before = compute(games, names)[0]
        after = compute(games + [game(5, 3, 'D', 'C', 0, 60)], names)[0]
        loss = lambda rows: next(r for r in rows if r['Team'] == 'A')['Loss Details']
        self.assertEqual(loss(before), loss(after))
        self.assertEqual(loss(before)[0]['teamRankAtGame'], 1)
        self.assertEqual(loss(before)[0]['opponentRankAtGame'], 3)
        self.assertEqual(before, compute(games[:2] + list(reversed(games[2:])), names)[0])
        self.assertEqual(before, compute(list(reversed(games)), names)[0])

    def test_hidden_fcs_loss(self):
        rows, _, _ = compute([game(1, 1, 'A', 'B', 30, 0), game(2, 2, 'A', 'FCS', 7, 14)], ['A', 'B'])
        self.assertEqual(len(rows), 2)
        detail = next(r for r in rows if r['Team'] == 'A')['Loss Details'][0]
        self.assertEqual(detail['opponentRankAtGame'], 3)
        self.assertEqual(detail['penalty'], 68)

if __name__ == '__main__':
    unittest.main()
