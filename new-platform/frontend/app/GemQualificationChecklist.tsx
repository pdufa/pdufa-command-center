"use client";
import {useRef, useState} from "react";
import type {Candidate} from "./Workspace";
import {normalizeTrialId, twoTrialInputError} from "../lib/two-trial-programs";

type Trial = Candidate;
export type GemCriterionAudit = {key:string;label:string;passed:number;failed:number;unknown:number};
export type GemScanResult = {
  runNumber:number;
  audits:GemCriterionAudit[];
  asOf: string;
  evaluatedAt: string;
  baseline: number;
  sourceTotal: number;
  selected: string[];
  passes: Candidate[];
  needsReview: Candidate[];
  fails: Candidate[];
};
function completedPhase3(row:Trial) {
  const facts=row.trialFilters;
  const evidencePhase3=facts?.registeredPhase==="Phase 3" ||
    /^Phase 3(?: Results)?$/i.test(row.stage||"") ||
    Boolean(row.phase3Date) ||
    row.technical?.benchmarks?.phase3===true;
  if (!evidencePhase3) return false;
  const status=[facts?.trialStatus,row.phase3Status,row.stage].filter(Boolean).join(" ");
  return facts?.resultsReleased===true ||
    facts?.primaryOutcome==="SUCCESS" ||
    row.technical?.benchmarks?.phase3===true ||
    Boolean(row.phase3Date) ||
    /completed|results|readout|primary completion/i.test(status);
}
const criteria:[string,string,(x:Trial)=>boolean|null][]=[
["phase3","Successful Phase 3 independently verified",x=>{
  if(x.technical?.benchmarks?.phase3===true)return true;
  if(x.trialFilters?.primaryOutcome==="SUCCESS"&&x.trialFilters?.resultsReleased===true)return true;
  if(/FAIL|NOT_MET|NEGATIVE/i.test(x.trialFilters?.primaryOutcome||""))return false;
  const registered=x.trialFilters?.registeredPhase||"";
  if(/^(Early Phase 1|Phase 1|Phase 1\/2|Phase 2)$/i.test(registered||x.stage||""))return false;
  return null;
}],
["registry","Phase 3 trial status recorded",x=>x.trialFilters?.registeredPhase==="Phase 3" || /^Phase 3(?: Results)?$/i.test(x.stage||"")?true:x.trialFilters?.registeredPhase?false:null],
["issuer","Issuer Phase 3 evidence linked",x=>x.phase3Source? /^https:\/\//.test(x.phase3Source):null],
["financing","Second financing verified (optional)",x=>x.technical?.benchmarks?.secondFinancing??x.trialFilters?.secondFinancingClosed??null],
["cash","SEC cash runway ≥12 months",x=>{const n=x.technical?.runwayMonths??x.trialFilters?.runwayMonths;return n==null?null:n>=12}],
["dilution","No unresolved dilution",x=>{const d=x.trialFilters?.dilution?.trim().toUpperCase();return !d?null:/^(NO|NONE|CLEAR|RESOLVED|NO UNRESOLVED)$/.test(d)?true:/UNRESOLVED|ACTIVE|AT RISK/.test(d)?false:null}],
["marketcap","Market cap $300M–$10B (optional)",x=>x.marketCap==null?null:x.marketCap>=300e6&&x.marketCap<=10e9],
["pdufa","Verified PDUFA date source",x=>x.pdufaDate&&x.fdaSource?/^https:\/\//.test(x.fdaSource):null],
["window","PDUFA in next 30–90 days",x=>{if(!x.pdufaDate)return null;const n=(Date.parse(x.pdufaDate.slice(0,10)+"T00:00:00Z")-Date.now())/86400000;return Number.isFinite(n)?n>=30&&n<=90:null}],
["volume","Relative volume ≥1.5×",x=>x.technical?.rvol==null?null:x.technical.rvol>=1.5],
["rsi","RSI 45–65",x=>x.technical?.rsi14==null?null:x.technical.rsi14>=45&&x.technical.rsi14<=65],
["trend","Close above SMA20 and SMA50",x=>{const t=x.technical;return t?.close==null||t.sma20==null||t.sma50==null?null:t.close>t.sma20&&t.close>t.sma50}],
["liquidity","20-day average dollar volume ≥$5M",x=>x.technical?.avgDollarVolume20==null?null:x.technical.avgDollarVolume20>=5000000],
["marketfresh","Current market evidence",x=>x.technical?.eodFresh??null],
["insiders","Insider buying verified",()=>null],
["institutions","Institutional accumulation verified",()=>null],
["sec","Fresh SEC source reconciliation",()=>null]
];
type OptionalAlert = {key:string;title:string;goal:string;unit:string;options?:string[];number?:boolean};
const OPTIONAL_GROUPS:{heading:string;items:OptionalAlert[]}[]=[
 {heading:"1. Identify Regulatory Fast-Track Indicators",items:[
  {key:"priority_review",title:"Priority Review",goal:"6",unit:"month FDA review goal",number:true},
  {key:"breakthrough_rmat",title:"Breakthrough Therapy / RMAT",goal:"Either designation verified",unit:"designation",options:["Either designation verified","Breakthrough Therapy","RMAT"]},
  {key:"star_pilot",title:"STAR Pilot Program",goal:"FDA participation verified",unit:"participation",options:["FDA participation verified","FDA announcement","Official correspondence"]}]},
 {heading:"2. Evaluate Clinical Trial Data Strength",items:[
  {key:"statistical_significance",title:"Statistical Significance",goal:"0.05",unit:"maximum adjusted p-value",number:true},
  {key:"two_trial",title:"The Two-Trial Paradigm",goal:"2",unit:"distinct pivotal trials"},
  {key:"safety_cleanliness",title:"Safety Cleanliness",goal:"No material safety imbalance",unit:"safety criterion",options:["No material safety imbalance","SAE risk difference reviewed","FDA safety review favorable"]}]},
 {heading:"3. Track Advisory Committee (AdCom) Scheduling",items:[
  {key:"no_adcom",title:"No AdCom Scheduled",goal:"FDA confirms no meeting planned",unit:"AdCom evidence",options:["FDA confirms no meeting planned","No meeting announced (unconfirmed)"]},
  {key:"favorable_adcom",title:"Favorable AdCom Vote",goal:"0.5",unit:"minimum favorable vote fraction (0–1)",number:true}]},
 {heading:"4. Analyze Commercial Viability & Competition",items:[
  {key:"orphan_unmet",title:"Unmet Medical Need / Orphan Status",goal:"FDA orphan designation confirmed",unit:"evidence",options:["FDA orphan designation confirmed","Unmet need independently supported","Both verified"]},
  {key:"tam",title:"Large Addressable Market (TAM)",goal:"1000000000",unit:"minimum annual TAM in USD",number:true}]}
];
const OPTIONAL_ALL=OPTIONAL_GROUPS.flatMap(group=>group.items);
const suggestedByStage:Record<"GEM_JR"|"GEM",string[]>={GEM_JR:["phase3","registry","issuer","cash","marketfresh"],GEM:["phase3","registry","issuer","cash","pdufa","window","volume","rsi","trend","liquidity","marketfresh"]};
export default function GemQualificationChecklist({stage,pipeline,asOf,stageTotal,onScan,onReset}:{stage:"GEM_JR"|"GEM";pipeline:Trial[];asOf:string;stageTotal:number;onScan:(result:GemScanResult)=>void;onReset:()=>void}) {
 const [selected,setSelected]=useState<string[]>(()=>[...suggestedByStage[stage]]);
 const [result,setResult]=useState<GemScanResult|null>(null);
 const [optionalGoals,setOptionalGoals]=useState<Record<string,string>>(()=>Object.fromEntries(OPTIONAL_ALL.map(a=>[a.key,a.goal])));
 const [twoTrialIds,setTwoTrialIds]=useState<[string,string]>(["",""]);
 const twoTrialError=stage==="GEM_JR"&&selected.includes("two_trial")?twoTrialInputError(twoTrialIds):null;
 const [open,setOpen]=useState(true);
 const [running,setRunning]=useState(false);
 const [message,setMessage]=useState("");
 const runSequence=useRef(0);
 const phase3ResearchCount=pipeline.filter(completedPhase3).length;
 function selectRequirements(next:string[]){
   if(running)return;
   setSelected(next);
   setResult(null);
   setMessage("Selections updated. Press SCAN to evaluate these requirements.");
   onReset();
 }
 function toggle(key:string){selectRequirements(selected.includes(key)?selected.filter(x=>x!==key):[...selected,key])}
 function setTwoTrialId(index:0|1,value:string){
   const normalized=value.toUpperCase();
   setTwoTrialIds(current=>index===0?[normalized,current[1]]:[current[0],normalized]);
   setResult(null);
   setMessage("Trial IDs updated. Press SCAN after entering two distinct registered trials.");
   onReset();
 }
 async function scan(){
   if(running||!pipeline.length)return;
   if(twoTrialError){
     setMessage("Two-Trial Paradigm: "+twoTrialError);
     return;
   }
   setRunning(true);
   setMessage("Running the selected requirements across the full loaded PIPELINE…");
   setResult(null);
   onReset();
   // Paint SCANNING before the CPU-bound saved-data evaluation begins.
   await new Promise<void>(resolve=>setTimeout(resolve,25));
   try{
     const chosen:[string,string,(x:Trial)=>boolean|null][]=criteria.filter(([key])=>selected.includes(key));
     if(stage==="GEM_JR")for(const item of OPTIONAL_ALL){if(selected.includes(item.key)){
       // An operator target is not evidence. Until exact-program sourced fields are
       // published and verified, this optional check must remain UNKNOWN.
       const goal=item.key==="two_trial"
         ? "trial 1 "+normalizeTrialId(twoTrialIds[0])+"; trial 2 "+normalizeTrialId(twoTrialIds[1])+"; verify independent pivotal evidence"
         : (optionalGoals[item.key]||"unset")+" "+item.unit;
       chosen.push([item.key,item.title+" (goal: "+goal+")",()=>null]);
     }}
     const audits:GemCriterionAudit[]=chosen.map(([key,label])=>({key,label,passed:0,failed:0,unknown:0}));
     const passes:Trial[]=[],fails:Trial[]=[],needsReview:Trial[]=[];
     for(const record of pipeline){
       let hasFail=false,hasUnknown=false;
       for(let i=0;i<chosen.length;i++){
         const status=chosen[i][2](record);
         if(status===true)audits[i].passed++;
         else if(status===false){audits[i].failed++;hasFail=true;}
         else {audits[i].unknown++;hasUnknown=true;}
       }
       if(hasFail)fails.push(record);
       else if(hasUnknown)needsReview.push(record);
       else passes.push(record);
     }
     const runNumber=++runSequence.current;
     const next:GemScanResult={
       asOf,evaluatedAt:new Date().toISOString(),sourceTotal:pipeline.length,
       runNumber,audits,baseline:pipeline.length,selected:[...selected],passes,needsReview,fails
     };
     setResult(next);
     onScan(next);
     setMessage("Run #"+runNumber+" completed at "+new Date(next.evaluatedAt).toLocaleTimeString()+
       " — "+(selected.length?"selected requirements applied":"no restrictions; all records included")+".");
   }catch(error){
     setMessage("Scan failed: "+(error instanceof Error?error.message:"Unknown error"));
   }finally{setRunning(false)}
 }

 return <section className="panel" aria-label={(stage==="GEM"?"GEM":"GEM JR")+" qualification checklist"} style={{margin:"18px 0",padding:16,border:"2px solid #236847",borderRadius:10,background:"#f8fff8",color:"#163522"}}>
 <button type="button" onClick={()=>setOpen(!open)} aria-expanded={open} style={{width:"100%",textAlign:"left",fontWeight:800,fontSize:18,padding:10,background:"#d9efdf",color:"#123b25",border:"1px solid #6c9e78",borderRadius:6}}>{open?"▾":"▸"} {stage==="GEM"?"GEM":"GEM JR"} — 17 qualification requirements{stage==="GEM_JR"?" + 10 optional evidence alerts":""} ({selected.length} selected)</button>

 <div role="status" style={{display:"flex",gap:12,flexWrap:"wrap",marginTop:12,marginBottom:12}}><div style={{padding:"10px 14px",background:"#e4f3e8",borderRadius:6}}><strong style={{fontSize:22}}>{pipeline.length.toLocaleString("en-US")}</strong><div>Pipeline research candidates (all stages)</div></div><div style={{padding:"10px 14px",background:"#e4f3e8",borderRadius:6}}><strong style={{fontSize:22}}>{stageTotal.toLocaleString("en-US")}</strong><div>{stage==="GEM"?"GEM":"GEM JR"} candidates</div></div><div style={{padding:"10px 14px",background:"#e4f3e8",borderRadius:6}}><strong style={{fontSize:22}}>{pipeline.length.toLocaleString("en-US")}</strong><div>Full source records available to scan</div></div></div>
 {open&&<><p>Every SCAN evaluates all {pipeline.length.toLocaleString("en-US")} currently loaded PIPELINE records against <strong>only your selected checkboxes</strong>. No boxes selected means an unrestricted scan. Phase 3 is not silently required; select its checkbox to enforce verified Phase 3 success. The source has {phase3ResearchCount.toLocaleString("en-US")} Phase 3/readout indicators, which are not the same as independently verified successful Phase 3 programs. Unknown source evidence is not treated as passing. Published data as of {asOf||"unverified"}; no live-market fetches, membership changes or trades.</p>
 <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(230px,1fr))",gap:9,marginBottom:14}}>{criteria.map(([key,label])=><label key={key} style={{display:"flex",gap:8,alignItems:"flex-start",padding:8,border:"1px solid #c1d8c8",borderRadius:5,background:"white"}}><input type="checkbox" checked={selected.includes(key)} onChange={()=>toggle(key)}/><span>{label}</span></label>)}</div>

 {stage==="GEM_JR"&&<div style={{marginBottom:14,border:"1px solid #b8d4c0",borderRadius:8,padding:12,background:"#ffffff"}}>
   <h3 style={{margin:"0 0 7px"}}>Optional GEM JR evidence alerts</h3>
   <p style={{fontSize:13,margin:"0 0 10px"}}>Optional checks are off by default. Enter your desired threshold in the boxed goal column, or choose a goal. This is your screening target, not a verified result. Checked alerts without sourced application-specific evidence report NEEDS VERIFICATION, never PASS.</p>
   {OPTIONAL_GROUPS.map(group=><details key={group.heading} open style={{marginBottom:8,border:"1px solid #d6e7dc",borderRadius:5}}>
     <summary style={{padding:9,fontWeight:700,cursor:"pointer"}}>{group.heading}</summary>
     <div style={{overflowX:"auto",padding:8}}>
       <table style={{width:"100%",borderCollapse:"collapse",fontSize:13,minWidth:570}}>
         <thead><tr><th style={{textAlign:"left",width:45}}>Use</th><th style={{textAlign:"left"}}>Indicator</th><th style={{textAlign:"left",width:"40%"}}>Goal / options</th><th style={{textAlign:"left"}}>Evidence</th></tr></thead>
         <tbody>{group.items.map(item=><tr key={item.key}>
           <td style={{padding:7,borderTop:"1px solid #e5eee7"}}><input aria-label={"Include "+item.title} type="checkbox" checked={selected.includes(item.key)} onChange={()=>toggle(item.key)} /></td>
           <td style={{padding:7,borderTop:"1px solid #e5eee7",paddingLeft:15}}>{item.title}</td>
           <td style={{padding:7,borderTop:"1px solid #e5eee7"}}>
             <div style={{border:"1px solid #7a9c81",borderRadius:5,padding:6,background:"#f3faf5"}}>
               {item.key==="two_trial"?
                 <div>
                   <strong style={{display:"block",marginBottom:6}}>Goal: 2 separate successful pivotal trials</strong>
                   {selected.includes("two_trial")?([0,1] as const).map(index=><label key={index} style={{display:"block",marginBottom:8,fontSize:12}}>
                     {"Trial "+(index+1)+" — NCT ID"}
                     <input type="text" value={twoTrialIds[index]} maxLength={11} placeholder={"NCT"+(index===0?"12345678":"87654321")}
                       autoComplete="off" aria-label={"Two-Trial Paradigm Trial "+(index+1)+" NCT ID"}
                       aria-invalid={Boolean(twoTrialError&&twoTrialIds[index])}
                       onChange={event=>setTwoTrialId(index,event.target.value)}
                       style={{display:"block",marginTop:3,width:"100%",padding:6,boxSizing:"border-box"}}/>
                   </label>):<small style={{display:"block",marginBottom:7}}>Select this checkbox to enter two trial IDs.</small>}
                   {selected.includes("two_trial")&&twoTrialError&&<small role="alert" style={{display:"block",color:"#8b2222"}}>{twoTrialError}</small>}
                   <small style={{display:"block"}}>Enter two distinct ClinicalTrials.gov studies. IDs alone do not verify success.</small>
                 </div>:
                item.number?<input aria-label={item.title+" target"} type="number" step="any" min="0" value={optionalGoals[item.key]??item.goal}
                 onChange={event=>{setOptionalGoals(current=>({...current,[item.key]:event.target.value}));setResult(null);onReset();}}
                 style={{width:"100%",padding:5,boxSizing:"border-box"}}/>:
                 <select aria-label={item.title+" goal"} value={optionalGoals[item.key]??item.goal} onChange={event=>{setOptionalGoals(current=>({...current,[item.key]:event.target.value}));setResult(null);onReset();}}
                   style={{width:"100%",padding:5}}>{item.options?.map(choice=><option key={choice} value={choice}>{choice}</option>)}</select>}
               <small style={{display:"block",marginTop:3}}>{item.unit}</small>
             </div>
           </td>
           <td style={{padding:7,borderTop:"1px solid #e5eee7"}}>{item.key==="two_trial"&&selected.includes("two_trial")&&twoTrialError?"IDs incomplete":"Needs verification"}</td>
         </tr>)}</tbody>
       </table>
     </div>
   </details>)}
 </div>}
 <div style={{display:"flex",gap:12,flexWrap:"wrap"}}><button type="button" onClick={()=>void scan()} disabled={running||!pipeline.length} style={{background:"#135a32",color:"white",padding:"10px 20px",borderRadius:6,fontWeight:700}}>{running?"SCANNING…":"SCAN "+(stage==="GEM"?"GEM":"GEM JR")}</button><div aria-label="Unrestricted Phase 3 baseline" title="Historical approximate count; not verified live" style={{display:"flex",alignItems:"center",gap:8,padding:"8px 14px",border:"2px solid #1d6d4b",borderRadius:6,background:"#effaf3"}}><strong style={{fontSize:24}}>~730</strong><span style={{fontSize:12}}>Phase 3 completed<br/>Before restrictions</span></div><button type="button" onClick={()=>selectRequirements([])}>Clear selections</button><button type="button" onClick={()=>selectRequirements([...suggestedByStage[stage]])} style={{padding:"10px 14px",border:"1px solid #1d6d4b",borderRadius:6,background:"#e4f3e8",fontWeight:700}}>SUGGESTED</button></div>


 <p role="status" aria-live="polite" style={{fontWeight:700,marginTop:12}}>{message||"Ready to scan "+pipeline.length.toLocaleString("en-US")+" PIPELINE records."}</p>
 {result&&<div role="status" style={{marginTop:15,padding:12,background:"#e8f2ec",borderRadius:6}}>
  <strong>Full PIPELINE evidence screen complete · Run #{result.runNumber}</strong>
  <p>{result.baseline.toLocaleString("en-US")} PIPELINE records evaluated · {result.passes.length.toLocaleString("en-US")} {result.selected.length?"passed all checked requirements":"unrestricted matches"} · {result.fails.length.toLocaleString("en-US")} failed · {result.needsReview.length.toLocaleString("en-US")} need verification. Completed at {new Date(result.evaluatedAt).toLocaleTimeString()}.</p>
  <p><strong>Applied requirements:</strong> {result.audits.length?result.audits.map(x=>x.label).join(" · "):"None (all records included)"}</p>
  {result.audits.length>0&&<div style={{maxWidth:"100%",overflowX:"auto"}}>
    <table style={{width:"100%",borderCollapse:"collapse",fontSize:13}}>
      <thead><tr><th style={{textAlign:"left"}}>Requirement</th><th>Pass</th><th>Fail</th><th>No evidence</th></tr></thead>
      <tbody>{result.audits.map(a=><tr key={a.key}>
        <td style={{padding:"6px 3px"}}>{a.label}</td>
        <td style={{textAlign:"right",padding:6}}>{a.passed.toLocaleString("en-US")}</td>
        <td style={{textAlign:"right",padding:6}}>{a.failed.toLocaleString("en-US")}</td>
        <td style={{textAlign:"right",padding:6}}>{a.unknown.toLocaleString("en-US")}</td>
      </tr>)}</tbody>
    </table>
  </div>}
  {result.audits.some(a=>a.unknown===result.baseline)&&<p style={{fontWeight:700}}>Some selected requirements have no verifiable evidence for any of these records. They cannot produce verified passes until that evidence is available, regardless of how many times you scan.</p>}
  <p>Passed programs and those needing verification appear in the candidate table below. Scanning does not add records to saved GEM membership.</p>
 </div>}

 </>}</section>
}
