'use client';
import {useEffect,useState} from 'react';
const api='/api/assessments/runtime';
const valid=(s:string)=>/^NCT\d{8}$/.test(s);
type Entry={nct:string;level:number;status:string;detail:string};
export default function AssessmentLauncher({source='FOCUS'}:{source?:'POOL'|'FOCUS'|'HISTORICAL'}){
 const [open,setOpen]=useState(false),[population,setPopulation]=useState(source),[scope,setScope]=useState('selected');
 const [input,setInput]=useState(''),[levels,setLevels]=useState<number[]>([1,2,3,4,5,6]);
 const [mode,setMode]=useState('CURRENT_EVIDENCE'),[cutoff,setCutoff]=useState(''),[entries,setEntries]=useState<Entry[]>([]);
 const [working,setWorking]=useState(false),[error,setError]=useState(''),[catalog,setCatalog]=useState<string[]>([]);
 useEffect(()=>{setPopulation(source)},[source]);
 const selected=Array.from(new Set(input.toUpperCase().split(/[\s,;]+/).filter(Boolean)));
 async function json(url:string,init?:RequestInit){const response=await fetch(url,{cache:'no-store',...init});const body=await response.json();if(!response.ok)throw Error(body.error||'Assessment service unavailable');return body;}
 async function load(){setError('');try{const data=await json(api+'?'+new URLSearchParams({population,q:''}));setCatalog((data.trials||[]).map((r:{nct:string})=>r.nct));if((data.trials||[]).length>=50)setError('The inventory API returns at most 50 trials. Entire-list submission is blocked until paginated inventory is available; no partial list will be treated as complete.');}catch(e){setError(String(e));}}
 function clearPopup(){if(working)return;setInput('');setScope('selected');setLevels([1,2,3,4,5,6]);setMode('CURRENT_EVIDENCE');setCutoff('');setEntries([]);setCatalog([]);setError('');setPopulation(source);}
 async function submit(){if(working)return;const ids=scope==='all'?catalog:selected;if(!ids.length||ids.some(id=>!valid(id))||!levels.length||(mode==='BLIND_HISTORICAL'&&!cutoff)||(scope==='all'&&catalog.length>=50))return;
 setWorking(true);setError('');const work=ids.flatMap(nct=>levels.map(level=>({nct,level,status:'QUEUED',detail:''})));setEntries(work);
 for(let i=0;i<work.length;i++){const task=work[i];const update=(status:string,detail:string)=>setEntries(prev=>prev.map((e,j)=>i===j?{...e,status,detail}:e));
 try{update('SUBMITTING','');const created=await json(api,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({nct:task.nct,level:task.level,mode,...(mode==='BLIND_HISTORICAL'?{cutoffDate:cutoff}:{})})});
 if(!created.runId)throw Error('No run ID returned');update('RUNNING',created.runId);
 let done=false;for(let attempt=0;attempt<90;attempt++){await new Promise(resolve=>setTimeout(resolve,2000));const result=await json(api+'?'+new URLSearchParams({nct:task.nct,runId:created.runId}));if(result.status==='FAILED')throw Error(result.error||'Assessment failed');if(result.status==='COMPLETED'){update('COMPLETED',created.runId);done=true;break;}}
 if(!done)update('PENDING','Check saved history; execution not yet confirmed');
 }catch(e){update('FAILED',e instanceof Error?e.message:String(e));}
 }setWorking(false);
 }
 return <section style={{margin:'12px 0'}}><button type="button" onClick={()=>{setOpen(!open);setError('')}} aria-expanded={open}>Assess Trials · Levels 1–6</button>
 {open&&<div role="dialog" aria-label="Scientific assessment launcher" style={{background:'#fff',color:'#173d2b',border:'2px solid #16856c',padding:16,borderRadius:12,maxWidth:740,marginTop:8}}>
 <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',gap:12}}><h2>Scientific Assessment · Levels 1–6</h2><div style={{display:'flex',gap:8}}><button type="button" aria-label="Clear assessment popup" title="Clear selections and results" disabled={working} onClick={clearPopup}>✕ Clear</button><button type="button" aria-label="Close assessment popup" title="Close popup" onClick={()=>setOpen(false)}>✕ Close</button></div></div>
 <p>Run selected trials or an entire verified inventory. Each selected level saves its own immutable report; evidence coverage is not an FDA approval probability.</p>
 <label>Source <select value={population} disabled={working} onChange={e=>{setPopulation(e.target.value as typeof population);setCatalog([])}}><option>POOL</option><option>FOCUS</option><option>HISTORICAL</option></select></label>{' '}
 <label>Scope <select value={scope} disabled={working} onChange={e=>setScope(e.target.value)}><option value="selected">Selected trials</option><option value="all">Entire source list</option></select></label>
 {scope==='selected'?<p><label>Exact NCT IDs (separated by commas or lines)<textarea style={{display:'block',width:'100%',minHeight:75}} disabled={working} value={input} onChange={e=>setInput(e.target.value)}/></label></p>:<p><button disabled={working} onClick={()=>void load()}>Load source inventory</button> {catalog.length} NCTs loaded. {catalog.length>=50?'Inventory may be truncated; cannot submit all.':''}</p>}
 <fieldset disabled={working}><legend>Selected levels</legend>{[1,2,3,4,5,6].map(level=><label key={level} style={{display:'inline-block',marginRight:12}}><input type="checkbox" checked={levels.includes(level)} onChange={e=>setLevels(current=>e.target.checked?[...current,level].sort():current.filter(n=>n!==level))}/> {level}</label>)}</fieldset>
 <p><label>Evidence mode <select disabled={working} value={mode} onChange={e=>setMode(e.target.value)}><option value="CURRENT_EVIDENCE">Current evidence</option><option value="BLIND_HISTORICAL">Blind historical</option></select></label>{mode==='BLIND_HISTORICAL'&&<label> Cutoff date <input type="date" disabled={working} value={cutoff} onChange={e=>setCutoff(e.target.value)}/></label>}</p>
 <p>Historical mode requires authentic pre-cutoff snapshots for every requested trial, past or present. Missing snapshots fail explicitly; no present-day substitution.</p>
 <button disabled={working||!levels.length||(scope==='selected'&&(!selected.length||selected.some(id=>!valid(id))))||(scope==='all'&&(!catalog.length||catalog.length>=50))||(mode==='BLIND_HISTORICAL'&&!cutoff)} onClick={()=>void submit()}>{working?'Running batch…':'Submit assessments'}</button>
 {error&&<p role="alert">{error}</p>}
 {entries.length>0&&<div aria-live="polite"><h3>Batch progress · {entries.filter(e=>e.status==='COMPLETED').length}/{entries.length} completed</h3><ul>{entries.map((e,i)=><li key={i}>{e.nct} · Level {e.level} · {e.status} {e.detail}</li>)}</ul><a href="/assessments">Open ASSESSMENTS history</a></div>}
 </div>}</section>;
}
