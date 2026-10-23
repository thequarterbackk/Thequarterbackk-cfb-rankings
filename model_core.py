"""Current-season, team-name-invariant rating and walk-forward evaluation.

Colley résumé equations: https://www.colleyrankings.com/matrate.pdf
Opponent-adjusted margins follow regularized least-squares rating principles.
No polls, recruiting, budgets, conference labels, market lines or prior seasons.
"""
import math

def colley(games, names):
    teams=sorted(set(names)|{g[k] for g in games for k in ('homeTeam','awayTeam')})
    opponents={t:[] for t in teams}; b={t:1.0 for t in teams}
    for g in games:
        h,a=g['homeTeam'],g['awayTeam'];d=g['homePoints']-g['awayPoints']
        opponents[h].append(a);opponents[a].append(h)
        outcome=0.5 if d>0 else -0.5 if d<0 else 0
        b[h]+=outcome;b[a]-=outcome
    ratings={t:0.5 for t in teams}
    for _ in range(400):
        updated={t:(b[t]+sum(ratings[o] for o in opponents[t]))/(2+len(opponents[t])) for t in teams}
        delta=max((abs(updated[t]-ratings[t]) for t in teams),default=0)
        ratings=updated
        if delta<1e-10:break
    return ratings

def fit_power(games, names, shrink=2.0, cap=35.0):
    teams=sorted(set(names)|{g[k] for g in games for k in ('homeTeam','awayTeam')})
    ratings={t:0.0 for t in teams};home=0.0
    edges=[(g['homeTeam'],g['awayTeam'],cap*math.tanh((g['homePoints']-g['awayPoints'])/cap),
            0.0 if g.get('neutralSite') else 1.0) for g in games]
    counts={t:0 for t in teams}
    for h,a,_,_ in edges:counts[h]+=1;counts[a]+=1
    # Damped Jacobi solves ridge normal equations, including joint home edge.
    # Equal priors for all programs; no min-max normalization or prestige seed.
    for _ in range(250):
        sums={t:0.0 for t in teams};home_sum=0.0;home_count=0
        for h,a,margin,site in edges:
            sums[h]+=margin+ratings[a]-site*home
            sums[a]+=-margin+ratings[h]+site*home
            if site:home_sum+=margin-ratings[h]+ratings[a];home_count+=1
        next_home=max(-5.0,min(5.0,home_sum/(home_count+100)))
        updated={t:0.5*ratings[t]+0.5*sums[t]/(counts[t]+shrink) for t in teams}
        next_home=0.5*home+0.5*next_home
        delta=max([abs(next_home-home)]+[abs(updated[t]-ratings[t]) for t in teams])
        ratings,home=updated,next_home
        if delta<1e-7:break
    return ratings,home

