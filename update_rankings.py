#!/usr/bin/env python3
# Refresh requested after the October 29, 2026 JMU–Troy final.
import json, os, sys, urllib.request, urllib.parse
from datetime import datetime, timezone, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from model_core import resume_rankings, walk_forward
from season_forecast import build_forecast

ROOT=Path(__file__).resolve().parent
DATA_PATH=ROOT/'data.json'
STATE_PATH=ROOT/'automation_state.json'
PREDICTIONS_PATH=ROOT/'model_predictions.json'
MARKET_PATH=ROOT/'market_closing_lines.json'
TEAM_CACHE=ROOT/'team_meta.json'
SEASON=2026
API='https://api.collegefootballdata.com'
CURRENT_FORECAST_ENGINE='v7-baseline'
KEY=os.environ.get('CFBD_API_KEY')
if not KEY:
    raise SystemExit('CFBD_API_KEY is not set')

ALIASES={
    "Miami":"Miami (FL)", "Hawai'i":"Hawaii", "Louisiana Monroe":"Louisiana-Monroe",
    "UL Monroe":"Louisiana-Monroe", "Southern Mississippi":"Southern Miss",
    "App State":"Appalachian State", "Connecticut":"UConn"
}
STATE_ABBR={
'Alabama':'AL','Alaska':'AK','Arizona':'AZ','Arkansas':'AR','California':'CA','Colorado':'CO','Connecticut':'CT','Delaware':'DE','District of Columbia':'DC','Florida':'FL','Georgia':'GA','Hawaii':'HI','Idaho':'ID','Illinois':'IL','Indiana':'IN','Iowa':'IA','Kansas':'KS','Kentucky':'KY','Louisiana':'LA','Maine':'ME','Maryland':'MD','Massachusetts':'MA','Michigan':'MI','Minnesota':'MN','Mississippi':'MS','Missouri':'MO','Montana':'MT','Nebraska':'NE','Nevada':'NV','New Hampshire':'NH','New Jersey':'NJ','New Mexico':'NM','New York':'NY','North Carolina':'NC','North Dakota':'ND','Ohio':'OH','Oklahoma':'OK','Oregon':'OR','Pennsylvania':'PA','Rhode Island':'RI','South Carolina':'SC','South Dakota':'SD','Tennessee':'TN','Texas':'TX','Utah':'UT','Vermont':'VT','Virginia':'VA','Washington':'WA','West Virginia':'WV','Wisconsin':'WI','Wyoming':'WY'
}

def name(x): return ALIASES.get(x,x)
def read_json(path, default):
    try: return json.loads(path.read_text())
    except Exception: return default

def api_get(path, params=None):
    q='?'+urllib.parse.urlencode(params or {}) if params else ''
    req=urllib.request.Request(API+path+q,headers={'Authorization':f'Bearer {KEY}','User-Agent':'thequarterbackk-cfb-rankings/1.0'})
    with urllib.request.urlopen(req,timeout=45) as r:
        return json.load(r)

def getv(obj,*keys):
    for k in keys:
        if isinstance(obj,dict) and k in obj and obj[k] is not None: return obj[k]
    return None

def norm_state(s):
    if not s:return None
    s=str(s).strip()
    return STATE_ABBR.get(s,s if len(s)==2 else s)

def load_team_meta():
    cached=read_json(TEAM_CACHE,[])
    if cached: return cached
    raw=api_get('/teams/fbs',{'year':SEASON})
    out=[]
    for t in raw:
        loc=t.get('location') or {}
        logos=getv(t,'logos') or []
        lat=getv(loc,'latitude','lat') or getv(t,'latitude','lat')
        lon=getv(loc,'longitude','lon','lng') or getv(t,'longitude','lon','lng')
        school=name(getv(t,'school','team','name'))
        if not school: continue
        out.append({
            'team':school,'classification':'fbs','conference':getv(t,'conference'),
            'state':norm_state(getv(loc,'state') or getv(t,'state')),
            'city':getv(loc,'city') or getv(t,'city'),'latitude':float(lat) if lat is not None else None,
            'longitude':float(lon) if lon is not None else None,
            'color':('#'+str(getv(t,'color')).lstrip('#')) if getv(t,'color') else None,
            'altColor':('#'+str(getv(t,'alt_color','altColor')).lstrip('#')) if getv(t,'alt_color','altColor') else None,
            'logo':logos[0] if isinstance(logos,list) and logos else None
        })
    TEAM_CACHE.write_text(json.dumps(out,indent=2))
    return out

