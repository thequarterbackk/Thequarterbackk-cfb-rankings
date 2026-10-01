/* Team positions and conference means always use the published Final Rating. */
function strengthGroups(data){
  const metadata=new Map((data.teamMeta||[]).map(t=>[t.team,t]));
  const groups=new Map();
  for(const row of data.rankings||[]){
    const meta=metadata.get(row.Team)||{};
    if(meta.classification && meta.classification.toLowerCase()!=='fbs')continue;
    const rating=row['Final Rating'];
    if(typeof rating!=='number'||!Number.isFinite(rating))continue;
    const conference=meta.conference||'Conference unavailable';
    if(!groups.has(conference))groups.set(conference,[]);
    groups.get(conference).push({...row,rating,meta});
  }
  return [...groups].map(([name,teams])=>({name,teams:teams.sort((a,b)=>b.rating-a.rating||a.Team.localeCompare(b.Team)),mean:teams.reduce((s,t)=>s+t.rating,0)/teams.length}))
    .sort((a,b)=>b.mean-a.mean||a.name.localeCompare(b.name));
}

function renderStrengthLadder(data){
  const holder=document.getElementById('ladderChart');
  const groups=strengthGroups(data);
  if(!groups.length){holder.textContent='Conference strength will appear when model ratings are available.';return;}
  const short={'American Athletic':'AAC','Mountain West':'MWC','Mid-American':'MAC','Conference USA':'CUSA','Sun Belt':'SBC','FBS Independents':'IND'};
  const colors={'SEC':'#8eaaff','Big Ten':'#55c8f4','Big 12':'#fa7e94','ACC':'#79a9ff','Pac-12':'#5bd1cb','American Athletic':'#70d8b1','Mountain West':'#c6a0ef','Sun Belt':'#ffbf6e','Conference USA':'#e4a17c','Mid-American':'#c1d27f','FBS Independents':'#aab8ca'};
  const ratings=groups.flatMap(g=>g.teams.map(t=>t.rating));
  const spread=Math.max(...ratings)-Math.min(...ratings);
  const rough=Math.max(spread/8,1), magnitude=10**Math.floor(Math.log10(rough));
  const step=[1,2,5,10].map(n=>n*magnitude).find(n=>n>=rough);
  const min=Math.floor((Math.min(...ratings)-step*.4)/step)*step;
  const max=Math.ceil((Math.max(...ratings)+step*.4)/step)*step;
  const top=108,bottom=1260,left=80;
  const y=rating=>top+(max-rating)/(max-min)*(bottom-top);
  // Horizontal lanes prevent logo overlaps without moving any team's rating vertically.
  let width=left;
  for(const group of groups){
    const laneEnds=[];
    group.positions=group.teams.map(team=>{
      const cy=y(team.rating);
      let lane=laneEnds.findIndex(end=>cy-end>=42);
      if(lane===-1)lane=laneEnds.length;
      laneEnds[lane]=cy;
      return {team,lane,cy};
    });
    group.lanes=laneEnds.length;
    group.width=Math.max(136,group.lanes*42+28);
    group.x=width;width+=group.width;
  }
  width+=18;
  const ns='http://www.w3.org/2000/svg';
  const el=(tag,attrs={},text)=>{const node=document.createElementNS(ns,tag);Object.entries(attrs).forEach(([k,v])=>node.setAttribute(k,v));if(text!==undefined)node.textContent=text;return node;};
  const svg=el('svg',{viewBox:`0 0 ${width} 1320`,width,height:1320,role:'img','aria-labelledby':'ladderSvgTitle ladderSvgDescription'});
  svg.append(el('title',{id:'ladderSvgTitle'},'Conference Strength Ladder — Final Rating'));
  svg.append(el('desc',{id:'ladderSvgDescription'},'Team logos are positioned at their exact published model rating. Bars show conference mean ratings. Full values are provided in the tables below.'));
  groups.forEach((g,i)=>svg.append(el('rect',{x:g.x,y:top-26,width:g.width,height:bottom-top+52,fill:i%2?'#14253d':'#0c1a2c'})));
  for(let value=min;value<=max;value+=step){
    const cy=y(value);
    svg.append(el('line',{x1:left,y1:cy,x2:width-18,y2:cy,stroke:'#2b405b','stroke-dasharray':value===0?'':'3 4'}));
    svg.append(el('text',{x:left-12,y:cy+5,fill:'#a9bdd4','text-anchor':'end','font-size':13},value.toLocaleString('en-US')));
  }
  svg.append(el('text',{x:left,y:24,fill:'#a9bdd4','font-size':13},'FINAL RATING • HIGHER IS BETTER'));
  for(const g of groups){
    const color=colors[g.name]||'#aab8ca',center=g.x+g.width/2;
    svg.append(el('text',{x:center,y:58,fill:color,'text-anchor':'middle','font-size':22,'font-weight':800},short[g.name]||g.name));
    svg.append(el('text',{x:center,y:78,fill:'#a9bdd4','text-anchor':'middle','font-size':11},`${g.teams.length} teams • mean ${g.mean.toFixed(1)}`));
    svg.append(el('line',{x1:g.x+10,y1:y(g.mean),x2:g.x+g.width-10,y2:y(g.mean),stroke:color,'stroke-width':4,'stroke-linecap':'round'}));
    for(const {team,lane,cy} of g.positions){
      const cx=center+(lane-(g.lanes-1)/2)*42;
      const label=`${team.Team} • #${team.Rank} • ${team.Record} • Final Rating ${team.rating.toFixed(2)} • ${g.name}`;
      const mark=el('g',{class:'ladder-team',tabindex:0,role:'button','aria-label':label,transform:`translate(${cx} ${cy})`});
      mark.append(el('title',{},label));
      mark.append(el('circle',{r:18,fill:'#ffffff',stroke:color,'stroke-width':2.5}));
      const fallback=el('text',{'text-anchor':'middle',y:4,fill:'#12243b','font-size':9,'font-weight':800},team.Team.split(/\s+/).map(s=>s[0]).join('').slice(0,4));
      mark.append(fallback);
      if(team.meta.logo){
        // Only load web image URLs, never markup supplied by metadata.
        let url;try{url=new URL(team.meta.logo);}catch{}
        if(url&&['https:','http:'].includes(url.protocol)){
          const img=el('image',{href:url.href,x:-13,y:-13,width:26,height:26,preserveAspectRatio:'xMidYMid meet'});
          img.addEventListener('load',()=>fallback.setAttribute('visibility','hidden'));
          img.addEventListener('error',()=>img.remove());mark.append(img);
        }
      }
      const select=()=>{document.getElementById('ladderDetail').textContent=label;svg.querySelectorAll('.ladder-team.selected').forEach(n=>n.classList.remove('selected'));mark.classList.add('selected');};
      mark.addEventListener('click',select);
      mark.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();select();}});
      svg.append(mark);
    }
  }
  svg.append(el('text',{x:left,y:1300,fill:'#a9bdd4','font-size':13},'Horizontal bar = group mean • logo height = exact Final Rating • IND = independent programs'));
  holder.replaceChildren(svg);
  const safe=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  document.querySelector('#ladderSummary tbody').innerHTML=groups.map(g=>`<tr><td><strong>${safe(g.name)}</strong></td><td>${g.teams.length}</td><td>${g.mean.toFixed(2)}</td><td>${safe(g.teams[0].Team)} (${g.teams[0].rating.toFixed(1)})</td><td>${safe(g.teams.at(-1).Team)} (${g.teams.at(-1).rating.toFixed(1)})</td></tr>`).join('');
  document.querySelector('#ladderTeams tbody').innerHTML=groups.flatMap(g=>g.teams.map(t=>`<tr><td>${safe(t.Team)}</td><td>${safe(g.name)}</td><td>#${safe(t.Rank)}</td><td>${safe(t.Record)}</td><td>${t.rating.toFixed(2)}</td></tr>`)).join('');
  const weeks=(data.matrix?.rows||[]).flatMap(row=>row.slice(1).flatMap(v=>[...String(v).matchAll(/\((\d+)\)/g)].map(m=>+m[1])));
  const week=weeks.length?Math.max(...weeks):null;
  document.getElementById('ladderWeek').textContent=`${data.meta?.season||''}${week!==null?` • Results through Week ${week}`:' • Awaiting results'}`;
}
