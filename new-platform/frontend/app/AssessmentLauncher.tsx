'use client';
import {useEffect,useRef,useState} from 'react';

type Population='POOL'|'FOCUS'|'HISTORICAL';
type Inventory={population:Population;total:number;blocked:number;inventoryHash:string;source:{status:string};records:{key:string;nct:string|null;blocker:string|null}[];nextOffset:number|null};
type Item={key:string;nct:string|null;level:number;cutoffDate:string|null;state:string;runId:string|null;reportHash:string|null;error:string|null};
type Batch={batchId:string;population:Population;mode:string;createdAt:string;status:string;source:{status:string};totalTrials:number;totalItems:number;counts:{completed:number;blocked:number;failed:number;running:number;pending:number;scored:number};items:Item[];canResume:boolean;terminal:boolean};
const api='/api/assessments/runtime';
const valid=(s:string)=>/^NCT[0-9]{8}$/.test(s);
const label=(p:Population)=>p==='HISTORICAL'?'PAST':p;
const human=(s:string)=>s.replaceAll('_',' ');
async function read(url:string,init?:RequestInit){
 const response=await fetch(url,{cache:'no-store',...init});const body=await response.json();
 if(!response.ok)throw Error(body.error||'Assessment service unavailable');return body;
}

export default function AssessmentLauncher({source='FOCUS',selectedNct}:{source?:Population;selectedNct?:string}){
 const [open,setOpen]=useState(false),[population,setPopulation]=useState<Population>(source),[scope,setScope]=useState('single');
 const [input,setInput]=useState(selectedNct||''),[levels,setLevels]=useState<number[]>([1,2,3]);
 const [mode,setMode]=useState(source==='HISTORICAL'?'BLIND_HISTORICAL':'CURRENT_EVIDENCE'),[cutoff,setCutoff]=useState('');
 const [inventory,setInventory]=useState<Inventory|null>(null),[batch,setBatch]=useState<Batch|null>(null);
 const [busy,setBusy]=useState(false),[error,setError]=useState(''),[recent,setRecent]=useState<{batchId:string;createdAt:string}[]>([]);
 const operation=useRef(false),revision=useRef(0),button=useRef<HTMLButtonElement>(null);
 const pendingRequest=useRef<{signature:string;key:string}|null>(null);
 const selected=Array.from(new Set(input.toUpperCase().split(/[\s,;]+/).filter(Boolean)));

 useEffect(()=>{revision.current++;setPopulation(source);setInventory(null);setBatch(null);setMode(source==='HISTORICAL'?'BLIND_HISTORICAL':'CURRENT_EVIDENCE');},[source]);
 useEffect(()=>{if(selectedNct){setInput(selectedNct);setScope('single');}},[selectedNct]);
 useEffect(()=>{
  if(!open)return;
  const controller=new AbortController(),current=revision.current;
  void read(api+'?'+new URLSearchParams({batches:'true',population}),{signal:controller.signal}).then(data=>{
   if(!controller.signal.aborted&&current===revision.current)setRecent(data.batches||[]);
  }).catch(e=>{if(!controller.signal.aborted)setError(e.message);});
  return()=>controller.abort();
 },[open,population]);
 useEffect(()=>{
  if(!batch||batch.terminal)return;
  const controller=new AbortController(),id=batch.batchId,current=revision.current;let timer:ReturnType<typeof setTimeout>;
  async function poll(){
   try{
    const result=await read(api+'?'+new URLSearchParams({batchId:id}),{signal:controller.signal}) as Batch;
    if(controller.signal.aborted||current!==revision.current)return;
    if(result.batchId!==id)throw Error('Saved batch identity mismatch; results withheld');
    setBatch(result);
    if(result.terminal){window.dispatchEvent(new Event('pdufa:assessment-saved'));return;}
    timer=setTimeout(()=>void poll(),2000);
   }catch(e){if(!controller.signal.aborted)setError(e instanceof Error?e.message:'Batch status unavailable');}
  }
  timer=setTimeout(()=>void poll(),500);
  return()=>{controller.abort();clearTimeout(timer);};
 },[batch?.batchId,batch?.terminal]);

 function changePopulation(next:Population){
  revision.current++;setPopulation(next);setInventory(null);setBatch(null);setRecent([]);setError('');
  setMode(next==='HISTORICAL'?'BLIND_HISTORICAL':'CURRENT_EVIDENCE');
 }
 function clear(){
  if(operation.current)return;
  revision.current++;setInput(selectedNct||'');setScope('single');setLevels([1,2,3]);setCutoff('');
  setBatch(null);setInventory(null);setError('');pendingRequest.current=null;
 }
 async function loadInventory(){
  if(operation.current)return;operation.current=true;setBusy(true);setError('');setInventory(null);
  const current=revision.current,requested=population;
  try{
   let offset=0;let snapshot:Inventory|null=null;const records:Inventory['records']=[];
   for(let page=0;page<10;page++){
    const data=await read(api+'?'+new URLSearchParams({inventory:'true',population:requested,offset:String(offset),limit:'100'})) as Inventory;
    if(current!==revision.current)return;
    if(data.population!==requested||snapshot&&snapshot.inventoryHash!==data.inventoryHash)throw Error('Source inventory changed during loading; reload before running');
    snapshot=data;records.push(...data.records);
    if(data.nextOffset===null)break;
    if(data.nextOffset<=offset)throw Error('Invalid inventory pagination; whole-list execution withheld');
    offset=data.nextOffset;
   }
   if(!snapshot||records.length!==snapshot.total||new Set(records.map(r=>r.key)).size!==records.length)throw Error('Incomplete source inventory; no partial list will be submitted');
   setInventory({...snapshot,records,nextOffset:null});
  }catch(e){if(current===revision.current)setError(e instanceof Error?e.message:'Inventory unavailable');}
  finally{operation.current=false;setBusy(false);}
 }
 async function loadBatch(id:string){
  const current=revision.current;setError('');
  try{const result=await read(api+'?'+new URLSearchParams({batchId:id})) as Batch;
   if(current!==revision.current)return;
   if(result.batchId!==id||result.population!==population)throw Error('Saved cohort identity mismatch; results withheld');setBatch(result);
  }catch(e){if(current===revision.current)setError(e instanceof Error?e.message:'Saved batch unavailable');}
 }
 const historicalCutoffRequired=mode==='BLIND_HISTORICAL'&&!(population==='HISTORICAL'&&scope==='all');
 const allowed=levels.length>0&&(scope==='all'?!!inventory?.total:selected.length>0&&selected.every(valid)&&(scope!=='single'||selected.length===1))&&(!historicalCutoffRequired||!!cutoff);
 async function submit(){
  if(operation.current||!allowed)return;operation.current=true;setBusy(true);setError('');
  const current=revision.current;
  const selection={population,scope:scope==='all'?'all':'selected',ncts:scope==='all'?[]:selected,levels,mode,
   ...(mode==='BLIND_HISTORICAL'&&cutoff?{cutoffDate:cutoff}:{}),...(scope==='all'?{inventoryHash:inventory!.inventoryHash}:{})};
  const signature=JSON.stringify(selection);
  if(pendingRequest.current?.signature!==signature)pendingRequest.current={signature,key:crypto.randomUUID()};
  try{
   const result=await read(api,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'COHORT_BATCH_CREATE',requestKey:pendingRequest.current.key,...selection})}) as Batch;
   if(current!==revision.current)return;
   if(result.population!==population||result.mode!==mode||!result.batchId)throw Error('Saved assessment selection mismatch; completion not confirmed');
   setBatch(result);pendingRequest.current=null;
   setRecent(prev=>[{batchId:result.batchId,createdAt:result.createdAt},...prev.filter(b=>b.batchId!==result.batchId)]);
   if(result.terminal)window.dispatchEvent(new Event('pdufa:assessment-saved'));
  }catch(e){if(current===revision.current)setError(e instanceof Error?e.message:'Batch submission failed');}
  finally{operation.current=false;setBusy(false);}
 }
 async function resume(){
  if(operation.current||!batch)return;operation.current=true;setBusy(true);setError('');
  try{
   await read(api,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'COHORT_BATCH_RESUME',batchId:batch.batchId})});
   await loadBatch(batch.batchId);
  }catch(e){setError(e instanceof Error?e.message:'Resume failed');}
  finally{operation.current=false;setBusy(false);}
 }
 return <section style={{margin:'12px 0',minWidth:0}}>
  <button ref={button} type="button" onClick={()=>setOpen(!open)} aria-expanded={open}>Assess Trials · Levels 1–3</button>
  {open&&<div role="dialog" aria-label="Scientific assessment launcher" aria-modal="false" style={{background:'#fff',color:'#173d2b',border:'2px solid #16856c',padding:16,borderRadius:12,maxWidth:800,marginTop:8,minWidth:0,overflowWrap:'anywhere'}}>
   <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',flexWrap:'wrap',gap:12}}><h2>Assess one trial or the whole list</h2><div><button type="button" disabled={busy} onClick={clear}>Clear selections</button>{' '}<button type="button" aria-label="Close assessment popup" onClick={()=>{setOpen(false);button.current?.focus();}}>Close</button></div></div>
   <p>Levels 1–3 save separate reports for trial verification, clinical design, and efficacy/statistics. Batch progress is saved on the server and continues when this popup closes.</p>
   <fieldset disabled={busy}><legend>Choose trials</legend>
    <label>Source <select aria-label="Assessment source" value={population} onChange={e=>changePopulation(e.target.value as Population)}>{(['FOCUS','HISTORICAL','POOL'] as Population[]).map(p=><option key={p} value={p}>{label(p)}</option>)}</select></label>{' '}
    <label>Scope <select aria-label="Assessment scope" value={scope} onChange={e=>{setScope(e.target.value);setInventory(null);setError('');}}><option value="single">Single trial</option><option value="selected">Selected trials</option><option value="all">Whole {label(population)} list</option></select></label>
    {scope==='all'?<div><p><button type="button" onClick={()=>void loadInventory()}>Load complete {label(population)} inventory</button></p>
     {inventory&&<><p role="status">{inventory.total} {population==='HISTORICAL'?'source events':'exact trials'} loaded · {inventory.blocked} blocked by missing identity links. {human(inventory.source.status)}.</p>
      {inventory.blocked>0&&<details><summary>Show missing trial links</summary><ul>{inventory.records.filter(r=>r.blocker).map(r=><li key={r.key}>{r.key}: {r.blocker}</li>)}</ul></details>}</>}
    </div>:<p><label>Exact NCT {scope==='single'?'identifier':'identifiers, separated by commas or lines'}<textarea aria-label="Assessment NCT IDs" style={{display:'block',boxSizing:'border-box',width:'100%',minHeight:60}} value={input} onChange={e=>setInput(e.target.value)}/></label>{scope==='single'&&selected.length>1&&<span role="alert">Select one NCT or change scope to Selected trials.</span>}</p>}
   </fieldset>
   <fieldset disabled={busy}><legend>Assessment levels</legend>{[1,2,3].map(l=><label key={l} style={{display:'inline-block',marginRight:16}}><input type="checkbox" checked={levels.includes(l)} onChange={e=>setLevels(prev=>e.target.checked?[...prev,l].sort():prev.filter(v=>v!==l))}/> L0{l}</label>)}</fieldset>
   <p><label>Evidence mode <select aria-label="Batch evidence mode" disabled={busy||population==='HISTORICAL'} value={mode} onChange={e=>setMode(e.target.value)}><option value="CURRENT_EVIDENCE">Current evidence</option><option value="BLIND_HISTORICAL">Historical evidence before cutoff</option></select></label></p>
   {mode==='BLIND_HISTORICAL'&&<p><label>{historicalCutoffRequired?'Required evidence cutoff':'Optional common cutoff; otherwise 30 days before each verified decision'} <input aria-label="Batch historical cutoff" type="date" disabled={busy} value={cutoff} onChange={e=>setCutoff(e.target.value)}/></label></p>}
   {population==='HISTORICAL'&&<p>PAST includes every event in the dated queue. Missing exact trial/application links or original pre-cutoff evidence stay BLOCKED and count separately. Historical source isolation does not certify that the researcher was unaware of the outcome.</p>}
   <button type="button" disabled={busy||!allowed} onClick={()=>void submit()}>{busy?'Saving request…':'Submit assessments'}</button>
   {error&&<p role="alert">{error}</p>}
   {recent.length>0&&<p><label>Saved batches <select aria-label="Saved assessment batches" value={batch?.batchId||''} onChange={e=>{if(e.target.value)void loadBatch(e.target.value);}}><option value="">Choose saved progress</option>{recent.map(b=><option key={b.batchId} value={b.batchId}>{b.createdAt} · {b.batchId.slice(0,8)}</option>)}</select></label></p>}
   {batch&&<section aria-label="Saved batch progress" aria-live="polite"><h3>{label(batch.population)} · {batch.counts.completed}/{batch.totalItems} reports saved</h3>
    <p>{batch.totalTrials} {batch.population==='HISTORICAL'?'source events':'trials'} · {human(batch.status)} · {batch.counts.blocked} blocked · {batch.counts.failed} failed · {batch.counts.scored} validated numerical scores.</p>
    <p>Saved reports with evidence gaps remain incomplete scientific assessments. FDA predictions without a validated model remain ABSTAIN.</p>
    {batch.canResume&&<button type="button" disabled={busy} onClick={()=>void resume()}>Resume saved batch</button>}{' '}
    <button type="button" onClick={()=>void loadBatch(batch.batchId)}>Refresh batch status</button>
    <details><summary>Show each trial and level</summary><ul style={{maxHeight:420,overflow:'auto'}}>{batch.items.map(i=><li key={i.key+'|'+i.level}>{i.nct||i.key} · L0{i.level} · {human(i.state)}{i.error&&' · '+i.error}{i.reportHash&&i.nct&&<> · <a href={'/assessments?nct='+encodeURIComponent(i.nct)}>Saved report and history</a></>}</li>)}</ul></details>
    <small>Batch {batch.batchId}</small>
   </section>}
  </div>}
 </section>;
}