def cache_team_logos(metadata):
    """Serve exact provider PNGs from our origin for reliable chart exports."""
    import hashlib
    from concurrent.futures import ThreadPoolExecutor
    folder=ROOT/'team_logos';folder.mkdir(exist_ok=True)
    def cache(team):
        filename=hashlib.sha256(team['team'].encode()).hexdigest()[:16]+'.png'
        path=folder/filename
        if not path.exists():
            url=team.get('logo')
            if not url or not str(url).startswith('https://cdn.collegefootballdata.com/'):
                return
            try:
                with urllib.request.urlopen(url,timeout=12) as response:
                    content=response.read(1_000_001)
                if len(content)>1_000_000 or not content.startswith(b'\x89PNG\r\n\x1a\n'):
                    return
                path.write_bytes(content)
            except Exception as exc:
                print('Logo unavailable for',team['team'],type(exc).__name__)
                return
        team['logo']='team_logos/'+filename
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(cache,metadata))
    return metadata

def normalize_game(g):
    return {
      'id':getv(g,'id'),'season':getv(g,'season'),'week':int(getv(g,'week') or 0),'seasonType':getv(g,'seasonType','season_type') or 'regular',
      'startDate':getv(g,'startDate','start_date'),'completed':bool(getv(g,'completed')),
      'neutralSite':bool(getv(g,'neutralSite','neutral_site')),
      'homeTeam':name(getv(g,'homeTeam','home_team')),'awayTeam':name(getv(g,'awayTeam','away_team')),
      'homePoints':getv(g,'homePoints','home_points'),'awayPoints':getv(g,'awayPoints','away_points'),
      'homeClassification':str(getv(g,'homeClassification','home_classification') or '').lower(),
      'awayClassification':str(getv(g,'awayClassification','away_classification') or '').lower(),
    }

def is_final(g): return g['completed'] and g['homePoints'] is not None and g['awayPoints'] is not None

def perf(pf,pa,result): return (100 if result=='W' else 50 if result=='T' else 0)+pf-1.5*pa

def normalize_scores(scores):
    if not scores:return {}
    vals=list(scores.values());lo=min(vals);hi=max(vals)
    if abs(hi-lo)<1e-9:return {k:50.0 for k in scores}
    return {k:100*(v-lo)/(hi-lo) for k,v in scores.items()}

def result_for(team,g):
    if team==g['homeTeam']: pf,pa=g['homePoints'],g['awayPoints']
    else: pf,pa=g['awayPoints'],g['homePoints']
    return ('W' if pf>pa else 'L' if pf<pa else 'T'),pf,pa

def loss_penalty(team_rank, opponent_rank, pf, pa):
    """Extra résumé cost, using only model ranks frozen before the game week.

    Coefficients are explicit policy weights on the existing 100-points/win
    scale, not fitted probabilities. Unknown opening-week ranks add no upset
    component. Scoring and dynamic opponent quality remain separate terms.
    """
    if pa <= pf:
        return 0.0
    gap = max(0, opponent_rank - team_rank) if team_rank is not None and opponent_rank is not None else 0
    return float(50 + 2 * gap + 2 * (pa - pf))

def compute_rankings(completed, fbs_names):
    return resume_rankings(completed, fbs_names, loss_penalty)

