"use client";
import {useEffect,useMemo,useState} from "react";
import {loadRegistryEvidenceIndex,type RegistryEvidenceIndex,type RegistryTrialEvidence}
 from "../lib/raas-registry-evidence";
import {stageResearchReviewsForUnverifiedTrial}
 from "../lib/raas-reviewed-full-score";
import type {ReadoutRow} from "../lib/phase3-public-readout";
import type {Phase3CensusRegistryStatus} from "../lib/phase3-census-rows";
import RaasMetricGradebook from "./RaasMetricGradebook";
import RaasTrialHistoryButton from "./RaasTrialHistoryButton";
import {buildRaas762MetricEvidenceQueue}
 from "../lib/raas-762-metric-evidence-queue";

const PAGE_SIZE=50;
type EvidenceFilter="all"|"posted"|"protocol";
type ScoreFilter="all"|"partial"|"unscored";
const statuses=new Set<string>([
 "RECRUITING","ACTIVE_NOT_RECRUITING","ENROLLING_BY_INVITATION",
 "NOT_YET_RECRUITING","COMPLETED","TERMINATED","WITHDRAWN","UNKNOWN"
]);
const cell={padding:"10px 9px",verticalAlign:"top" as const,borderBottom:"1px solid #d6e5dc"};
const control={padding:"9px 10px",border:"1px solid #aac7b5",borderRadius:7,
 color:"#164b32",background:"#fff",fontSize:13};
