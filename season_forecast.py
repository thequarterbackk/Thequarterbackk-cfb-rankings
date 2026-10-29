"""Deterministic season scenarios; hypothetical games never enter published rankings."""
import math
from model_core import resume_rankings

MAJOR={'ACC','Big Ten','Big 12','SEC'}
GROUP={'American Athletic','American','Conference USA','Mid-American','Mountain West','Pac-12','Sun Belt'}

def project_game(game, completed, power, home_edge, sigma=17):
    h,a=game['homeTeam'],game['awayTeam']
    margin=power.get(h,0)-power.get(a,0)+(0 if game.get('neutralSite') else home_edge)
    # Shrink each team's scoring environment toward the season mean; margin stays
    # exactly the existing forecasting engine's output before integer rounding.
    league=sum(g['homePoints']+g['awayPoints'] for g in completed)/max(1,len(completed))
    def total(t):
        gs=[g for g in completed if t in (g['homeTeam'],g['awayTeam'])]
        return (sum(g['homePoints']+g['awayPoints'] for g in gs)+4*league)/(len(gs)+4)
    expected=max(abs(margin)+6,(total(h)+total(a))/2)
    hp=max(0,round((expected+margin)/2));ap=max(0,round((expected-margin)/2))
    if hp==ap:
        if margin>=0:hp+=1
        else:ap+=1
    p=0.5*(1+math.erf(margin/(max(1,sigma)*math.sqrt(2))))
    return dict(game,homePoints=hp,awayPoints=ap,completed=True,projected=True,
                projectedHomeMargin=round(margin,3),winner=h if hp>ap else a,
                winnerConfidence=round(100*max(p,1-p),1))

def select_field(rows, metadata, champions):
    by={r['Team']:r for r in rows};conf={t['team']:t.get('conference') for t in metadata}
    auto={t for c,t in champions.items() if c in MAJOR}
    group=next((r['Team'] for r in rows if conf.get(r['Team']) in GROUP),None)
    if group:auto.add(group)
    selected=set(auto)
    if 'Notre Dame' in by and by['Notre Dame']['Rank']<=12:selected.add('Notre Dame')
    for r in rows:
        if len(selected)>=12:break
        selected.add(r['Team'])
    return [dict(r,seed=i+1,bid='Automatic' if r['Team'] in auto else 'Notre Dame top 12' if r['Team']=='Notre Dame' else 'At-large')
            for i,r in enumerate(r for r in rows if r['Team'] in selected)]

def build_forecast(games,completed,metadata,power,home_edge,penalty_fn,sigma=17):
    names=[t['team'] for t in metadata];conf={t['team']:t.get('conference') for t in metadata}
    scenario=list(completed);projections=[];snapshots=[];champions={}
    remaining=[g for g in games if not g.get('completed') and (g['homeTeam'] in names or g['awayTeam'] in names)]
    def standings(rows):
        rank={r['Team']:r['Rank'] for r in rows};groups={}
        for t in names:
            c=conf[t]
            if not c or c in ('FBS Independents','Independent','Independents'):continue
            gs=[g for g in scenario if t in (g['homeTeam'],g['awayTeam']) and conf.get(g['homeTeam'])==c and conf.get(g['awayTeam'])==c]
            w=sum((g['homePoints']>g['awayPoints'])==(g['homeTeam']==t) for g in gs)
            groups.setdefault(c,[]).append((t,w/len(gs) if gs else 0,rank[t]))
        return {c:[x[0] for x in sorted(ts,key=lambda x:(-x[1],x[2]))] for c,ts in groups.items()}
    def snapshot(label):
        rows,_,_=resume_rankings(scenario,names,penalty_fn)
        leaders={c:ts[0] for c,ts in standings(rows).items()}
        leaders.update(champions)
        field=select_field(rows,metadata,leaders)
        snapshots.append({'label':label,'field':field})
        return rows
    snapshot('Current model')
    for week in sorted({g['week'] for g in remaining}):
        for g in sorted((g for g in remaining if g['week']==week),key=lambda g:str(g['id'])):
            p=project_game(g,completed,power,home_edge,sigma);projections.append(p);scenario.append(p)
        snapshot('After week '+str(week))
    rows,_,_=resume_rankings(scenario,names,penalty_fn)
    title_games=[];week=max([g['week'] for g in scenario]+[14])+1
    for c,ts in standings(rows).items():
        if len(ts)<2:continue
        g={'id':'title-'+c,'week':week,'homeTeam':ts[0],'awayTeam':ts[1],'neutralSite':True,'conference':c,'startDate':None}
        p=project_game(g,completed,power,home_edge,sigma);title_games.append(p);scenario.append(p);champions[c]=p['winner']
    rows=snapshot('After conference championships')
    field=snapshots[-1]['field'];seed={r['seed']:r['Team'] for r in field}
    rounds=[]
    def match(h,a,label,neutral=True):
        return project_game({'id':label+'-'+h+'-'+a,'homeTeam':h,'awayTeam':a,'neutralSite':neutral,'startDate':None},completed,power,home_edge,sigma)
    first=[match(seed[h],seed[a],'First round',False) for h,a in [(5,12),(8,9),(6,11),(7,10)]]
    quarters=[match(seed[s],first[i]['winner'],'Quarterfinal') for s,i in [(1,1),(4,0),(2,3),(3,2)]]
    semis=[match(quarters[i]['winner'],quarters[i+1]['winner'],'Semifinal') for i in (0,2)]
    final=[match(semis[0]['winner'],semis[1]['winner'],'Championship')]
    for label,gs in [('First round · Dec 18–19',first),('Quarterfinals · Dec 30 / Jan 1',quarters),('Semifinals · Jan 14–15',semis),('National championship · Jan 25',final)]:rounds.append({'label':label,'games':gs})
    return {'games':projections,'weeklyFields':snapshots,'conferenceTitles':title_games,'rounds':rounds,'champion':final[0]['winner'],'records':{r['Team']:r['Record'] for r in rows},'engine':'Fixed current validated power; projected results replay the résumé model weekly.'}
