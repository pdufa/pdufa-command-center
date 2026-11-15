'use client';
import {useEffect,useRef,useState} from 'react';
import pastQueue from '../data/level4BlindAssessmentQueue20261112.json';
const api='/api/assessments/runtime';
const valid=(s:string)=>/^NCT\d{8}$/.test(s);
type Entry={nct:string;level:number;status:string;detail:string;cutoffDate?:string;eventKey?:string};
type PastEvent={eventKey:string;status:string;reason?:string};
type WholeTask={nct:string;cutoffDate?:string;eventKey?:string};
export default function AssessmentLauncher({source='FOCUS',historicalYear='2026',lockSource=false}:{source?:'POOL'|'FOCUS'|'HISTORICAL';historicalYear?:string;lockSource?:boolean}){
 const [open,setOpen]=useState(false),[population,setPopulation]=useState(source),[scope,setScope]=useState('selected');
 const [input,setInput]=useState(''),[singleNct,setSingleNct]=useState(''),[levels,setLevels]=useState<number[]>([1,2,3]);
 const [mode,setMode]=useState('CURRENT_EVIDENCE'),[cutoff,setCutoff]=useState(''),[entries,setEntries]=useState<Entry[]>([]);
 const [working,setWorking]=useState(false),[error,setError]=useState(''),[catalog,setCatalog]=useState<string[]>([]),[verifiedAll,setVerifiedAll]=useState(false);
 const [missingPast,setMissingPast]=useState<string[]>([]),[wholeTasks,setWholeTasks]=useState<WholeTask[]>([]);
 const [pastAudited,setPastAudited]=useState(false),[pastRows,setPastRows]=useState<PastEvent[]>([]);
 const loadVersion=useRef(0);
 useEffect(()=>{setPopulation(source);loadVersion.current++;setCatalog([]);setVerifiedAll(false);setMissingPast([]);setWholeTasks([]);setPastAudited(false);setPastRows([])},[source,historicalYear]);
 const selected=Array.from(new Set(input.toUpperCase().split(/[\s,;]+/).filter(Boolean)));
 async function json(url:string,init?:RequestInit){const response=await fetch(url,{cache:'no-store',...init});const body=await response.json();if(!response.ok)throw Error(body.error||'Assessment service unavailable');return body;}
 async function load(){
  const version=++loadVersion.current;
  setError('');setCatalog([]);setVerifiedAll(false);setMissingPast([]);setWholeTasks([]);setPastAudited(false);setPastRows([]);
  // This manifest is the exact 2026 PAST page cohort, NOT the broader trial
  // history catalog. Ticker/date alone cannot establish application identity.
  if(population==='HISTORICAL'){
   const events=historicalYear==='2026'?pastQueue.historical2026:[];
   try{
    const report=await json(api+'?pastRoster='+encodeURIComponent(historicalYear));
    if(version!==loadVersion.current)return;
    const expectedKeys=new Set(events.map(e=>e.eventKey));
    const eventRows:PastEvent[]=Array.isArray(report.events)?report.events:[];
    const aligned=events.length>0&&eventRows.length===events.length&&
      eventRows.every(e=>expectedKeys.has(e.eventKey)&&typeof e.status==='string')&&
      new Set(eventRows.map(e=>e.eventKey)).size===events.length;
    const readyKeys=new Set(eventRows.filter(e=>e.status==='READY').map(e=>e.eventKey));
    const items:WholeTask[]=Array.isArray(report.eligibleTasks)?report.eligibleTasks:[];
    const ids=items.map(t=>t.nct);
    const tasksValid=items.every(t=>valid(t.nct)&&readyKeys.has(t.eventKey||'')&&
      typeof t.cutoffDate==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(t.cutoffDate));
    const full=report.ready===true&&report.status==='VERIFIED_WHOLE_PAST_COHORT'&&report.linked===events.length;
    const consistent=report.year===Number(historicalYear)&&report.total===events.length&&
      report.linked===readyKeys.size&&aligned&&tasksValid&&new Set(ids).size===ids.length&&
      (readyKeys.size===0?items.length===0:readyKeys.size<=items.length)&&
      (!full||readyKeys.size===events.length);
    if(!consistent){
     setError('PAST '+historicalYear+' roster incomplete or inconsistent; no whole-year operation authorized.');return;
    }
    const unresolved=eventRows.filter(e=>e.status!=='READY');
    setPastRows(eventRows);setWholeTasks(items);setCatalog(ids);setVerifiedAll(full);
    setPastAudited(true);
    setMissingPast(unresolved.map(e=>e.eventKey+' · '+e.status+(e.reason?' · '+e.reason:'')));
   }catch(e){if(version===loadVersion.current)setError(e instanceof Error?e.message:String(e));}
   return;
  }
  if(population!=='FOCUS'){setError('Whole POOL roster is not yet paginated and fully verified; no truncated list will be submitted.');return;}
  try{
   const [inventory,summary]=await Promise.all([
    json(api+'?'+new URLSearchParams({population:'FOCUS',q:''})),
    json(api+'?focus=true')
   ]);
   if(version!==loadVersion.current)return;
   const ids:string[]=Array.from(new Set<string>((inventory.trials||[]).map((r:{nct:string})=>r.nct)));
   const savedIds:string[]=Array.isArray(summary.trials)?summary.trials.map((r:{nct:string})=>r.nct):[];
   const sameRoster=ids.length===savedIds.length&&ids.every(id=>savedIds.includes(id));
   if(inventory.population!=='FOCUS'||summary.status!=='DATABASE_SAVED_RECONCILED_OWNER_ROSTER'||!summary.source?.roster_id||!Number.isInteger(summary.total)||summary.total<1||summary.total>=50||ids.length!==summary.total||!sameRoster||ids.some(id=>!valid(id))){
    setError('FOCUS roster could not be verified as complete; no partial or unlinked batch will be submitted.');return;
   }
   setCatalog(ids);setVerifiedAll(true);
  }catch(e){if(version===loadVersion.current)setError(e instanceof Error?e.message:String(e));}
 }
 function clearPopup(){if(working)return;loadVersion.current++;setInput('');setSingleNct('');setScope('selected');setLevels([1,2,3]);setMode('CURRENT_EVIDENCE');setCutoff('');setEntries([]);setCatalog([]);setVerifiedAll(false);setMissingPast([]);setWholeTasks([]);setPastAudited(false);setPastRows([]);setError('');setPopulation(source);}
 async function submit(){
  if(working)return;
  const pastWhole=scope==='all'&&population==='HISTORICAL';
  const ids=scope==='all'?catalog:scope==='single'?[singleNct.trim().toUpperCase()]:selected;
  const eligible=wholeTasks.length===ids.length&&wholeTasks.every(t=>valid(t.nct)&&t.cutoffDate);
  const runMode=pastWhole?'BLIND_HISTORICAL':mode;
  if((!pastWhole&&!ids.length)||ids.some(id=>!valid(id))||!levels.length||
     (runMode==='BLIND_HISTORICAL'&&!cutoff&&!pastWhole)||
     (scope==='all'&&(pastWhole?(!pastAudited||!eligible):!verifiedAll))){
    setError('Choose valid exact-NCT trials and Levels 1–3. Whole PAST needs a completed audit; unresolved events are reported without generating predictions.');return;
  }
  setWorking(true);setError('');
  const tasks:WholeTask[]=pastWhole?wholeTasks:ids.map(nct=>({nct}));
  const work:Entry[]=tasks.flatMap(t=>levels.map(level=>({
   nct:t.nct,level,status:'QUEUED',detail:'',eventKey:t.eventKey,
   ...(runMode==='BLIND_HISTORICAL'?{cutoffDate:pastWhole?t.cutoffDate:cutoff}:{})
  })));
  const excluded:Entry[]=pastWhole?pastRows.filter(e=>e.status!=='READY').map(e=>({
   nct:'',eventKey:e.eventKey,level:0,status:'NOT_ASSESSED_UNVERIFIED',
   detail:e.reason||'FDA application, exact trial or original pre-decision evidence missing; no score or FDA prediction.'
  })):[];
  setEntries([...work,...excluded]);
  for(let i=0;i<work.length;i++){
   const task=work[i];
   const update=(status:string,detail:string)=>setEntries(prev=>prev.map((e,j)=>i===j?{...e,status,detail}:e));
   try{
    update('SUBMITTING','');
    const created=await json(api,{method:'POST',headers:{'Content-Type':'application/json'},
     body:JSON.stringify({nct:task.nct,level:task.level,mode:runMode,contract:'SCIENTIFIC_1_3',
     ...(runMode==='BLIND_HISTORICAL'?{cutoffDate:task.cutoffDate}:{})})});
    if(typeof created.runId!=='string'||!/^[a-f0-9-]{36}$/.test(created.runId))throw Error('No valid run ID returned');
    update('RUNNING',created.runId);
    let done=false;
    for(let attempt=0;attempt<90;attempt++){
     await new Promise(resolve=>setTimeout(resolve,2000));
     const result=await json(api+'?'+new URLSearchParams({nct:task.nct,runId:created.runId}));
     if(result.status==='FAILED')throw Error(result.error||'Assessment failed');
     if(result.status==='COMPLETED'){
      if(!result.report||result.report.runId!==created.runId||result.report.nct!==task.nct||
         result.report.level!==task.level||result.report.mode!==runMode||
         result.report.contract!=='SCIENTIFIC_1_3'||
         (runMode==='BLIND_HISTORICAL'&&result.report.cutoffDate!==task.cutoffDate))
        throw Error('Saved assessment identity, level, mode, or cutoff mismatch');
      update('COMPLETED',created.runId);done=true;break;
     }
    }
    if(!done)update('PENDING','Check saved history; execution not yet confirmed');
   }catch(e){update('FAILED',e instanceof Error?e.message:String(e));}
  }
  setWorking(false);
 }

 return <section style={{margin:'12px 0'}}><button type="button" onClick={()=>{setOpen(!open);setError('')}} aria-expanded={open}>Assess Trials · Levels 1–3</button>
 {open&&<div role="dialog" aria-label="Scientific assessment launcher" style={{background:'#fff',color:'#173d2b',border:'2px solid #16856c',padding:16,borderRadius:12,maxWidth:740,marginTop:8}}>
 <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',gap:12}}><h2>Scientific Assessment · Levels 1–3</h2><div style={{display:'flex',gap:8}}><button type="button" aria-label="Clear assessment popup" title="Clear selections and results" disabled={working} onClick={clearPopup}>✕ Clear</button><button type="button" aria-label="Close assessment popup" title="Close popup" onClick={()=>setOpen(false)}>✕ Close</button></div></div>
 <p>Run one or selected trials, or audit an entire PAST year. Verified trials may be assessed; unresolved FDA events are listed as not assessed without invented trials, scores or predictions. Each selected level saves its own immutable report; evidence coverage is not an FDA approval probability.</p>
 <label>Source <select value={population} disabled={working||lockSource} onChange={e=>{loadVersion.current++;setPopulation(e.target.value as typeof population);setCatalog([]);setVerifiedAll(false);setMissingPast([]);setWholeTasks([]);setPastAudited(false);setPastRows([]);setError('')}}><option>POOL</option><option>FOCUS</option><option>HISTORICAL</option></select></label>{' '}
 <label>Scope <select aria-label="Assessment scope" value={scope} disabled={working} onChange={e=>setScope(e.target.value)}><option value="single">Single trial</option><option value="selected">Selected trials</option><option value="all">Whole list</option></select></label>
 {scope==='single'?<p><label>Exact NCT for one trial <input aria-label="Single trial NCT" placeholder="NCT12345678" maxLength={11} disabled={working} value={singleNct} onChange={e=>setSingleNct(e.target.value.toUpperCase())}/></label></p>
 :scope==='selected'?<p><label>Exact NCT IDs (separated by commas or lines)<textarea style={{display:'block',width:'100%',minHeight:75}} disabled={working} value={input} onChange={e=>setInput(e.target.value)}/></label></p>
 :<p><button type="button" disabled={working} onClick={()=>void load()}>{population==='FOCUS'?'Verify and load whole FOCUS list':population==='HISTORICAL'?'Audit whole PAST '+historicalYear+' list':'Check whole POOL availability'}</button> {catalog.length} verified NCTs loaded. {population==='HISTORICAL'?(pastAudited?'Whole PAST audit loaded: '+wholeTasks.length+' verified trials; '+missingPast.length+' events not assessable.':'Audit the selected PAST year first.'):(verifiedAll?'Full FOCUS roster confirmed.':'Whole FOCUS requires complete verified source membership.')}</p>}
 {scope==='all'&&population==='HISTORICAL'&&missingPast.length>0&&<details open><summary>{missingPast.length} PAST events requiring verified linkage or evidence</summary><ul>{missingPast.map(event=><li key={event}>{event}</li>)}</ul><p>These entries need source-verified NCT, application/review cycle, decision-date association and historical source snapshots. Ticker-only matching is prohibited.</p></details>}
 {population==='HISTORICAL'&&<p role="note">Whole PAST reports every event. Only source-verified trials with original pre-decision evidence can run; unresolved events remain NOT ASSESSED. Single/selected NCT runs do not establish FDA event linkage.</p>}
 <fieldset disabled={working}><legend>Selected levels</legend>{[1,2,3,4,5,6].map(level=><label key={level} style={{display:'inline-block',marginRight:12}}><input type="checkbox" disabled={level>3} checked={levels.includes(level)} onChange={e=>setLevels(current=>e.target.checked?[...current,level].sort():current.filter(n=>n!==level))}/> {level}</label>)}</fieldset>
 <p><label>Evidence mode <select disabled={working||(scope==='all'&&population==='HISTORICAL')} value={scope==='all'&&population==='HISTORICAL'?'BLIND_HISTORICAL':mode} onChange={e=>setMode(e.target.value)}><option value="CURRENT_EVIDENCE">Current evidence</option><option value="BLIND_HISTORICAL">Historical pre-cutoff (outcome-isolated; not independently blind)</option></select></label>{mode==='BLIND_HISTORICAL'&&!(scope==='all'&&population==='HISTORICAL')&&<label> Cutoff date <input type="date" disabled={working} value={cutoff} onChange={e=>setCutoff(e.target.value)}/></label>}</p>
 <p>Historical mode requires authentic pre-cutoff snapshots for every requested trial, past or present. Missing snapshots fail explicitly; no present-day substitution.</p>
 <button disabled={working||!levels.length||(scope==='single'&&!valid(singleNct.trim().toUpperCase()))||(scope==='selected'&&(!selected.length||selected.some(id=>!valid(id))))||(scope==='all'&&(population==='HISTORICAL'?!pastAudited:!verifiedAll))||(mode==='BLIND_HISTORICAL'&&!cutoff&&!(scope==='all'&&population==='HISTORICAL'&&verifiedAll))} onClick={()=>void submit()}>{working?'Running batch…':'Submit assessments'}</button>
 {error&&<p role="alert">{error}</p>}
 {entries.length>0&&<div aria-live="polite"><h3>Whole-list results · {entries.filter(e=>e.status==='COMPLETED').length} assessments completed · {entries.filter(e=>e.status==='NOT_ASSESSED_UNVERIFIED').length} events not assessed</h3><ul>{entries.map((e,i)=><li key={i}>{e.eventKey||e.nct}{e.level>0?' · Level '+e.level:''} · {e.status} {e.detail}</li>)}</ul><a href="/assessments">Open ASSESSMENTS history</a></div>}
 </div>}</section>;
}
