#!/usr/bin/env python3
import json, os, sys, urllib.request, urllib.parse
from datetime import datetime, timezone, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parent
DATA_PATH=ROOT/'data.json'
STATE_PATH=ROOT/'automation_state.json'
TEAM_CACHE=ROOT/'team_meta.json'
SEASON=2026
API='https://api.collegefootballdata.com'
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
            'altColor':('#'+str(getv(t,'alt_color','altColor')).lstrip('#')) if getv(t,'alt_color','altColor') else None
        })
    TEAM_CACHE.write_text(json.dumps(out,indent=2))
    return out

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

def direct_quality_opponent(team,opp,fbs_set):
    # Only FBS-involving matchups use the named opponent directly. Non-FBS vs non-FBS is neutral placeholder.
    return opp if (team in fbs_set or opp in fbs_set) else None

def compute_rankings(completed, fbs_names):
    fbs_set=set(fbs_names)
    named_non=set()
    for g in completed:
        if g['homeClassification']=='fbs' and g['awayTeam'] not in fbs_set: named_non.add(g['awayTeam'])
        if g['awayClassification']=='fbs' and g['homeTeam'] not in fbs_set: named_non.add(g['homeTeam'])
    participants=set(fbs_set)|named_non
    relevant=[g for g in completed if g['homeTeam'] in participants or g['awayTeam'] in participants]
    weeks=sorted({g['week'] for g in relevant})
    original={}
    prev_final={};prev_rank={};current={}
    games_by_team={t:[] for t in participants}
    for g in relevant:
        if g['homeTeam'] in participants: games_by_team[g['homeTeam']].append(g)
        if g['awayTeam'] in participants: games_by_team[g['awayTeam']].append(g)

    for w in weeks:
        prior_games={t:[g for g in games_by_team[t] if g['week']<w] for t in participants}
        if prev_final:
            entered=normalize_scores({t:r for t,r in prev_final.items() if prior_games[t]})
        else: entered={}
        for g in [x for x in relevant if x['week']==w]:
            for team,opp in ((g['homeTeam'],g['awayTeam']),(g['awayTeam'],g['homeTeam'])):
                if team not in participants: continue
                qopp=direct_quality_opponent(team,opp,fbs_set)
                original[(g['id'],team)]=50.0 if not qopp else entered.get(qopp,50.0)

        # later validation score maps for every earlier cutoff
        later_norm={}
        for cutoff in weeks:
            if cutoff>=w: continue
            raw={}
            for t in participants:
                vals=[]
                for g in games_by_team[t]:
                    if cutoff<g['week']<=w:
                        res,pf,pa=result_for(t,g);vals.append(perf(pf,pa,res))
                if vals:raw[t]=sum(vals)/len(vals)
            later_norm[cutoff]=normalize_scores(raw)

        current={}
        for t in participants:
            gs=[g for g in games_by_team[t] if g['week']<=w]
            wins=losses=ties=pf=pa=0;quality=0.0
            for g in gs:
                res,tfp,tpa=result_for(t,g);pf+=tfp;pa+=tpa
                wins+=res=='W';losses+=res=='L';ties+=res=='T'
                opp=g['awayTeam'] if t==g['homeTeam'] else g['homeTeam']
                qopp=direct_quality_opponent(t,opp,fbs_set)
                orig=original.get((g['id'],t),50.0)
                if qopp and g['week']<w:
                    val=later_norm.get(g['week'],{}).get(qopp,orig)
                else: val=orig
                eff=.60*orig+.40*val
                if res=='W':quality+=.75*eff
                elif res=='L':quality-=.75*(100-eff)
            base=wins*100+pf-1.5*pa
            final=base+quality
            current[t]={'wins':wins,'losses':losses,'ties':ties,'games':len(gs),'pf':pf,'pa':pa,'base':base,'quality':quality,'final':final}
        ordered=sorted(current,key=lambda t:(-current[t]['final'],-current[t]['wins'],current[t]['losses'],t))
        prev_final={t:current[t]['final'] for t in participants}

    # Recreate prior-week ranks explicitly to avoid ambiguity during partially completed current week.
    latest=max(weeks) if weeks else 0
    prior_ranks={}
    if weeks and len(weeks)>1:
        prior_week=weeks[-2]
        # run a compact recursive pass through prior week using same function by truncating; recursion terminates.
        prior_completed=[g for g in completed if g['week']<=prior_week]
        prior_rows,_,_=compute_rankings(prior_completed,fbs_names)
        prior_ranks={r['Team']:r['Rank'] for r in prior_rows}

    ordered=sorted(current,key=lambda t:(-current[t]['final'],-current[t]['wins'],current[t]['losses'],t)) if current else sorted(participants)
    rows=[]
    for i,t in enumerate(ordered,1):
        r=current.get(t,{'wins':0,'losses':0,'ties':0,'games':0,'pf':0,'pa':0,'base':0,'quality':0,'final':0})
        record=f"{r['wins']}-{r['losses']}"+(f"-{r['ties']}" if r['ties'] else '')
        pr=prior_ranks.get(t,i);rows.append({'Rank':i,'Team':t,'Record':record,'Games':r['games'],'Points For':r['pf'],'Points Allowed':r['pa'],'Point Diff':r['pf']-r['pa'],'Base Rating':round(r['base'],4),'Dynamic Validation':round(r['quality'],4),'Final Rating':round(r['final'],4),'Prior Rank':pr,'Rank Change':pr-i,'Model Logic':'60/40 dynamic opponent validation'})
    return rows,named_non,relevant

