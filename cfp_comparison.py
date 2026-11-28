"""Replay the résumé model through each official CFP poll's game cutoff."""
import json
import re
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

SOURCE = 'https://collegefootballplayoff.com/sports/2026/8/9/wk-x-wk-rankings'
EASTERN = ZoneInfo('America/New_York')
# The Nov. 17 release included a Sunday game. Selection Day follows title games.
CUTOFFS_2026 = {
    'NOVEMBER 3': ('2026-11-03', '2026-10-31'),
    'NOVEMBER 10': ('2026-11-10', '2026-11-07'),
    'NOVEMBER 17': ('2026-11-17', '2026-11-15'),
    'NOVEMBER 24': ('2026-11-24', '2026-11-21'),
    'DECEMBER 1': ('2026-12-01', '2026-11-28'),
    'DECEMBER 6': ('2026-12-06', '2026-12-05'),
}
CFP_NAMES = {
    'Miami': 'Miami (FL)',
    'Southern California': 'USC',
    'Mississippi': 'Ole Miss',
    'Hawai‘i': 'Hawaii',
    'Hawai\'i': 'Hawaii',
    'Connecticut': 'UConn',
}


def parse_polls(html):
    season = re.search(
        r'\{\s*id:\s*"y2026"\s*,\s*label:\s*"2026"\s*,\s*weeks:\s*\[(.*?)\]'
        r'\s*,\s*teams:\s*\[(.*?)\]\s*\}(?=\s*,\s*\{\s*id:|\s*\]\s*;)', html, flags=re.S,
    )
    if not season:
        raise ValueError('2026 CFP archive data was missing')
    labels = re.findall(r'label:\s*"([^"]+)"\s*,\s*sub:\s*"([^"]*)"', season[1])
    teams = [
        (CFP_NAMES.get(team, team), json.loads('[' + ranks + ']'))
        for team, ranks in re.findall(r'name:\s*"([^"]+)"[^{}]*?ranks:\s*\[([^\]]*)\]', season[2])
    ]
    polls = []
    for i, (label, sub) in enumerate(labels):
        dates = CUTOFFS_2026.get((sub or label).upper())
        if dates is None:
            continue
        ranked = sorted(
            (int(ranks[i]), team) for team, ranks in teams
            if i < len(ranks) and str(ranks[i]).isdigit()
        )
        if [rank for rank, _ in ranked] != list(range(1, 26)):
            continue
        if len({team for _, team in ranked}) != 25:
            continue
        polls.append({'released': dates[0], 'through': dates[1], 'cfp': [team for _, team in ranked]})
    if not polls:
        raise ValueError('CFP archive contained no complete Top 25')
    return polls


def build_comparison(polls, games, team_meta, compute_rankings, previous=None):
    teams = {row['team']: row['conference'] or 'Independent' for row in team_meta}
    dated_games = [
        (datetime.fromisoformat(game['startDate']).astimezone(EASTERN).date().isoformat(), game)
        for game in games if game.get('startDate')
    ]
    snapshots = {}
    if previous and previous.get('season') == 2026:
        snapshots = {row['released']: row for row in previous['polls']}
    for poll in sorted(polls, key=lambda row: row['released']):
        if not set(poll['cfp']).issubset(teams):
            raise ValueError(f"Unmatched CFP teams: {set(poll['cfp']) - set(teams)}")
        eligible = [game for date, game in dated_games if date <= poll['through']]
        if not eligible:
            continue
        rankings, _, _ = compute_rankings(eligible, list(teams))
        snapshots[poll['released']] = {
            **poll,
            'model': [
                {'team': row['Team'], 'rank': row['Rank'], 'record': row['Record']}
                for row in rankings if row['Games']
            ],
        }
    return {'season': 2026, 'source': SOURCE, 'teams': teams, 'polls': sorted(
        snapshots.values(), key=lambda row: row['released'], reverse=True,
    )}


def refresh_comparison(path, games, team_meta, compute_rankings, include_title_games=None):
    previous = json.loads(path.read_text()) if path.exists() else None
    try:
        with urllib.request.urlopen(SOURCE, timeout=20) as response:
            polls = parse_polls(response.read().decode('utf-8'))
    except (OSError, ValueError) as error:
        print(f'CFP archive refresh failed: {error}. Reusing published polls.')
        polls = previous['polls'] if previous else []
    if not polls:
        return
    # Rebuild previous releases too, in case past scores or model rules change.
    by_release = {row['released']: row for row in (previous or {}).get('polls', [])}
    by_release.update({row['released']: row for row in polls})
    if include_title_games and '2026-12-06' in by_release:
        games = include_title_games(games, team_meta)
    comparison = build_comparison(
        [{key: row[key] for key in ('released', 'through', 'cfp')} for row in by_release.values()],
        games, team_meta, compute_rankings, previous,
    )
    path.write_text(json.dumps(comparison, separators=(',', ':')) + '\n')
