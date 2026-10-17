"use strict";
// Streamlit's documented component message protocol; no remote UI dependencies.
const app = document.getElementById("dashboard");
const PAGE_SIZE = 8;
let data = null, state = null, chartBars = [], lastHeight = 0;
const icons = {
  leaf:'<path d="M17 29C12 20 11 13 17 5M15 21C6 22 2 16 2 8c9 0 13 4 13 10M16 13C18 3 25 1 31 2c0 9-4 14-12 14M18 22l8-7"/>',
  users:'<circle cx="8" cy="5" r="2"/><circle cx="16" cy="7" r="2"/><path d="M3 14v-2a5 5 0 0 1 10 0v2M13 15h8v-2a5 5 0 0 0-5-4M4 18h8M6 16v5M10 16v5"/>',
  building:'<path d="M4 21V3h13v18M1 21h22M17 10h4v11M7 6h2M12 6h2M7 10h2M12 10h2M7 14h2M12 14h2M8 21v-4h5v4"/>',
  tree:'<path d="M12 6v5M4 17v-6h16v6"/><rect x="9" y="1" width="6" height="5" rx="1"/><rect x="1" y="17" width="6" height="5" rx="1"/><rect x="9" y="17" width="6" height="5" rx="1"/><rect x="17" y="17" width="6" height="5" rx="1"/><path d="M12 11v6"/>',
  file:'<path d="M5 2h9l5 5v15H5zM14 2v6h5M8 12h8M8 16h8M8 19h5"/>',
  chart:'<rect x="2" y="3" width="20" height="18" rx="2"/><path d="M6 16V9M10 18V6M14 15V8M18 13V5"/>',
  check:'<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M7 12l3 3 7-8"/>',
  flag:'<path d="M5 22V2M5 3c6-5 9 6 16 1v10c-7 5-10-6-16-1"/>',
  target:'<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><path d="M12 2v5M12 17v5M2 12h5M17 12h5"/>',
  bell:'<path d="M4 17h16l-2-3V9a6 6 0 0 0-12 0v5zM10 21h4M12 1v2"/>',
  pulse:'<path d="M1 12h5l3-8 5 16 3-8h6"/>',
  history:'<path d="M3 8a9 9 0 1 1-1 7M3 2v6h6M12 7v6l4 2"/>',
};
const icon = (name, cls="icon") => `<span class="${cls}" aria-hidden="true"><svg viewBox="0 0 ${name==="leaf"?34:24} ${name==="leaf"?34:24}" fill="none" stroke="currentColor" stroke-width="${name==="leaf"?2.6:1.9}" stroke-linecap="round" stroke-linejoin="round">${icons[name] || icons.file}</svg></span>`;
const esc = value => String(value ?? "—").replace(/[&<>"']/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch]));
const finite = value => typeof value === "number" && Number.isFinite(value);
const num = (value, digits=2) => finite(value) ? value.toLocaleString("en-US", {maximumFractionDigits:digits}) : "—";
const price = value => finite(value) ? value.toFixed(value<1?3:2) : "—";
const dateLabel = value => value && /^\d{4}-\d{2}-\d{2}/.test(value) ? new Date(value.slice(0,10)+"T12:00:00Z").toLocaleDateString("en-US",{month:"short",day:"numeric",year:"numeric",timeZone:"UTC"}) : esc(value || "—");
const badge = (label, type="unknown") => `<span class="badge ${esc(type)}">${esc(label)}</span>`;
const safeLink = (url, label) => {try{const u=new URL(url);return u.protocol==="https:"?`<a href="${esc(u.href)}" target="_blank" rel="noopener noreferrer">${esc(label)} ↗</a>`:esc(label);}catch{return esc(label);}};
const read = (key, fallback) => {try{return JSON.parse(localStorage.getItem(key)) ?? fallback;}catch{return fallback;}};
const write = (key, value) => {try{localStorage.setItem(key,JSON.stringify(value));return true;}catch{return false;}};
const sessionRead = key => {try{return JSON.parse(sessionStorage.getItem(key)) || {};}catch{return {};}};
const persist = () => {try{sessionStorage.setItem("gem_dashboard_"+data.stage,JSON.stringify(state));}catch{}};
function announce(message){document.getElementById("announcement").textContent=message;}
function send(action, fields={}){
  const nonce=Date.now().toString(36)+"-"+Math.random().toString(36).slice(2);
  window.parent.postMessage({isStreamlitMessage:true,type:"streamlit:setComponentValue",value:{action,...fields,nonce},dataType:"json"},"*");
}
function resize(){const height=Math.ceil(document.body.getBoundingClientRect().height)+3;if(height!==lastHeight){lastHeight=height;window.parent.postMessage({isStreamlitMessage:true,type:"streamlit:setFrameHeight",height},"*");}}
const card=(title,name,content,cls="",tools="")=>`<section class="card ${cls}"><header class="card-head">${icon(name)}<h2>${esc(title)}</h2>${tools?`<div class="card-tools">${tools}</div>`:""}</header><div class="card-body">${content}</div></section>`;
const empty=(title,description,small=false)=>`<div class="empty ${small?"table-empty":"empty-panel"}">${small?"":icon("users")}<strong>${esc(title)}</strong><span>${esc(description)}</span></div>`;
function table(headers,rows,cls="",widths=null){return `<table class="data-table ${cls}">${widths?`<colgroup>${widths.map(x=>`<col style="width:${x}%">`).join("")}</colgroup>`:""}<thead><tr>${headers.map(x=>`<th scope="col">${esc(x)}</th>`).join("")}</tr></thead><tbody>${rows.map(row=>`<tr>${row.map(cell=>`<td>${cell}</td>`).join("")}</tr>`).join("")}</tbody></table>`;}
function spark(bars){if(!bars || bars.length<2)return '<span class="muted">No EOD data</span>';const b=bars.slice(-60),lo=Math.min(...b.map(x=>x.close)),hi=Math.max(...b.map(x=>x.close)),span=hi-lo||1;return `<svg class="spark" viewBox="0 0 110 20" role="img" aria-label="Saved closing-price trend"><path class="spark-line" d="${b.map((x,i)=>(i?"L":"M")+(1+i*108/(b.length-1)).toFixed(1)+","+(18-(x.close-lo)*16/span).toFixed(1)).join(" ")}"/></svg>`;}

/* Priority controls reorder observations only; they never alter stage membership. */
const MARKET_CAP_MIN=300000000, MARKET_CAP_MAX=10000000000;

function priorityCriteria(){
  const entries={
    clinical:["Phase 3 clinical evidence","Exact drug / indication; GEM requires source-verified positive Phase 3"],
    endpoint:["Primary endpoint and p-value","Trial-matched numerical endpoint result where source-linked"],
    clinical_quality:["Clinical science quality","Saved science score; research only, not a proven clinical ranking"],
    safety:["Safety signals and adverse risks","Documented safety conflicts and saved safety score where available"],
    risk:["Overall clinical / financing risk factor","Current source-gated clinical and financing risk assessment"],
    finance1:["Financing #1 — SEC closing","First independent post-readout closing, or GEM JR research lead"],
    finance2:["Financing #2 — SEC closing","Second distinct post-readout close required for GEM, tracked in GEM JR"],
    dilution:["Share dilution and financing risk","Explicit saved dilution risk flags"],
    warrants:["Warrant exposure","SEC review notes mentioning warrants; outstanding amount not inferred"],
    convertibles:["Convertible debt / securities","SEC review notes mentioning convertibles, not an attested balance"],
    runway:["Cash runway in months","Independent SEC-based cash runway, preferably longer"],
    regulatory:["FDA regulatory history / risks","Recorded historical outcomes, regulatory gaps and saved assessment"],
    cmc:["Manufacturing and CMC readiness","Saved CMC score, not evidence of FDA clearance"],
    pdufa:["PDUFA timing / date verification","Source-verified FDA target date; nearest calendar date first"],
    cap:["Market cap $300M–$10B","In-range saved market capitalization ranked first"],
    liquidity:["Dollar-volume liquidity","20-day average daily dollar turnover from fresh saved price bars"],
    volume:["Relative trading volume (RVOL)","Saved relative volume, source freshness required"],
    short:["Short interest","Saved short-interest figure; smaller figures displayed first"],
    float:["Public float","Saved tradable share float; larger figures shown first"],
    institutional:["Institutional ownership","Saved institutional ownership figure; report not live holdings"],
    hedge:["Hedge-fund accumulation / 13F","Source-linked quarterly holdings if independently saved"],
    insider_buy:["Insider purchases","Saved Form 4 / insider acquisition evidence where available"],
    insider_sell:["Insider sales","Saved Form 4 / insider disposition evidence where available"],
    base:["Price-base formation","Observed daily-close base and support tests; not intraday proof"],
    breakout:["Base breakout / volume confirmation","Saved breakout-volume observation, not confirmed trade signal"],
    trend:["Price trend: SMA20 / SMA50","Fresh daily price and moving-average comparisons"],
    macd:["MACD momentum signal","Fresh saved bullish/bearish indicator, not a buy permission"],
    rsi:["RSI (14)","Fresh saved momentum value; descriptive and not a calibrated threshold"],
    relative_strength:["Relative strength vs sector","Needs matching sector benchmark; otherwise unavailable"],
    reward:["Reward-to-risk ratio","Calculated only from personal entry, stop and target reference levels"],
    plan:["Entry / stop / target plan","Complete saved reference plan, separate from trade execution"],
    poa:["Approval probability estimate","Saved uncalibrated probability; not a guarantee"],
    updates:["Documented catalyst / source updates","Dated source-linked observations, not an independent news scan"]
  };
  const jr=["clinical","endpoint","safety","risk","clinical_quality","finance1","finance2","dilution",
    "warrants","convertibles","runway","regulatory","cmc","pdufa","institutional","hedge",
    "insider_buy","insider_sell","cap","float","short","liquidity","volume","trend",
    "base","breakout","macd","rsi","relative_strength","poa","updates","reward","plan"];
  const gem=["clinical","endpoint","clinical_quality","finance1","finance2","safety","risk",
    "dilution","warrants","convertibles","runway","regulatory","cmc","pdufa","cap",
    "liquidity","float","short","institutional","hedge","insider_buy","insider_sell",
    "base","breakout","trend","volume","macd","rsi","relative_strength","reward",
    "plan","poa","updates"];
  const keys=data.junior?jr:gem;
  return keys.map(key=>[key,...entries[key]]);
}
function criterionEvidence(r,key){
  const missing=why=>({tier:0,metric:0,label:"Unavailable",detail:why||"This observation is missing or not source-verified"});
  const result=(tier,metric,label,detail)=>({tier,metric:Number.isFinite(metric)?metric:0,label,detail});
  const source=label=>r.sources?.find(s=>s.label===label);
  if(["clinical","finance1","finance2"].includes(key)){
    const label=key==="clinical"?"Phase 3 results":key==="finance1"?"Financing #1":"Financing #2";
    const s=source(label);
    if(!s?.url||!s?.date)return missing("Dated primary evidence missing; qualification is unchanged");
    const verified=!data.junior&&s.type==="pass";
    return result(verified?2:1,0,verified?"Verified source":"Dated source · review",
      verified?"Saved source under existing GEM qualification":"GEM JR lead under review; a linked document alone does not verify Phase 3 success or SEC closing");
  }
  if(key==="risk"){
    const factor=r.exit_checks?.find(x=>x.label==="Clinical / financing risk");
    const raw=String(factor?.points||"");
    if(!raw.endsWith("/20"))return missing("Current source-gated clinical/financing risk scoring unavailable");
    const points=Number(raw.slice(0,-3));
    if(!Number.isFinite(points)||points<0||points>20)return missing("Unknown risk factor");
    return result(1,-points,points===0?"No saved flag":"Observed risk: "+points+"/20",
      "Absence of a source flag does not establish safety; lower recorded risk points first");
  }
  if(key==="runway"){
    if(!Number.isFinite(r.runway))return missing("Independent SEC-based runway unavailable");
    return result(r.runway>=12?2:1,r.runway,r.runway.toFixed(1)+" months",
      "12 months is a reference for research only, not an additional eligibility gate");
  }
  if(key==="pdufa"){
    const stamp=Date.parse(String(r.pdufa||"").slice(0,10)+"T00:00:00Z");
    if(!r.pdufa_verified||!Number.isFinite(stamp))return missing("PDUFA date not independently source-confirmed");
    return result(2,-stamp/86400000,dateLabel(r.pdufa),
      "Earlier source-verified FDA decision date first; past and resolved outcomes still require separate exclusions");
  }
  if(key==="cap"){
    if(!Number.isFinite(r.market_cap))return missing("Saved market capitalization not recorded");
    const fit=r.market_cap>=300000000&&r.market_cap<=10000000000;
    return result(fit?2:1,0,fit?"In range (saved)":"Outside range (saved)",
      "$300M–$10B saved market-cap screen; this sort does not add an eligibility gate");
  }
  if(key==="volume"){
    if(!r.fresh||!Number.isFinite(r.rvol))return missing("Fresh source-saved relative volume missing");
    return result(1,r.rvol,r.rvol.toFixed(2)+"× RVOL",
      "Relative volume is not verified bid/ask execution liquidity");
  }
  if(key==="liquidity"){
    if(!r.fresh||!Number.isFinite(r.dollar_volume))return missing("Source-current 20-day dollar turnover unavailable");
    return result(1,r.dollar_volume,"$"+num(r.dollar_volume,0)+" / day",
      "Saved 20-day average dollar turnover; not actual quoted market depth");
  }
  if(key==="trend"){
    if(!r.fresh||![r.close,r.sma20,r.sma50].every(Number.isFinite))return missing("Fresh close, SMA20 and SMA50 required");
    const n=Number(r.close>=r.sma20)+Number(r.close>=r.sma50)+Number(r.sma20>=r.sma50);
    return result(1,n,n+"/3 EOD conditions",
      "Close≥SMA20; close≥SMA50; SMA20≥SMA50. No independently tested accuracy claim");
  }
  if(key==="macd"){
    if(!r.fresh||!["Bullish","Bearish"].includes(r.macd))return missing("Fresh saved MACD directional signal missing");
    return result(1,r.macd==="Bullish"?1:0,r.macd+" (saved)",
      "Saved MACD directional state; bullish is not a mandatory trading signal");
  }
  if(key==="rsi"){
    if(!r.fresh||!Number.isFinite(r.rsi))return missing("Fresh saved RSI 14 unavailable");
    return result(1,r.rsi,r.rsi.toFixed(1)+" RSI",
      "Higher recorded RSI first; overbought readings can increase risk");
  }
  if(key==="relative_strength")
    return missing("No corresponding sector benchmark in this exact-program dataset; cannot calculate relative strength from absolute return");
  if(key==="reward"){
    const p=getPlan(r);
    if(![p.entry,p.stop,p.target].every(Number.isFinite)||
      !(p.stop<p.entry&&p.entry<p.target))return missing("Enter valid entry, stop and target in chart reference levels first");
    const rr=(p.target-p.entry)/(p.entry-p.stop);
    return result(1,rr,rr.toFixed(2)+":1 planned",
      "Personal reference math only; planned reward-to-risk is not a forecast or executable fill");
  }
  if(key==="plan"){
    const p=getPlan(r);
    if(![p.entry,p.stop,p.target].every(Number.isFinite)||
      !(p.stop<p.entry&&p.entry<p.target))return missing("No complete locally saved entry/stop/target plan");
    return result(1,0,"Local plan · unverified",
      "Personal chart reference levels only, not current market or order authorization");
  }
  if(key==="updates"){
    const links=(r.alerts||[]).filter(x=>x.url&&x.date).length;
    if(!links)return missing("No dated source-linked observations in the saved program");
    return result(1,links,links+" sourced item"+(links===1?"":"s"),
      "Saved clinical/SEC/regulatory sources; not a comprehensive or real-time news scan");
  }
  const fact=r.criteria_facts?.[key];
  if(fact&&Number.isFinite(fact.tier)&&fact.tier>0){
    return result(fact.tier,fact.metric,fact.label||"Observed",
      fact.detail||"Saved source observation; no independent certainty claim");
  }
  return missing("No unambiguous, program-specific recorded evidence for this criterion");
}
function criterionName(){return priorityCriteria().find(x=>x[0]===state.focus)?.[1]||null;}
function matching(){let r=data.candidates.filter(x=>(state.status==="All Statuses"||x.status===state.status)&&(`${x.ticker} ${x.company} ${x.drug} ${x.indication} ${x.nct}`).toLowerCase().includes(state.search.toLowerCase()));if(state.focus){r=[...r].sort((a,b)=>{const x=criterionEvidence(a,state.focus),y=criterionEvidence(b,state.focus);return y.tier-x.tier||y.metric-x.metric||data.candidates.indexOf(a)-data.candidates.indexOf(b);});}else if(state.sort){r=[...r].sort((a,b)=>{let x=a[state.sort],y=b[state.sort];if(x==null)return y==null?0:1;if(y==null)return -1;return (typeof x==="number"?x-y:String(x).localeCompare(String(y)))*(state.desc?-1:1);});}return r;}
function candidateCard(rows){
  state.page=Math.min(Math.max(0,state.page),Math.max(0,Math.ceil(rows.length/PAGE_SIZE)-1));
  const paged=rows.slice(state.page*PAGE_SIZE,(state.page+1)*PAGE_SIZE);
  const labels=[["#",null],["Criterion evidence",null],["Ticker","ticker"],["Company","company"],["Indication","indication"],["Phase",null],["P3 Readout","readout"],["PDUFA","pdufa"],["Financing Status",null],["Cash Runway",null],["Market Cap","market_cap"],["PoA",null],["Short Int.",null],["Entry Score","entry"],["Exit Risk","exit_risk"],["Status","status"],["Trend (saved)",null],["W",null],["T",null],["Details",null]];
  const head=labels.map(([label,key])=>`<th scope="col"${key?` aria-sort="${state.sort===key?(state.desc?"descending":"ascending"):"none"}"`:""}>${key?`<button class="sort" data-action="sort" data-key="${key}" style="border:0;background:none;padding:0;font:inherit;font-weight:700" title="Sort by ${esc(label)}">${esc(label)}${state.sort===key?(state.desc?" ▾":" ▴"):""}</button>`:esc(label)}</th>`).join("");
  const body=paged.map((r,i)=>`<tr class="${r.id===state.selected?"selected":""}" data-program="${esc(r.id)}"><td class="number">${state.page*PAGE_SIZE+i+1}</td><td title="${esc(state.focus?criterionEvidence(r,state.focus).detail:"Choose a criterion to reorder the candidates")}">${state.focus?esc(criterionEvidence(r,state.focus).label):'<span class="muted">Original order</span>'}</td><td><button class="ticker" data-action="select" data-id="${esc(r.id)}">${esc(r.ticker)}</button></td><td title="${esc(r.company)}">${esc(r.company)}</td><td title="${esc(r.drug+" · "+r.indication)}">${esc(r.indication)}</td><td class="number">P3</td><td title="${esc(r.readout)}">${dateLabel(r.readout)}</td><td title="${esc(r.pdufa_verified?"Source-verified target":"Saved target; verify source")}">${dateLabel(r.pdufa)}${r.pdufa&&!r.pdufa_verified?" *":""}</td><td title="${esc(r.financing_detail)}">${esc(r.financing_label)}</td><td class="number" title="${esc(r.runway_reason)}">${r.runway==null?"—":num(r.runway,1)+" mo"}</td><td class="number">${esc(r.market_cap_display)}</td><td class="number" title="Saved model estimate; not a forecast guarantee">${esc(r.poa_display)}</td><td class="number">${esc(r.short_display)}</td><td class="number" title="${esc(r.entry_status)}">${num(r.entry,0)}</td><td class="number" title="${esc(r.exit_status)}">${num(r.exit_risk,0)}</td><td title="${esc(r.trade_status)}">${badge(r.status,r.status_type)}</td><td>${spark(r.bars)}</td><td class="number"><button class="wt" data-action="watch" data-id="${esc(r.id)}" aria-label="Watch ${esc(r.ticker)}" aria-pressed="${data.watch.includes(r.ticker)}">W</button></td><td class="number"><button class="wt" data-action="trade" data-id="${esc(r.id)}" aria-label="Trade workspace for ${esc(r.ticker)}" aria-pressed="${data.trade.includes(r.ticker)}" title="Open existing WT research workspace">T</button></td><td class="number"><button class="details" data-action="select" data-id="${esc(r.id)}" aria-label="Details for ${esc(r.ticker)} ${esc(r.drug)}">Details</button></td></tr>`).join("");
  const statuses=["All Statuses",...new Set(data.candidates.map(r=>r.status))];
  const tools=`<span class="header-count">${rows.length} candidate${rows.length===1?"":"s"}</span><input type="search" id="candidate-search" aria-label="Search candidates" placeholder="Search ticker or company…" value="${esc(state.search)}"><select id="status-filter" aria-label="Filter by status">${statuses.map(s=>`<option${s===state.status?" selected":""}>${esc(s)}</option>`).join("")}</select>`;
  const grid=`<div class="candidate-wrap scroll"><table class="data-table candidate-table"><colgroup>${[1.6,9,3.6,9,10,2.8,6,6,9,4.7,5,3,3.8,4.3,4.3,7.2,7,2.4,2.4,4.9].map(w=>`<col style="width:${w}%">`).join("")}</colgroup><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>`;
  return card(data.stage+" Candidates","users",grid+(!rows.length?empty(data.candidates.length?"No matching candidates":"No active "+data.stage+" candidates",data.candidates.length?"Change the search or status filter to see available programs.":"The current source snapshot has no programs meeting this stage’s criteria.",true):"")+`<div class="toolbar-footer"><span>Ordering: ${esc(criterionName()|| (state.sort?"Column "+state.sort:"original stage priority"))} · Unverified ranked last · * PDUFA unverified</span><div class="pagination"><button data-action="export" title="Export every matching candidate">Export CSV</button><button data-action="prev" ${state.page===0?"disabled":""} aria-label="Previous candidate page">‹</button><span>${rows.length?state.page+1:0} / ${Math.ceil(rows.length/PAGE_SIZE)}</span><button data-action="next" ${((state.page+1)*PAGE_SIZE>=rows.length)?"disabled":""} aria-label="Next candidate page">›</button></div></div>`,"candidates",tools);
}

function reviewNavigator(rows,r){
  const position=r?rows.findIndex(item=>item.id===r.id):-1;
  const more=state.sort||state.focus?"← Previous in sorted list":"← Higher priority";
  const less=state.sort||state.focus?"Next in sorted list →":"Lower priority →";
  const options=rows.map((item,i)=>'<option value="'+esc(item.id)+'"'+(item.id===state.selected?' selected':'')+'>'+esc((i+1)+'. '+item.ticker+' — '+item.drug+' · '+item.nct)+'</option>').join("");
  const details=r?esc(r.ticker+' · '+r.drug+' · '+r.indication+' · '+r.nct):"No matching candidate";
  const descriptor=state.sort||state.focus?"Position in current sorted results":"Position in source-prioritized results";
  return '<section id="candidate-review" class="review-nav" aria-label="'+esc(data.stage)+' prioritized candidate navigation">'+
    '<div class="review-summary"><strong>'+details+'</strong><span>'+esc(descriptor)+': '+(position<0?'0':position+1)+' / '+rows.length+'</span></div>'+
    '<div class="review-controls">'+
    '<button data-action="step-candidate" data-step="-1" aria-label="'+esc(more)+'" '+(position<=0?'disabled':'')+'>'+esc(more)+'</button>'+
    '<label for="candidate-jump" class="review-picker-label">Pick any candidate</label>'+
    '<select id="candidate-jump" aria-label="Choose exact ticker drug and trial" '+(rows.length?'':'disabled')+'>'+options+'</select>'+
    '<button data-action="step-candidate" data-step="1" aria-label="'+esc(less)+'" '+(position<0||position>=rows.length-1?'disabled':'')+'>'+esc(less)+'</button>'+
    '<button class="blue" data-action="open-details" '+(r?'':'disabled')+'>Inspect details ↓</button>'+
    '<button class="blue" data-action="open-chart" '+(r?'':'disabled')+'>Enlarge price chart ↗</button></div>'+
    '<p class="review-note">Arrows move one program at a time in the displayed order. The selected company, clinical trial, sources, checklists and price chart update together. Missing market data remain unavailable.</p></section>';
}
function chooseCandidate(id,mode="details"){
  const rows=matching(),index=rows.findIndex(item=>item.id===id);
  if(index<0)return;
  state.selected=id;state.page=Math.floor(index/PAGE_SIZE);
  if(mode==="details"&&!data.junior)state.rulesTab="trials";
  state.chartFocus=mode==="chart";
  render();
  requestAnimationFrame(()=>{
    if(mode==="chart")app.querySelector(".focused-chart .chart-close")?.focus();
    else document.getElementById("candidate-review")?.scrollIntoView({block:"start",behavior:"smooth"});
  });
  announce("Selected "+rows[index].ticker+" — "+rows[index].drug+". "+(mode==="chart"?"Price chart enlarged.":"Detailed trial profile ready."));
}
function companyTrialSection(r){
  const all=Array.isArray(r.company_trials)?r.company_trials:[];
  const query=(state.companyTrialSearch||"").trim().toLowerCase();
  const filtered=all.filter(t=>!query||`${t.nct} ${t.drug} ${t.indication} ${t.phase} ${(t.stage_labels||[]).join(" ")}`.toLowerCase().includes(query));
  const pageSize=20;
  const lastPage=Math.max(0,Math.ceil(filtered.length/pageSize)-1);
  state.companyTrialPage=Math.min(Math.max(0,state.companyTrialPage||0),lastPage);
  const shown=filtered.slice(state.companyTrialPage*pageSize,(state.companyTrialPage+1)*pageSize);
  const rows=shown.map(t=>{
    const selected=String(r.nct||"").includes(t.nct);
    const markers=(t.stage_labels||[]).map(stage=>`<span class="trial-stage-tag ${stage==="GEM"?"gem":"junior"}">${esc(stage)}</span>`).join("");
    const stage=markers||'<span class="muted">Not a current candidate</span>';
    const trialLink=safeLink(t.url,t.nct);
    return `<tr class="${selected?"company-trial-current":""}"><td class="wrap"><strong>${esc(t.drug)}</strong><div class="trial-muted">${esc(t.indication)}</div></td><td class="wrap">${esc(t.phase)}</td><td>${trialLink}</td><td class="wrap">${stage}</td></tr>`;
  });
  const meta=`<div class="company-trial-header"><h3>Company Trials — All Saved Phases</h3><span>${all.length} trial${all.length===1?"":"s"} recorded</span></div>`;
  const controls=`<div class="company-trial-controls"><label for="company-trial-search">Find a trial</label><input type="search" id="company-trial-search" aria-label="Search ${esc(r.ticker)} trials by phase drug or NCT" placeholder="Drug, NCT, phase, GEM…" value="${esc(state.companyTrialSearch||"")}"><span>${filtered.length} matching</span></div>`;
  const listing=all.length?`<div class="company-trial-scroll scroll"><table class="data-table company-trial-table"><colgroup><col style="width:37%"><col style="width:21%"><col style="width:19%"><col style="width:23%"></colgroup><thead><tr><th scope="col">Drug / indication</th><th scope="col">Phase</th><th scope="col">Trial ↗</th><th scope="col">Candidate status</th></tr></thead><tbody>${rows.join("")}</tbody></table>${!filtered.length?empty("No matching saved trials","Change the trial search to show available records.",true):""}</div>`:
   empty("No trials in saved inventory","An unavailable or incomplete trial inventory is not proof that this company has no other studies.",true);
  const paging=filtered.length?`<div class="company-trial-pagination"><span>Showing ${state.companyTrialPage*pageSize+1}–${Math.min(filtered.length,(state.companyTrialPage+1)*pageSize)} of ${filtered.length}</span><button data-action="company-trial-prev" ${state.companyTrialPage<=0?"disabled":""} aria-label="Previous company trials page">← Earlier</button><button data-action="company-trial-next" ${state.companyTrialPage>=lastPage?"disabled":""} aria-label="Next company trials page">More →</button></div>`:"";
  const coverage=`<p class="company-trial-coverage">${esc(r.company_trial_coverage||"Trial source coverage unverified.")} Candidate labels use exact ticker + NCT associations; the links go to ClinicalTrials.gov, not independent sponsor verification.</p>`;
  return '<section class="company-trial-list" aria-label="All saved trials and GEM stage status for '+esc(r.company)+'">'+meta+controls+listing+paging+coverage+'</section>';
}
function profileCard(r){
  if(!r)return card("Selected Company","building",empty("No selected program","Select a candidate to view its source-linked profile."));
  if(state.companyTrialTicker!==r.ticker){state.companyTrialTicker=r.ticker;state.companyTrialSearch="";state.companyTrialPage=0;}
  const facts='<table class="data-table key-values"><tbody>'+r.profile.map(([key,val])=>'<tr><td class="label-cell">'+esc(key)+'</td><td title="'+esc(val)+'">'+esc(val)+'</td></tr>').join('')+'<tr><td class="label-cell">Current Status</td><td>'+badge(r.status,r.status_type)+'</td></tr></tbody></table>';
  return card("Selected Company","building",facts+companyTrialSection(r),"profile",badge(r.status,r.status_type));
}
function hierarchy(r){if(!r)return empty("No trial selected","Company → Drug / Indication → Trial. Each program retains its own evidence.");return `<div class="tree tree-body"><details open data-tree="company"><summary>Level 1 · ${esc(r.company)} (${esc(r.ticker)})</summary>${r.hierarchy.map((group,gi)=>`<details ${group.selected?"open":""} data-tree="drug-${gi}"><summary>Level 2 · ${esc(group.drug)} — ${esc(group.indication)}</summary>${group.trials.map(t=>`<details ${t.selected?"open":""} data-tree="trial-${esc(t.nct)}"><summary>Level 3 · ${esc(t.nct)} — ${esc(t.phase)}</summary><div class="trial-detail">${table(["Trial ID","Primary endpoint","p-value","Result / status"],[[safeLink(t.url,t.nct),esc(t.endpoint),esc(t.p_value),badge(t.result,t.result_type)]])}<div class="source-note">Readout: ${dateLabel(t.readout)} · Patients / sites: ${esc(t.patients || "Not available in saved feed")}</div>${t.note?`<div class="callout ${t.result_type==="pass"?"":"warning"}"><span class="status-icon">${t.result_type==="pass"?"✓":"!"}</span><span>${esc(t.note)}</span></div>`:""}</div></details>`).join("")}</details>`).join("")}</details></div>`;}
function clinicalCard(r){return card("Trial Structure (3-Level View)","tree",hierarchy(r),"clinical");}
function rulesCard(r){const rules=data.rules.map(x=>`<li>${esc(x)}</li>`).join("");return card("GEM Qualification Rules","file",`<div class="mini-tabs" role="tablist" aria-label="Qualification and trials"><button role="tab" aria-selected="${state.rulesTab!=="trials"}" class="${state.rulesTab!=="trials"?"active":""}" data-action="rules-tab" data-tab="rules">Qualification rules</button><button role="tab" aria-selected="${state.rulesTab==="trials"}" class="${state.rulesTab==="trials"?"active":""}" data-action="rules-tab" data-tab="trials">Trial structure · 3 levels</button></div>${state.rulesTab==="trials"?hierarchy(r):`<ol class="rules">${rules}</ol><div class="callout warning"><span class="status-icon">!</span><span><strong>Qualification ≠ automatic BUY.</strong> Valuation, technicals, runway, dilution and current sources still require review.</span></div>`}`,"qualification");}
function financeCard(r,junior){
  if(!r)return card(junior?"Financing Verification / Source Check":"Two-Financing Verification","target",empty("No financing selected","Dated clinical and SEC evidence appears when a program is selected."),"financing");
  const sourceRows=r.sources.map(s=>[esc(s.label),safeLink(s.url,s.reference),dateLabel(s.date),badge(s.status,s.type)]);
  let body;
  if(junior||state.financeTab==="sources")body=table(["Source / item","Filing / reference","Date","Status"],sourceRows,"source-table",[25,38,17,20]);
  else body=table(["#","Date","Amount","Price / share","Warrants","SEC Filing","Status"],r.financings.map((f,i)=>[i+1,dateLabel(f.date),esc(f.amount),esc(f.price),esc(f.warrants),safeLink(f.url,"SEC filing"),badge(f.status,f.type)]),"finance-table",[5,16,13,14,16,16,20])+`<div class="callout"><span class="status-icon">✓</span><span>Two distinct post-readout financing closures. Each close is tied to its own saved SEC evidence.</span></div><div class="source-note">${esc(r.financing_detail)}</div>`;
  const tabs=junior?"":`<div class="mini-tabs" role="tablist" aria-label="Financing evidence"><button role="tab" aria-selected="${state.financeTab!=="sources"}" class="${state.financeTab!=="sources"?"active":""}" data-action="finance-tab" data-tab="financing">Two financings</button><button role="tab" aria-selected="${state.financeTab==="sources"}" class="${state.financeTab==="sources"?"active":""}" data-action="finance-tab" data-tab="sources">Source check</button></div>`;
  return card(junior?"Financing Verification / Source Check":"Two-Financing Verification ("+r.ticker+")","target",tabs+`<div class="finance-scroll">${body}</div><div class="source-actions"><span>Source review: ${dateLabel(r.source_review)}</span><button data-action="refresh" title="Reload saved source records; run live collectors in SCANS">↻ Refresh sources</button></div>`,"financing");
}
function checklist(r,kind){const entry=kind==="entry",name=entry?"Entry Checklist":"Exit Checklist",value=r?.[entry?"entry":"exit_risk"],checks=r?.[entry?"entry_checks":"exit_checks"]||data.empty_checks[kind];return card(name+" ("+data.stage+")",entry?"check":"flag",table(["#","Criterion",entry?"Details / threshold":"Trigger / condition","Status","Points"],checks.map((x,i)=>[i+1,esc(x.label),`<span title="${esc(x.detail)}">${esc(x.detail)}</span>`,`<span class="${x.status===true?(entry?"check-mark":"check-fail"):x.status===false?(entry?"check-fail":"check-mark"):"check-unknown"}" title="${x.status===true?(entry?"Evidence observed":"Risk condition observed"):x.status===false?"Condition not met":"Unknown / unverified"}">${x.status===true?"☑":x.status===false?"✕":"—"}</span>`,esc(x.points)]))+`<div class="coverage">${esc(r?.[entry?"entry_status":"exit_status"]||"Source coverage unavailable")} · Coverage ${r?.[entry?"entry_coverage":"exit_coverage"]||0}/100. ${entry?"Provisional readiness":"Higher exit risk means more risk"}.</div>`,"checklist",`<span class="score-badge ${value==null?"unavailable":""}">${entry?"Total score":"Risk"}: ${value==null?"N/A":num(value,0)} / 100</span>`);}
function getPlan(r){return r?read("gem_chart_plan_"+r.id,{}):{};}
function signals(r,compact=false){const plan=getPlan(r);const rows=r?[["MACD",r.macd],["RVOL",r.rvol==null?"—":num(r.rvol)+"×"],["RSI (14)",num(r.rsi)],["SMA20",price(r.sma20)],["SMA50",price(r.sma50)],["Closing support",price(r.support)],["Closing resistance",price(r.resistance)],["Entry (plan)",price(plan.entry)],["Stop (plan)",price(plan.stop)],["Target (plan)",price(plan.target)],["Base status",r.base_status]]:[["MACD","—"],["RVOL","—"],["RSI (14)","—"],["Closing support","—"],["Closing resistance","—"],["Entry / stop / target","—"]];return `<table class="data-table ${compact?"":"signal-table"}"><tbody>${rows.map(([k,v])=>`<tr><td>${esc(k)}</td><td title="${esc(v)}">${esc(v)}</td></tr>`).join("")}</tbody></table>`;}
function signalCard(r){return card("Key Signals"+(r?" ("+r.ticker+")":""),"check",signals(r)+`<p class="coverage">ATR / VWAP require OHLC / intraday data.</p>`,"signals");}
function chartCard(r,junior){const ranges=["1M","3M","6M","1Y","ALL"].map(x=>`<button data-action="range" data-range="${x}" class="${state.range===x?"active":""}" aria-pressed="${state.range===x}">${x}</button>`).join("");return card((r?r.ticker+" — ":"")+state.range+" Trading Chart","chart",r?`<div class="chart-layout"><div class="chart-main"><div class="chart-subtitle"><strong>${esc(r.ticker)}</strong><span class="price">Close ${price(r.close)}</span><span class="pill-note">${r.fresh?"Saved EOD":"Saved EOD · stale / unverified"} · ${dateLabel(r.market_date)}</span></div><div class="chart-legend"><span style="--line:#05ab68">Close</span><span style="--line:#1673eb">SMA20 ${price(r.sma20)}</span><span style="--line:#f49429">SMA50 ${price(r.sma50)}</span></div><div class="chart-canvas" id="price-chart">${state.chartMode==="tv"?'<div id="tv-widget" style="height:100%"></div>':""}</div><div class="chart-caption"><span>${state.chartMode==="tv"?"External TradingView · may be delayed":r.bars.length+" saved sessions · closes and volume only"}</span><span><button data-action="chart-mode">${state.chartMode==="tv"?"Saved EOD":"Candles"}</button> <button data-action="plan">Reference levels</button> ${safeLink("https://www.tradingview.com/chart/?symbol="+encodeURIComponent(r.ticker),"Open chart")}</span></div></div>${junior?`<aside class="chart-signals"><h3>Key Signals</h3>${signals(r,true)}</aside>`:""}</div>`:empty("No chart selected","Select an active candidate to load its saved price history or external candlesticks."),"chart"+(state.chartFocus?" focused-chart":""),ranges+(state.chartFocus?'<button class="chart-close" data-action="close-chart" aria-label="Close enlarged chart">✕ Close</button>':""));}
function drawPriceChart(r){
  const host=document.getElementById("price-chart");if(!host||!r)return;
  if(state.chartMode==="tv"){
    const widget=document.getElementById("tv-widget");if(!widget)return;
    const frame=document.createElement("div");frame.className="tradingview-widget-container__widget";frame.style.height="100%";widget.append(frame);
    const script=document.createElement("script");script.src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js";script.async=true;
    script.textContent=JSON.stringify({autosize:true,symbol:r.ticker,interval:"D",range:state.range==="ALL"?"ALL":state.range,timezone:"America/Los_Angeles",theme:"light",style:"1",locale:"en",enable_publishing:false,hide_top_toolbar:false,allow_symbol_change:false,save_image:false,studies:["MASimple@tv-basicstudies"],support_host:"https://www.tradingview.com"});widget.append(script);return;
  }
  if(!r.bars.length){host.innerHTML=empty("Saved EOD data unavailable","Use Candles to open the external chart. Missing prices are not simulated.");return;}
  const ranges={"1M":31,"3M":93,"6M":186,"1Y":366,"ALL":Infinity};
  const last=Date.parse(r.bars.at(-1).date),cut=last-ranges[state.range]*864e5;
  chartBars=r.bars.map((b,i)=>({...b,sma20:i>=19?r.bars.slice(i-19,i+1).reduce((a,x)=>a+x.close,0)/20:null,sma50:i>=49?r.bars.slice(i-49,i+1).reduce((a,x)=>a+x.close,0)/50:null})).filter(b=>Date.parse(b.date)>=cut);
  const p=getPlan(r),levels=[["Closing support",r.support,"#7f95a5"],["Closing resistance",r.resistance,"#3184cb"],["Entry (plan)",p.entry,"#7750bd"],["Stop (plan)",p.stop,"#f04b47"],["Target (plan)",p.target,"#00a84f"]].filter(x=>finite(x[1]));
  const vals=[...chartBars.flatMap(b=>[b.close,b.sma20,b.sma50].filter(finite)),...levels.map(x=>x[1])];
  const lo=Math.min(...vals),hi=Math.max(...vals),pad=(hi-lo)*.12||hi*.1||1,min=lo-pad,max=hi+pad;
  const W=640,H=235,left=36,right=85,top=8,base=175,volTop=184,volBottom=216,plotWidth=W-left-right;
  const x=i=>left+(chartBars.length>1?i/(chartBars.length-1):.5)*plotWidth,y=v=>top+(max-v)/(max-min)*(base-top);
  let svg=`<svg viewBox="0 0 ${W} ${H}" class="price-chart" role="img" aria-label="${esc(r.ticker)} source-saved closing prices and daily volume"><defs><linearGradient id="area-fill" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#00b975" stop-opacity=".10"/><stop offset="1" stop-color="#00b975" stop-opacity="0"/></linearGradient><clipPath id="plot-clip"><rect x="${left}" y="${top}" width="${plotWidth}" height="${base-top}"/></clipPath></defs>`;
  for(let i=0;i<5;i++){const py=top+i*(base-top)/4,v=max-i*(max-min)/4;svg+=`<line class="chart-grid" x1="${left}" x2="${W-right}" y1="${py}" y2="${py}"/><text class="chart-axis" x="${left-5}" y="${py+3}" text-anchor="end">${price(v)}</text>`;}
  const ticks=Math.min(6,chartBars.length);for(let k=0;k<ticks;k++){const i=Math.round(k*(chartBars.length-1)/Math.max(1,ticks-1)),b=chartBars[i];svg+=`<line class="chart-grid" x1="${x(i)}" x2="${x(i)}" y1="${top}" y2="${volBottom}"/><text class="chart-axis" x="${x(i)}" y="231" text-anchor="middle">${new Date(b.date+"T12:00:00Z").toLocaleDateString("en-US",{month:"short",day:"numeric",timeZone:"UTC"})}</text>`;}
  const path=(key)=>chartBars.map((b,i)=>finite(b[key])?`${i>0&&finite(chartBars[i-1][key])?"L":"M"}${x(i).toFixed(2)},${y(b[key]).toFixed(2)}`:"").join(" ");
  if(chartBars.length>1)svg+=`<path d="${path("close")} L${x(chartBars.length-1)},${base} L${x(0)},${base} Z" fill="url(#area-fill)" clip-path="url(#plot-clip)"/>`;
  for(const [key,color] of [["close","#02a65b"],["sma20","#1d78ec"],["sma50","#ed982d"]])svg+=`<path d="${path(key)}" fill="none" stroke="${color}" stroke-width="${key==="close"?1.8:1.2}" clip-path="url(#plot-clip)"/>`;
  if(chartBars.length===1)svg+=`<circle cx="${x(0)}" cy="${y(chartBars[0].close)}" r="3" fill="#00a65c"/>`;
  let previous=-100;for(const [label,v,color] of [...levels].sort((a,b)=>b[1]-a[1])){const py=y(v),labelY=Math.max(py,previous+13);previous=labelY;svg+=`<line x1="${left}" x2="${W-right+3}" y1="${py}" y2="${py}" stroke="${color}" stroke-dasharray="4 3"/><rect x="${W-right+4}" y="${labelY-6}" width="79" height="12" rx="2" fill="${color}"/><text x="${W-right+7}" y="${labelY+2}" font-size="8" fill="white">${esc(label.replace("Closing ",""))} ${price(v)}</text>`;}
  const maxVol=Math.max(...chartBars.map(b=>b.volume),1),barWidth=Math.min(9,plotWidth/Math.max(chartBars.length,1)*.66);chartBars.forEach((b,i)=>{const h=b.volume/maxVol*(volBottom-volTop);svg+=`<rect x="${x(i)-barWidth/2}" y="${volBottom-h}" width="${barWidth}" height="${h}" fill="${i&&b.close<chartBars[i-1].close?"#ef8d88":"#42c68b"}"/>`;});
  svg+=`<text class="chart-axis" x="${left+3}" y="${volTop+7}">Volume ${num(chartBars.at(-1).volume,0)}</text><line class="chart-crosshair" id="crosshair" x1="0" x2="0" y1="${top}" y2="${volBottom}" visibility="hidden"/><rect id="chart-hit" x="${left}" y="${top}" width="${plotWidth}" height="${volBottom-top}" fill="transparent"/></svg><div class="price-tooltip" hidden></div>`;
  host.innerHTML=svg;
  const hit=host.querySelector("#chart-hit"),tooltip=host.querySelector(".price-tooltip"),cross=host.querySelector("#crosshair");
  hit.addEventListener("pointermove",ev=>{const box=host.querySelector("svg").getBoundingClientRect(),sx=(ev.clientX-box.left)/box.width*W,i=Math.max(0,Math.min(chartBars.length-1,Math.round((sx-left)/plotWidth*(chartBars.length-1)))),b=chartBars[i];cross.setAttribute("x1",x(i));cross.setAttribute("x2",x(i));cross.setAttribute("visibility","visible");tooltip.hidden=false;tooltip.innerHTML=`${dateLabel(b.date)}<br><strong>Close $${price(b.close)}</strong><br>Volume ${num(b.volume,0)}`;tooltip.style.left=Math.min(host.clientWidth-135,Math.max(0,ev.clientX-box.left+9))+"px";tooltip.style.top="12px";});
  hit.addEventListener("pointerleave",()=>{tooltip.hidden=true;cross.setAttribute("visibility","hidden");});
}
function historyCard(){const rows=data.history;return card(data.junior?"Promotion History (GEM JR → GEM)":"Promotion / History / Exited Candidates","history",rows.length?table(["Date","Ticker","Drug / program","Movement / reason"],rows.map(r=>[dateLabel(r.date),esc(r.ticker),esc(r.drug),esc(r.reason)])): '<div class="history-empty">No scan-observed departures recorded in the saved stage ledger.<br>Discovery and departure dates are retained only when actually observed.</div>',"history");}
function alertsCard(r){const rows=r?r.alerts:data.alerts;return card(data.junior?"Alerts / Watchlist":"Alerts / Watchlist / Trade","bell",rows.length?table(["Date","Ticker","Event","Details"],rows.map(x=>[dateLabel(x.date),esc(x.ticker),esc(x.type),`<span title="${esc(x.detail)}">${x.url?safeLink(x.url,x.detail):esc(x.detail)}</span>`])):'<div class="history-empty">No source-linked alerts for this selection. Review published scans for updates.</div>',"alerts",`<button class="scan-open" data-action="navigate" data-tab="WT">Open W / T</button>`);}
function scansCard(){return card("Scan Diagnostics","pulse",table(["Scan Type","Last Update","Status"],data.scans.map(s=>[esc(s.label),`<span title="${esc(s.date)}">${dateLabel(s.date)}</span>`,badge(s.status,s.type)]))+`<div class="source-note">10 PM Pacific sequential schedule · ${esc(data.scan_note)}</div>`,"diagnostics",'<button class="scan-open" data-action="navigate" data-tab="SCANS">Open scans</button>');}
function policyCard(){const value=state.policy;return card("Hard Stop / PDUFA Exit Policy","flag",`<p>${value==="unresolved"?"Policy decision required:":"Selected research policy:"}</p><div class="policy-options">${[["pre","Exit before PDUFA (reduce event risk)"],["partial","Hold a partial position through PDUFA"],["hold","Hold the full position through PDUFA"]].map(([id,label])=>`<label><input type="radio" name="exit-policy" value="${id}"${value===id?" checked":""}>${esc(label)}</label>`).join("")}</div><div class="callout warning"><span>! ${value==="unresolved"?"Unresolved. Define a consistent exit policy.":"Saved as a research preference. Apply manually with your position and risk plan."}</span></div>`,"policy-card");}
function criteriaCard(){
  const list=priorityCriteria().map((item,index)=>{
    const [key,title,hint]=item,active=state.focus===key;
    return '<li><button class="criterion-button'+(active?' active':'')+'" data-action="criterion" data-criterion="'+esc(key)+'" aria-pressed="'+active+'" title="'+esc(hint)+'"><span class="criterion-rank">'+(index+1)+'</span><span class="criterion-content"><strong>'+esc(title)+'</strong><small>'+esc(hint)+'</small></span><span class="criterion-effect">'+(active?'Selected ✓':'Rank ↓')+'</span></button></li>';
  }).join("");
  const active=criterionName();
  return card("Ranked Criteria ("+data.stage+")","check",
    '<div class="criteria-intro"><strong>1 = highest importance.</strong> Click a criterion to reorder '+esc(data.stage)+' candidates by recorded evidence, without changing stage membership.</div>'+
    '<ol class="criteria-list scroll" aria-label="Scroll through all criterion ranking controls">'+list+'</ol>'+
    '<div class="criteria-focus">'+(active?'Active: <strong>'+esc(active)+'</strong> · observed first, unknown last.':'Original source-qualified priority order')+'</div>'+
    '<div class="criteria-reset"><button data-action="criteria-reset" '+(active?'':'disabled')+'>↺ Restore original order</button></div>'+
    '<div class="criteria-foot">Current candidates: <strong>'+data.candidates.length+'</strong> · Held for review: <strong>'+data.held_count+'</strong><br>Sort priority is advisory. Source qualification, missing-data holds and trading restrictions never change.</div>',
    "criteria-card");
}
function stageSummary(){
  const label=data.junior?"Earlier Setups — Post Phase 3 / Pre-PDUFA":"Higher Conviction — Near PDUFA";
  return '<div class="stage-banner '+(data.junior?"junior":"senior")+'"><strong>'+esc(data.stage)+'</strong><span>'+esc(label)+'</span><span class="stage-tally">Candidates: '+data.candidates.length+'</span><span class="stage-health">'+(data.source_current?"Saved source status current":"Source review required")+'</span></div>';
}
function render(focusSearch=false,focusTrialSearch=false){if(!data)return;const rows=matching();if(!rows.some(r=>r.id===state.selected))state.selected=rows[0]?.id||null;const r=rows.find(x=>x.id===state.selected)||null;if(!r)state.chartFocus=false;
  const intro=data.junior?"Earlier Setups (Post Phase 3 / Pre-PDUFA)":"Higher Conviction (Near PDUFA)";
  const subtitle=data.junior?"Earlier setups with more time to develop. Monitor trial evidence, financing progress and promotion to GEM.":"Later-stage research with stronger qualification requirements. Exact-program Phase 3 and two independently verified financing closures.";
  const notice=data.notice||(!data.source_current?"Published SEC / source coverage is partial or stale. Clinical and financing clearance does not clear new trading entries.":"");
  app.innerHTML=`${stageSummary()}<header class="hero">${icon("leaf","hero-icon")}<div><h1>${esc(data.stage)} — ${intro}</h1><p>${subtitle}</p></div><div class="hero-tools"><button data-action="navigate" data-tab="SCANS">Scans</button><button data-action="navigate" data-tab="WT">Watchlist / Trade</button></div></header>${notice?`<aside class="notice"><span>${esc(notice)}</span><button data-action="navigate" data-tab="SCANS">Review sources ↗</button></aside>`:""}<div class="page"><div class="reference-top-layout">${criteriaCard()}${candidateCard(rows)}</div>${reviewNavigator(rows,r)}${state.chartFocus?'<button type="button" class="chart-backdrop" data-action="close-chart" aria-label="Close enlarged chart"></button>':""}${data.junior?`<div class="grid jr-top">${profileCard(r)}${clinicalCard(r)}${chartCard(r,true)}</div><div class="grid jr-bottom">${financeCard(r,true)}${checklist(r,"entry")}${checklist(r,"exit")}</div><div class="grid footer">${historyCard()}${alertsCard(r)}${scansCard()}</div>`:`<div class="grid gem-top">${profileCard(r)}${rulesCard(r)}${financeCard(r,false)}</div><div class="grid gem-bottom">${chartCard(r,false)}${signalCard(r)}${checklist(r,"entry")}${checklist(r,"exit")}</div><div class="grid footer gem-footer">${policyCard()}${historyCard()}${alertsCard(r)}${scansCard()}</div>`}</div><p class="footnote">Saved source observations · Missing values stay unavailable · W = Watchlist · T = existing trade research workspace · No orders are placed</p>`;
  app.setAttribute("aria-busy","false");drawPriceChart(r);if(state.chartFocus){const enlarged=app.querySelector(".focused-chart");enlarged?.setAttribute("role","dialog");enlarged?.setAttribute("aria-modal","true");enlarged?.setAttribute("aria-label","Enlarged "+data.stage+" price chart");enlarged?.querySelector(".chart-close")?.focus();}persist();
  app.querySelectorAll("details[data-tree]").forEach(el=>{const key=r?.id+":"+el.dataset.tree;if(Object.hasOwn(state.tree,key))el.open=state.tree[key];el.addEventListener("toggle",()=>{state.tree[key]=el.open;persist();});});
  if(focusSearch){const input=document.getElementById("candidate-search");input.focus();input.setSelectionRange(input.value.length,input.value.length);}if(focusTrialSearch){const input=document.getElementById("company-trial-search");input?.focus();input?.setSelectionRange(input.value.length,input.value.length);}resize();
}
app.addEventListener("input",ev=>{if(ev.target.id==="candidate-search"){state.search=ev.target.value;state.page=0;render(true);}else if(ev.target.id==="company-trial-search"){state.companyTrialSearch=ev.target.value;state.companyTrialPage=0;render(false,true);}});
app.addEventListener("change",ev=>{if(ev.target.id==="status-filter"){state.status=ev.target.value;state.page=0;render();}if(ev.target.id==="candidate-jump"){chooseCandidate(ev.target.value,"details");}if(ev.target.name==="exit-policy"){state.policy=ev.target.value;write("gem_pdufa_exit_policy",state.policy);persist();send("policy",{policy:state.policy});announce("Research exit policy saved.");}});
app.addEventListener("click",ev=>{
  const button=ev.target.closest("button[data-action]");if(!button||button.disabled)return;
  const action=button.dataset.action,id=button.dataset.id,r=data.candidates.find(x=>x.id===(id||state.selected));
  if(action==="select"){chooseCandidate(id,"details");}
  else if(action==="criterion"){const key=button.dataset.criterion;if(!priorityCriteria().some(x=>x[0]===key))return;state.focus=state.focus===key?null:key;state.sort=null;state.desc=false;state.page=0;state.selected=matching()[0]?.id||null;render();announce(state.focus?"Sorted "+data.stage+" by "+criterionName():"Restored original "+data.stage+" order");}
  else if(action==="criteria-reset"){state.focus=null;state.sort=null;state.desc=false;state.page=0;state.selected=matching()[0]?.id||null;render();announce("Restored original "+data.stage+" order");}
  else if(action==="company-trial-prev"||action==="company-trial-next"){state.companyTrialPage=Math.max(0,(state.companyTrialPage||0)+(action==="company-trial-prev"?-1:1));render();document.querySelector(".company-trial-list")?.scrollIntoView({block:"nearest"});}
  else if(action==="step-candidate"){const rows=matching(),i=rows.findIndex(item=>item.id===state.selected),target=rows[i+Number(button.dataset.step)];if(target)chooseCandidate(target.id,"details");}
  else if(action==="open-details"){if(state.selected)chooseCandidate(state.selected,"details");}
  else if(action==="open-chart"||action==="show-chart"){if(id||state.selected)chooseCandidate(id||state.selected,"chart");}
  else if(action==="close-chart"){state.chartFocus=false;render();document.getElementById("candidate-review")?.querySelector('[data-action="open-chart"]')?.focus();}
  else if(action==="watch"||action==="trade"){if(!r)return;button.disabled=true;send(action,{id:r.id});announce(action==="watch"?"Updating watchlist for "+r.ticker:"Opening trade workspace for "+r.ticker);}
  else if(action==="navigate"){send("navigate",{tab:button.dataset.tab});}
  else if(action==="refresh"){button.disabled=true;button.textContent="Reloading…";send("refresh");}
  else if(action==="range"){state.range=button.dataset.range;render();}
  else if(action==="chart-mode"){state.chartMode=state.chartMode==="tv"?"saved":"tv";render();}
  else if(action==="prev"||action==="next"){state.page+=action==="prev"?-1:1;render();}
  else if(action==="sort"){state.focus=null;if(state.sort===button.dataset.key)state.desc=!state.desc;else{state.sort=button.dataset.key;state.desc=["entry","exit_risk","market_cap"].includes(state.sort);}state.page=0;render();}
  else if(action==="rules-tab"){state.rulesTab=button.dataset.tab;render();}
  else if(action==="finance-tab"){state.financeTab=button.dataset.tab;render();}
  else if(action==="export")exportRows(matching());
  else if(action==="plan"&&r){const dialog=document.getElementById("plan-dialog"),form=document.getElementById("plan-form"),plan=getPlan(r);form.dataset.id=r.id;for(const key of ["entry","stop","target"])form.elements[key].value=plan[key]??"";document.getElementById("plan-error").textContent="";dialog.showModal();}
});
function exportRows(rows){const fields=[["Ticker","ticker"],["Company","company"],["Drug","drug"],["Indication","indication"],["NCT ID","nct"],["Exact program","id"],["Phase 3 readout","readout"],["PDUFA","pdufa"],["Financing","financing_label"],["Runway months","runway"],["Market cap USD","market_cap"],["PoA (saved)","poa_display"],["Entry readiness","entry"],["Exit risk","exit_risk"],["Status","trade_status"]];const cell=x=>'"'+String(x??"").replace(/^[=+@\t\r-]/,"'$&").replace(/"/g,'""')+'"';const csv=[fields.map(x=>cell(x[0])).join(","),...rows.map(r=>fields.map(x=>cell(r[x[1]])).join(","))].join("\r\n");const url=URL.createObjectURL(new Blob(["\ufeff"+csv],{type:"text/csv;charset=utf-8"})),a=document.createElement("a");a.href=url;a.download=data.stage.toLowerCase().replace(/ /g,"-")+"-candidates.csv";a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);announce("Exported "+rows.length+" matching source records.");}
document.getElementById("plan-form").addEventListener("submit",ev=>{if(ev.submitter?.value!=="save")return;ev.preventDefault();const form=ev.target,plan={};for(const k of ["entry","stop","target"]){if(form.elements[k].value!==""){const v=Number(form.elements[k].value);if(!Number.isFinite(v)||v<=0)return;plan[k]=v;}}if(finite(plan.entry)&&((finite(plan.stop)&&plan.stop>=plan.entry)||(finite(plan.target)&&plan.target<=plan.entry))){document.getElementById("plan-error").textContent="Use a stop below entry and a target above entry.";return;}write("gem_chart_plan_"+form.dataset.id,plan);document.getElementById("plan-dialog").close();render();announce("Chart reference levels saved for this exact program.");});
document.querySelector('[data-action="clear-plan"]').addEventListener("click",()=>{const form=document.getElementById("plan-form");write("gem_chart_plan_"+form.dataset.id,{});document.getElementById("plan-dialog").close();render();});
window.addEventListener("message",event=>{if(event.source!==window.parent||event.data?.type!=="streamlit:render")return;const payload=event.data.args?.payload;if(!payload||!Array.isArray(payload.candidates))return;const changed=!data||data.stage!==payload.stage;data=payload;if(changed){state={search:"",status:"All Statuses",sort:null,desc:false,focus:null,page:0,selected:null,companyTrialTicker:null,companyTrialSearch:"",companyTrialPage:0,range:"6M",chartMode:"saved",rulesTab:"rules",financeTab:"financing",policy:read("gem_pdufa_exit_policy","unresolved"),tree:{},...sessionRead("gem_dashboard_"+data.stage)};if(!["pre","partial","hold","unresolved"].includes(state.policy))state.policy="unresolved";state.tree=state.tree||{};if(!priorityCriteria().some(x=>x[0]===state.focus))state.focus=null;state.chartFocus=false;}render();});
document.addEventListener("keydown",ev=>{if(ev.key==="Escape"&&state?.chartFocus){ev.preventDefault();state.chartFocus=false;render();document.getElementById("candidate-review")?.querySelector('[data-action="open-chart"]')?.focus();}});
new ResizeObserver(()=>resize()).observe(document.body);
window.parent.postMessage({isStreamlitMessage:true,type:"streamlit:componentReady",apiVersion:1},"*");
resize();
