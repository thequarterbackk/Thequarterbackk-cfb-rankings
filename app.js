let DATA=null, sortKey='Rank', sortAsc=true;
let heatZoom={scale:1,x:0,y:0};
let ownershipState={svg:null,g:null,zoom:null,countyUnits:null,countyFeatures:null,ownersByCounty:null,colorByTeam:{},teamMeta:[]};

const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const num=v=>typeof v==='number'?v:Number(v);
const fmt=v=>typeof v==='number' ? (Math.round(v*10)/10).toLocaleString() : (v??'');
const stateFips={"01":"AL","02":"AK","04":"AZ","05":"AR","06":"CA","08":"CO","09":"CT","10":"DE","11":"DC","12":"FL","13":"GA","15":"HI","16":"ID","17":"IL","18":"IN","19":"IA","20":"KS","21":"KY","22":"LA","23":"ME","24":"MD","25":"MA","26":"MI","27":"MN","28":"MS","29":"MO","30":"MT","31":"NE","32":"NV","33":"NH","34":"NJ","35":"NM","36":"NY","37":"NC","38":"ND","39":"OH","40":"OK","41":"OR","42":"PA","44":"RI","45":"SC","46":"SD","47":"TN","48":"TX","49":"UT","50":"VT","51":"VA","53":"WA","54":"WV","55":"WI","56":"WY"};

function updateStamp(){
  const raw=DATA?.meta?.lastUpdated;
  let text='Last updated: awaiting first automated refresh';
  if(raw){
    const dt=new Date(raw);
    text=`Last updated: ${dt.toLocaleString('en-US',{timeZone:'America/New_York',month:'short',day:'numeric',year:'numeric',hour:'numeric',minute:'2-digit',timeZoneName:'short'})}`;
  }
  document.getElementById('globalStamp').textContent=text;
  document.querySelectorAll('[data-update-stamp]').forEach(el=>el.textContent=text);
}

function renderRankings(){
  const q=document.getElementById('rankSearch').value.trim().toLowerCase();
  let rows=(DATA.rankings||[]).filter(r=>!q||String(r.Team).toLowerCase().includes(q));
  rows.sort((a,b)=>{
    let av=a[sortKey],bv=b[sortKey];
    if(typeof av==='string'&&typeof bv==='string') return (sortAsc?1:-1)*av.localeCompare(bv);
    av=num(av);bv=num(bv);if(Number.isNaN(av))av=-999999;if(Number.isNaN(bv))bv=-999999;
    return (sortAsc?1:-1)*(av-bv);
  });
  document.querySelector('#rankTable tbody').innerHTML=rows.map(r=>{
    const mv=num(r['Rank Change']);const move=mv>0?`▲ ${mv}`:mv<0?`▼ ${Math.abs(mv)}`:'—';const mclass=mv>0?'move-up':mv<0?'move-down':'move-flat';
    return `<tr class="${num(r.Rank)<=25?'top25':''}"><td class="rank-num">#${esc(r.Rank)}</td><td><strong>${esc(r.Team)}</strong></td><td>${esc(r.Record)}</td><td><strong>${fmt(r['Final Rating'])}</strong></td><td>${fmt(r['Base Rating'])}</td><td>${fmt(r['Dynamic Validation'])}</td><td class="${mclass}">${move}</td><td>${esc(r['Points For'])}</td><td>${esc(r['Points Allowed'])}</td><td>${esc(r['Point Diff'])}</td></tr>`;
  }).join('');
}

function renderPicks(){
  document.getElementById('pickCards').innerHTML=(DATA.picks||[]).map(r=>{
    const conf=String(r.Confidence||'').replaceAll(' ','-');
    const siteLabel=r.Site==='Home'?'Home vs.':r.Site==='Away'?'Away at':'Neutral vs.';
    return `<article class="card"><div class="pickrank">PICK #${esc(r['Pick Rank'])}</div><h3>${esc(r.Team)}</h3><div class="versus">${siteLabel} ${esc(r.Opponent)}</div><div class="metrics"><div class="metric"><b>#${esc(r['Dynamic Rank'])}</b><span>Current rank</span></div><div class="metric"><b>${fmt(r['Final Rating'])}</b><span>Rating</span></div><div class="metric"><b>${fmt(r['Model Edge'])}</b><span>Model edge</span></div><div class="metric"><b>${esc(r.Record)}</b><span>Record</span></div></div><span class="conf ${conf}">${esc(r.Confidence)}</span></article>`;
  }).join('');
}

