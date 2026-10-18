"""Reproducible FBS-subset temporal comparison. No network, polls or market inputs."""
import ast, json, math, random
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).parent
d = json.loads((ROOT/'data.json').read_text())
games = json.loads((ROOT/'all_completed_games.json').read_text()) if (ROOT/'all_completed_games.json').exists() else d['ownershipGames']
names = [r['Team'] for r in d['rankings']]
tree = ast.parse((ROOT/'update_rankings.py').read_text())
needed = {'compute_rankings','normalize_scores','perf','result_for'}
source = '\n\n'.join(ast.unparse(n) for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in needed)
# Prior-rank recursion affects displayed rank change only, not ratings.
start = source.index('    if weeks and len(weeks) > 1:')
end = source.index('    ordered = sorted(fbs_set',start)
source = source[:start]+source[end:]

def model(anchor, quality):
    text = source.replace('0.6 * orig + 0.4 * val',f'{anchor} * orig + {1-anchor} * val')
    text = text.replace('0.75 * eff',f'{quality} * eff').replace('0.75 * (100 - eff)',f'{quality} * (100 - eff)')
    ns = {}; exec(text,ns)
    return ns['compute_rankings']

def score(rows):
    n=len(rows)
    return {'games':n,'correct':sum(r['credit'] for r in rows),'accuracy':100*sum(r['credit'] for r in rows)/n,
            'brier':sum((r['probability']-r['actual'])**2 for r in rows)/n}

def probability(x,scale):
    return 1/(1+math.exp(-max(-40,min(40,x/scale))))

def run(anchor,quality):
    fn=model(anchor,quality); predictions=[]; ranks={}
    for week in range(2,8):
        rows,_,_=fn([g for g in games if g['week']<week],names)
        ratings={r['Team']:r['Final Rating'] for r in rows}
        # Fit probability scale from earlier predictions only, shared grid for every candidate.
        historical=[r for r in predictions if r['week']>=3]
        scales=[25,50,75,100,150,200,300,500,750,1000]
        scale=min(scales,key=lambda s:sum((probability(r['difference'],s)-r['actual'])**2 for r in historical)) if historical else 200
        for g in games:
            if g['week']!=week:continue
            if g['homeTeam'] not in ratings or g['awayTeam'] not in ratings:continue
            diff=ratings[g['homeTeam']]-ratings[g['awayTeam']]
            actual=int(g['homePoints']>g['awayPoints'])
            predictions.append({'id':g['id'],'week':week,'difference':diff,'actual':actual,
                 'probability':probability(diff,scale),'credit':0.5 if diff==0 else int((diff>0)==bool(actual))})
    rows,_,_=fn(games,names)
    return {'anchor':anchor,'quality':quality,
            'development':score([r for r in predictions if 4<=r['week']<=6]),
            'holdout':score([r for r in predictions if r['week']==7]),
            'weekly':{str(w):score([r for r in predictions if r['week']==w]) for w in range(3,8)},
            'ranks':{r['Team']:r['Rank'] for r in rows},'predictions':predictions}

anchors=[0,.25,.4,.5,.6,.75,1]
results=[run(a,.75) for a in anchors]
base=next(r for r in results if r['anchor']==.6)
selected=max(results,key=lambda r:(r['development']['accuracy'],-r['development']['brier']))
# Separate SOS-size sensitivity; do not select a new combination after viewing holdout.
weights=[run(.6,q) for q in [0,.375,1.125,1.5]]
def paired(candidate,reference):
    c={r['id']:r for r in candidate['predictions'] if r['week']==7}
    b={r['id']:r for r in reference['predictions'] if r['week']==7}
    gains=sum(c[i]['credit']>b[i]['credit'] for i in c)
    losses=sum(c[i]['credit']<b[i]['credit'] for i in c)
    n=gains+losses
    p=min(1,2*sum(math.comb(n,k) for k in range(min(gains,losses)+1))/2**n) if n else 1
    return {'improved_games':gains,'worsened_games':losses,'exact_two_sided_sign_p':p}
out={'source_timestamp':d['meta']['lastUpdated'],'game_counts':dict(Counter(g['week'] for g in games)),
     'baseline':{'anchor':.6,'quality':.75},'selected_on_development':selected['anchor'],
     'holdout_comparison':paired(selected,base),'anchor_results':results,'weight_sensitivity':[base]+weights}
(ROOT/'sos_results.json').write_text(json.dumps(out,indent=2))
print('Anchor split tests:')
for r in results:
    moves=[abs(r['ranks'][t]-base['ranks'][t]) for t in names]
    print(r['anchor'],json.dumps(r['development']),json.dumps(r['holdout']),'max move',max(moves))
print('Selected on development:',selected['anchor'],out['holdout_comparison'])
print('SOS weight sensitivity:')
for r in [base]+weights: print(r['quality'],json.dumps(r['development']),json.dumps(r['holdout']))
print('Weekly baseline',base['weekly'])
print('Pitt',[(r['anchor'],r['ranks'].get('Pittsburgh')) for r in results])