def validate_rankings(rows, fbs_names):
    import math
    if len(rows)!=len(set(fbs_names)) or {r['Team'] for r in rows}!=set(fbs_names):
        raise ValueError('Public rankings must contain every FBS team exactly once')
    if [r['Rank'] for r in rows]!=list(range(1,len(rows)+1)):
        raise ValueError('Rank sequence is incomplete')
    for row in rows:
        expected=row['Base Rating']+row['Margin Adjustment']-row['Loss Penalty']
        if not math.isfinite(row['Final Rating']) or abs(row['Final Rating']-expected)>0.001:
            raise ValueError('Rating components do not reconcile: '+row['Team'])
        if sum(d['penalty'] for d in row['Loss Details'])!=row['Loss Penalty']:
            raise ValueError('Loss audit does not reconcile: '+row['Team'])
        if sum(int(x) for x in row['Record'].split('-'))!=row['Games']:
            raise ValueError('Record/game count mismatch: '+row['Team'])


def power_ratings(completed, names):
    """Current-season results only. FBS/FCS opponents enter the same connected game graph."""
    import math
    teams=set(names)
    games=[g for g in completed if g['homeTeam'] and g['awayTeam']]
    for g in games:
        teams.add(g['homeTeam']);teams.add(g['awayTeam'])
    ratings={t:0.0 for t in teams}
    if not games:return ratings,0.0
    latest=max(g['week'] for g in games)
    # Empirical home edge from completed games; shrink toward zero with limited evidence.
    neutral_free=[g for g in games if not g['neutralSite']]
    home_edge=(sum(g['homePoints']-g['awayPoints'] for g in neutral_free)/
               (len(neutral_free)+100)) if neutral_free else 0.0
    home_edge=max(-5.0,min(5.0,home_edge))
    for _ in range(100):
        sums={t:0.0 for t in teams};counts={t:0.0 for t in teams}
        for g in games:
            h,a=g['homeTeam'],g['awayTeam']
            margin=35*math.asinh((g['homePoints']-g['awayPoints'])/35)
            edge=0.0 if g['neutralSite'] else home_edge
            weight=0.96**max(0,latest-g['week'])
            sums[h]+=weight*(margin+ratings[a]-edge)
            sums[a]+=weight*(-margin+ratings[h]+edge)
            counts[h]+=weight;counts[a]+=weight
        new={t:sums[t]/(counts[t]+2.0) if counts[t] else 0.0 for t in teams}
        center=sum(new.values())/len(new)
        updated={t:new[t]-center for t in teams}
        delta=max(abs(updated[t]-ratings[t]) for t in teams)
        ratings=updated
        if delta<0.0001:break
    return ratings,home_edge

def weekly_lines(games, completed, names, ratings, home_edge):
    now=datetime.now(timezone.utc)
    future=[]
    for g in games:
        if is_final(g) or g['homeTeam'] not in ratings or g['awayTeam'] not in ratings:continue
        try: dt=datetime.fromisoformat(g['startDate'].replace('Z','+00:00'))
        except (AttributeError,ValueError):continue
        if dt>=now:future.append(g)
    if not future:return []
    week=min(g['week'] for g in future)
    output=[]
    for g in future:
        if g['week']!=week:continue
        h,a=g['homeTeam'],g['awayTeam']
        margin=ratings[h]-ratings[a]+(0 if g['neutralSite'] else home_edge)
        output.append({'id':g['id'],'homeAdvantage':round(0 if g['neutralSite'] else home_edge,3),'projectedHomeMargin':round(margin,3),'week':week,'startDate':g['startDate'],'homeTeam':h,'awayTeam':a,'favorite':h if margin>=0 else a,'spread':-round(abs(margin)*2)/2,'homePower':round(ratings[h],2),'awayPower':round(ratings[a],2)})
    return sorted(output,key=lambda x:x['startDate'] or '')


