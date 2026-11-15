'use client';
import {useEffect,useRef,useState} from 'react';
import pastQueue from '../data/level4BlindAssessmentQueue20261112.json';
const api='/api/assessments/runtime';
const valid=(s:string)=>/^NCT\d{8}$/.test(s);
type Entry={nct:string;level:number;status:string;detail:string;cutoffDate?:string};
type WholeTask={nct:string;cutoffDate?:string;eventKey?:string};
export default function AssessmentLauncher({source='FOCUS',historicalYear='2026'}:{source?:'POOL'|'FOCUS'|'HISTORICAL';historicalYear?:string}){
 const [open,setOpen]=useState(false),[population,setPopulation]=useState(source),[scope,setScope]=useState('selected');
 const [input,setInput]=useState(''),[singleNct,setSingleNct]=useState(''),[levels,setLevels]=useState<number[]>([1,2,3]);
 const [mode,setMode]=useState('CURRENT_EVIDENCE'),[cutoff,setCutoff]=useState(''),[entries,setEntries]=useState<Entry[]>([]);
 const [working,setWorking]=useState(false),[error,setError]=useState(''),[catalog,setCatalog]=useState<string[]>([]),[verifiedAll,setVerifiedAll]=useState(false);
 const [missingPast,setMissingPast]=useState<string[]>([]),[wholeTasks,setWholeTasks]=useState<WholeTask[]>([]);
 const loadVersion=useRef(0);
 useEffect(()=>{setPopulation(source);loadVersion.current++;setCatalog([]);setVerifiedAll(false);setMissingPast([]);setWholeTasks([])},[source,historicalYear]);
 const selected=Array.from(new Set(input.toUpperCase().split(/[\s,;]+/).filter(Boolean)));
 async function json(url:string,init?:RequestInit){const response=await fetch(url,{cache:'no-store',...init});const body=await response.json();if(!response.ok)throw Error(body.error||'Assessment service unavailable');return body;}
 async function load(){
  const version=++loadVersion.current;
  setError('');setCatalog([]);setVerifiedAll(false);setMissingPast([]);setWholeTasks([]);
  // This manifest is the exact 2026 PAST page cohort, NOT the broader trial
  // history catalog. Ticker/date alone cannot establish application identity.
  if(population==='HISTORICAL'){
   const events=historicalYear==='2026'?pastQueue.historical2026:[];
   try{
    const report=await json(api+'?pastRoster='+encodeURIComponent(historicalYear));
    if(version!==loadVersion.current)return;
    const expectedKeys=new Set(events.map(e=>e.eventKey));
    const eventRows:{eventKey:string;status:string;reason?:string}[]=Array.isArray(report.events)?report.events:[];
    const aligned=events.length>0&&eventRows.length===events.length&&eventRows.every(e=>expectedKeys.has(e.eventKey))&&new Set(eventRows.map(e=>e.eventKey)).size===events.length;
    const items:WholeTask[]=Array.isArray(report.tasks)?report.tasks:[];
    const ids=items.map(t=>t.nct);
    const complete=report.status==='VERIFIED_WHOLE_PAST_COHORT'&&report.ready===true&&report.year===Number(historicalYear)&&report.linked===events.length&&report.total===events.length&&aligned&&items.length>=events.length&&ids.every(valid)&&new Set(ids).size===ids.length&&items.every(t=>expectedKeys.has(t.eventKey||'')&&typeof t.cutoffDate==='string'&&/^\\d{4}-\\d{2}-\\d{2}$/.test(t.cutoffDate));
    if(!complete){
     const missing=eventRows.filter(e=>e.status!=='READY');
     setMissingPast(missing.length?missing.map(e=>e.eventKey+' · '+e.status+(e.reason?' · '+e.reason:'')):events.map(e=>e.eventKey));
     setError('Whole PAST '+historicalYear+' needs verified FDA event/trial links and authentic pre-decision sources. '+(report.linked??0)+' of '+(report.total??'unknown')+' event links ready; incomplete cohorts cannot run.');
     return;
    }
    setCatalog(ids);setWholeTasks(items);setVerifiedAll(true);
   }catch(e){if(version===loadVersion.current){setMissingPast(events.map(e=>e.eventKey));setError(e instanceof Error?e.message:String(e));}}
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
 function clearPopup(){if(working)return;loadVersion.current++;setInput('');setSingleNct('');setScope('selected');setLevels([1,2,3]);setMode('CURRENT_EVIDENCE');setCutoff('');setEntries([]);setCatalog([]);setVerifiedAll(false);setMissingPast([]);setWholeTasks([]);setError('');setPopulation(source);}
 async function submit(){if(working)return;const ids=scope==='all'?catalog:scope==='single'?[singleNct.trim().toUpperCase()]:selected;if(!ids.length||ids.some(id=>!valid(id))||!levels.length||(mode==='BLIND_HISTORICAL'&&!cutoff)||(scope==='all'&&!verifiedAll)){setError('Choose valid exact-NCT trials, Levels 1–3 and a valid evidence mode. Entire-list batches require a verified complete FOCUS roster.');return;}
 setWorking(true);setError('');const work=ids.flatMap(nct=>levels.map(level=>({nct,level,status:'QUEUED',detail:''})));setEntries(work);
 for(let i=0;i<work.length;i++){const task=work[i];const update=(status:string,detail:string)=>setEntries(prev=>prev.map((e,j)=>i===j?{...e,status,detail}:e));
 try{update('SUBMITTING','');const created=await json(api,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({nct:task.nct,level:task.level,mode,contract:'SCIENTIFIC_1_3',...(mode==='BLIND_HISTORICAL'?{cutoffDate:cutoff}:{})})});
 if(typeof created.runId!=='string'||!/^[a-f0-9-]{36}$/.test(created.runId))throw Error('No valid run ID returned');update('RUNNING',created.runId);
 let done=false;for(let attempt=0;attempt<90;attempt++){await new Promise(resolve=>setTimeout(resolve,2000));const result=await json(api+'?'+new URLSearchParams({nct:task.nct,runId:created.runId}));if(result.status==='FAILED')throw Error(result.error||'Assessment failed');if(result.status==='COMPLETED'){if(!result.report||result.report.runId!==created.runId||result.report.nct!==task.nct||result.report.level!==task.level||result.report.mode!==mode||result.report.contract!=='SCIENTIFIC_1_3'||(mode==='BLIND_HISTORICAL'&&result.report.cutoffDate!==cutoff))throw Error('Saved assessment identity, level, mode or contract mismatch');update('COMPLETED',created.runId);done=true;break;}}
 if(!done)update('PENDING','Check saved history; execution not yet confirmed');
 }catch(e){update('FAILED',e instanceof Error?e.message:String(e));}
 }setWorking(false);
 }
 return <section style={{margin:'12px 0'}}><button type="button" onClick={()=>{setOpen(!open);setError('')}} aria-expanded={open}>Assess Trials · Levels 1–3</button>
 {open&&<div role="dialog" aria-label="Scientific assessment launcher" style={{background:'#fff',color:'#173d2b',border:'2px solid #16856c',padding:16,borderRadius:12,maxWidth:740,marginTop:8}}>
 <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',gap:12}}><h2>Scientific Assessment · Levels 1–3</h2><div style={{display:'flex',gap:8}}><button type="button" aria-label="Clear assessment popup" title="Clear selections and results" disabled={working} onClick={clearPopup}>✕ Clear</button><button type="button" aria-label="Close assessment popup" title="Close popup" onClick={()=>setOpen(false)}>✕ Close</button></div></div>
 <p>Run one trial, selected trials, or a complete source-verified PAST year or FOCUS roster. Each selected level saves its own immutable report; evidence coverage is not an FDA approval probability.</p>
 <label>Source <select value={population} disabled={working} onChange={e=>{loadVersion.current++;setPopulation(e.target.value as typeof population);setCatalog([]);setVerifiedAll(false);setMissingPast([]);setWholeTasks([]);setError('')}}><option>POOL</option><option>FOCUS</option><option>HISTORICAL</option></select></label>{' '}
 <label>Scope <select aria-label="Assessment scope" value={scope} disabled={working} onChange={e=>setScope(e.target.value)}><option value="single">Single trial</option><option value="selected">Selected trials</option><option value="all">Whole list</option></select></label>
 {scope==='single'?<p><label>Exact NCT for one trial <input aria-label="Single trial NCT" placeholder="NCT12345678" maxLength={11} disabled={working} value={singleNct} onChange={e=>setSingleNct(e.target.value.toUpperCase())}/></label></p>
 :scope==='selected'?<p><label>Exact NCT IDs (separated by commas or lines)<textarea style={{display:'block',width:'100%',minHeight:75}} disabled={working} value={input} onChange={e=>setInput(e.target.value)}/></label></p>
 :<p><button type="button" disabled={working} onClick={()=>void load()}>{population==='FOCUS'?'Verify and load whole FOCUS list':population==='HISTORICAL'?'Audit whole PAST '+historicalYear+' list':'Check whole POOL availability'}</button> {catalog.length} verified NCTs loaded. {verifiedAll?'Full '+(population==='HISTORICAL'?'PAST '+historicalYear:'FOCUS')+' roster confirmed.':'Whole-list submission requires complete verified source membership.'}</p>}
 {scope==='all'&&population==='HISTORICAL'&&missingPast.length>0&&<details open><summary>{missingPast.length} PAST events requiring verified linkage or evidence</summary><ul>{missingPast.map(event=><li key={event}>{event}</li>)}</ul><p>These entries need source-verified NCT, application/review cycle, decision-date association and historical source snapshots. Ticker-only matching is prohibited.</p></details>}
 {population==='HISTORICAL'&&<p role="note">PAST event links must be independently verified. Single and selected NCT assessments are saved by trial identity and do not independently prove association with a displayed historical FDA event.</p>}
 <fieldset disabled={working}><legend>Selected levels</legend>{[1,2,3,4,5,6].map(level=><label key={level} style={{display:'inline-block',marginRight:12}}><input type="checkbox" disabled={level>3} checked={levels.includes(level)} onChange={e=>setLevels(current=>e.target.checked?[...current,level].sort():current.filter(n=>n!==level))}/> {level}</label>)}</fieldset>
 <p><label>Evidence mode <select disabled={working} value={mode} onChange={e=>setMode(e.target.value)}><option value="CURRENT_EVIDENCE">Current evidence</option><option value="BLIND_HISTORICAL">Historical pre-cutoff (outcome-isolated; not independently blind)</option></select></label>{mode==='BLIND_HISTORICAL'&&!(scope==='all'&&population==='HISTORICAL')&&<label> Cutoff date <input type="date" disabled={working} value={cutoff} onChange={e=>setCutoff(e.target.value)}/></label>}</p>
 <p>Historical mode requires authentic pre-cutoff snapshots for every requested trial, past or present. Missing snapshots fail explicitly; no present-day substitution.</p>
 <button disabled={working||!levels.length||(scope==='single'&&!valid(singleNct.trim().toUpperCase()))||(scope==='selected'&&(!selected.length||selected.some(id=>!valid(id))))||(scope==='all'&&(population!=='FOCUS'||!verifiedAll))||(mode==='BLIND_HISTORICAL'&&!cutoff&&!(scope==='all'&&population==='HISTORICAL'&&verifiedAll))} onClick={()=>void submit()}>{working?'Running batch…':'Submit assessments'}</button>
 {error&&<p role="alert">{error}</p>}
 {entries.length>0&&<div aria-live="polite"><h3>Batch progress · {entries.filter(e=>e.status==='COMPLETED').length}/{entries.length} completed</h3><ul>{entries.map((e,i)=><li key={i}>{e.nct} · Level {e.level} · {e.status} {e.detail}</li>)}</ul><a href="/assessments">Open ASSESSMENTS history</a></div>}
 </div>}</section>;
}