function renderMatrix(){
  const q=document.getElementById('matrixSearch').value.trim().toLowerCase();
  const headers=DATA.matrix?.headers||[];
  const rows=(DATA.matrix?.rows||[]).filter(r=>!q||String(r[0]).toLowerCase().includes(q));
  const thead='<thead><tr>'+headers.map(h=>`<th>${esc(h??'')}</th>`).join('')+'</tr></thead>';
  const tbody='<tbody>'+rows.map(r=>'<tr>'+r.map((v,i)=>{let cls='';if(i>0&&typeof v==='string'){if(v.startsWith('+'))cls='win';else if(v.startsWith('-'))cls='loss';else if(v==='—')cls='diag';}return `<td class="${cls}">${esc(v??'')}</td>`;}).join('')+'</tr>').join('')+'</tbody>';
  document.getElementById('matrixTable').innerHTML=thead+tbody;
}

function drawHeatmapImage(){
  const canvas=document.getElementById('heatmapCanvas');
  const headers=DATA.matrix?.headers||[]; const rows=DATA.matrix?.rows||[];
  if(!headers.length||!rows.length)return;
  const cell=24,rowLabel=220,headerH=220;
  canvas.width=rowLabel+(headers.length-1)*cell;
  canvas.height=headerH+rows.length*cell;
  const ctx=canvas.getContext('2d');
  ctx.fillStyle='#091421';ctx.fillRect(0,0,canvas.width,canvas.height);
  ctx.font='10px system-ui';ctx.textBaseline='middle';
  ctx.save();ctx.translate(rowLabel,headerH);ctx.rotate(-Math.PI/2);ctx.fillStyle='#9fb0c7';
  headers.slice(1).forEach((h,i)=>ctx.fillText(String(h),6,-i*cell-cell/2));ctx.restore();
  rows.forEach((r,ri)=>{
    const y=headerH+ri*cell;
    ctx.fillStyle='#14253d';ctx.fillRect(0,y,rowLabel,cell);ctx.fillStyle='#dce8f7';ctx.fillText(String(r[0]),7,y+cell/2);
    for(let ci=1;ci<r.length;ci++){
      const v=r[ci],x=rowLabel+(ci-1)*cell;
      if(v==='—')ctx.fillStyle='#1a2431'; else if(typeof v==='string'&&v.startsWith('+'))ctx.fillStyle='#173d2a'; else if(typeof v==='string'&&v.startsWith('-'))ctx.fillStyle='#492020'; else ctx.fillStyle='#0b1626';
      ctx.fillRect(x,y,cell-1,cell-1);
      if(v&&v!=='—'){ctx.fillStyle=v.startsWith('+')?'#8fe5b5':'#ffaaaa';ctx.font='7px system-ui';ctx.fillText(String(v).split(' ')[0],x+2,y+cell/2);ctx.font='10px system-ui';}
    }
  });
  resetHeatZoom();
}

function applyHeatZoom(){document.getElementById('heatImageSurface').style.transform=`translate(${heatZoom.x}px,${heatZoom.y}px) scale(${heatZoom.scale})`;}
function resetHeatZoom(){
  const vp=document.getElementById('heatImageViewport'), canvas=document.getElementById('heatmapCanvas');
  if(!canvas.width)return; heatZoom.scale=Math.min(vp.clientWidth/canvas.width,vp.clientHeight/canvas.height); heatZoom.x=(vp.clientWidth-canvas.width*heatZoom.scale)/2;heatZoom.y=(vp.clientHeight-canvas.height*heatZoom.scale)/2;applyHeatZoom();
}
function zoomHeat(factor){const vp=document.getElementById('heatImageViewport');const cx=vp.clientWidth/2,cy=vp.clientHeight/2;const old=heatZoom.scale;const next=Math.max(.05,Math.min(6,old*factor));heatZoom.x=cx-(cx-heatZoom.x)*(next/old);heatZoom.y=cy-(cy-heatZoom.y)*(next/old);heatZoom.scale=next;applyHeatZoom();}
function initHeatGestures(){
  const vp=document.getElementById('heatImageViewport');let touches=[],lastDist=0,lastMid=null;
  vp.addEventListener('touchstart',e=>{touches=[...e.touches];if(touches.length===2){lastDist=Math.hypot(touches[0].clientX-touches[1].clientX,touches[0].clientY-touches[1].clientY);lastMid={x:(touches[0].clientX+touches[1].clientX)/2,y:(touches[0].clientY+touches[1].clientY)/2};}else if(touches.length===1){lastMid={x:touches[0].clientX,y:touches[0].clientY};}},{passive:true});
  vp.addEventListener('touchmove',e=>{if(!e.touches.length)return;if(e.touches.length===2){const a=e.touches[0],b=e.touches[1],dist=Math.hypot(a.clientX-b.clientX,a.clientY-b.clientY),mid={x:(a.clientX+b.clientX)/2,y:(a.clientY+b.clientY)/2};const rect=vp.getBoundingClientRect(),mx=mid.x-rect.left,my=mid.y-rect.top;const old=heatZoom.scale,next=Math.max(.05,Math.min(6,old*(dist/lastDist)));heatZoom.x=mx-(mx-heatZoom.x)*(next/old)+(mid.x-lastMid.x);heatZoom.y=my-(my-heatZoom.y)*(next/old)+(mid.y-lastMid.y);heatZoom.scale=next;lastDist=dist;lastMid=mid;}else{const t=e.touches[0];heatZoom.x+=t.clientX-lastMid.x;heatZoom.y+=t.clientY-lastMid.y;lastMid={x:t.clientX,y:t.clientY};}applyHeatZoom();},{passive:true});
}

