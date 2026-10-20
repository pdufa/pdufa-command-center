"use client";
import {useEffect, useMemo, useRef, useState} from "react";
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
  sourceKind: "PIPELINE" | "GEM_JR" | "GEM_JR_LIVE" | "GEM_JR_UNSCREENED";
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
const suggestedByStage:Record<"GEM_JR"|"GEM",string[]>={GEM_JR:["phase3","registry","issuer","cash","marketfresh"],GEM:["pdufa","window","volume","rsi","trend","liquidity"]};
const FA_CRITERIA=["registry","marketcap"];
// GEM's FA button controls only the existing optional GEM JR source input.
// The GEM JR FA preset and qualification filters remain untouched.
export function toggleGemJrTrialsRequirement(selected:readonly string[]):string[]{
 return selected.includes("gem_jr_source")
   ?selected.filter(key=>key!=="gem_jr_source")
   :[...selected,"gem_jr_source"];
}
// GEM JR owns the FS/FA qualification criteria. GEM only displays the
// downstream checkboxes, while its GEM JR input control remains available.
const GEM_JR_OWNED_CRITERIA=new Set([...suggestedByStage.GEM_JR,...FA_CRITERIA]);
const visibleCriteriaByStage=(stage:"GEM_JR"|"GEM")=>stage==="GEM_JR"?criteria:criteria.filter(([key])=>!GEM_JR_OWNED_CRITERIA.has(key));
type Criterion=typeof criteria[number];
// Display-only partition of the existing original checkboxes. Neither the
// checkbox IDs nor their scan evaluators, FS/FA presets, or defaults change.
const TRADING_KEYS=new Set([
  "financing","cash","dilution","marketcap","window","volume","rsi",
  "trend","liquidity","marketfresh","insiders","institutions","sec"
]);
export function checkboxGroupsForStage(stage:"GEM_JR"|"GEM") {
  const existing=visibleCriteriaByStage(stage);
  const clinical:Criterion[]=existing.filter(([key])=>!TRADING_KEYS.has(key));
  const trading:Criterion[]=existing.filter(([key])=>TRADING_KEYS.has(key));
  if(clinical.length+trading.length!==existing.length ||
    new Set([...clinical,...trading].map(([key])=>key)).size!==existing.length){
    throw Error("Missing or duplicated GEM qualification checkbox");
  }
  return {clinical,trading};
}

export type GemJrLivePreview={asOf:string;sourceTotal:number;selected:string[];passes:Trial[];needsReview:Trial[]};
export type GemJrUiDraft={asOf:string;sourceTotal:number;selected:string[];showSuggestions:boolean;faActive:boolean;fiActive?:boolean;fiSelected?:string[];optionalGoals:Record<string,string>;twoTrialIds:[string,string]};
// Current GEM JR checkbox intersection; UNKNOWN is not a verified PASS.
export function buildGemJrLivePreview(rows:Trial[],checks:[string,string,(x:Trial)=>boolean|null][],asOf:string,sourceTotal:number,inheritedReviewIds:ReadonlySet<string>=new Set()):GemJrLivePreview {
 const passes:Trial[]=[],needsReview:Trial[]=[];
 for(const row of rows){
  let unknown=inheritedReviewIds.has(row.id),failed=false;
  for(const [, ,evaluate] of checks){
   const status=evaluate(row);
   if(status===false){failed=true;break;}
   if(status===null)unknown=true;
  }
  if(!failed)(unknown?needsReview:passes).push(row);
 }
 return {asOf,sourceTotal,selected:checks.map(([key])=>key),passes,needsReview};
}
// GEM JR membership saved to a stage and the research candidate universe
// are not the same list. Never substitute 11 saved for ~694 screened rows.
export function resolveGemJrSource(gemJrScan:GemScanResult|null,livePreview:GemJrLivePreview|null,fullPipeline:Trial[]){
 if(gemJrScan) return {
  rows:[...gemJrScan.passes,...gemJrScan.needsReview],
  reviewIds:new Set(gemJrScan.needsReview.map(row=>row.id)),
  sourceKind:"GEM_JR" as const,
  label:"completed GEM JR combined scan candidates",
  scanAvailable:true
 };
 if(livePreview) return {
  rows:[...livePreview.passes,...livePreview.needsReview],
  reviewIds:new Set(livePreview.needsReview.map(row=>row.id)),
  sourceKind:"GEM_JR_LIVE" as const,
  label:"current GEM JR checkbox screen candidates (not a completed scan)",
  scanAvailable:false
 };
 return {
  rows:fullPipeline,
  // Unscreened research universe never qualifies as passed GEM JR evidence.
  reviewIds:new Set(fullPipeline.map(row=>row.id)),
  sourceKind:"GEM_JR_UNSCREENED" as const,
  label:"full published research universe — no GEM JR screen yet; all need verification",
  scanAvailable:false
 };
}