def walk_forward(games, names):
    """Choose settings using earlier weeks only; evaluate on the next week.

    Fixed grid is public. Comparison baseline is the previously shipped v7
    power engine. Evaluation includes FBS-vs-FBS games from week 3 onward.
    Retrospective backtests are explicitly distinct from archived predictions.
    """
    names=set(names);weeks=sorted({g['week'] for g in games})
    candidates=[(s,c) for s in (1.0,2.0,4.0) for c in (21.0,35.0,49.0)]
    default=(2.0,35.0);errors={p:[] for p in candidates};rows=[];paired=[]
    for week in weeks:
        if week<3:continue
        train=[g for g in games if g['week']<week]
        test=[g for g in games if g['week']==week and g['homeTeam'] in names and g['awayTeam'] in names]
        if not train or not test:continue
        # Minimum sample threshold avoids selecting on one or two results.
        selected=min(candidates,key=lambda p:(sum(errors[p])/len(errors[p]),p)) if len(errors[default])>=30 else default
        predictions={p:fit_power(train,names,*p) for p in candidates}
        old,edge=legacy_power(train,names)
        selected_errors=[];legacy_errors=[];correct=0
        for g in test:
            h,a=g['homeTeam'],g['awayTeam'];actual=g['homePoints']-g['awayPoints'];site=0 if g.get('neutralSite') else 1
            for p,(ratings,home) in predictions.items():
                estimate=ratings[h]-ratings[a]+site*home
                errors[p].append(abs(estimate-actual))
                if p==selected:
                    selected_errors.append(abs(estimate-actual))
                    correct+=int((estimate>0)==(actual>0)) if actual else 0
            legacy_errors.append(abs(old[h]-old[a]+site*edge-actual))
        paired.extend(old-new for old,new in zip(legacy_errors,selected_errors))
        rows.append({'week':week,'games':len(test),'absoluteError':sum(selected_errors),
                     'baselineAbsoluteError':sum(legacy_errors),'correct':correct,
                     'parameters':{'shrink':selected[0],'marginCap':selected[1]}})
    selected=min(candidates,key=lambda p:(sum(errors[p])/len(errors[p]),p)) if len(errors[default])>=30 else default
    count=sum(r['games'] for r in rows)
    current_mae=sum(r['absoluteError'] for r in rows)/count if count else None
    baseline_mae=sum(r['baselineAbsoluteError'] for r in rows)/count if count else None
    # Promote only when the sequential selection process beat v7 out of sample.
    improvement=(baseline_mae-current_mae) if count else 0.0
    stderr=(sum((d-improvement)**2 for d in paired)/(count-1)/count)**0.5 if count>1 else 0.0
    promote=count>=100 and improvement>=0.01*baseline_mae and improvement-1.96*stderr>0
    power,home=fit_power(games,names,*selected) if promote else legacy_power(games,names)
    report={'evaluation':'Retrospective walk-forward; train only on earlier weeks',
            'games':count,'candidateMAE':round(current_mae,3) if count else None,
            'v7BaselineMAE':round(baseline_mae,3) if count else None,
            'candidateWinnerAccuracy':round(100*sum(r['correct'] for r in rows)/count,2) if count else None,
            'promoted':promote,'forecastEngine':'robust-ridge' if promote else 'v7-baseline',
            'selectedParameters':{'shrink':selected[0],'marginCap':selected[1]},
            'weeks':rows,'minimumPromotionGames':100,'minimumRelativeImprovement':0.01,
            'meanMAEImprovement':round(improvement,4),'pairedImprovement95CI':[round(improvement-1.96*stderr,4),round(improvement+1.96*stderr,4)],
            'limitations':'One current season; no claim of national superiority. Ranking blend and loss-penalty weights are policy choices, not fitted probabilities.'}
    return power,home,report

def legacy_power(games,names):
    """Exact v7 power behavior for a reproducible baseline."""
    teams=set(names)|{g[k] for g in games for k in ('homeTeam','awayTeam')}
    ratings={t:0.0 for t in teams}
    if not games:return ratings,0.0
    latest=max(g['week'] for g in games)
    nonneutral=[g for g in games if not g.get('neutralSite')]
    home=max(-5.0,min(5.0,sum(g['homePoints']-g['awayPoints'] for g in nonneutral)/(len(nonneutral)+100)))
    for _ in range(100):
        sums={t:0.0 for t in teams};counts={t:0.0 for t in teams}
        for g in games:
            h,a=g['homeTeam'],g['awayTeam'];margin=35*math.asinh((g['homePoints']-g['awayPoints'])/35)
            edge=0 if g.get('neutralSite') else home;weight=0.96**max(0,latest-g['week'])
            sums[h]+=weight*(margin+ratings[a]-edge);sums[a]+=weight*(-margin+ratings[h]+edge)
            counts[h]+=weight;counts[a]+=weight
        new={t:sums[t]/(counts[t]+2.0) if counts[t] else 0.0 for t in teams}
        center=sum(new.values())/len(new) if new else 0
        updated={t:new[t]-center for t in teams}
        delta=max((abs(updated[t]-ratings[t]) for t in teams),default=0)
        ratings=updated
        if delta<0.0001:break
    return ratings,home