function caseRow(x:RegistryTrialEvidence):ReadoutRow{
 return {
  nctId:x.nctId,ticker:x.ticker,
  company:"Company identity requires current source verification",
  status:(statuses.has(x.registryStatus)?x.registryStatus:"UNKNOWN") as Phase3CensusRegistryStatus,
  sourceUrl:x.sourceUrl,pipelineQualification:null,fdaPdufaVerification:false,evidence:null
 };
}
type ScoringRow={
 evidence:RegistryTrialEvidence;trial:ReadoutRow;topReviewed:number;
 bottomReviewed:number;independentReviews:number;
 hasPartial:boolean;remainingTop:number;remainingBottom:number
};
function setupRows(index:RegistryEvidenceIndex):ScoringRow[]{
 return index.records.map(x=>{
  const trial={nctId:x.nctId,ticker:x.ticker};
  const top=stageResearchReviewsForUnverifiedTrial(trial,"pre");
  const bottom=stageResearchReviewsForUnverifiedTrial(trial,"post");
  const topReviewed=top?.reviewedCount??0,bottomReviewed=bottom?.reviewedCount??0;
  return {evidence:x,trial:caseRow(x),topReviewed,bottomReviewed,
   independentReviews:(top?.independentReviewedCount??0)+
    (bottom?.independentReviewedCount??0),
   hasPartial:topReviewed+bottomReviewed>0,
   remainingTop:30-topReviewed,remainingBottom:30-bottomReviewed
  };
 }).sort((a,b)=>Number(b.hasPartial)-Number(a.hasPartial)||
  Number(b.evidence.postedResults)-Number(a.evidence.postedResults)||
  a.trial.ticker.localeCompare(b.trial.ticker)||
  a.trial.nctId.localeCompare(b.trial.nctId));
}
export default function Raas762ScoringWorkspace(){
 const [index,setIndex]=useState<RegistryEvidenceIndex|null>(null);
 const [state,setState]=useState<"loading"|"ready"|"error">("loading");
 const [search,setSearch]=useState("");
 const [evidenceFilter,setEvidenceFilter]=useState<EvidenceFilter>("all");
 const [scoreFilter,setScoreFilter]=useState<ScoreFilter>("all");
 const [page,setPage]=useState(0);
 const [exportBusy,setExportBusy]=useState(false);
 const [exportMessage,setExportMessage]=useState("");
 useEffect(()=>{
  let alive=true;
  void loadRegistryEvidenceIndex().then(x=>{
   if(!alive)return;
   if(!x||x.records.length!==762||
    x.summary.researchNcts!==762||
    new Set(x.records.map(r=>r.nctId)).size!==762){
    setState("error");return;
   }
   setIndex(x);setState("ready");
  }).catch(()=>{if(alive)setState("error")});
  return ()=>{alive=false};
 },[]);
 const rows=useMemo(()=>index?setupRows(index):[],[index]);
 const partial=useMemo(()=>rows.filter(r=>r.hasPartial).length,[rows]);
 const posted=useMemo(()=>rows.filter(r=>r.evidence.postedResults).length,[rows]);
 const filtered=useMemo(()=>{
  const q=search.trim().toLowerCase();
  return rows.filter(x=>
   (scoreFilter==="all"||(scoreFilter==="partial"?x.hasPartial:!x.hasPartial))&&
   (evidenceFilter==="all"||(evidenceFilter==="posted"?x.evidence.postedResults:
    !x.evidence.postedResults))&&
   (!q||[x.trial.nctId,x.trial.ticker,x.evidence.registryStatus,
    ...x.evidence.registeredConditions.slice(0,10),
    ...x.evidence.registeredInterventions.slice(0,10)]
    .some(v=>v.toLowerCase().includes(q)))
  );
 },[rows,search,scoreFilter,evidenceFilter]);
 const pages=Math.max(1,Math.ceil(filtered.length/PAGE_SIZE));
 const currentPage=Math.min(page,pages-1);
 const shown=filtered.slice(currentPage*PAGE_SIZE,(currentPage+1)*PAGE_SIZE);
 async function downloadMetricQueue(){
  if(!index||exportBusy)return;
  setExportBusy(true);setExportMessage("");
  // Let iPhone paint the active state before generating the full CSV.
  await new Promise<void>(resolve=>requestAnimationFrame(()=>resolve()));
  try{
   const result=buildRaas762MetricEvidenceQueue(index);
   const blob=new Blob(["\uFEFF",result.csv],{type:"text/csv;charset=utf-8"});
   const url=URL.createObjectURL(blob);
   const anchor=document.createElement("a");
   anchor.href=url;
   anchor.download="raas-762-all-45720-metric-evidence-slots.csv";
   document.body.appendChild(anchor);
   anchor.click();anchor.remove();
   window.setTimeout(()=>URL.revokeObjectURL(url),2000);
   setExportMessage(
    "Prepared "+result.summary.metricSlots.toLocaleString()+
    " exact-NCT metric rows; "+result.summary.provisionalReviewSlots+
    " provisional source-checked grades; "+
    result.summary.metricSlotsRequiringReviewedGrades.toLocaleString()+
    " not yet graded. No full RAAS score was inferred.");
  }catch(error){
   setExportMessage("The exact metric queue could not be verified. No incomplete or fabricated CSV was exported.");
  }finally{setExportBusy(false)}
 }
 if(state==="loading")return <p role="status" style={{padding:14}}>
  Loading exact ClinicalTrials.gov NCT source records for the 762-row scoring setup…
 </p>;
 if(state==="error")return <p role="alert" style={{padding:14,color:"#8a2b16"}}>
  The exact 762-record source index could not be verified. Trial rows and counts
  are withheld rather than reconstructed from an unrelated population.
 </p>;
 return <section aria-label="RAAS 762 trial scoring workspace"
  data-raas-762-scoring-workspace="source-verified-rows-unvalidated-scores">
  <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(145px,1fr))",
   gap:10,margin:"14px 0"}} data-raas-762-scoring-summary="true">
   {[
    {value:rows.length,label:"Trial rows set up"},
    {value:partial,label:"Trial rows with partial reviews"},
    {value:rows.length-partial,label:"Trial rows awaiting first metric review"},
    {value:0,label:"Full independently validated RAAS scores"},
    {value:posted,label:"Trial rows with posted registry results"},
    {value:rows.length-posted,label:"Trial rows with protocol-only evidence"}
   ].map(x=><div key={x.label} style={{background:"#fff",border:"1px solid #bfd6c7",
    borderRadius:9,padding:12}}>
    <strong style={{display:"block",fontSize:24,fontVariantNumeric:"tabular-nums"}}>{x.value}</strong>
    <span style={{display:"block",fontSize:12,color:"#42644c",lineHeight:1.4}}>{x.label}</span>
   </div>)}
  </div>
  <p style={{fontSize:13,lineHeight:1.55,margin:"12px 0",color:"#385944"}}>
   <strong>Scoring setup, not predicted results.</strong> Every one of the 762
   NCTs has one row; each row opens separate TOP and BOTTOM 30-metric checklists,
   so all 60 metric slots are available without inventing values. Metrics
   requiring evidence remain N/A, not zero or neutral. A partially reviewed
   metric is not a validated overall RAAS score. This inventory does not itself
   certify the current $300M–$10B Pipeline or FDA PDUFA eligibility.
  </p>
  <section data-raas-762-all-metric-queue="45720-exact-slots"
   style={{margin:"15px 0",border:"1px solid #9ac4a6",borderRadius:10,
    padding:"14px 15px",background:"#f4faf5"}}>
   <strong style={{display:"block",fontSize:16,color:"#174b30"}}>
    All 762 trials × 60 scoring requirements = 45,720 metric rows
   </strong>
   <p style={{fontSize:13,lineHeight:1.5,margin:"8px 0"}}>
    Each export row identifies the exact NCT, TOP/BOTTOM stage, metric,
    required evidence, benchmark, source lead, source date, next review
    action and any genuinely recorded provisional component score.
    The 82 existing AI-assisted findings are retained, not repeated
    across stages. Unreviewed grades and full RAAS scores remain blank.
   </p>
   <button type="button" onClick={()=>{void downloadMetricQueue()}}
    disabled={exportBusy} aria-busy={exportBusy}
    data-raas-762-export-45720="true"
    style={{...control,background:"#d8eee0",fontWeight:750,padding:"11px 14px"}}>
    {exportBusy?"Preparing exact metric worklist…":
     "Download all 45,720 metric evidence rows (CSV)"}
   </button>
   <p role="status" style={{fontSize:12,color:"#3d674d",margin:"8px 0 0"}}>
    {exportMessage||"Missing grades are empty; registry facts are research source leads, not RAAS or FDA predictions."}
   </p>
  </section>
  <div style={{display:"flex",flexWrap:"wrap",gap:12,margin:"14px 0",fontSize:13}}>
   <a href="/raas-trial-score-ledger.csv" download>Export 762 rows · trial ledger (CSV)</a>
   <a href="/raas-all-trials-partial-metric-ratings.csv" download>
    Export TOP/BOTTOM research metrics · 1,524 stage rows (CSV)</a>
   <a href="/raas-active-phase3-source-screen.csv" download>
    Export current Phase 3 source prescreen (CSV)</a>
  </div>
  <div style={{display:"flex",gap:9,flexWrap:"wrap",alignItems:"end",margin:"18px 0"}}>
   <label style={{display:"flex",flexDirection:"column",gap:4,fontSize:12}}>
    Search the 762 NCTs
    <input type="search" aria-label="Find trial within 762 scoring rows"
     value={search} onChange={e=>{setSearch(e.target.value);setPage(0)}}
     placeholder="NCT ID, ticker, disease, drug" maxLength={100}
     style={{...control,minWidth:210}}/>
   </label>
   <label style={{display:"flex",flexDirection:"column",gap:4,fontSize:12}}>
    Score review status
    <select aria-label="Filter 762 scoring review status" value={scoreFilter}
     onChange={e=>{setScoreFilter(e.target.value as ScoreFilter);setPage(0)}}
     style={control}>
     <option value="all">All 762 rows</option>
     <option value="partial">Has reviewed metrics</option>
     <option value="unscored">No reviewed metrics yet</option>
    </select>
   </label>
   <label style={{display:"flex",flexDirection:"column",gap:4,fontSize:12}}>
    ClinicalTrials.gov evidence
    <select aria-label="Filter 762 registry evidence" value={evidenceFilter}
     onChange={e=>{setEvidenceFilter(e.target.value as EvidenceFilter);setPage(0)}}
     style={control}>
     <option value="all">All source states</option>
     <option value="posted">Results posted</option>
     <option value="protocol">Protocol only</option>
    </select>
   </label>
   <button type="button" style={control}
    onClick={()=>{setSearch("");setEvidenceFilter("all");setScoreFilter("all");setPage(0)}}>
    Clear all filters
   </button>
  </div>
  <p role="status" style={{fontSize:12,color:"#3a6049"}}>
   {filtered.length} matching NCTs · displaying {shown.length} on this page.
   Partial metric reviews are provisional and can occur in both stages.
  </p>
  <div role="region" aria-label="RAAS 762 exact NCT scoring row table" tabIndex={0}
   style={{overflowX:"auto",maxWidth:"100%",border:"1px solid #c5d8ca",borderRadius:8}}>
   <table style={{width:"100%",borderCollapse:"collapse",minWidth:750,fontSize:13}}>
    <thead style={{background:"#eaf4ed",color:"#19452c"}}>
     <tr>
      {["NCT / ticker","Registry evidence","TOP reviewed","BOTTOM reviewed",
       "Overall RAAS","60-metric score details","Cross-stage history"].map(h=>
       <th key={h} scope="col" style={{...cell,textAlign:"left",fontSize:12}}>{h}</th>)}
     </tr>
    </thead>
    <tbody>{shown.map(x=><tr key={x.trial.nctId}
     data-raas-scoring-nct={x.trial.nctId}>
     <td style={cell}><strong>{x.trial.ticker}</strong>
      <span style={{display:"block"}}><a href={x.trial.sourceUrl}
       target="_blank" rel="noopener noreferrer">{x.trial.nctId}</a></span>
      <small style={{display:"block",maxWidth:225}}>
       {x.evidence.registeredConditions.slice(0,2).join(", ")||"Condition not supplied"}
      </small>
     </td>
     <td style={cell}>{x.evidence.postedResults?"Results posted":"Protocol only"}
      <span style={{display:"block",fontSize:11,color:"#52705c"}}>
       {x.evidence.registryStatus.replaceAll("_"," ").toLowerCase()}
      </span>
     </td>
     <td style={cell}><strong>{x.topReviewed}/30</strong>
      <small style={{display:"block"}}>{x.remainingTop} lacking metric reviews</small></td>
     <td style={cell}><strong>{x.bottomReviewed}/30</strong>
      <small style={{display:"block"}}>{x.remainingBottom} lacking metric reviews</small></td>
     <td style={cell}><strong>Not validated</strong>
      <small style={{display:"block"}}>N/A · never 0/100</small>
      {x.independentReviews>0&&<small style={{display:"block"}}>
       {x.independentReviews} independent reviews</small>}
     </td>
     <td style={cell}><RaasMetricGradebook row={x.trial} bucket={null}/></td>
     <td style={cell}><RaasTrialHistoryButton row={x.trial} bucket={null}/></td>
    </tr>)}</tbody>
   </table>
  </div>
  <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",
   gap:12,margin:"14px 0"}}>
   <button type="button" style={control} disabled={currentPage<=0}
    onClick={()=>setPage(x=>Math.max(0,x-1))}>Previous 50</button>
   <span style={{fontSize:12}}>Page {currentPage+1} of {pages}</span>
   <button type="button" style={control} disabled={currentPage>=pages-1}
    onClick={()=>setPage(x=>Math.min(pages-1,x+1))}>Next 50</button>
  </div>
  <p style={{fontSize:12,color:"#53705b",lineHeight:1.5}}>
   Source collection as of {index?.sourceAsOf}. History follows the same
   NCT across research stages; no earlier issuer or FDA event is backdated
   as a previously frozen score.
  </p>
 </section>;
}