function hashColor(name){let h=0;for(let i=0;i<name.length;i++)h=(h*31+name.charCodeAt(i))>>>0;return `hsl(${h%360} 62% 48%)`;}
function teamColor(name){return ownershipState.colorByTeam[name]||hashColor(name);}
function hav(a,b){const R=6371,rad=x=>x*Math.PI/180,dLat=rad(b[1]-a[1]),dLon=rad(b[0]-a[0]),la1=rad(a[1]),la2=rad(b[1]);const q=Math.sin(dLat/2)**2+Math.cos(la1)*Math.cos(la2)*Math.sin(dLon/2)**2;return 2*R*Math.asin(Math.sqrt(q));}

async function renderOwnershipMap(){
  const holder=document.getElementById('ownershipMap'),status=document.getElementById('ownershipStatus');
  const meta=(DATA.teamMeta||[]).filter(t=>Number.isFinite(+t.latitude)&&Number.isFinite(+t.longitude));
  if(!meta.length){status.textContent='Ownership geography will appear after the first GitHub Action refresh builds team-location data.';holder.innerHTML='<div style="padding:24px;color:#9fb0c7">Run the Update rankings & maps workflow once after uploading this package.</div>';return;}
  status.textContent='Building county ownership…';ownershipState.teamMeta=meta;ownershipState.colorByTeam={};meta.forEach(t=>ownershipState.colorByTeam[t.team]=t.color||hashColor(t.team));
  const us=await fetch('https://cdn.jsdelivr.net/npm/us-atlas@3/counties-10m.json').then(r=>r.json());
  const counties=topojson.feature(us,us.objects.counties).features;const states=topojson.mesh(us,us.objects.states,(a,b)=>a!==b);
  const width=1100,height=700,svg=d3.select(holder).html('').append('svg').attr('viewBox',`0 0 ${width} ${height}`);const g=svg.append('g');
  const projection=d3.geoAlbersUsa().fitSize([width,height],topojson.feature(us,us.objects.states));const path=d3.geoPath(projection);
  const fbs=meta.filter(t=>(t.classification||'fbs').toLowerCase()==='fbs');
  const units=[];const ownersByCounty={};const countyFeatures={};
  counties.forEach(f=>{
    const fid=String(f.id).padStart(5,'0'),st=stateFips[fid.slice(0,2)];countyFeatures[fid]=f;
    let inside=fbs.filter(t=>d3.geoContains(f,[+t.longitude,+t.latitude]));
    let seeds=[];
    if(inside.length>1)seeds=inside.map(t=>t.team);else{
      const centroid=d3.geoCentroid(f);let candidates=fbs.filter(t=>t.state===st);if(!candidates.length)candidates=fbs;
      candidates.sort((a,b)=>hav(centroid,[+a.longitude,+a.latitude])-hav(centroid,[+b.longitude,+b.latitude]));
      if(candidates[0])seeds=[candidates[0].team];
    }
    ownersByCounty[fid]=seeds.slice();seeds.forEach((seed,i)=>units.push({id:`${fid}::${i}::${seed}`,county:fid,owner:seed,seed}));
  });
  const games=(DATA.ownershipGames||[]).slice().sort((a,b)=>new Date(a.startDate)-new Date(b.startDate)||(+a.id)-(+b.id));
  games.forEach(game=>{if(game.homePoints==null||game.awayPoints==null||game.homePoints===game.awayPoints)return;const winner=game.homePoints>game.awayPoints?game.homeTeam:game.awayTeam,loser=game.homePoints>game.awayPoints?game.awayTeam:game.homeTeam;let moved=false;units.forEach(u=>{if(u.owner===loser){u.owner=winner;moved=true;}});if(moved&&!ownershipState.colorByTeam[winner])ownershipState.colorByTeam[winner]=hashColor(winner);});
  const cur={};units.forEach(u=>(cur[u.county]??=[]).push(u.owner));Object.keys(cur).forEach(k=>cur[k]=[...new Set(cur[k])]);ownershipState.ownersByCounty=cur;ownershipState.countyUnits=units;ownershipState.countyFeatures=countyFeatures;
  const defs=svg.append('defs');
  function fillFor(fid){const owners=cur[fid]||[];if(owners.length<=1)return owners[0]?teamColor(owners[0]):'#1b2635';const id='p'+fid;const p=defs.append('pattern').attr('id',id).attr('width',12).attr('height',12).attr('patternUnits','userSpaceOnUse').attr('patternTransform','rotate(35)');const w=12/owners.length;owners.forEach((o,i)=>p.append('rect').attr('x',i*w).attr('width',w).attr('height',12).attr('fill',teamColor(o)));return `url(#${id})`;}
  g.selectAll('path.county').data(counties).join('path').attr('class','county').attr('d',path).attr('fill',d=>fillFor(String(d.id).padStart(5,'0'))).on('click',(e,d)=>showCounty(String(d.id).padStart(5,'0')));
  g.append('path').datum(states).attr('class','state-border').attr('d',path);
  const zoom=d3.zoom().scaleExtent([1,18]).on('zoom',e=>g.attr('transform',e.transform));svg.call(zoom);ownershipState.svg=svg;ownershipState.g=g;ownershipState.zoom=zoom;
  const distinctOwners=[...new Set(units.map(u=>u.owner))];status.textContent=`${units.length.toLocaleString()} territory units • ${distinctOwners.length} current landholders • pinch to zoom`;
}