def update_prediction_archive(all_games, lines):
    archive=read_json(PREDICTIONS_PATH,{})
    if not isinstance(archive,dict):archive={}
    by_id={str(g['id']):g for g in all_games if g['id'] is not None}
    for key,row in archive.items():
        g=by_id.get(key)
        if g and is_final(g) and row.get('actualHomeMargin') is None:
            row['actualHomeMargin']=g['homePoints']-g['awayPoints']
            row['absoluteError']=round(abs(row['projectedHomeMargin']-row['actualHomeMargin']),2)
    timestamp=datetime.now(timezone.utc).isoformat()
    for row in lines:
        key=str(row['id'])
        if key not in archive and row['id'] is not None:
            archive[key]={'id':row['id'],'week':row['week'],'homeTeam':row['homeTeam'],
                          'awayTeam':row['awayTeam'],'startDate':row['startDate'],
                          'projectedHomeMargin':row['projectedHomeMargin'],
                          'recordedAt':timestamp,'actualHomeMargin':None,'forecastEngine':CURRENT_FORECAST_ENGINE}
    PREDICTIONS_PATH.write_text(json.dumps(archive,indent=2,sort_keys=True))
    scored=[r for r in archive.values() if r.get('absoluteError') is not None]
    return {'archivedPredictions':len(archive),'evaluatedGames':len(scored),
            'meanAbsoluteError':round(sum(r['absoluteError'] for r in scored)/len(scored),2) if scored else None}


def fetch_market_lines(all_games):
    """Read market data separately. Never pass these values into ranking or power functions."""
    now=datetime.now(timezone.utc)
    weeks=set()
    for g in all_games:
        try: dt=datetime.fromisoformat((g['startDate'] or '').replace('Z','+00:00'))
        except ValueError:continue
        if not is_final(g) and now<=dt<=now+timedelta(days=15):weeks.add(g['week'])
    result={}
    for week in sorted(weeks):
        try: market_games=api_get('/lines',{'year':SEASON,'week':week,'seasonType':'regular'})
        except Exception as exc:
            print('Market lines unavailable for week',week,exc)
            continue
        for g in market_games:
            game_id=getv(g,'id')
            providers=getv(g,'lines') or []
            # Stable provider preference; never average incompatible snapshots.
            preferred=next((x for x in providers if str(x.get('provider','')).lower()=='consensus'),None)
            if preferred is None:preferred=next((x for x in providers if x.get('spread') is not None),None)
            if preferred is None:continue
            try:spread=float(preferred['spread'])
            except (ValueError,TypeError,KeyError):continue
            result[str(game_id)]={'homeSpread':spread,'provider':preferred.get('provider','Unknown')}
    return result

def update_market_archive(all_games, model_lines, latest_market):
    archive=read_json(MARKET_PATH,{})
    if not isinstance(archive,dict):archive={}
    now=datetime.now(timezone.utc)
    by_id={str(g['id']):g for g in all_games if g.get('id') is not None}
    for game_id,quote in latest_market.items():
        game=by_id.get(game_id)
        if not game or is_final(game):continue
        try:kickoff=datetime.fromisoformat(game['startDate'].replace('Z','+00:00'))
        except (ValueError,AttributeError):continue
        if now>=kickoff:continue
        entry=archive.setdefault(game_id,{'gameId':game_id,'week':game['week'],
            'homeTeam':game['homeTeam'],'awayTeam':game['awayTeam'],'kickoff':game['startDate']})
        # Most recent successfully observed pre-kickoff quote is our closing-line proxy.
        entry.update({'homeSpread':quote['homeSpread'],'provider':quote['provider'],
                      'observedAt':now.isoformat()})
    MARKET_PATH.write_text(json.dumps(archive,indent=2,sort_keys=True))
    model_archive=read_json(PREDICTIONS_PATH,{})
    for game_id,entry in archive.items():
        game=by_id.get(game_id)
        if game and is_final(game):
            entry['actualHomeMargin']=game['homePoints']-game['awayPoints']
        prediction=model_archive.get(game_id)
        if prediction and prediction.get('projectedHomeMargin') is not None:
            entry['modelHomeMargin']=prediction['projectedHomeMargin']
    MARKET_PATH.write_text(json.dumps(archive,indent=2,sort_keys=True))
    rows=[]
    for game_id,entry in archive.items():
        actual=entry.get('actualHomeMargin')
        model=entry.get('modelHomeMargin')
        market=entry.get('homeSpread')
        if actual is None or model is None or market is None:continue
        # Bet against the closing market only if frozen model margin differs.
        edge=model+market
        outcome=actual+market
        result='push' if abs(outcome)<1e-8 else ('win' if edge*outcome>0 else 'loss')
        if abs(edge)<1e-8:result='no edge'
        rows.append({'week':entry['week'],'gameId':game_id,'result':result,
                     'absoluteError':abs(model-actual)})
    weeks={}
    for row in rows:
        week=str(row['week'])
        stats=weeks.setdefault(week,{'wins':0,'losses':0,'pushes':0,'noEdge':0,'games':0,'absoluteErrorTotal':0})
        stats['games']+=1
        stats['absoluteErrorTotal']+=row['absoluteError']
        if row['result']=='win':stats['wins']+=1
        elif row['result']=='loss':stats['losses']+=1
        elif row['result']=='push':stats['pushes']+=1
        else:stats['noEdge']+=1
    for stats in weeks.values():
        stats['meanAbsoluteError']=round(stats.pop('absoluteErrorTotal')/stats['games'],2)
        decisions=stats['wins']+stats['losses']
        stats['winRate']=round(100*stats['wins']/decisions,1) if decisions else None
    current=[]
    for row in model_lines:
        entry=archive.get(str(row.get('id')),{})
        market=entry.get('homeSpread')
        enriched=dict(row)
        enriched['vegasHomeSpread']=market
        enriched['vegasProvider']=entry.get('provider')
        enriched['vegasObservedAt']=entry.get('observedAt')
        enriched['modelVsVegasEdge']=round(row['projectedHomeMargin']+market,2) if market is not None else None
        current.append(enriched)
    return current,{'weekly':weeks,'totalArchivedMarketGames':len(archive)}

