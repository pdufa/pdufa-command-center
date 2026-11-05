"use client";
import {useEffect,useMemo,useState} from "react";
import {loadRegistryEvidenceIndex,registryMetricLeads,type RegistryEvidenceIndex,
 type RegistryMetricLead,type RegistryTrialEvidence}
 from "../lib/raas-registry-evidence";
import {clinicalFiveForTrial} from "../lib/raas-clinical-five";
import type {ReadoutRow} from "../lib/phase3-public-readout";
import type {Phase3CensusRegistryStatus} from "../lib/phase3-census-rows";
import RaasClinicalFiveCell from "./RaasClinicalFiveCell";
import RaasTrialHistoryButton from "./RaasTrialHistoryButton";
import historicalSixGapSources from "../data/raas-historical-six-gap-source-leads.json";

const PAGE_SIZE=50;
const historicalSourceByNct=new Map(historicalSixGapSources.records.map(x=>[x.nctId,x]));
type EvidenceFilter="all"|"posted"|"protocol";
type ScoreFilter="all"|"partial"|"unscored";
type LeadFilter="all"|"has-leads"|"no-leads";
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
 evidence:RegistryTrialEvidence;trial:ReadoutRow;
 /** Research-only category from exact registry posting; NOT issuer readout. */
 stage:"pre"|"post";reviewed:number;independentReviews:number;
 hasPartial:boolean;remaining:number;
 sourceLeads:RegistryMetricLead[];leadMetricCount:number
};
function setupRows(index:RegistryEvidenceIndex):ScoringRow[]{
 return index.records.map(x=>{
  const trial={nctId:x.nctId,ticker:x.ticker};
  const stage:"pre"|"post"=x.postedResults?"post":"pre";
  const review=clinicalFiveForTrial(trial,stage,false);
  const reviewed=review.graded;
  const sourceLeads=registryMetricLeads(x,stage,trial).map(lead=>({
   ...lead,metricIds:lead.metricIds.filter(id=>id.startsWith(stage+"-1-"))
  })).filter(lead=>lead.metricIds.length>0);
  const leadMetricCount=new Set(sourceLeads.flatMap(lead=>lead.metricIds)).size;
  return {evidence:x,trial:caseRow(x),stage,reviewed,
   independentReviews:0,
   hasPartial:reviewed>0,remaining:5-reviewed,sourceLeads,leadMetricCount
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
 const [leadFilter,setLeadFilter]=useState<LeadFilter>("all");
 const [page,setPage]=useState(0);
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
 const withLeads=useMemo(()=>rows.filter(r=>r.sourceLeads.length>0).length,[rows]);
 const sourceGaps=useMemo(()=>rows.filter(r=>r.sourceLeads.length===0),[rows]);
 const filtered=useMemo(()=>{
  const q=search.trim().toLowerCase();
  return rows.filter(x=>
   (scoreFilter==="all"||(scoreFilter==="partial"?x.hasPartial:!x.hasPartial))&&
   (leadFilter==="all"||(leadFilter==="has-leads"?x.sourceLeads.length>0:
    x.sourceLeads.length===0))&&
   (evidenceFilter==="all"||(evidenceFilter==="posted"?x.evidence.postedResults:
    !x.evidence.postedResults))&&
   (!q||[x.trial.nctId,x.trial.ticker,x.evidence.registryStatus,
    ...x.evidence.registeredConditions.slice(0,10),
    ...x.evidence.registeredInterventions.slice(0,10)]
    .some(v=>v.toLowerCase().includes(q)))
  );
 },[rows,search,scoreFilter,leadFilter,evidenceFilter]);
 const pages=Math.max(1,Math.ceil(filtered.length/PAGE_SIZE));
 const currentPage=Math.min(page,pages-1);
 const shown=filtered.slice(currentPage*PAGE_SIZE,(currentPage+1)*PAGE_SIZE);
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
    {value:rows.length-posted,label:"Before · no registry results posted"},
    {value:posted,label:"Past · registry results posted"},
    {value:rows.length*5,label:"Active five-factor clinical assessment slots"},
    {value:partial,label:"Rows with provisional reviews in assigned category"},
    {value:withLeads,label:"Rows with ungraded registry source leads"},
    {value:0,label:"Full independently validated RAAS scores"}
   ].map(x=><div key={x.label} style={{background:"#fff",border:"1px solid #bfd6c7",
    borderRadius:9,padding:12}}>
    <strong style={{display:"block",fontSize:24,fontVariantNumeric:"tabular-nums"}}>{x.value}</strong>
    <span style={{display:"block",fontSize:12,color:"#42644c",lineHeight:1.4}}>{x.label}</span>
   </div>)}
  </div>
  <p style={{fontSize:13,lineHeight:1.55,margin:"12px 0",color:"#385944"}}>
   <strong>Research preparation only. RAAS applies to the 762 Before/Past spreadsheet rows, never the 11,000+ POOL.</strong>
   Each exact NCT has ONE active five-factor clinical checklist based on whether ClinicalTrials.gov
   results are posted: Before (not posted) or Past (posted). There are 3,810 clinical
   assessment slots, not duplicate stage rows. Previous research and rating
   changes remain in the same NCT history. Registry posting does NOT independently
   verify issuer readout timing, a calibrated score or FDA eligibility.
   Missing metric grades remain N/A, never invented zero or neutral values.
   Registry source leads identify possible review materials only; they do not count
   as scored or independently reviewed metrics.
  </p>
  <details data-raas-registry-source-gap-queue="requires-primary-source-research"
   style={{margin:"16px 0",border:"1px solid #b8cdbd",borderRadius:9,padding:12}}>
   <summary style={{cursor:"pointer",fontWeight:700,fontSize:14}}>
    Source discovery worklist · {sourceGaps.length} NCTs with no eligible registry metric lead
   </summary>
   <p style={{fontSize:13,lineHeight:1.5}}>
    These trials have no metric-specific lead in the saved registry extract.
    Some have separately documented historical research leads below, but those
    require exact NCT and protocol crosschecks before any metric can be reviewed.
    They are not scored as failures. First recover the dated primary endpoint,
    trial protocol and reported results from the registry, sponsor disclosures,
    publications or original FDA materials. Verify the exact drug, indication and
    NCT before promoting any evidence into a provisional metric assessment.
    A trial shown as completed does not establish successful efficacy.
   </p>
   <button type="button" style={{...control,marginBottom:10}}
    onClick={()=>{setSearch("");setEvidenceFilter("all");setScoreFilter("all");
     setLeadFilter("no-leads");setPage(0)}}>
    Filter main table to source gaps
   </button>
   <div role="region" aria-label="RAAS registry source discovery worklist"
    tabIndex={0} style={{overflowX:"auto"}}>
    <table style={{width:"100%",borderCollapse:"collapse",minWidth:690,fontSize:12}}>
     <thead><tr style={{background:"#eaf4ed"}}>
      {["Trial / issuer","Registry status","Drug and indication",
       "Saved registry evidence","Next source research"].map(h=><th key={h}
       scope="col" style={{...cell,textAlign:"left"}}>{h}</th>)}
     </tr></thead>
     <tbody>{sourceGaps.map(x=><tr key={x.trial.nctId}>
      <td style={cell}><strong>{x.trial.ticker}</strong>
       <small style={{display:"block"}}><a href={x.trial.sourceUrl}
        target="_blank" rel="noopener noreferrer">{x.trial.nctId}</a></small></td>
      <td style={cell}>{x.evidence.registryStatus}</td>
      <td style={cell}>{x.evidence.registeredInterventions.slice(0,2).join(", ")||"Drug unspecified"}
       <small style={{display:"block"}}>
        {x.evidence.registeredConditions.slice(0,2).join(", ")||"Indication unspecified"}
       </small></td>
      <td style={cell}>
       {x.evidence.postedResults?"Registry results posted":"No posted registry results"};
       {" "}{x.evidence.primaryDefinitions.length===0?
        "primary endpoint not described in saved extract":
        "primary endpoint listed but no eligible metric lead"}.
       <small style={{display:"block"}}>
        Registry updated: {x.evidence.registryLastUpdated||"date unavailable"}
       </small></td>
      <td style={cell}>Locate dated protocol/endpoint and any sponsor or
       published readout. Match exact NCT, drug and indication;
       independently assess efficacy, risk and comparators.
       {historicalSourceByNct.get(x.trial.nctId)&&<details style={{marginTop:6}}>
        <summary style={{cursor:"pointer",color:"#135c45"}}>
         Historical source investigation (unscored)
        </summary>
        {(()=>{const lead=historicalSourceByNct.get(x.trial.nctId)!;return <div
         style={{padding:"7px 0",fontSize:12,lineHeight:1.5}}>
         <strong>{lead.evidenceType.replaceAll("_"," ")}</strong>
         <p>Source identity: {lead.identityBasis}</p>
         {lead.sourceUrl&&<a href={lead.sourceUrl}
          target="_blank" rel="noopener noreferrer">
          {lead.sourceTitle||"Open historical source"}</a>}
         {lead.sourceDate&&<small style={{display:"block"}}>
          Source dated {lead.sourceDate}</small>}
         <p>{lead.summary}</p>
         <strong>Next verification:</strong> {lead.nextAction}
         <p><strong>Numeric RAAS grade: N/A</strong> · Historical lead does not
          change registry posting classification or authorize FDA predictions.</p>
        </div>})()}
       </details>}
      </td>
     </tr>)}</tbody>
    </table>
   </div>
  </details>
  <div style={{display:"flex",flexWrap:"wrap",gap:12,margin:"14px 0",fontSize:13}}>
   <a href="/raas-trial-score-ledger.csv" download>Export 762 rows · trial ledger (CSV)</a>
   <a href="/raas-active-phase3-source-screen.csv" download>
    Export current Phase 3 source prescreen (CSV)</a>
   <a href="/api/raas-762-review-queue" download>
    Export all 22,860 assigned metric review tasks (CSV)</a>
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
     <option value="all">Both spreadsheet categories</option>
     <option value="posted">Past · results posted</option>
     <option value="protocol">Before · results not posted</option>
    </select>
   </label>
   <label style={{display:"flex",flexDirection:"column",gap:4,fontSize:12}}>
    Registry source leads
    <select aria-label="Filter registry source leads" value={leadFilter}
     onChange={e=>{setLeadFilter(e.target.value as LeadFilter);setPage(0)}}
     style={control}>
     <option value="all">All source states</option>
     <option value="has-leads">Has ungraded source leads</option>
     <option value="no-leads">Needs source discovery</option>
    </select>
   </label>
   <button type="button" style={control}
    onClick={()=>{setSearch("");setEvidenceFilter("all");setScoreFilter("all");setLeadFilter("all");setPage(0)}}>
    Clear all filters
   </button>
  </div>
  <p role="status" style={{fontSize:12,color:"#3a6049"}}>
   {filtered.length} matching NCTs · displaying {shown.length} on this page.
   Reviews are counted only in each trial's current registry-posting category.
  </p>
  <div role="region" aria-label="RAAS 762 exact NCT scoring row table" tabIndex={0}
   style={{overflowX:"auto",maxWidth:"100%",border:"1px solid #c5d8ca",borderRadius:8}}>
   <table style={{width:"100%",borderCollapse:"collapse",minWidth:750,fontSize:13}}>
    <thead style={{background:"#eaf4ed",color:"#19452c"}}>
     <tr>
      {["NCT / ticker","Spreadsheet category","Registry source leads","Reviewed metrics","Awaiting review",
       "Overall RAAS","Five clinical factors","Cross-stage history"].map(h=>
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
     <td style={cell}><strong>{x.stage==="pre"?"Before":"Past"}</strong>
      <small style={{display:"block",color:"#52705c"}}>
       {x.evidence.postedResults?"Results posted":"Results not posted"}
      </small>
     </td>
     <td style={cell}>
      <strong>{x.leadMetricCount}/5 possible metric areas</strong>
      <small style={{display:"block"}}>{x.sourceLeads.length} ungraded source leads</small>
      {x.sourceLeads.length>0&&<details style={{marginTop:5}}>
       <summary style={{cursor:"pointer",color:"#135c45"}}>View sources and measurements</summary>
       <div style={{maxHeight:280,overflowY:"auto",minWidth:240}}>
        {x.sourceLeads.map(lead=><div key={lead.id}
         style={{padding:"8px 0",borderBottom:"1px solid #dce8dc",fontSize:12}}>
         <strong>{lead.metricIds.join(", ")}</strong>
         <small style={{display:"block"}}>{lead.kind} · {lead.sourceDate}</small>
         <span style={{display:"block"}}>{lead.description}</span>
         {lead.measurement&&<small style={{display:"block"}}>
          Recorded {lead.measurement.label}: {lead.measurement.value} {lead.measurement.unit}
         </small>}
         <a href={lead.sourceUrl} target="_blank" rel="noopener noreferrer">
          Open primary registry record</a>
        </div>)}
       </div>
      </details>}
      {x.sourceLeads.length===0&&<small style={{display:"block"}}>
       No matching registry lead; additional primary-source research needed
      </small>}
     </td>
     <td style={cell}><strong>{x.reviewed}/5</strong>
      <small style={{display:"block"}}>Provisional review only</small></td>
     <td style={cell}><strong>{x.remaining}/5</strong>
      <small style={{display:"block"}}>Missing graded evidence</small></td>
     <td style={cell}><strong>Not validated</strong>
      <small style={{display:"block"}}>N/A · never 0/100</small>
      {x.independentReviews>0&&<small style={{display:"block"}}>
       {x.independentReviews} independent reviews</small>}
     </td>
     <td style={cell}><RaasClinicalFiveCell row={x.trial} bucket={null} researchStageOnly={x.stage}/></td>
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
