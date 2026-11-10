"use client";

import {useState} from "react";
import styles from "../evidence-gaps/EvidenceRecoveryBoardR68.module.css";
type Roster=NonNullable<typeof import(
 "../../../lib/focus-r91-posted-results-reconciliation").R91_POSTED_RESULTS_ROSTER>;
type Row=Roster["rows"][number];
type ReportedGroup={id:string;title:string;description:string|null};
type Outcome={
 type:string;title:string;timeFrame:string|null;
 populationDescription:string|null;description:string|null;unitOfMeasure:string|null;
 paramType:string|null;groups:ReportedGroup[];
 denominators:Array<{units:string;counts:Array<{groupId:string;value:string}>}>;
 measurements:Array<{groupId:string;category:string|null;
  classTitle:string|null;value:string|null;spread:string|null;
  lowerLimit:string|null;upperLimit:string|null}>;
 analyses:Array<{groupIds:string[];pValue:string|null;pValueMethod:string|null;
  ciPct:number|null;ciLowerLimit:string|null;ciUpperLimit:string|null}>
};
type Report={
 nct:string;ticker:string;sourceStatus:string;sourceSHA256:string;sourceApiUrl:string;
 readbackAtUtc:string;sourceChangedSinceDatedSnapshot:boolean;
 outcomeMeasureCount:number;primaryOutcomeCount:number;
 participantFlowGroups:ReportedGroup[];
 registeredOutcomes:Outcome[];
 safetyExposureGroups:Array<{groupId:string;title:string;
  seriousNumAffected:number|null;seriousNumAtRisk:number|null;
  otherNumAffected:number|null;otherNumAtRisk:number|null}>;
 seriousAdverseEventTerms:Array<{term:string;organSystem:string|null;
  stats:Array<{groupId:string;affected:number|null;atRisk:number|null;events:number|null}>}>;
 otherAdverseEventTerms:Array<{term:string}>;
 originalSignedSAPVerified:false;independentStatisticalReanalysis:false;
 independentSafetyAdjudication:false;FDAForecast:"ABSTAIN";
};
type Lookup={status:"loading"|"ok"|"error";data?:Report;error?:string};
function errName(value:unknown){
 return value&&typeof value==="object"&&"error" in value&&
 typeof value.error==="string"?value.error:"OFFICIAL_SOURCE_NOT_VERIFIED";
}
export default function PostedResultsR91Client({rows}:{rows:Row[]}){
 const [observed,setObserved]=useState<Record<string,Lookup>>({});
 const [allBusy,setAllBusy]=useState(false);
 async function load(nct:string){
  setObserved(x=>({...x,[nct]:{status:"loading"}}));
  try{
   const res=await fetch(
    "/predictions/scientific-reconciliation/check?nct="+encodeURIComponent(nct),
    {cache:"no-store",headers:{"Accept":"application/json"}});
   const value:unknown=await res.json();
   if(!res.ok||!value||typeof value!=="object"||
      !("nct" in value)||value.nct!==nct||
      !("sourceSHA256" in value)||typeof value.sourceSHA256!=="string"||
      !/^[a-f0-9]{64}$/u.test(value.sourceSHA256)||
      !("FDAForecast" in value)||value.FDAForecast!=="ABSTAIN"){
     setObserved(x=>({...x,[nct]:{status:"error",error:errName(value)}}));
     return;
   }
   setObserved(x=>({...x,[nct]:{status:"ok",data:value as Report}}));
  }catch{
   setObserved(x=>({...x,[nct]:{status:"error",
    error:"PUBLIC_RESULTS_SOURCE_UNAVAILABLE_NOT_A_NEGATIVE_TRIAL_RESULT"}}));
  }
 }
 const originallyPosted=rows.filter(r=>r.resultsPostedInDatedRegistrySnapshot);
 async function loadAll(){
  if(allBusy)return;
  setAllBusy(true);
  try{
   for(let i=0;i<originallyPosted.length;i+=3){
    await Promise.all(originallyPosted.slice(i,i+3).map(r=>load(r.nct)));
   }
  }finally{setAllBusy(false);}
 }
 const completed=originallyPosted.filter(r=>observed[r.nct]?.status==="ok").length;
 const failed=originallyPosted.filter(r=>observed[r.nct]?.status==="error").length;
 return <section aria-label="Scientific read-only original results reconciliation">
  <p className={styles.notice}>
   <button type="button" onClick={()=>{void loadAll();}} disabled={allBusy}
    style={{borderRadius:7,padding:"10px 14px",border:"none",
     background:"#165c45",color:"#fff",fontWeight:700,cursor:"pointer"}}>
    {allBusy?"Retrieving official posted results…":
     "Check all 12 publicly posted result records"}
   </button>
   {" "}<strong>{completed}/{originallyPosted.length}</strong> successful
   live original result reads this session; <strong>{failed}</strong>
   lookup errors. The source is the public official registry and all
   clinical significance, SAP compliance, patient-level data, qualified
   reviewer conclusions and FDA forecasts remain unverified.
  </p>
  <div className={styles.coverageGrid}>
  {rows.map(r=>{
   const current=observed[r.nct],data=current?.data;
   return <article className={styles.coverageGroup} key={r.nct}>
    <strong>{r.ticker} · {r.nct}</strong>
    <div>{r.phase} · retained original aggregate results:
     <strong> {r.resultsPostedInDatedRegistrySnapshot?"POSTED":"NOT POSTED"}</strong>
     {" "}as of {r.sourceArchiveDate} UTC</div>
    <div>Provisional application grouping: {r.cycleIds.join(", ")}</div>
    <p><button type="button" disabled={current?.status==="loading"||allBusy}
      onClick={()=>{void load(r.nct);}}
      style={{border:"1px solid #77a690",background:"#fff",
       color:"#145b44",padding:"7px 11px",borderRadius:7,
       fontWeight:700,cursor:"pointer"}}>
      {current?.status==="loading"?"Reading original public results…":
       "Compare current registry aggregate outcomes and safety groups"}
     </button></p>
    {current?.status==="error"&&<p role="alert">No original-source readback:
     {current.error}. This does not establish a missing or failed clinical result.</p>}
    {data&&<div aria-live="polite">
      <div><b>Registry source:</b> {data.sourceStatus}</div>
      {data.sourceChangedSinceDatedSnapshot&&<p role="alert">
       Current registry posting availability differs from the dated
       census. Review original source change before any scientific use.</p>}
      <div>Outcome entries: {data.outcomeMeasureCount} total;
       <strong> {data.primaryOutcomeCount}</strong> flagged PRIMARY.
       Participant-flow arm groups: {data.participantFlowGroups.length}.
       Serious adverse-event terms: {data.seriousAdverseEventTerms.length}.</div>
      <details className={styles.coverageDetails}>
       <summary>Original reported PRIMARY outcomes ({data.registeredOutcomes.length})</summary>
       {data.registeredOutcomes.length===0?
        <p>No PRIMARY outcome data parsed from the current official record.
         Do not infer trial success or failure.</p>:
        data.registeredOutcomes.map((m,i)=><div key={i}>
         <p><b>{i+1}. {m.title}</b> · {m.timeFrame??"timeframe unlisted"}
          {" · "}{m.unitOfMeasure??"unit not provided"}</p>
         <p><small>Registry analysis population:
          {m.populationDescription??"not described"}.
          Reported parameter: {m.paramType??"not listed"}.
          Exact final estimand/SAP still unverified.</small></p>
         <div>Original outcome group labels:
          {m.groups.map(g=>" "+g.id+": "+g.title).join("; ")}</div>
         {m.denominators.map((d,j)=><div key={j}>
          <b>Reported denominator ({d.units}):</b>
          {d.counts.map(x=>" "+x.groupId+"="+x.value).join("; ")}
         </div>)}
         <details className={styles.coverageDetails}>
          <summary>Original group-level measurement entries ({m.measurements.length}) and reported comparisons ({m.analyses.length})</summary>
          <div style={{maxHeight:320,overflowY:"auto"}}>
           {m.measurements.slice(0,40).map((v,j)=><div key={j}>
            {v.classTitle??"Class"} / {v.category??"Category"} ·
            {v.groupId}: {v.value??"value unlisted"}
            {v.spread?" ± "+v.spread:""}
            {v.lowerLimit||v.upperLimit?
             " (bounds: "+(v.lowerLimit??"?")+" to "+(v.upperLimit??"?")+")":""}
           </div>)}
           {m.measurements.length>40&&<small>
            First 40 source entries displayed; complete parsed source
            is available from the exact-NCT JSON endpoint.
           </small>}
           {m.analyses.map((v,j)=><div key={"a"+j}>
            Reported comparison group(s): {v.groupIds.join(", ")||"not specified"}.
            Registry p-value: {v.pValue??"not reported"}.
            Method: {v.pValueMethod??"not specified"}.
            {v.ciLowerLimit||v.ciUpperLimit?
             " Reported CI bounds: "+(v.ciLowerLimit??"?")+" to "+
              (v.ciUpperLimit??"?"):""}
            {" "}No independent statistical inference was performed.
           </div>)}
          </div>
         </details>
        </div>)}
      </details>
      <details className={styles.coverageDetails}>
       <summary>Original adverse-event exposure denominators and terms</summary>
       {data.safetyExposureGroups.map((g,i)=><div key={i}>
        <b>{g.title} ({g.groupId})</b>: serious AEs
        {" "}{g.seriousNumAffected??"?"} affected /
        {" "}{g.seriousNumAtRisk??"?"} at risk; other AEs
        {" "}{g.otherNumAffected??"?"} affected /
        {" "}{g.otherNumAtRisk??"?"} at risk
       </div>)}
       <p>Serious adverse event terms listed: {data.seriousAdverseEventTerms.length}.
        Other adverse event terms: {data.otherAdverseEventTerms.length}.
        These are source group denominators; they are not verified
        exposure-adjusted risks or adjudicated safety conclusions.</p>
       {data.seriousAdverseEventTerms.slice(0,20).map((e,i)=><div key={i}>
         {e.term} ({e.organSystem??"organ system unlisted"}):
         {e.stats.map(x=>" "+x.groupId+" affected="+
           (x.affected??"?")+"/atRisk="+(x.atRisk??"?")).join("; ")}
        </div>)}
       {data.seriousAdverseEventTerms.length>20&&<small>
        First 20 serious event terms shown; use exact-NCT JSON endpoint
        for all source-reported rows.</small>}
      </details>
      <div><small>Original official response SHA-256:
       <code>{data.sourceSHA256}</code>. Retrieved {data.readbackAtUtc}.
       Source only; NOT qualified clinical review or FDA validation.</small></div>
    </div>}
    <p><a href={r.originalRegistryUrl+"?tab=results"}
     target="_blank" rel="noopener noreferrer">
     Open official current ClinicalTrials.gov result record
    </a></p>
    <p><small>Prospectively signed SAP: NOT VERIFIED.
     Independent efficacy model: NOT REANALYZED.
     Safety adjudication: NOT SIGNED.
     FDA approval forecast: ABSTAIN.</small></p>
   </article>;
  })}
  </div>
 </section>;
}