def probability_home(margin, sigma):
    """Normal-error estimate; sigma is estimated from prior archived residuals."""
    import math
    return 0.5 * (1.0 + math.erf(margin / (max(1.0, sigma) * math.sqrt(2.0))))

def prediction_sigma(archive):
    errors=[float(r['projectedHomeMargin'])-float(r['actualHomeMargin'])
            for r in archive.values() if isinstance(r,dict)
            and r.get('actualHomeMargin') is not None and r.get('projectedHomeMargin') is not None
            and r.get('forecastEngine','v7-baseline')==CURRENT_FORECAST_ENGINE]
    # Conservative until at least 30 genuine pregame observations exist.
    if len(errors)<30:return 17.0,len(errors),False
    import math
    mean=sum(errors)/len(errors)
    sd=math.sqrt(sum((e-mean)**2 for e in errors)/len(errors))
    return max(10.0,min(30.0,sd)),len(errors),True

def enrich_probabilities(lines, archive):
    sigma,n,calibrated=prediction_sigma(archive)
    for row in lines:
        margin=row['projectedHomeMargin']
        row['homeWinProbability']=round(100*probability_home(margin,sigma),1)
        row['winnerConfidence']=round(max(row['homeWinProbability'],100-row['homeWinProbability']),1)
        market=row.get('vegasHomeSpread')
        if market is not None:
            row['homeCoverProbability']=round(100*probability_home(margin+market,sigma),1)
            row['coverPick']=row['homeTeam'] if row['homeCoverProbability']>=50 else row['awayTeam']
            row['coverConfidence']=round(max(row['homeCoverProbability'],100-row['homeCoverProbability']),1)
        else:
            row['homeCoverProbability']=None
            row['coverPick']=None
            row['coverConfidence']=None
        row['uncertaintyPoints']=round(sigma,2)
        row['probabilityCalibrated']=calibrated
    return {'sampleSize':n,'sigma':round(sigma,2),'empiricallyCalibrated':calibrated}