def build_matrix(completed, fbs_names, named_non):
    fbs=sorted(fbs_names);non=sorted(named_non);teams=fbs+non+['NON-FBS'];idx={t:i for i,t in enumerate(teams)}
    cells=[[[] for _ in teams] for __ in teams]
    for i in range(len(teams)): cells[i][i]=['—']
    def put(a,b,val):
        if a in idx and b in idx:
            target=cells[idx[a]][idx[b]]
            if target==['—']:return
            target.append(val)
    fbs_set=set(fbs);non_set=set(non)
    for g in completed:
        h,a=g['homeTeam'],g['awayTeam'];hp,ap=g['homePoints'],g['awayPoints'];w=g['week']
        def sval(diff):return ('+' if diff>0 else '')+str(diff)+f' ({w})'
        if h in fbs_set and a in (fbs_set|non_set): put(h,a,sval(hp-ap));put(a,h,sval(ap-hp))
        elif a in fbs_set and h in non_set: put(h,a,sval(hp-ap));put(a,h,sval(ap-hp))
        else:
            if h in non_set: put(h,'NON-FBS',sval(hp-ap));put('NON-FBS',h,sval(ap-hp))
            if a in non_set: put(a,'NON-FBS',sval(ap-hp));put('NON-FBS',a,sval(hp-ap))
    rows=[]
    for i,t in enumerate(teams):
        row=[t]
        for j in range(len(teams)):
            vals=cells[i][j]
            row.append('—' if vals==['—'] else ' · '.join(vals))
        rows.append(row)
    return {'headers':['Team']+teams,'rows':rows}

def build_picks(all_games, rankings):
    now=datetime.now(timezone.utc);future=[]
    for g in all_games:
        if is_final(g):continue
        try:dt=datetime.fromisoformat(g['startDate'].replace('Z','+00:00')) if g['startDate'] else now+timedelta(days=365)
        except:dt=now+timedelta(days=365)
        if dt>=now-timedelta(hours=5) and (g['homeClassification']=='fbs' or g['awayClassification']=='fbs'):future.append((g,dt))
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
    state=read_json(STATE_PATH,{})
    team_meta=load_team_meta();fbs_names=[t['team'] for t in team_meta]
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
    if not new_finals and not need_full:
        print('No new finals and full refresh not due. Nothing to do.')
        return

    raw_games=api_get('/games',{'year':SEASON,'seasonType':'regular'})
    all_games=[normalize_game(g) for g in raw_games]
    completed=[g for g in all_games if is_final(g)]
    rankings,named_non,relevant=compute_rankings(completed,fbs_names)
    matrix=build_matrix(completed,fbs_names,named_non)
    picks=build_picks(all_games,rankings)
    eastern=datetime.now(ZoneInfo('America/New_York')).isoformat(timespec='seconds')
    data={'meta':{'season':SEASON,'lastUpdated':eastern,'updateMode':'Automatic final-score refresh via CFBD + GitHub Actions','modelVersion':'Dynamic Validation 60/40 v2'},'rankings':rankings,'picks':picks,'matrix':matrix,'teamMeta':team_meta,'ownershipGames':[g for g in completed]}
    DATA_PATH.write_text(json.dumps(data,separators=(',',':')))
    state={'last_full_refresh':now.isoformat(),'seen_completed_ids':sorted({str(g['id']) for g in completed if g['id'] is not None}),'last_updated':eastern}
    STATE_PATH.write_text(json.dumps(state,indent=2))
    print(f'Updated: {len(completed)} completed games, {len(rankings)} ranked teams, {len(picks)} picks, {len(named_non)} named non-FBS teams.')

if __name__=='__main__':main()
