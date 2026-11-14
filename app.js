'use strict';
const $=s=>document.querySelector(s), colours={PH:'#d43b4c',BN:'#2453a0',PN:'#2988ac',BERSATU:'#a43b32',BERSAMA:'#c59c22',BEBAS:'#737d89',PUTRA:'#875a9d'},grey='#ccd6e0';
let data,geometry,selected='N.01',mode='unofficial',loading=false,health,extra,source="awani";
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=n=>n===null||n===undefined?'—':n.toLocaleString('en-MY');
const when=s=>new Date(s).toLocaleString('en-MY',{timeZone:'Asia/Kuala_Lumpur',day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit',hour12:false})+' MYT';
const total=s=>s.candidates.reduce((a,c)=>a+(c.votes||0),0);
function leader(s){const cs=[...s.candidates].sort((a,b)=>(b.votes||0)-(a.votes||0));return total(s)>0&&cs[0].votes>(cs[1].votes||0)?cs[0]:null;}
function seats(){return source==='bernama'?data.modes[mode]:extra.sources[source].seats;}
function activeFeed(){return source==='bernama'?{checkedAt:data.checkedAt,ok:health?.ok}:extra.sources[source];}
function sourceCards(){
 const labels={awani:'Astro AWANI',spr:'SPR',malaysiakini:'Malaysiakini'};
 $('#sourceStatus').innerHTML=Object.entries(labels).map(([key,label])=>{const f=extra?.sources?.[key];return `<p><b>${label}</b> — ${esc(f?.message||'Source status unavailable')}${f?.checkedAt?' · Checked '+when(f.checkedAt):''} ${f?.url?`<a href="${esc(f.url)}" target="_blank" rel="noopener">View source ↗</a>`:''}</p>`;}).join('');
 for(const key of ['awani','spr']) $('#source').querySelector(`[value="${key}"]`).disabled=!extra?.sources?.[key]?.seats;
}

function render(){
 sourceCards();if(source!=='bernama'&&!extra?.sources?.[source]?.seats)source='bernama';$('#source').value=source;$('#mode').disabled=source!=='bernama';
 const all=seats(),reported=all.filter(s=>s.candidates.some(c=>c.votes!==null)).length;
 $('#phase').textContent=reported?`${reported} / 28 seats reporting`:'AWAITING RESULTS';
 $('#updated').textContent='Source checked '+when(activeFeed().checkedAt);
 const stale=Date.now()-Date.parse(activeFeed().checkedAt)>15*60e3;
 $('#notice').textContent=(!activeFeed().ok?'Source refresh failed. Last valid snapshot retained. ':stale?'Snapshot is over 15 minutes old. The refresh workflow may not be running yet. ':'')+(reported?'Counts may be incomplete. A lead is not a declared victory.':'No vote totals reported in this feed. Charts will appear when counts are published.');
 const leads=Object.fromEntries(Object.keys(colours).map(p=>[p,all.filter(s=>leader(s)?.party===p).length]));
 $('#partyCards').innerHTML=Object.entries(colours).map(([p,c])=>`<div class="party-card" style="--colour:${c}"><b>${p}</b><strong>${leads[p]}</strong><small>seats leading</small></div>`).join('');
 $('#seatTrack').innerHTML=Object.keys(colours).flatMap(p=>Array.from({length:leads[p]},()=>`<i style="background:${colours[p]}" title="${p} leading"></i>`)).concat(Array.from({length:28-Object.values(leads).reduce((a,b)=>a+b,0)},()=>'<i title="No lead / tied"></i>')).join('');
 $('#seat').innerHTML=all.map(s=>`<option value="${s.code}">${s.code} · ${esc(s.name)}</option>`).join('');$('#seat').value=selected;
 $('#legend').innerHTML=Object.entries({...colours,'No lead / tied':grey}).map(([p,c])=>`<span><i class="dot" style="--colour:${c}"></i>${p}</span>`).join('');
 $('#grid').innerHTML=all.map(s=>`<button data-seat="${s.code}" style="--colour:${colours[leader(s)?.party]||grey}">${s.code}<br>${esc(s.name)}</button>`).join('');
 drawMap();detail();table();
}
function drawMap(){
 if(!geometry)return;
 const points=geometry.features.flatMap(f=>f.geometry.type==='Polygon'?f.geometry.coordinates.flat():f.geometry.coordinates.flat(2));
 const xs=points.map(p=>p[0]),ys=points.map(p=>p[1]),minX=Math.min(...xs),maxX=Math.max(...xs),minY=Math.min(...ys),maxY=Math.max(...ys),scale=Math.min(530/(maxX-minX),330/(maxY-minY));
 const project=p=>[35+(p[0]-minX)*scale,25+(maxY-p[1])*scale];
 const paths=geometry.features.map(f=>{const code=f.properties.code_dun,s=seats().find(s=>s.code===code);const rings=f.geometry.type==='Polygon'?f.geometry.coordinates:f.geometry.coordinates.flat();const d=rings.map(r=>r.map((p,i)=>(i?'L':'M')+project(p).map(v=>v.toFixed(2)).join(',')).join(' ')+'Z').join(' ');return `<path d="${d}" fill-rule="evenodd" fill="${colours[leader(s)?.party]||grey}" data-seat="${code}" class="${selected===code?'selected':''}" role="button" tabindex="0" aria-label="${code} ${esc(s.name)}"><title>${code} ${esc(s.name)} · ${leader(s)?.party||'Awaiting lead'}</title></path>`;}).join('');
 $('#map').innerHTML=`<svg viewBox="0 0 600 390" aria-label="Interactive Melaka DUN constituency map">${paths}<text x="28" y="370" style="font-size:12px;fill:#76879a">STRAIT OF MALACCA</text><text x="555" y="28" style="font-size:12px">N ↑</text></svg>`;
}
function detail(){const s=seats().find(s=>s.code===selected),sum=total(s),known=s.candidates.filter(c=>c.votes!==null).length;
 $('#seatName').textContent=s.name;$('#seatMeta').textContent=`${s.code} · ${fmt(s.registered)} registered voters · ${s.candidates.length} candidates`;
 $('#total').textContent=known?fmt(sum):'—';$('#countStatus').textContent=known?`${source==='spr'||(source==='awani'&&s.official)||(source==='bernama'&&mode==='official')?'Official':'Unofficial'} · ${source==='bernama'?'BERNAMA':source==='awani'?'Astro AWANI':'SPR'}`:'Awaiting results';
 let offset=0;const slices=sum?s.candidates.map(c=>{const pct=(c.votes||0)/sum*100;const el=`<circle cx="64" cy="64" r="48" fill="none" stroke="${colours[c.party]}" stroke-width="24" pathLength="100" stroke-dasharray="${pct} ${100-pct}" stroke-dashoffset="${-offset}" transform="rotate(-90 64 64)"/>`;offset+=pct;return el;}).join(''):'';
 $('#pie').innerHTML=`<svg viewBox="0 0 128 128" role="img" aria-label="${sum?'Vote share by candidate, values listed below':'No vote share data yet'}"><circle cx="64" cy="64" r="48" fill="none" stroke="#e8edf2" stroke-width="24"/>${slices}<text x="64" y="62" text-anchor="middle" fill="#132943" font-size="16" font-weight="bold">${sum?'100%':'—'}</text><text x="64" y="78" text-anchor="middle" fill="#617083" font-size="9">${sum?'REPORTED':'NO DATA'}</text></svg>`;
 $('#candidateCards').innerHTML=[...s.candidates].sort((a,b)=>(b.votes??-1)-(a.votes??-1)).map(c=>`<div class="candidate" style="--colour:${colours[c.party]}"><div class="candidate-top"><div class="candidate-name">${esc(c.name)}<small><i class="dot"></i>${c.party}</small></div><div class="num"><b>${fmt(c.votes)}</b><small>${sum&&c.votes!==null?(c.votes/sum*100).toFixed(1)+'%':'—'}</small></div></div><div class="bar"><span style="width:${sum?(c.votes||0)/sum*100:0}%"></span></div></div>`).join('');
 $('#chartNote').textContent=known<s.candidates.length&&known?'Partial candidate coverage: percentages include only published votes.':sum?'Vote share includes reported candidate votes only; excludes rejected ballots.':'Pie chart awaiting reported votes. No estimates or simulated counts are shown.';
}
function table(){let n=0;const q=$('#search').value.toLowerCase(),p=$('#partyFilter').value;$('#rows').innerHTML=seats().flatMap(s=>s.candidates.filter(c=>(!p||c.party===p)&&`${s.code} ${s.name} ${c.name} ${c.party}`.toLowerCase().includes(q)).map(c=>{n++;return `<tr><td><button data-seat="${s.code}">${s.code}<small>${esc(s.name)}</small></button></td><td>${esc(c.name)}</td><td><i class="dot" style="--colour:${colours[c.party]}"></i>${c.party}</td><td class="num">${fmt(c.votes)}</td><td class="num">${total(s)&&c.votes!==null?(c.votes/total(s)*100).toFixed(1)+'%':'—'}</td></tr>`;})).join('')||'<tr><td colspan="5">No candidates match your search.</td></tr>';$('#rowCount').textContent=`${n} candidates`;}
async function load(){if(loading)return;loading=true;$('#refresh').disabled=true;try{const r=await fetch('data/results.json?t='+Date.now(),{cache:'no-store'});if(!r.ok)throw Error();const next=await r.json();if(!next.modes||next.modes.unofficial.length!==28)throw Error();data=next;try{const h=await fetch('data/status.json?t='+Date.now(),{cache:'no-store'});health=h.ok?await h.json():{ok:false};}catch{health={ok:false};}try{const x=await fetch('data/sources.json?t='+Date.now(),{cache:'no-store'});if(!x.ok)throw Error();extra=await x.json();}catch{if(extra) for(const f of Object.values(extra.sources))f.ok=false;}render();}catch{$('#notice').textContent=data?'Cannot retrieve the latest snapshot. Showing the previous data.':'Unable to load election data. Serve this folder through GitHub Pages or a local HTTP server, then retry.';}finally{loading=false;$('#refresh').disabled=false;}}
$('#partyFilter').innerHTML+=Object.keys(colours).map(p=>`<option>${p}</option>`).join('');
$('#source').onchange=e=>{source=e.target.value;if(data)render();};
$('#mode').onchange=e=>{mode=e.target.value;if(data)render();};$('#seat').onchange=e=>{selected=e.target.value;detail();drawMap();};$('#refresh').onclick=load;$('#search').oninput=table;$('#partyFilter').onchange=table;
function choose(e){const el=e.target.closest('[data-seat]');if(!el||!data)return;selected=el.dataset.seat;$('#seat').value=selected;detail();drawMap();if(el.closest('table'))$('#explore').scrollIntoView({behavior:'smooth'});}
document.addEventListener('click',choose);document.addEventListener('keydown',e=>{if((e.key==='Enter'||e.key===' ')&&e.target.matches('path[data-seat]')){e.preventDefault();choose(e);}});
function view(grid){$('#grid').hidden=!grid;$('#map').hidden=grid;$('#mapButton').setAttribute('aria-pressed',!grid);$('#gridButton').setAttribute('aria-pressed',grid);}
$('#mapButton').onclick=()=>view(false);$('#gridButton').onclick=()=>view(true);
fetch('data/melaka.geojson').then(r=>{if(!r.ok)throw Error();return r.json();}).then(g=>{geometry=g;if(data)drawMap();}).catch(()=>{$('#map').innerHTML='<p>Map unavailable. Use the Seats view or constituency selector.</p>';});load();setInterval(load,60000);