function showCounty(fid){const owners=ownershipState.ownersByCounty?.[fid]||[];document.getElementById('ownerName').textContent=owners.length?owners.join(' / '):'Unassigned';const counts=owners.map(o=>({o,n:ownershipState.countyUnits.filter(u=>u.owner===o).length}));document.getElementById('ownerTerritory').textContent=counts.map(x=>`${x.o}: ${x.n} territory unit${x.n===1?'':'s'}`).join(' • ')||'No territory owner';document.getElementById('ownerSwatches').innerHTML=owners.map(o=>`<span class="swatch" title="${esc(o)}" style="background:${teamColor(o)}"></span>`).join('');}
function findOwner(){const q=document.getElementById('ownerSearch').value.trim().toLowerCase();if(!q||!ownershipState.svg)return;const team=[...new Set(ownershipState.countyUnits.map(u=>u.owner))].find(x=>x.toLowerCase().includes(q));if(!team)return;const county=ownershipState.countyUnits.find(u=>u.owner===team)?.county;if(!county)return;showCounty(county);ownershipState.g.selectAll('path.county').attr('opacity',d=>{const fid=String(d.id).padStart(5,'0');return (ownershipState.ownersByCounty[fid]||[]).includes(team)?1:.16;});setTimeout(()=>ownershipState.g.selectAll('path.county').attr('opacity',1),1800);}

function activateTab(id){document.querySelectorAll('.tab').forEach(x=>x.classList.toggle('active',x.dataset.tab===id));document.querySelectorAll('.panel').forEach(x=>x.classList.toggle('active',x.id===id));if(id==='matrixImage')setTimeout(()=>{drawHeatmapImage();resetHeatZoom();},30);if(id==='ownership'&&!ownershipState.svg)setTimeout(renderOwnershipMap,30);}

document.addEventListener('click',e=>{
  if(e.target.matches('.tab'))activateTab(e.target.dataset.tab);
  if(e.target.matches('#rankTable th')){const k=e.target.dataset.key;if(!k)return;if(sortKey===k)sortAsc=!sortAsc;else{sortKey=k;sortAsc=true;}renderRankings();}
});

document.getElementById('heatZoomIn').addEventListener('click',()=>zoomHeat(1.35));document.getElementById('heatZoomOut').addEventListener('click',()=>zoomHeat(1/1.35));document.getElementById('heatZoomReset').addEventListener('click',resetHeatZoom);document.getElementById('mapReset').addEventListener('click',()=>{if(ownershipState.svg)ownershipState.svg.transition().duration(250).call(ownershipState.zoom.transform,d3.zoomIdentity);});document.getElementById('ownerSearch').addEventListener('change',findOwner);initHeatGestures();window.addEventListener('resize',()=>{if(document.getElementById('matrixImage').classList.contains('active'))resetHeatZoom();});

fetch(`data.json?v=${Date.now()}`,{cache:'no-store'}).then(r=>r.json()).then(d=>{DATA=d;updateStamp();renderRankings();renderPicks();renderMatrix();document.getElementById('rankSearch').addEventListener('input',renderRankings);document.getElementById('matrixSearch').addEventListener('input',renderMatrix);}).catch(err=>{document.getElementById('globalStamp').textContent='Could not load current data';console.error(err);});
