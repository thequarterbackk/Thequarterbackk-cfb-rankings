/* Exact data-driven images. No screenshot service or third-party export API. */
let ladderImageURL=null;
function downloadBlob(blob,name){const a=document.createElement('a');const url=URL.createObjectURL(blob);a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),60000);}
function exportHeatPNG(){const canvas=document.getElementById('heatmapCanvas');canvas.toBlob(blob=>{if(blob)downloadBlob(blob,`cfb-results-heatmap-${DATA.meta.season}.png`);});}
async function buildLadderImage(){
  const source=document.querySelector('#ladderChart svg');if(!source)return;
  const status=document.getElementById('ladderImageStatus');status.textContent='Preparing the full-resolution image…';
  const svg=source.cloneNode(true),ns='http://www.w3.org/2000/svg';
  const box=source.viewBox.baseVal;svg.setAttribute('viewBox',`0 0 ${box.width} ${box.height+90}`);svg.setAttribute('width',box.width);svg.setAttribute('height',box.height+90);
  svg.setAttribute('xmlns',ns);svg.style.fontFamily='Arial, sans-serif';
  const group=document.createElementNS(ns,'g');group.setAttribute('transform','translate(0 76)');while(svg.firstChild)group.append(svg.firstChild);
  const background=document.createElementNS(ns,'rect');background.setAttribute('width','100%');background.setAttribute('height','100%');background.setAttribute('fill','#091421');svg.append(background);
  function text(y,size,value,color){const t=document.createElementNS(ns,'text');t.setAttribute('x',28);t.setAttribute('y',y);t.setAttribute('fill',color);t.setAttribute('font-size',size);t.setAttribute('font-weight','700');t.textContent=value;svg.append(t);}
  text(32,25,'THEQUARTERBACKK • CONFERENCE STRENGTH','#f4f7fb');
  text(55,13,`${DATA.meta.season} • ${new Date(DATA.meta.lastUpdated).toLocaleString('en-US',{timeZone:'America/New_York'})} ET • Team ratings and conference means`,'#a9bdd4');svg.append(group);
  // Inline logos when CORS permits. Never leave external images in an export;
  // blocked/timed-out logos retain readable initials and cannot taint the PNG.
  const images=[...svg.querySelectorAll('image')];let next=0,missing=0;
  async function worker(){while(next<images.length){const image=images[next++];try{
    const response=await fetch(image.getAttribute('href'),{signal:AbortSignal.timeout(5000)});if(!response.ok)throw Error('image');const blob=await response.blob();if(!blob.type.startsWith('image/'))throw Error('type');
    const data=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result);reader.onerror=reject;reader.readAsDataURL(blob);});image.setAttribute('href',data);
  }catch{image.parentNode.querySelector('text')?.removeAttribute('visibility');image.remove();missing++;}}}
  await Promise.all(Array.from({length:6},worker));
  svg.querySelectorAll('[tabindex]').forEach(n=>{n.removeAttribute('tabindex');n.removeAttribute('role');n.classList.remove('selected');});
  const blob=new Blob([new XMLSerializer().serializeToString(svg)],{type:'image/svg+xml;charset=utf-8'});
  if(ladderImageURL)URL.revokeObjectURL(ladderImageURL);ladderImageURL=URL.createObjectURL(blob);
  const preview=document.getElementById('ladderImage');preview.src=ladderImageURL;
  const open=document.getElementById('ladderImageOpen');open.href=ladderImageURL;open.hidden=false;
  document.getElementById('ladderImageDownload').disabled=false;
  status.textContent=`Full-resolution image • all conferences in one view${missing?' • initials used for '+missing+' unavailable logos':''}`;
}
async function showLadderView(view){
  document.getElementById('ladderImageView').hidden=view!=='image';document.getElementById('ladderChart').hidden=view==='image';
  document.getElementById('ladderViewImage').setAttribute('aria-pressed',String(view==='image'));document.getElementById('ladderViewChart').setAttribute('aria-pressed',String(view==='chart'));
  if(view==='image'&&!ladderImageURL)await buildLadderImage();
}
async function exportLadderPNG(){
  if(!ladderImageURL)await buildLadderImage();if(!ladderImageURL)return;
  const img=new Image();img.src=ladderImageURL;await img.decode();
  const canvas=document.createElement('canvas');canvas.width=img.naturalWidth*2;canvas.height=img.naturalHeight*2;
  canvas.getContext('2d').drawImage(img,0,0,canvas.width,canvas.height);
  canvas.toBlob(blob=>{if(blob)downloadBlob(blob,`conference-strength-${DATA.meta.season}.png`);});
}
document.getElementById('ladderViewImage').addEventListener('click',()=>showLadderView('image').catch(()=>{document.getElementById('ladderImageStatus').textContent='Image unavailable. Use Explore chart to view current ratings.';}));
document.getElementById('ladderViewChart').addEventListener('click',()=>showLadderView('chart'));
document.getElementById('ladderImageDownload').addEventListener('click',()=>exportLadderPNG().catch(()=>{document.getElementById('ladderImageStatus').textContent='PNG export unavailable in this browser. Open the full image to save it.';}));
document.getElementById('heatDownload').addEventListener('click',exportHeatPNG);
