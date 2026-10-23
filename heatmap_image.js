/* Results image uses actual scores; ranking affects display order only. */
let heatCells={teams:[],values:new Map(),cell:24,left:240,top:260};
function heatSelection(data,conference,query){
  const metadata=new Map((data.teamMeta||[]).map(t=>[t.team,t]));
  const order=(data.rankings||[]).map(r=>r.Team);
  const selected=new Set(order.filter(t=>(!conference||metadata.get(t)?.conference===conference)&&(!query||t.toLowerCase().includes(query.toLowerCase()))));
  // A team focus includes its opponents; conference filter alone is a square
  // within-conference view. State that scope explicitly in the image title.
  if(query){const focus=new Set(selected);for(const g of data.ownershipGames||[])if(focus.has(g.homeTeam)||focus.has(g.awayTeam)){
    if(order.includes(g.homeTeam))selected.add(g.homeTeam);if(order.includes(g.awayTeam))selected.add(g.awayTeam);
  }}
  return order.filter(t=>selected.has(t));
}
function drawHeatmapImage(){
  if(!DATA)return;
  const canvas=document.getElementById('heatmapCanvas'),ctx=canvas.getContext('2d');
  const conference=document.getElementById('heatConference').value,query=document.getElementById('heatFocus').value.trim();
  const teams=heatSelection(DATA,conference,query),n=teams.length,cell=n>70?24:32,left=246,top=270;
  const values=new Map();for(const row of DATA.matrix?.rows||[])for(let i=1;i<row.length;i++)if(row[i])values.set(`${row[0]}\0${DATA.matrix.headers[i]}`,String(row[i]));
  heatCells={teams,values,cell,left,top};canvas.width=Math.max(900,left+n*cell+24);canvas.height=Math.max(440,top+n*cell+66);
  ctx.fillStyle='#091421';ctx.fillRect(0,0,canvas.width,canvas.height);
  ctx.fillStyle='#f0f6ff';ctx.font='bold 25px system-ui';ctx.fillText('THEQUARTERBACKK • RESULTS HEATMAP',20,38);
  ctx.fillStyle='#b7cbe3';ctx.font='13px system-ui';ctx.fillText(`${DATA.meta.season} • ${conference||'All conferences'}${query?' • Team focus: '+query:''} • signed margin • ranked order`,20,64);
  ctx.fillText('Teal + = win   Orange − = loss   Gray = same team   Dark = no game   Stronger color = larger margin',20,88);
  ctx.fillText(`Updated ${new Date(DATA.meta.lastUpdated).toLocaleString('en-US',{timeZone:'America/New_York'})} ET • ${n} teams${conference&&!query?' • Conference games only':''}`,20,110);
  if(!n){ctx.fillText('No matching teams. Clear the filters to show all FBS teams.',20,160);resetHeatZoom();return;}
  const ranks=new Map((DATA.rankings||[]).map(r=>[r.Team,r.Rank]));
  ctx.font='11px system-ui';ctx.textBaseline='middle';
  teams.forEach((t,i)=>{ctx.save();ctx.translate(left+i*cell+cell/2,top-12);ctx.rotate(-Math.PI/2);ctx.fillStyle='#c8dcf4';ctx.textAlign='left';ctx.fillText(`#${ranks.get(t)} ${t}`,0,0,148);ctx.restore();});
  teams.forEach((team,ri)=>{
    const y=top+ri*cell;ctx.fillStyle=ri%2?'#14253d':'#102036';ctx.fillRect(0,y,left-3,cell);
    ctx.fillStyle='#e3efff';ctx.font='12px system-ui';ctx.textAlign='left';ctx.fillText(`#${ranks.get(team)} ${team}`,12,y+cell/2,left-22);
    teams.forEach((opp,ci)=>{
      const x=left+ci*cell,v=values.get(`${team}\0${opp}`)||'',matches=[...v.matchAll(/([+-]?\d+)\s*\((\d+)\)/g)],margin=matches.length?Number(matches.at(-1)[1]):null;
      ctx.fillStyle=team===opp?'#28394c':margin===null?'#0c1929':margin>=0?`hsl(171 61% ${22+Math.min(Math.abs(margin),42)*.42}%)`:`hsl(24 77% ${23+Math.min(Math.abs(margin),42)*.43}%)`;
      ctx.fillRect(x,y,cell-1,cell-1);
      if(margin!==null){ctx.fillStyle='#ffffff';ctx.font=`bold ${cell>24?12:10}px system-ui`;ctx.textAlign='center';ctx.fillText((margin>0?'+':'')+margin,x+cell/2,y+cell/2,cell-2);}
    });
  });
  ctx.textAlign='left';ctx.font='12px system-ui';ctx.fillStyle='#9cb4cf';ctx.fillText('Rows show the named team’s result against the column opponent. Repeated matchups: latest margin shown; tap for all results.',20,canvas.height-24);
  canvas.setAttribute('aria-label',`${n}-team football results heatmap. Use the Results Heatmap table for accessible game values.`);resetHeatZoom();
}
function initHeatImageControls(){
  const conf=document.getElementById('heatConference');const names=[...new Set((DATA.teamMeta||[]).map(t=>t.conference).filter(Boolean))].sort();
  names.forEach(name=>{const option=document.createElement('option');option.value=name;option.textContent=name;conf.append(option);});
  conf.addEventListener('change',drawHeatmapImage);document.getElementById('heatFocus').addEventListener('input',drawHeatmapImage);
  const canvas=document.getElementById('heatmapCanvas');canvas.addEventListener('click',e=>{
    const r=canvas.getBoundingClientRect(),x=(e.clientX-r.left)*canvas.width/r.width,y=(e.clientY-r.top)*canvas.height/r.height;
    const col=Math.floor((x-heatCells.left)/heatCells.cell),row=Math.floor((y-heatCells.top)/heatCells.cell);
    const a=heatCells.teams[row],b=heatCells.teams[col];if(!a||!b)return;
    document.getElementById('heatCellDetail').textContent=`${a} vs ${b}: ${heatCells.values.get(`${a}\0${b}`)||'No completed matchup'}`;
  });
  const vp=document.getElementById('heatImageViewport');let drag=null;
  vp.addEventListener('pointerdown',e=>{if(e.pointerType==='mouse'){drag={x:e.clientX,y:e.clientY};vp.setPointerCapture(e.pointerId);}});
  vp.addEventListener('pointermove',e=>{if(!drag)return;heatZoom.x+=e.clientX-drag.x;heatZoom.y+=e.clientY-drag.y;drag={x:e.clientX,y:e.clientY};applyHeatZoom();});
  ['pointerup','pointercancel'].forEach(type=>vp.addEventListener(type,()=>drag=null));
  vp.addEventListener('wheel',e=>{e.preventDefault();zoomHeat(e.deltaY<0?1.12:1/1.12);},{passive:false});
}
