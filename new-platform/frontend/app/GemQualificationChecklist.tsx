"use client";
import {useMemo, useRef, useState} from "react";
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
  sourceKind: "PIPELINE" | "GEM_JR";
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
export default function GemQualificationChecklist({stage,pipeline,asOf,stageTotal,gemJrCandidates,onScan,onReset}:{stage:"GEM_JR"|"GEM";pipeline:Trial[];asOf:string;stageTotal:number;gemJrCandidates:Trial[];onScan:(result:GemScanResult)=>void;onReset:()=>void}) {
 const [selected,setSelected]=useState<string[]>([]);
 const [showSuggestions,setShowSuggestions]=useState(false);
 const [result,setResult]=useState<GemScanResult|null>(null);
 const [optionalGoals,setOptionalGoals]=useState<Record<string,string>>(()=>Object.fromEntries(OPTIONAL_ALL.map(a=>[a.key,a.goal])));
 const [twoTrialIds,setTwoTrialIds]=useState<[string,string]>(["",""]);
 const twoTrialError=stage==="GEM_JR"&&selected.includes("two_trial")?twoTrialInputError(twoTrialIds):null;
 const [open,setOpen]=useState(true);
 const [running,setRunning]=useState(false);
 const [message,setMessage]=useState("");
 const runSequence=useRef(0);
 const phase3ResearchCount=pipeline.filter(completedPhase3).length;
 // GEM can screen the exact saved GEM JR list, without reclassifying any
 // candidate or substituting a ticker-level match for a program identity.
 const useGemJrSource=stage==="GEM"&&selected.includes("gem_jr_source");
 const sourceRows=useGemJrSource?gemJrCandidates:pipeline;
 const sourceLabel=useGemJrSource?"saved GEM JR candidates":"PIPELINE records";
 // Use the same criterion evaluators for the live intersection count and
 // the full SCAN audit, so the two result totals cannot disagree.
 const chosen=useMemo(() => {
   const checked=new Set(selected);
   const checks:[string,string,(x:Trial)=>boolean|null][]=criteria.filter(([key])=>checked.has(key));
   if(stage==="GEM_JR")for(const item of OPTIONAL_ALL){
     if(!checked.has(item.key))continue;
     // A screening target or an NCT ID is not verification of an FDA/clinical
     // fact. These optional alerts remain UNKNOWN until sourced evidence exists.
     const goal=item.key==="two_trial"
       ? "trial 1 "+normalizeTrialId(twoTrialIds[0])+"; trial 2 "+normalizeTrialId(twoTrialIds[1])+"; verify independent pivotal evidence"
       : (optionalGoals[item.key]||"unset")+" "+item.unit;
     checks.push([item.key,item.title+" (goal: "+goal+")",()=>null]);
   }
   return checks;
 },[selected,stage,optionalGoals,twoTrialIds]);
 const liveCounts=useMemo(() => {
   let passes=0,needsReview=0,fails=0;
   for(const row of sourceRows){
     let hasFail=false,hasUnknown=false;
     for(const [, , evaluate] of chosen){
       const status=evaluate(row);
       if(status===false){hasFail=true;break;}
       if(status===null)hasUnknown=true;
     }
     if(hasFail)fails++;
     else if(hasUnknown)needsReview++;
     else passes++;
   }
   return {passes,needsReview,fails,total:passes+needsReview};
 },[sourceRows,chosen]);
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
   if(running)return;
   if(!sourceRows.length){
     setMessage(useGemJrSource?"No saved GEM JR candidates are available. GEM scan was not run.":"No PIPELINE candidates are loaded.");
     return;
   }
   if(twoTrialError){
     setMessage("Two-Trial Paradigm: "+twoTrialError);
     return;
   }
   setRunning(true);
   setMessage("Running selected requirements across "+sourceRows.length.toLocaleString("en-US")+" "+sourceLabel+"…");
   setResult(null);
   onReset();
   // Paint SCANNING before the CPU-bound saved-data evaluation begins.
   await new Promise<void>(resolve=>setTimeout(resolve,25));
   try{
     const audits:GemCriterionAudit[]=chosen.map(([key,label])=>({key,label,passed:0,failed:0,unknown:0}));
     const passes:Trial[]=[],fails:Trial[]=[],needsReview:Trial[]=[];
     for(const record of sourceRows){
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
       sourceKind:useGemJrSource?"GEM_JR":"PIPELINE",
       runNumber,audits,baseline:sourceRows.length,selected:[...selected],passes,needsReview,fails
     };
     setResult(next);
     onScan(next);
     setMessage("Run #"+runNumber+" completed at "+new Date(next.evaluatedAt).toLocaleTimeString()+
       " — "+sourceRows.length.toLocaleString("en-US")+" "+sourceLabel+" evaluated; "+
       (audits.length?"selected requirements applied":"no qualification restrictions")+".");
   }catch(error){
     setMessage("Scan failed: "+(error instanceof Error?error.message:"Unknown error"));
   }finally{setRunning(false)}
 }

 return <section className="panel" aria-label={(stage==="GEM"?"GEM":"GEM JR")+" qualification checklist"} style={{margin:"18px 0",padding:16,border:"2px solid #236847",borderRadius:10,background:"#f8fff8",color:"#163522"}}>
 <button type="button" onClick={()=>setOpen(!open)} aria-expanded={open} style={{width:"100%",textAlign:"left",fontWeight:800,fontSize:18,padding:10,background:"#d9efdf",color:"#123b25",border:"1px solid #6c9e78",borderRadius:6}}>{open?"▾":"▸"} {stage==="GEM"?"GEM":"GEM JR"} — 17 qualification requirements{stage==="GEM_JR"?" + 10 optional evidence alerts":""} ({selected.length} selected)</button>

 <div role="status" style={{display:"flex",gap:12,flexWrap:"wrap",marginTop:12,marginBottom:12}}><div style={{padding:"10px 14px",background:"#e4f3e8",borderRadius:6}}><strong style={{fontSize:22}}>{pipeline.length.toLocaleString("en-US")}</strong><div>Pipeline research candidates (all stages)</div></div><div style={{padding:"10px 14px",background:"#e4f3e8",borderRadius:6}}><strong style={{fontSize:22}}>{stageTotal.toLocaleString("en-US")}</strong><div>{stage==="GEM"?"GEM":"GEM JR"} candidates</div></div><div style={{padding:"10px 14px",background:"#e4f3e8",borderRadius:6}}><strong style={{fontSize:22}}>{sourceRows.length.toLocaleString("en-US")}</strong><div>{useGemJrSource?"Saved GEM JR input records":"Full PIPELINE records available to scan"}</div></div></div>
 {open&&<><p>Every SCAN evaluates {sourceRows.length.toLocaleString("en-US")} {sourceLabel} against <strong>only your selected qualification checkboxes</strong>. No boxes selected means an unrestricted scan. Phase 3 is not silently required; select its checkbox to enforce verified Phase 3 success. The source has {phase3ResearchCount.toLocaleString("en-US")} Phase 3/readout indicators, which are not the same as independently verified successful Phase 3 programs. Unknown source evidence is not treated as passing. Published data as of {asOf||"unverified"}; no live-market fetches, membership changes or trades.</p>
 {stage==="GEM_JR"&&<div style={{marginBottom:14,border:"1px solid #b8d4c0",borderRadius:8,padding:12,background:"#ffffff"}}>
   <h3 style={{margin:"0 0 7px"}}>Optional GEM JR evidence alerts</h3>
   <p style={{fontSize:13,margin:"0 0 10px"}}>Optional checks are off by default. Enter your desired threshold in the boxed goal column, or choose a goal. This is your screening target, not a verified result. Checked alerts without sourced application-specific evidence report NEEDS VERIFICATION, never PASS.</p>
   <div style={{display:"grid",gridTemplateColumns:"repeat(2,minmax(0,1fr))",gap:12,alignItems:"start"}}>
   {OPTIONAL_GROUPS.map(group=><details key={group.heading} open style={{marginBottom:8,border:"1px solid #d6e7dc",borderRadius:5}}>
     <summary style={{padding:9,fontWeight:700,cursor:"pointer"}}>{group.heading}</summary>
     <div style={{overflowX:"auto",padding:8}}>
       <table style={{width:"100%",borderCollapse:"collapse",fontSize:12,minWidth:0}}>
         <thead><tr><th style={{textAlign:"left",width:45}}>Use</th><th style={{textAlign:"left"}}>Indicator</th><th style={{textAlign:"left",width:"45%"}}>Goal / options</th><th style={{textAlign:"left"}}>Evidence</th></tr></thead>
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
   </div>
 </div>}

 <p style={{fontSize:13,margin:"0 0 9px",fontWeight:650}}>All checkboxes start unchecked. In GEM JR, earlier recommendations have green Suggested labels beside their names (regardless of what you check). FS toggles highlighting without selecting boxes; DESELECT ALL clears all selections.</p>
 <div style={{display:"grid",gridTemplateColumns:"repeat(2,minmax(0,1fr))",gap:9,marginBottom:14}}>
 {stage==="GEM"&&<label key="gem_jr_source" style={{display:"flex",gap:8,alignItems:"flex-start",padding:8,border:"1px solid #c1d8c8",borderRadius:5,background:"white",gridColumn:"1"}}>
   <input type="checkbox" aria-label="Gem Jr Trials (optional)" checked={useGemJrSource} onChange={()=>toggle("gem_jr_source")} disabled={running} />
   <span>Gem Jr Trials <small style={{fontSize:12,color:"#175a35",fontWeight:700}}>Optional</small>
     {useGemJrSource&&gemJrCandidates.length===0&&<small role="alert" style={{display:"block",color:"#9b2828",fontWeight:700}}>No saved GEM JR trials available — cannot run the scan.</small>}
   </span>
 </label>}
 {criteria.map(([key,label])=>{const recommended=suggestedByStage[stage].includes(key);const highlighted=showSuggestions&&recommended;return <label key={key} style={{display:"flex",gap:8,alignItems:"flex-start",padding:8,border:highlighted?"2px solid #2d8a56":"1px solid #c1d8c8",borderRadius:5,background:highlighted?"#e4f5e9":"white"}}><input type="checkbox" checked={selected.includes(key)} onChange={()=>toggle(key)}/><span>{label}{recommended&&(stage==="GEM_JR"||showSuggestions)&&<small style={{display:"inline",marginLeft:8,fontSize:11,color:"#175a35",fontWeight:700}}>Suggested</small>}</span></label>})}</div>

 <div role="status" aria-live="polite" aria-label="Combined count for all checked GEM qualification requirements" style={{border:"1px solid #9dbda5",borderRadius:8,padding:12,marginBottom:14,background:"#f1f9f2"}}>
   <strong style={{display:"block",marginBottom:7}}>LIVE COMBINED RESULT — {selected.length.toLocaleString("en-US")} checked {selected.length===1?"option":"options"} (all selected requirements together)</strong>
   <div style={{display:"flex",gap:14,flexWrap:"wrap",alignItems:"baseline"}}>
     <span><strong style={{fontSize:24}}>{liveCounts.total.toLocaleString("en-US")}</strong> not ruled out</span>
     <span><strong>{liveCounts.passes.toLocaleString("en-US")}</strong> verified matches</span>
     <span><strong>{liveCounts.needsReview.toLocaleString("en-US")}</strong> need evidence</span>
     <span><strong>{liveCounts.fails.toLocaleString("en-US")}</strong> excluded</span>
   </div>
   <small style={{display:"block",marginTop:6}}>{sourceRows.length.toLocaleString("en-US")} {sourceLabel} considered. {chosen.length===0?"No qualification filters selected; the entire input qualifies for review.":"All checked qualification rules must pass together. Unknown evidence is counted for review, never as a verified pass."} These numbers update when checkboxes change; SCAN displays the detailed results.</small>
 </div>
 <div style={{display:"flex",gap:12,flexWrap:"wrap"}}><button type="button" onClick={()=>void scan()} disabled={running||!sourceRows.length} style={{background:"#135a32",color:"white",padding:"10px 20px",borderRadius:6,fontWeight:700}}>{running?"SCANNING…":"SCAN "+(stage==="GEM"?"GEM":"GEM JR")}</button><div aria-label="Unrestricted Phase 3 baseline" title="Historical approximate count; not verified live" style={{display:"flex",alignItems:"center",gap:8,padding:"8px 14px",border:"2px solid #1d6d4b",borderRadius:6,background:"#effaf3"}}><strong style={{fontSize:24}}>~730</strong><span style={{fontSize:12}}>Phase 3 completed<br/>Before restrictions</span></div><button type="button" onClick={()=>selectRequirements([])}>DESELECT ALL</button><button type="button" onClick={()=>setShowSuggestions(value=>!value)} aria-pressed={showSuggestions} aria-label="FS: toggle suggested criteria highlighting" title="FS — toggle suggested criteria highlighting (does not check boxes)" style={{padding:"10px 14px",border:"1px solid #176b39",borderRadius:6,background:showSuggestions?"#ffffff":"#176b39",color:showSuggestions?"#176b39":"#ffffff",fontWeight:700}}>FS</button></div>


 <p role="status" aria-live="polite" style={{fontWeight:700,marginTop:12}}>{message||"Ready to scan "+sourceRows.length.toLocaleString("en-US")+" "+sourceLabel+"."}</p>
 {result&&<div role="status" style={{marginTop:15,padding:12,background:"#e8f2ec",borderRadius:6}}>
  <strong>{result.sourceKind==="GEM_JR"?"Saved GEM JR":"Full PIPELINE"} evidence screen complete · Run #{result.runNumber}</strong>
  <p>{result.baseline.toLocaleString("en-US")} {result.sourceKind==="GEM_JR"?"GEM JR candidates":"PIPELINE records"} evaluated · {result.passes.length.toLocaleString("en-US")} {result.audits.length?"passed all checked requirements":"unrestricted matches"} · {result.fails.length.toLocaleString("en-US")} failed · {result.needsReview.length.toLocaleString("en-US")} need verification. Completed at {new Date(result.evaluatedAt).toLocaleTimeString()}.</p>
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