def resume_rankings(completed,names,penalty_fn):
    """Replay weeks under one universal rule, freezing rank evidence each week.

    Final = 1000*Colley + 10*robust power - frozen loss penalties.
    Blend weights are explicit policy choices, not an accuracy claim.
    Only direct FBS games enter the hidden opponent graph, as in v7.
    """
    names=set(names)
    games=sorted((g for g in completed if g['homeTeam'] in names or g['awayTeam'] in names),key=lambda g:(g['week'],str(g['id'])))
    weeks=sorted({g['week'] for g in games});penalties={t:[] for t in names};previous={};rows=[];hidden={}
    for week in weeks:
        entering={};last_score=None;shared_rank=0
        for i,r in enumerate(rows,1):
            if not r['Games']:continue
            if last_score is None or abs(r['Final Rating']-last_score)>0.0001:shared_rank=i
            entering[r['Team']]=shared_rank;last_score=r['Final Rating']
        previous=entering.copy()
        for g in (g for g in games if g['week']==week):
            h,a=g['homeTeam'],g['awayTeam'];hp,ap=g['homePoints'],g['awayPoints']
            loser,opp,pf,pa=(h,a,hp,ap) if hp<ap else (a,h,ap,hp)
            if hp==ap or loser not in names:continue
            tr=entering.get(loser);opr=entering.get(opp) if opp in names else len(names)+1
            cost=penalty_fn(tr,opr,pf,pa)
            penalties[loser].append({'gameId':g['id'],'week':week,'opponent':opp,
                                    'teamRankAtGame':tr,'opponentRankAtGame':opr,'margin':pa-pf,'penalty':cost})
        through=[g for g in games if g['week']<=week]
        col=colley(through,names);power,_=fit_power(through,names)
        hidden={t:round(100*r,4) for t,r in col.items() if t not in names}
        rows=[]
        for t in sorted(names):
            gs=[g for g in through if t in (g['homeTeam'],g['awayTeam'])]
            pf=pa=wins=losses=ties=0;opponents=[]
            for g in gs:
                h=t==g['homeTeam'];a,b=(g['homePoints'],g['awayPoints']) if h else (g['awayPoints'],g['homePoints'])
                pf+=a;pa+=b;wins+=a>b;losses+=a<b;ties+=a==b
                opponents.append(g['awayTeam'] if h else g['homeTeam'])
            base=1000*col[t];adjustment=10*power[t];cost=sum(d['penalty'] for d in penalties[t])
            score=base+adjustment-cost
            rows.append({'Team':t,'Record':f'{wins}-{losses}'+(f'-{ties}' if ties else ''),'Games':len(gs),
                         'Points For':pf,'Points Allowed':pa,'Point Diff':pf-pa,'Base Rating':round(base,4),
                         'Dynamic Validation':round(adjustment,4),'Margin Adjustment':round(adjustment,4),
                         'Resume Rating':round(col[t],6),'Resume Power':round(power[t],4),
                         'Schedule Strength':round(100*sum(col[o] for o in opponents)/len(opponents),3) if opponents else None,
                         'Loss Penalty':cost,'Loss Details':list(penalties[t]),'Final Rating':round(score,4),
                         'Model Logic':'1000 × schedule-adjusted résumé + 10 × robust power − frozen rank loss penalties'})
        rows.sort(key=lambda r:(-r['Final Rating'],-int(r['Record'].split('-')[0]),r['Team']))
        for i,r in enumerate(rows,1):
            r['Rank']=i;r['Prior Rank']=previous.get(r['Team'],i);r['Rank Change']=r['Prior Rank']-i
    if not rows:
        # Equal evidence yields equal ratings. Alphabetical display is not a seed.
        for i,t in enumerate(sorted(names),1):
            rows.append({'Rank':i,'Team':t,'Record':'0-0','Games':0,'Points For':0,'Points Allowed':0,'Point Diff':0,
                         'Base Rating':500.0,'Dynamic Validation':0.0,'Margin Adjustment':0.0,'Resume Rating':0.5,
                         'Resume Power':0.0,'Schedule Strength':None,'Loss Penalty':0,'Loss Details':[],
                         'Final Rating':500.0,'Prior Rank':i,'Rank Change':0,'Model Logic':'Awaiting results'})
    return rows,hidden,games