def predictive_picks(lines, rankings, fbs_names):
    allowed=set(fbs_names)
    ranks={r['Team']:r for r in rankings}
    out=[]
    for row in lines:
        h,a=row['homeTeam'],row['awayTeam']
        if h not in allowed or a not in allowed:continue
        favorite=row['favorite'];opp=a if favorite==h else h
        p=row['winnerConfidence']
        out.append({'Team':favorite,'Opponent':opp,'Site':'Neutral' if row['homeAdvantage']==0 else ('Home' if favorite==h else 'Away'),
                    'Dynamic Rank':ranks.get(favorite,{}).get('Rank','N/A'),
                    'Record':ranks.get(favorite,{}).get('Record','0-0'),
                    'Final Rating':ranks.get(favorite,{}).get('Final Rating',0),
                    'Opponent Rank':ranks.get(opp,{}).get('Rank','N/A'),
                    'Opponent Rating':ranks.get(opp,{}).get('Final Rating',0),
                    'Model Edge':round(abs(row['projectedHomeMargin']),2),
                    'Confidence':('High' if p>=75 else 'Moderate' if p>=60 else 'Low'),
                    'Win Probability':p,'Model Spread':row['spread'],
                    'Cover Pick':row.get('coverPick'),'Cover Confidence':row.get('coverConfidence'),
                    'startDate':row['startDate']})
    out.sort(key=lambda r:-r['Win Probability'])
    for i,row in enumerate(out[:20],1):row['Pick Rank']=i
    return out[:20]

def build_matrix(completed, fbs_names):
    fbs=sorted(fbs_names);teams=fbs;idx={t:i for i,t in enumerate(teams)}
    cells=[[[] for _ in teams] for __ in teams]
    for i in range(len(teams)): cells[i][i]=['—']
    def put(a,b,val):
        if a in idx and b in idx:
            target=cells[idx[a]][idx[b]]
            if target==['—']:return
            target.append(val)
    fbs_set=set(fbs)
    for g in completed:
        h,a=g['homeTeam'],g['awayTeam'];hp,ap=g['homePoints'],g['awayPoints'];w=g['week']
        def sval(diff):return ('+' if diff>0 else '')+str(diff)+f' ({w})'
        if h in fbs_set and a in fbs_set:
            put(h,a,sval(hp-ap));put(a,h,sval(ap-hp))
    rows=[]
    for i,t in enumerate(teams):
        row=[t]
        for j in range(len(teams)):
            vals=cells[i][j]
            row.append('—' if vals==['—'] else ' · '.join(vals))
        rows.append(row)
    return {'headers':['Team']+teams,'rows':rows}

def build_picks(all_games, rankings, fbs_names):
    now=datetime.now(timezone.utc);future=[]
    fbs_set=set(fbs_names)
    for g in all_games:
        if is_final(g):continue
        try:dt=datetime.fromisoformat(g['startDate'].replace('Z','+00:00')) if g['startDate'] else now+timedelta(days=365)
        except:dt=now+timedelta(days=365)
        if dt>=now-timedelta(hours=5) and g['homeTeam'] in fbs_set and g['awayTeam'] in fbs_set:future.append((g,dt))
    if not future:return []
    minweek=min(g['week'] for g,dt in future);future=[x for x in future if x[0]['week']==minweek]
    rating={r['Team']:r['Final Rating'] for r in rankings};rank={r['Team']:r['Rank'] for r in rankings};record={r['Team']:r['Record'] for r in rankings}
    out=[]
    for g,dt in future:
        h,a=g['homeTeam'],g['awayTeam'];hr=rating.get(h,-100);ar=rating.get(a,-100)
        if g['neutralSite']:ha=hr;aa=ar
        else:ha=hr+6;aa=ar-2
        if ha>=aa:team,opp,site,edge=h,a,'Neutral' if g['neutralSite'] else 'Home',ha-aa
        else:team,opp,site,edge=a,h,'Neutral' if g['neutralSite'] else 'Away',aa-ha
        conf='Very High' if edge>=300 else 'High' if edge>=240 else 'Strong' if edge>=180 else 'Moderate'
        out.append({'Team':team,'Opponent':opp,'Site':site,'Dynamic Rank':rank.get(team,'N/A'),'Record':record.get(team,'0-0'),'Final Rating':rating.get(team,-100),'Opponent Rank':rank.get(opp,'N/A'),'Model Edge':round(edge,4),'Confidence':conf,'Opponent Rating':rating.get(opp,-100),'startDate':g['startDate']})
    out.sort(key=lambda x:-x['Model Edge'])
    for i,r in enumerate(out[:20],1):r['Pick Rank']=i
    return out[:20]

