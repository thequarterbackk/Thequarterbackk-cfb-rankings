
let DATA=null, sortKey='Rank', sortAsc=true;

const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const num=v=>typeof v==='number'?v:Number(v);
const fmt=v=>typeof v==='number' ? (Math.round(v*10)/10).toLocaleString() : (v??'');

function renderRankings(){
  const q=document.getElementById('rankSearch').value.trim().toLowerCase();
  let rows=DATA.rankings.filter(r=>!q||String(r.Team).toLowerCase().includes(q));
  rows.sort((a,b)=>{
    let av=a[sortKey], bv=b[sortKey];
    if(typeof av==='string' && typeof bv==='string') return (sortAsc?1:-1)*av.localeCompare(bv);
    av=num(av); bv=num(bv); if(Number.isNaN(av)) av=-999999;if(Number.isNaN(bv)) bv=-999999;
    return (sortAsc?1:-1)*(av-bv);
  });
  document.querySelector('#rankTable tbody').innerHTML=rows.map(r=>{
    const mv=num(r['Rank Change']);
    const move=mv>0?`▲ ${mv}`:mv<0?`▼ ${Math.abs(mv)}`:'—';
    const mclass=mv>0?'move-up':mv<0?'move-down':'move-flat';
    return `<tr class="${num(r.Rank)<=25?'top25':''}">
      <td class="rank-num">#${esc(r.Rank)}</td><td><strong>${esc(r.Team)}</strong></td><td>${esc(r.Record)}</td>
      <td><strong>${fmt(r['Final Rating'])}</strong></td><td>${fmt(r['Base Rating'])}</td>
      <td>${fmt(r['Dynamic Validation'])}</td><td class="${mclass}">${move}</td>
      <td>${esc(r['Points For'])}</td><td>${esc(r['Points Allowed'])}</td><td>${esc(r['Point Diff'])}</td>
    </tr>`;
  }).join('');
}

function renderPicks(){
  document.getElementById('pickCards').innerHTML=DATA.picks.map(r=>{
    const conf=String(r.Confidence||'').replaceAll(' ','-');
    return `<article class="card">
      <div class="pickrank">PICK #${esc(r['Pick Rank'])}</div>
      <h3>${esc(r.Team)}</h3>
      <div class="versus">${esc(r.Site)} vs. ${esc(r.Opponent)}</div>
      <div class="metrics">
        <div class="metric"><b>#${esc(r['Dynamic Rank'])}</b><span>Current rank</span></div>
        <div class="metric"><b>${fmt(r['Final Rating'])}</b><span>Rating</span></div>
        <div class="metric"><b>${fmt(r['Model Edge'])}</b><span>Model edge</span></div>
        <div class="metric"><b>${esc(r.Record)}</b><span>Record</span></div>
      </div>
      <span class="conf ${conf}">${esc(r.Confidence)}</span>
    </article>`;
  }).join('');
}

function renderMatrix(){
  const q=document.getElementById('matrixSearch').value.trim().toLowerCase();
  const headers=DATA.matrix.headers;
  const rows=DATA.matrix.rows.filter(r=>!q||String(r[0]).toLowerCase().includes(q));
  let thead='<thead><tr>'+headers.map((h,i)=>`<th>${esc(h??'')}</th>`).join('')+'</tr></thead>';
  let tbody='<tbody>'+rows.map(r=>'<tr>'+r.map((v,i)=>{
    let cls='';
    if(i>0&&typeof v==='string'){
      if(v.startsWith('+')) cls='win';
      else if(v.startsWith('-')) cls='loss';
      else if(v==='—') cls='diag';
    }
    return `<td class="${cls}">${esc(v??'')}</td>`;
  }).join('')+'</tr>').join('')+'</tbody>';
  document.getElementById('matrixTable').innerHTML=thead+tbody;
}

document.addEventListener('click',e=>{
  if(e.target.matches('.tab')){
    document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));
    document.querySelectorAll('.panel').forEach(x=>x.classList.remove('active'));
    e.target.classList.add('active');document.getElementById(e.target.dataset.tab).classList.add('active');
  }
  if(e.target.matches('#rankTable th')){
    const k=e.target.dataset.key;if(!k)return;
    if(sortKey===k) sortAsc=!sortAsc; else {sortKey=k;sortAsc=true;}
    renderRankings();
  }
});

fetch('data.json').then(r=>r.json()).then(d=>{
  DATA=d;renderRankings();renderPicks();renderMatrix();
  document.getElementById('rankSearch').addEventListener('input',renderRankings);
  document.getElementById('matrixSearch').addEventListener('input',renderMatrix);
});