export default function GemQualificationChecklist({stage,pipeline,asOf,stageTotal,completedScan,gemJrScan,gemJrSavedRows,gemJrLivePreview,gemJrDraft,gemDraft,onGemJrLivePreviewChange,onGemJrDraftChange,onGemLivePreviewChange,onGemDraftChange,onScan,onReset}:{stage:"GEM_JR"|"GEM";pipeline:Trial[];asOf:string;stageTotal:number;completedScan:GemScanResult|null;gemJrScan:GemScanResult|null;gemJrSavedRows:Trial[];gemJrLivePreview?:GemJrLivePreview|null;gemJrDraft?:GemJrUiDraft|null;gemDraft?:GemJrUiDraft|null;onGemLivePreviewChange?:(value:GemJrLivePreview)=>void;onGemDraftChange?:(value:GemJrUiDraft)=>void;onGemJrLivePreviewChange?:(value:GemJrLivePreview)=>void;onGemJrDraftChange?:(value:GemJrUiDraft)=>void;onScan:(result:GemScanResult)=>void;onReset:()=>void}) {
 const storedDraft=stage==="GEM_JR"?gemJrDraft:gemDraft;
 const draft=storedDraft?.asOf===asOf&&storedDraft.sourceTotal===pipeline.length?storedDraft:null;
 const [selected,setSelected]=useState<string[]>(()=>draft?.selected||[]);
 const [showSuggestions,setShowSuggestions]=useState(()=>draft?.showSuggestions||false);
 const [faActive,setFaActive]=useState(()=>draft?.faActive||false);
 // FI is a separate, opt-in set of scan restrictions; FS and FA remain untouched.
 const [fiActive,setFiActive]=useState(()=>draft?.fiActive||false);
 const [fiSelected,setFiSelected]=useState<string[]>(()=>draft?.fiSelected?.filter(key=>suggestedByStage[stage].includes(key))||[]);
 const [result,setResult]=useState<GemScanResult|null>(null);
 const [optionalGoals,setOptionalGoals]=useState<Record<string,string>>(()=>draft?.optionalGoals||Object.fromEntries(OPTIONAL_ALL.map(a=>[a.key,a.goal])));
 const [twoTrialIds,setTwoTrialIds]=useState<[string,string]>(()=>draft?.twoTrialIds||["",""]);
 const twoTrialError=stage==="GEM_JR"&&selected.includes("two_trial")?twoTrialInputError(twoTrialIds):null;
 const [open,setOpen]=useState(true);
 const [running,setRunning]=useState(false);
 const [message,setMessage]=useState("");
 const runSequence=useRef(0);
 const phase3ResearchCount=pipeline.filter(completedPhase3).length;
 // Screen the last GEM JR combined output by exact program identity, never
 // the independent saved membership list or a ticker-level approximation.
 // Both passed and needs-verification candidates feed GEM; failed do not.
 const useGemJrSource=stage==="GEM"&&selected.includes("gem_jr_source");
 const juniorSource=useMemo(()=>resolveGemJrSource(gemJrScan,gemJrLivePreview??null,pipeline),[gemJrScan,gemJrLivePreview,pipeline]);
 const gemJrRows=juniorSource.rows;
 // Saved membership is evidence that GEM JR tracked the exact program,
 // not proof that the user's selected GEM JR screening checks have passed.
 const gemJrNeedsReview=juniorSource.reviewIds;
 const sourceRows=useGemJrSource?gemJrRows:pipeline;
 const sourceLabel=useGemJrSource?juniorSource.label:"PIPELINE records";
 // Use the same criterion evaluators for the live intersection count and
 // the full SCAN audit, so the two result totals cannot disagree.
 const chosen=useMemo(() => {
   // An FI criterion is enforced only while FI is ON. Use one evaluator per
   // unique criterion even if it is also checked in the original FS/FA set.
   const checked=new Set([...selected,...(fiActive?fiSelected:[])]);
   const checks:[string,string,(x:Trial)=>boolean|null][]=visibleCriteriaByStage(stage).filter(([key])=>checked.has(key));
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
 },[selected,fiActive,fiSelected,stage,optionalGoals,twoTrialIds]);
 // GEM JR publishes its preview back to Workspace. Its own output must not
 // invalidate this calculation through the downstream GEM input's review set.
 const inheritedReviewIds=useGemJrSource?gemJrNeedsReview:undefined;
 const livePreview=useMemo(()=>buildGemJrLivePreview(
  sourceRows,chosen,asOf,pipeline.length,inheritedReviewIds
 ),[sourceRows,chosen,asOf,pipeline.length,inheritedReviewIds]);
 useEffect(()=>{
  if(stage==="GEM_JR")onGemJrLivePreviewChange?.(livePreview);
  else onGemLivePreviewChange?.(livePreview);
 },[stage,livePreview,onGemJrLivePreviewChange,onGemLivePreviewChange]);
 useEffect(()=>{
  const draft={asOf,sourceTotal:pipeline.length,selected,showSuggestions,faActive,fiActive,fiSelected,optionalGoals,twoTrialIds};
  if(stage==="GEM_JR")onGemJrDraftChange?.(draft);
  else onGemDraftChange?.(draft);
 },[stage,asOf,pipeline.length,selected,showSuggestions,faActive,fiActive,fiSelected,optionalGoals,twoTrialIds,onGemJrDraftChange,onGemDraftChange]);
 const liveCounts=useMemo(() => {
   if(livePreview){const passes=livePreview.passes.length,needsReview=livePreview.needsReview.length;return {passes,needsReview,fails:sourceRows.length-passes-needsReview,total:passes+needsReview};}
   let passes=0,needsReview=0,fails=0;
   for(const row of sourceRows){
     let hasFail=false,hasUnknown=useGemJrSource&&gemJrNeedsReview.has(row.id);
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
 },[sourceRows,chosen,useGemJrSource,gemJrNeedsReview,livePreview,stage]);
 function selectRequirements(next:string[]){
   if(running)return;
   setSelected(next);
   setResult(null);
   setMessage("Selections updated. Press SCAN to evaluate these requirements.");
   onReset();
 }
 function toggle(key:string){selectRequirements(selected.includes(key)?selected.filter(x=>x!==key):[...selected,key])}
 function toggleFs(){
   if(running)return;
   const suggestions=suggestedByStage[stage];
   // Do not remove the shared "registry" criterion while FA still uses it.
   const next=showSuggestions
     ? selected.filter(key=>!suggestions.includes(key)||(stage==="GEM_JR"&&faActive&&FA_CRITERIA.includes(key)))
     : [...new Set([...selected,...suggestions])];
   setShowSuggestions(!showSuggestions);
   selectRequirements(next);
 }
 function toggleFa(){
   if(running)return;
   if(stage==="GEM"){
     // Both GEM controls update the same optional source selection.
     selectRequirements(toggleGemJrTrialsRequirement(selected));
     return;
   }
   // FA combines the two formerly selected GEM JR defaults.
   // Keep the shared "registry" checkbox when FS is still on.
   const next=faActive
     ? selected.filter(key=>!FA_CRITERIA.includes(key)||(showSuggestions&&suggestedByStage[stage].includes(key)))
     : [...new Set([...selected,...FA_CRITERIA])];
   setFaActive(!faActive);
   selectRequirements(next);
 }
 function toggleFi(){
   if(running)return;
   setFiActive(current=>!current);
   setResult(null);
   setMessage("FI restrictions "+(fiActive?"disabled":"enabled")+". Press SCAN to evaluate the active selections.");
   onReset();
 }
 function toggleFiCriterion(key:string){
   if(running)return;
   setFiSelected(current=>current.includes(key)?current.filter(item=>item!==key):[...current,key]);
   // Checking a restriction turns FI on; removing it does not alter FS/FA.
   if(!fiSelected.includes(key))setFiActive(true);
   setResult(null);
   setMessage("FI selections updated. Press SCAN to evaluate active requirements.");
   onReset();
 }
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
     setMessage(useGemJrSource?(gemJrScan?"The current GEM JR combined scan contains no eligible or review candidates. GEM was not scanned.":"No saved GEM JR programs are available in the current published source snapshot."):"No PIPELINE candidates are loaded.");
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
       let hasFail=false,hasUnknown=useGemJrSource&&gemJrNeedsReview.has(record.id);
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
       sourceKind:useGemJrSource?juniorSource.sourceKind:"PIPELINE",
       runNumber,audits,baseline:sourceRows.length,selected:[...new Set([...selected,...(fiActive?fiSelected:[])])],passes,needsReview,fails
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

 function renderOriginalCheckboxes(items:Criterion[]){
  return items.map(([key,label])=>{const recommended=suggestedByStage[stage].includes(key);const faCriterion=stage==="GEM_JR"&&FA_CRITERIA.includes(key);const highlighted=(showSuggestions&&recommended)||(faActive&&faCriterion);return <label key={key} style={{display:"flex",gap:8,alignItems:"flex-start",padding:8,border:highlighted?"2px solid #2d8a56":"1px solid #c1d8c8",borderRadius:5,background:highlighted?"#e4f5e9":"white"}}><input type="checkbox" checked={selected.includes(key)} onChange={()=>toggle(key)}/><span>{label}{recommended&&(stage==="GEM_JR"||showSuggestions)&&<small style={{display:"inline",marginLeft:8,fontSize:11,color:"#175a35",fontWeight:700}}>Suggested</small>}{faCriterion&&<small style={{display:"inline",marginLeft:8,fontSize:11,color:"#175a35",fontWeight:700}}>FA</small>}</span></label>});
 }

 return <section className="panel" aria-label={(stage==="GEM"?"GEM":"GEM JR")+" qualification checklist"} style={{margin:"18px 0",padding:16,border:"2px solid #236847",borderRadius:10,background:"#f8fff8",color:"#163522"}}>
 <button type="button" onClick={()=>setOpen(!open)} aria-expanded={open} style={{width:"100%",textAlign:"left",fontWeight:800,fontSize:18,padding:10,background:"#d9efdf",color:"#123b25",border:"1px solid #6c9e78",borderRadius:6}}>{open?"▾":"▸"} {stage==="GEM"?"GEM":"GEM JR"} — {visibleCriteriaByStage(stage).length} qualification requirements{stage==="GEM_JR"?" + 10 optional evidence alerts":""} ({chosen.length} active scan checks)</button>

 <div role="status" aria-live="polite" aria-label="Total combined candidates across all selected qualification criteria" style={{border:"2px solid #4e8a5b",borderRadius:8,padding:14,margin:"12px 0",background:"#f1f9f2"}}>
   <strong style={{display:"block",fontSize:15,marginBottom:4}}>TOTAL COMBINED RESULTS — {stage==="GEM"?"GEM":"GEM JR"}</strong>
   <div style={{display:"flex",alignItems:"baseline",gap:12,flexWrap:"wrap"}}>
     <strong style={{fontSize:32}}>{liveCounts.total.toLocaleString("en-US")}</strong>
     <span>candidates in current research screen · {chosen.length.toLocaleString("en-US")} active scan requirement{chosen.length===1?"":"s"}</span>
   </div>
   <div style={{display:"flex",gap:18,flexWrap:"wrap",fontSize:13,marginTop:6}}>
     <span><strong>{liveCounts.passes.toLocaleString("en-US")}</strong> passed selected checks (not clinical eligibility)</span>
     <span><strong>{liveCounts.needsReview.toLocaleString("en-US")}</strong> require evidence review</span>
     <span><strong>{liveCounts.fails.toLocaleString("en-US")}</strong> excluded</span>
   </div>
   <small style={{display:"block",marginTop:8}}>{sourceRows.length.toLocaleString("en-US")} {sourceLabel} considered. {chosen.length===0?"No qualification criteria checked; all input records are included.":"Each candidate is counted once, only if it has no failed checked criterion. This is the intersection (AND), not a sum of individual checkbox matches."} Missing evidence, including verification gaps inherited from a GEM JR scan, never counts as a verified match. Counts update when any checkbox, FS, FA, or FI changes.</small>
 </div>
 <div role="status" style={{display:"flex",gap:12,flexWrap:"wrap",marginTop:12,marginBottom:12}}><div style={{padding:"10px 14px",background:"#e4f3e8",borderRadius:6}}><strong style={{fontSize:22}}>{pipeline.length.toLocaleString("en-US")}</strong><div>Pipeline research candidates (all stages)</div></div><div style={{padding:"10px 14px",background:"#e4f3e8",borderRadius:6}}><strong style={{fontSize:22}}>{stageTotal.toLocaleString("en-US")}</strong><div>{stage==="GEM"?"GEM":"GEM JR"} saved stage members (not screened total)</div></div><div style={{padding:"10px 14px",background:"#e4f3e8",borderRadius:6}}><strong style={{fontSize:22}}>{sourceRows.length.toLocaleString("en-US")}</strong><div>{useGemJrSource?juniorSource.label:"Full PIPELINE records available to scan"}</div></div></div>
 {open&&<><p>Every SCAN evaluates {sourceRows.length.toLocaleString("en-US")} {sourceLabel} against <strong>only your selected qualification checkboxes</strong>. No qualification checks selected means all records from the chosen input source are included. Phase 3 is not silently required; select its checkbox to enforce verified Phase 3 success. The source has {phase3ResearchCount.toLocaleString("en-US")} Phase 3/readout indicators, which are not the same as independently verified successful Phase 3 programs. Unknown source evidence is not treated as passing. Published data as of {asOf||"unverified"}; no live-market fetches, membership changes or trades.</p>
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

 <p style={{fontSize:13,margin:"0 0 9px",fontWeight:650}}>All checkboxes start unchecked. FI is a separate, optional set of scan restrictions with its own toggle and individual checkboxes. FI is not automatically applied by FS or FA. GEM JR retains the FS and FA qualification criteria; GEM shows downstream requirements plus the optional Gem Jr Trials source. FS selects suggested criteria. In GEM, FA toggles only Gem Jr Trials; in GEM JR, FA toggles Phase 3 trial status and Market cap $300M–$10B. Press either button again to deselect its options. DESELECT ALL clears everything.</p>
 <div className="gem-original-checklist-sections" data-stage={stage}>
  <section className="gem-original-clinical">
   <h3>CLINICAL / REGULATORY</h3>
   <div className="gem-original-criteria-grid">
 {stage==="GEM"&&<label key="gem_jr_source" style={{display:"flex",gap:8,alignItems:"flex-start",padding:8,border:"1px solid #c1d8c8",borderRadius:5,background:"white",gridColumn:"1"}}>
   <input type="checkbox" aria-label="Gem Jr Trials (optional)" checked={useGemJrSource} onChange={()=>toggle("gem_jr_source")} disabled={running} />
   <span>Gem Jr Trials <small style={{fontSize:12,color:"#175a35",fontWeight:700}}>Optional</small>
     {useGemJrSource&&<small style={{display:"block",marginTop:4,color:"#215b40"}}>{gemJrScan?"GEM JR completed scan: "+gemJrRows.length.toLocaleString("en-US")+" candidates":gemJrLivePreview?"GEM JR live checkbox results: "+gemJrRows.length.toLocaleString("en-US")+" candidates (not yet SCAN run)":"GEM JR full research universe: "+gemJrRows.length.toLocaleString("en-US")+" candidates (unscreened; verification required). Saved GEM JR stage: "+gemJrSavedRows.length.toLocaleString("en-US")+" programs."}</small>}
     {useGemJrSource&&gemJrRows.length===0&&<small role="alert" style={{display:"block",color:"#9b2828",fontWeight:700}}>{gemJrScan?"The current GEM JR scan produced no eligible or review candidates.":gemJrLivePreview?"The GEM JR checkbox results exclude all candidates.":"The full pipeline research universe has no published candidates."}</small>}
   </span>
 </label>}

    {renderOriginalCheckboxes(checkboxGroupsForStage(stage).clinical)}
   </div>
  </section>
  <details className="gem-original-trading" open>
   <summary>TRADING — FINANCIAL & MARKET CHECKBOXES ({checkboxGroupsForStage(stage).trading.length})</summary>
   <div className="gem-original-criteria-grid">
    {renderOriginalCheckboxes(checkboxGroupsForStage(stage).trading)}
   </div>
  </details>
 </div>

 <div style={{display:"flex",gap:12,flexWrap:"wrap"}}><button type="button" onClick={()=>void scan()} disabled={running||!sourceRows.length}
  aria-label={(stage==="GEM"?"GEM":"GEM JR")+" "+(running?"SCANNING":completedScan?"SCAN ENDED":"SCAN")}
  aria-live="polite"
  title={running?"Scan in progress":completedScan?"Previous scan ended; click to scan again using current FS, FA and FI choices":"Scan candidates using all checked FS, FA and active FI restrictions"}
  style={{background:running?"#a36b20":completedScan?"#176b39":"#135a32",color:"white",padding:"10px 20px",borderRadius:6,fontWeight:700}}>
  {running?"SCANNING":completedScan?"SCAN ENDED":"SCAN"}
 </button><div aria-label="Unrestricted Phase 3 baseline" title="Historical approximate count; not verified live" style={{display:"flex",alignItems:"center",gap:8,padding:"8px 14px",border:"2px solid #1d6d4b",borderRadius:6,background:"#effaf3"}}><strong style={{fontSize:24}}>~730</strong><span style={{fontSize:12}}>Phase 3 completed<br/>Before restrictions</span></div><button type="button" onClick={()=>{setShowSuggestions(false);setFaActive(false);setFiActive(false);setFiSelected([]);selectRequirements([]);}} disabled={running}>DESELECT ALL</button><button type="button" onClick={toggleFs} disabled={running} aria-pressed={showSuggestions} aria-label="FS: toggle suggested criteria checkboxes" title="FS — check recommended criteria; click again to uncheck them" style={{padding:"10px 14px",border:"1px solid #176b39",borderRadius:6,background:showSuggestions?"#ffffff":"#176b39",color:showSuggestions?"#176b39":"#ffffff",fontWeight:700}}>FS</button><button type="button" onClick={toggleFa} disabled={running} aria-pressed={stage==="GEM"?useGemJrSource:faActive} aria-label={stage==="GEM"?"FA: toggle Gem Jr Trials input":"FA: toggle Phase 3 trial status recorded and market cap qualification checkboxes"} title={stage==="GEM"?"FA — include or exclude Gem Jr Trials; click again to uncheck":"FA — check Phase 3 trial status recorded and Market cap $300M–$10B; click again to uncheck"} style={{padding:"10px 14px",border:"1px solid #176b39",borderRadius:6,background:(stage==="GEM"?useGemJrSource:faActive)?"#ffffff":"#176b39",color:(stage==="GEM"?useGemJrSource:faActive)?"#176b39":"#ffffff",fontWeight:700}}>FA</button><button type="button" onClick={toggleFi} disabled={running} aria-pressed={fiActive}
   aria-label={"FI: "+(fiActive?"disable":"enable")+" separate "+(stage==="GEM_JR"?"GEM JR":"GEM")+" scan restrictions"}
   title="FI — separately include your individually checked restrictions in the scan; click again to exclude them"
   style={{padding:"10px 14px",border:"1px solid #176b39",borderRadius:6,background:fiActive?"#ffffff":"#176b39",color:fiActive?"#176b39":"#ffffff",fontWeight:700}}>FI</button></div>

 <section className="gem-fi-filter-section" aria-label={(stage==="GEM_JR"?"GEM JR":"GEM")+" FI independent scan restrictions"}
   style={{margin:"12px 0 0",padding:12,border:"1px solid #91b5a0",borderRadius:8,background:fiActive?"#e9f6ec":"#f5f8f5"}}>
   <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",gap:10,flexWrap:"wrap"}}>
     <strong>FI — INDEPENDENT SCAN RESTRICTIONS</strong>
     <span role="status" style={{fontSize:12,fontWeight:800,color:fiActive?"#176b39":"#5a625c"}}>
       {fiActive?"Applied to SCAN · "+fiSelected.length+" of "+suggestedByStage[stage].length+" selected":"Not applied to SCAN · "+fiSelected.length+" selected"}
     </span>
   </div>
   <p style={{fontSize:12,margin:"7px 0 9px"}}>Click any checkbox to include or remove that FI rule. Use the FI button to include or exclude those rules from SCAN.
     Your FS/FA checkboxes are separate. Overlapping rules are evaluated once.</p>
   <div className="gem-original-criteria-grid">
     {visibleCriteriaByStage(stage).filter(([key])=>suggestedByStage[stage].includes(key)).map(([key,label])=>
       <label key={"fi-"+key} style={{display:"flex",gap:8,alignItems:"flex-start",padding:8,border:fiSelected.includes(key)?"2px solid #2d8a56":"1px solid #c1d8c8",borderRadius:5,background:fiSelected.includes(key)?"#e4f5e9":"white"}}>
         <input type="checkbox" disabled={running} checked={fiSelected.includes(key)} onChange={()=>toggleFiCriterion(key)} aria-label={"FI: "+label} />
         <span>{label}</span>
       </label>
     )}
   </div>
 </section>

 <p className="subtle" style={{fontSize:12,marginTop:9}}>SCAN combines every checked FS / FA / manual qualification criterion with the individually checked FI restrictions when FI is enabled. All active conditions must match; unknown evidence requires review.{stage==="GEM"&&useGemJrSource?" FA also limits the input to GEM JR candidates.":""} The SCAN ENDED button can be clicked again to rerun.</p>
 <p role="status" aria-live="polite" style={{fontWeight:700,marginTop:12}}>{message||(completedScan?"SCAN ENDED — "+completedScan.passes.length.toLocaleString("en-US")+" passed, "+completedScan.needsReview.length.toLocaleString("en-US")+" need verification; "+completedScan.fails.length.toLocaleString("en-US")+" excluded. Click SCAN ENDED to rerun.":"Ready to scan "+sourceRows.length.toLocaleString("en-US")+" "+sourceLabel+".")}</p>
 {result&&<div role="status" style={{marginTop:15,padding:12,background:"#e8f2ec",borderRadius:6}}>
  <strong>{result.sourceKind==="GEM_JR"?"GEM JR scan":result.sourceKind==="GEM_JR_LIVE"?"GEM JR checkbox preview":result.sourceKind==="GEM_JR_UNSCREENED"?"Unscreened pipeline research universe":"Full PIPELINE"} evidence screen complete · Run #{result.runNumber}</strong>
  <p><strong style={{fontSize:22}}>{(result.passes.length+result.needsReview.length).toLocaleString("en-US")} total combined candidates</strong> across all selected requirements (AND), counted once each. Of {result.baseline.toLocaleString("en-US")} {result.sourceKind==="GEM_JR"?"GEM JR scan candidates":result.sourceKind==="GEM_JR_LIVE"?"current GEM JR checkbox-screen candidates":result.sourceKind==="GEM_JR_UNSCREENED"?"unscreened full research universe":"PIPELINE records"} evaluated: {result.passes.length.toLocaleString("en-US")} verified matches · {result.needsReview.length.toLocaleString("en-US")} need evidence review · {result.fails.length.toLocaleString("en-US")} excluded. Completed at {new Date(result.evaluatedAt).toLocaleTimeString()}.</p>
  <p><strong>Applied requirements:</strong> {result.audits.length?result.audits.map(x=>x.label).join(" · "):"None (all records included)"}</p>

  {result.audits.some(a=>a.unknown===result.baseline)&&<p style={{fontWeight:700}}>Some selected requirements have no verifiable evidence for any of these records. They cannot produce verified passes until that evidence is available, regardless of how many times you scan.</p>}
  <p>Passed programs and those needing verification appear in the candidate table below. Scanning does not add records to saved GEM membership.</p>
 </div>}

 </>}</section>
}