def main():
    global CURRENT_FORECAST_ENGINE
    state=read_json(STATE_PATH,{})
    team_meta=cache_team_logos(load_team_meta());fbs_names=[t['team'] for t in team_meta]
    now=datetime.now(timezone.utc)
    need_full=not state.get('last_full_refresh')
    if not need_full:
        try: need_full=now-datetime.fromisoformat(state['last_full_refresh'])>timedelta(hours=12)
        except: need_full=True

    scoreboard=[]
    try: scoreboard=api_get('/scoreboard',{'classification':'fbs'})
    except Exception as e: print('Scoreboard check failed; falling back to full refresh:',e);need_full=True
    seen=set(str(x) for x in state.get('seen_completed_ids',[]))
    score_final_ids={str(getv(x,'id')) for x in scoreboard if str(getv(x,'status') or '').lower()=='completed'}
    new_finals=score_final_ids-seen
    # Refresh market snapshots hourly, even when no games have finished.

    raw_games=api_get('/games',{'year':SEASON,'seasonType':'regular'})
    all_games=[normalize_game(g) for g in raw_games]
    completed=[g for g in all_games if is_final(g)]
    rankings,hidden_non_fbs_strength,relevant=compute_rankings(completed,fbs_names)
    validate_rankings(rankings,fbs_names)
    power,home_edge,backtest=walk_forward(completed,fbs_names)
    CURRENT_FORECAST_ENGINE=backtest['forecastEngine']
    for row in rankings:
        row['Power Rating']=round(power[row['Team']],3)
        row['Performance Adjustment']=0.0
    lines=weekly_lines(all_games,completed,fbs_names,power,home_edge)
    accuracy=update_prediction_archive(all_games,lines)
    market=fetch_market_lines(all_games)
    lines,market_stats=update_market_archive(all_games,lines,market)
    probability_meta=enrich_probabilities(lines,read_json(PREDICTIONS_PATH,{}))
    matrix=build_matrix(completed,fbs_names)
    picks=predictive_picks(lines,rankings,fbs_names)
    eastern=datetime.now(ZoneInfo('America/New_York')).isoformat(timespec='seconds')
    data={'meta':{'season':SEASON,'lastUpdated':eastern,'updateMode':'Automatic final-score refresh via CFBD + GitHub Actions','modelVersion':'Schedule-adjusted résumé + robust power + frozen rank penalties v8'},'rankings':rankings,'modelBacktest':backtest,'modelInputs':{'completedGames':relevant,'rankingWeights':{'resume':1000,'robustPower':10},'marginCap':35,'lossWeights':{'base':50,'rankGap':2,'margin':2}},'modelLines':lines,'marketStats':market_stats,'modelAccuracy':accuracy,'probabilityMeta':probability_meta,'homeFieldEstimate':round(home_edge,3),'picks':picks,'matrix':matrix,'teamMeta':team_meta,'ownershipGames':sorted([g for g in completed if g['homeTeam'] in set(fbs_names) and g['awayTeam'] in set(fbs_names)],key=lambda g:(g.get('startDate') or '',g.get('id') or 0))}
    data['seasonForecast']=build_forecast(all_games,completed,team_meta,power,home_edge,loss_penalty,probability_meta['sigma'])
    DATA_PATH.write_text(json.dumps(data,separators=(',',':')))
    state={'last_full_refresh':now.isoformat(),'seen_completed_ids':sorted({str(g['id']) for g in completed if g['id'] is not None}),'last_updated':eastern}
    STATE_PATH.write_text(json.dumps(state,indent=2))
    print(f'Updated: {len(completed)} completed games, {len(rankings)} FBS teams, {len(picks)} FBS-only picks, {len(hidden_non_fbs_strength)} hidden non-FBS opponent ratings.')

if __name__=='__main__':main()


