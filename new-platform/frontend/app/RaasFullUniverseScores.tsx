"use client";
import {useEffect,useMemo,useState} from "react";
import {parsePhase3CensusCsv,type Phase3CensusRegistryStatus} from "../lib/phase3-census-rows";
import {classifyPhase3Readouts,type ReadoutClassification,type ReadoutRow} from "../lib/phase3-public-readout";
import {parseRaasScreenedPhase3Csv,RAAS_RESTRICTED_PHASE3_CSV_QUERY,
 type RaasScreenedTrialRoster} from "../lib/raas-full-universe-roster";
import {provisionalScoresForTrial} from "../lib/raas-provisional-trial-scores";
import {raasSpreadsheetSummary} from "../lib/raas-spreadsheet-status";
import {raasRegistryCoverage} from "../lib/raas-stage-source-coverage";
import {rawRaasRegistryDesignDiagnostic} from "../lib/raas-raw-registry-design";
import {raasClinicalReportingDiagnostic} from "../lib/raas-clinical-reporting-diagnostic";
import {fullReviewedTrialCandidate} from "../lib/raas-reviewed-full-score";
import type {RaasStage} from "../lib/raas-metric-specs";
import RaasTrialHistoryButton from "./RaasTrialHistoryButton";
import RaasMetricGradebook from "./RaasMetricGradebook";
import RaasRegistryEvidenceButton from "./RaasRegistryEvidenceButton";
import {loadRegistryEvidenceIndex,registryTrialFor,
 type RegistryEvidenceIndex} from "../lib/raas-registry-evidence";
import css from "./raas-history/page.module.css";

type Assessment={row:ReadoutRow;stage:RaasStage|null;timing:number|null;
 metricCount:number;overallScore:number|null;sourceUrl:string|null;sourceDate:string|null;
 aiSourceCrosschecks:number;independentReviewedCount:number};
const PAGE_SIZE=50;
const cell={padding:"9px 8px",borderBottom:"1px solid #d9e5dd",verticalAlign:"top" as const};
const short=(n:number)=>n.toLocaleString("en-US");
const stageLabel=(s:RaasStage|null)=>s==="pre"?"TOP":s==="post"?"BOTTOM":"UNVERIFIED";
function assess(row:ReadoutRow):Assessment{
 const stage=row.evidence?.kind==="PRE_AS_OF_CHECK"?"pre":
  row.evidence?.kind==="POST_PUBLIC_READOUT"?"post":null;
 if(!stage)return {row,stage:null,timing:null,metricCount:0,overallScore:null,sourceUrl:null,sourceDate:null,
  aiSourceCrosschecks:0,independentReviewedCount:0};
 const a=provisionalScoresForTrial({
  nctId:row.nctId,ticker:row.ticker,
  drug:row.evidence?.drug,indication:row.evidence?.indication
 },stage);
 const grade=a.scoredMetrics[0];
 const candidate=fullReviewedTrialCandidate({nctId:row.nctId,ticker:row.ticker,
  drug:row.evidence?.drug,indication:row.evidence?.indication},stage,true);
 const reviewed=raasSpreadsheetSummary({
  nctId:row.nctId,ticker:row.ticker,
  drug:row.evidence?.drug,indication:row.evidence?.indication,
  classifiedStage:stage
 });
 const metricIds=new Set([...a.scoredMetrics.map(x=>x.metricId),
  ...candidate.grades.map(x=>x.metricId)]);
 return {row,stage,timing:grade?.score??null,metricCount:metricIds.size,
  overallScore:reviewed.approvedScore,
  sourceUrl:grade?.sourceUrl??null,sourceDate:grade?.sourceDate??null,
  aiSourceCrosschecks:candidate.aiCrosscheckedCount,
  independentReviewedCount:candidate.independentReviewedCount};
}
export default function RaasFullUniverseScores(){
 const [classified,setClassified]=useState<ReadoutClassification|null>(null);
 const [registryIndex,setRegistryIndex]=useState<RegistryEvidenceIndex|null>(null);
 const [censusError,setCensusError]=useState("");
 const [live,setLive]=useState<RaasScreenedTrialRoster|null>(null);
 const [liveState,setLiveState]=useState<"loading"|"ready"|"unavailable">("loading");
 const [liveError,setLiveError]=useState("");
 const [scope,setScope]=useState<"cap"|"historical"|"registry">("registry");
 const [query,setQuery]=useState("");
 const [stage,setStage]=useState<"all"|"pre"|"post"|"unverified">("all");
 const [rating,setRating]=useState<"all"|"scored"|"missing">("all");
 const [registryFilter,setRegistryFilter]=useState<"all"|"posted"|"protocol"|"unavailable">("all");
 const [page,setPage]=useState(0);
 const [refresh,setRefresh]=useState(0);
 useEffect(()=>{
  let active=true;
  void loadRegistryEvidenceIndex().then(result=>{if(active)setRegistryIndex(result);});
  return ()=>{active=false;};
 },[]);
 useEffect(()=>{
  const ctrl=new AbortController();
  Promise.all([
   fetch("/phase3-census-2026-10-26.csv",{cache:"no-store",signal:ctrl.signal}),
   fetch("/phase3-public-readout-evidence-2026-11-01.json",{cache:"no-store",signal:ctrl.signal})
  ]).then(async ([csv,ev])=>{
   if(!csv.ok||!ev.ok)throw Error("Published Phase 3 research sources unavailable");
   return classifyPhase3Readouts(await ev.json(),parsePhase3CensusCsv(await csv.text()).rows);
  }).then(data=>{if(!ctrl.signal.aborted)setClassified(data);})
   .catch(e=>{if(!ctrl.signal.aborted)setCensusError(
    e instanceof Error?e.message:"Phase 3 census unavailable");});
  return ()=>ctrl.abort();
 },[]);
 useEffect(()=>{
  if(!classified)return;
  const ctrl=new AbortController();
  setLiveState("loading");setLiveError("");
  // This route already applies the $300M–$10B issuer cap screen, stages
  // and NCT-based trial deduplication, and returns ALL matching rows as CSV.
  // A 401/outage must not silently turn an old historical census into live PIPELINE.
  void fetch(RAAS_RESTRICTED_PHASE3_CSV_QUERY,{cache:"no-store",credentials:"same-origin",signal:ctrl.signal})
   .then(async response=>{
    if(!response.ok)throw Error(response.status===401?
     "Sign in to access the cap-screened Phase 3 population":
     "Current cap-screened source not available (HTTP "+response.status+")");
    const csv=await response.text();
    return parseRaasScreenedPhase3Csv(csv,classified);
   }).then(result=>{
    if(!ctrl.signal.aborted){setLive(result);setLiveState("ready");}
   }).catch(e=>{
    if(!ctrl.signal.aborted){setLive(null);setLiveState("unavailable");
     setLiveError(e instanceof Error?e.message:"Unable to verify live roster");}
   });
  return ()=>ctrl.abort();
 },[classified,refresh]);
 const historical=useMemo(()=>classified?
  [...classified.pre,...classified.post,...classified.unverified].sort(
   (a,b)=>a.ticker.localeCompare(b.ticker)||a.nctId.localeCompare(b.nctId)):[],[classified]);
 const registryResearchRows=useMemo(()=>{
  if(!classified||!registryIndex)return [];
  const documented=new Map([...classified.pre,...classified.post].map(x=>[x.nctId,x]));
  const validStatuses=new Set(["RECRUITING","ACTIVE_NOT_RECRUITING","ENROLLING_BY_INVITATION",
   "NOT_YET_RECRUITING","COMPLETED","TERMINATED","WITHDRAWN"]);
  return registryIndex.records.map(entry=>{
   const prior=documented.get(entry.nctId);
   const matched=prior&&prior.ticker===entry.ticker?prior:null;
   return {nctId:entry.nctId,ticker:entry.ticker,
    company:matched?matched.company:"Issuer name not in this registry source",
    status:(validStatuses.has(entry.registryStatus)?entry.registryStatus:"UNKNOWN") as Phase3CensusRegistryStatus,
    sourceUrl:entry.sourceUrl,pipelineQualification:null,fdaPdufaVerification:false as const,
    evidence:matched?matched.evidence:null};
  }).sort((a,b)=>a.ticker.localeCompare(b.ticker)||a.nctId.localeCompare(b.nctId));
 },[classified,registryIndex]);
 const effectiveLive=scope==="cap"&&liveState==="ready"&&live!==null;
 const fallback=scope==="cap"&&!effectiveLive;
 const universe=scope==="registry"?registryResearchRows:effectiveLive?live!.rows:historical;
 const assessments=useMemo(()=>universe.map(assess),[universe]);
 const indexed=useMemo(()=>assessments.map(x=>{
  const trial={nctId:x.row.nctId,ticker:x.row.ticker,drug:x.row.evidence?.drug};
  const registry=registryTrialFor(registryIndex,trial);
  return {...x,registry,
   topRegistryCoverage:raasRegistryCoverage(trial,"pre",registry),
   bottomRegistryCoverage:raasRegistryCoverage(trial,"post",registry),
   rawDesignDiagnostic:rawRaasRegistryDesignDiagnostic(registry,trial),
   clinicalReportingDiagnostic:raasClinicalReportingDiagnostic(registry,trial)};
 }),[assessments,registryIndex]);
 const stats=useMemo(()=>({
  top:assessments.filter(x=>x.stage==="pre").length,
  bottom:assessments.filter(x=>x.stage==="post").length,
  unverified:assessments.filter(x=>x.stage===null).length,
  numericallyGraded:assessments.filter(x=>x.metricCount>0).length,
  aiSourceCrosschecks:assessments.reduce((n,x)=>n+x.aiSourceCrosschecks,0),
  independentMetricReviews:assessments.reduce((n,x)=>n+x.independentReviewedCount,0),
  fullOverall:assessments.filter(x=>x.overallScore!==null).length,
  rawDesignGraded:indexed.filter(x=>x.rawDesignDiagnostic?.score!==null&&
   x.rawDesignDiagnostic?.score!==undefined).length,
  clinicalReportingGraded:indexed.filter(x=>x.clinicalReportingDiagnostic?.score!==null&&
   x.clinicalReportingDiagnostic?.score!==undefined).length,
  postedRegistry:indexed.filter(x=>x.registry?.postedResults===true).length,
  protocolRegistry:indexed.filter(x=>x.registry?.postedResults===false).length,
  missingRegistry:indexed.filter(x=>!x.registry).length
 }),[assessments,indexed]);
 const filtered=useMemo(()=>{
  const q=query.trim().toLowerCase();
  return indexed.filter(x=>
   (stage==="all"||(stage==="unverified"?x.stage===null:x.stage===stage))&&
   (rating==="all"||(rating==="scored"?x.metricCount>0:x.metricCount===0))&&
   (registryFilter==="all"||(registryFilter==="posted"?x.registry?.postedResults===true:
    registryFilter==="protocol"?x.registry?.postedResults===false:!x.registry))&&
   (!q||[x.row.nctId,x.row.ticker,x.row.company,
    x.row.evidence?.drug||"",x.row.evidence?.indication||""].some(v=>v.toLowerCase().includes(q))));
 },[indexed,stage,rating,registryFilter,query]);
 const pageCount=Math.ceil(filtered.length/PAGE_SIZE);
 const currentPage=Math.min(page,Math.max(0,pageCount-1));
 const visible=filtered.slice(currentPage*PAGE_SIZE,(currentPage+1)*PAGE_SIZE);
 if(censusError)return <section className={css.section} role="alert">
  <h2>All-trial RAAS assessment</h2><p>{censusError}. No trial counts asserted.</p></section>;
 if(!classified)return <section className={css.section} role="status">Loading the full Phase 3 source census and readout classifications…</section>;
 if(scope==="registry"&&!registryIndex)return <section className={css.section} role="status">
  Loading all 762 unique ClinicalTrials.gov research records and raw design grades…
 </section>;
 return <section className={css.section} data-raas-all-trials="true"
  data-raas-roster-scope={scope==="registry"?"registry-762-research":
   effectiveLive?"cap-screened":"historical-census"}>
  <div className={css.sectionTitle}>
   <h2>RAAS assessment · all available Phase 3 trial rows</h2>
   <span>{short(assessments.length)} trials in selected source · no five-trial cap</span>
  </div>
  <p className={css.disclaimer}><strong>Coverage is not a validated numeric score.</strong>
   Every candidate in the selected source is assessed for currently available
   research-only grading rules. No source evidence means <strong>Not scored</strong>,
   never 0/100. This view does not independently verify PIPELINE or PDUFA eligibility.
   TOP/BOTTOM are assigned only from separately documented issuer readouts; registry
   stage names alone do not establish public results. Every trial can now open both
   TOP and BOTTOM 30-metric evidence reviews while classification is unresolved.
   Use the Registry facts button
   on every row, including UNVERIFIED, to inspect newly collected evidence.</p>
  <div style={{display:"flex",gap:8,flexWrap:"wrap",alignItems:"center",margin:"12px 0"}}>
   <button type="button" aria-pressed={scope==="registry"}
    data-raas-full-source-roster="true" onClick={()=>{setScope("registry");setPage(0)}}
    style={{padding:"9px 12px",fontWeight:700,
     background:scope==="registry"?"#dceddf":"#f8fbf8",
     border:"1px solid #a9c8b3",borderRadius:7,color:"#144e32"}}>
    All 762 registry research trials · raw grades
   </button>
   <button type="button" aria-pressed={scope==="cap"}
    onClick={()=>{setScope("cap");setPage(0)}}
    style={{padding:"9px 12px",fontWeight:700,
     background:scope==="cap"?"#dceddf":"#f8fbf8",
     border:"1px solid #a9c8b3",borderRadius:7,color:"#144e32"}}>
    Market-cap-screened Phase 3 pool
   </button>
   <button type="button" aria-pressed={scope==="historical"}
    onClick={()=>{setScope("historical");setPage(0)}}
    style={{padding:"9px 12px",fontWeight:700,
     background:scope==="historical"?"#dceddf":"#f8fbf8",
     border:"1px solid #a9c8b3",borderRadius:7,color:"#144e32"}}>
    Historical 741-trial census
   </button>
   <button type="button" onClick={()=>setRefresh(n=>n+1)}
    disabled={liveState==="loading"}
    style={{padding:"9px 12px",border:"1px solid #a9c8b3",borderRadius:7}}>
    Refresh screened roster
   </button>
  </div>
  {fallback&&<p className={css.disclaimer} role="status"><strong>Screened source {liveState==="loading"?"loading":"unavailable"}.</strong>
   {liveError?" "+liveError+".":""} Showing the <strong>741-trial historical research census as a labeled fallback</strong>,
   not substituting it for the complete current PIPELINE.</p>}
  {scope==="cap"&&!fallback&&<p className={css.disclaimer} role="status">
   <strong>Screened-source snapshot:</strong> {live!.sourceAsOf}.
   This is the available $300M–$10B issuer-cap-screened Phase 3/Phase 3 Results
   subset from the existing TOOLS source. It is <strong>not</strong> proof
   of current capitalization, active study, lead-program status or FDA PDUFA eligibility.</p>}
  {scope==="registry"&&registryIndex&&<p className={css.disclaimer}
   data-raas-registry-full-762-status="true">
   Complete exact-NCT ClinicalTrials.gov research population: {registryIndex.records.length}
   trials, source snapshot {registryIndex.sourceAsOf}. This research inventory
   is not independently confirmed to be current $300M–$10B PIPELINE, or issuer-evidenced
   TOP/BOTTOM status. The raw 0–100 study-design diagnostic is separate from
   validated 30-metric RAAS scores and cannot predict efficacy, FDA decisions or returns.
  </p>}
  {scope==="historical"&&<p className={css.disclaimer}>
   Historical research census dated {classified.censusDate}; classification sources last checked
   {classified.sourceAsOf}. These 741 NCTs are not the full currently qualified PIPELINE.</p>}
  <div className={css.stats} data-raas-universe-summary="true">
   <div><strong>{short(assessments.length)}</strong><span>Unique NCTs evaluated for available score rules</span></div>
   <div><strong>{short(stats.numericallyGraded)}</strong><span>Trials with a source-backed experimental metric (not overall RAAS)</span></div>
   <div data-raas-ai-source-crosschecks="true"><strong>{short(stats.aiSourceCrosschecks)}</strong><span>AI source-and-independent-literature clinical checks · provisional only</span></div>
   <div data-raas-independent-reviews="true"><strong>{short(stats.independentMetricReviews)}</strong><span>Independently adjudicated metric reviews · full RAAS still requires 30/30 per stage</span></div>
   <div><strong>{short(stats.top)} / {short(stats.bottom)}</strong><span>Issuer-evidenced TOP / BOTTOM</span></div>
   <div><strong>{short(stats.unverified)}</strong><span>Unverified readout-stage trials · not assumed TOP</span></div>
   <div data-raas-raw-design-graded="true"><strong>{short(stats.rawDesignGraded)}</strong>
    <span>Trials with 0–100 experimental study-design grades; separate from overall RAAS</span></div>
   <div data-raas-clinical-reporting-graded="true"><strong>{short(stats.clinicalReportingGraded)}</strong>
    <span>Posted-result trials with numerical source-documentation grades (NOT efficacy or RAAS)</span></div>
  </div>
  <div className={css.stats} data-raas-registry-review-queues="true">
   <div><strong>{short(stats.postedRegistry)}</strong>
    <span>Registry-posted results · BOTTOM evidence review candidates, not verified BOTTOM</span></div>
   <div><strong>{short(stats.protocolRegistry)}</strong>
    <span>Registry protocol only · TOP evidence review candidates, not verified TOP</span></div>
   <div><strong>{short(stats.missingRegistry)}</strong>
    <span>Outside current registry evidence snapshot · needs separate source collection</span></div>
  </div>
  {registryIndex?.summary.trialsWithPrimaryGroupMeasurements!==undefined&&<div className={css.stats}
   data-raas-quantitative-clinical-evidence="true">
   <div><strong>{short(registryIndex.summary.trialsWithPrimaryGroupMeasurements)}</strong>
    <span>Trials with actual primary-outcome arm measurements (ungraded)</span></div>
   <div><strong>{short(registryIndex.summary.trialsWithPrimaryComparisons??0)}</strong>
    <span>Trials with documented identified-group statistical contrasts (ungraded)</span></div>
   <div><strong>{short(registryIndex.summary.trialsWithPrimaryConfidenceIntervals??0)}</strong>
    <span>Trials with published primary-analysis confidence limits (ungraded)</span></div>
   <div><strong>{short(registryIndex.summary.trialsWithSafetyRiskDenominators??0)}</strong>
    <span>Trials with serious-event affected/at-risk counts (ungraded)</span></div>
  </div>}
  <p style={{fontSize:13,lineHeight:1.5,margin:"12px 0"}} data-raas-ledger-download="true">
   <a href="/raas-trial-score-ledger.csv" download
    style={{fontWeight:700,color:"#135b3b",textDecoration:"underline"}}>
    Download all-trial RAAS source-score ledger (CSV)
   </a>
   {" "}· one row per registry NCT with numerical trial-design diagnostic where
   source facts are sufficient, observed and missing design facets, TOP/BOTTOM
   source-lead weights, separately counted AI/independent metric reviews,
   and explicit N/A for missing full RAAS scores. The design diagnostic is
   <strong> not </strong> an FDA probability or complete RAAS rating.
  </p>
  <p style={{fontSize:13,lineHeight:1.5,margin:"12px 0"}} data-raas-all-trials-reviewed-partial="true">
   <strong>Source-reviewed RAAS metric ratings for every NCT:</strong>{" "}
   <a href="/raas-all-trials-partial-metric-ratings.csv" download
    style={{fontWeight:700,color:"#135b3b",textDecoration:"underline"}}>
    Download all 762 trials · TOP/BOTTOM partial metric ratings and coverage (CSV)
   </a>. Two stage-specific research rows per NCT show independently counted
   AI source-checks, reviewed-metric-only mean out of 100, weighted 30-metric
   coverage, missing metric IDs and actual research findings. <strong>An observed
   partial mean is not a complete RAAS score.</strong> Missing metrics never become
   zero; a Phase 3 registration does not verify current PIPELINE eligibility,
   readout stage or prospective FDA PASS/CRL/extension probabilities.
  </p>
  <p style={{fontSize:13,lineHeight:1.5,margin:"12px 0"}} data-raas-current-phase3-top-pilot-download="true">
   <strong>Current cap-screened Phase 3 TOP scoring pilot:</strong>{" "}
   <a href="/raas-current-pipeline-pre-metric-audit.csv" download
    style={{fontWeight:700,color:"#135b3b",textDecoration:"underline"}}>
    Download five current Phase 3 trial-by-trial 30-metric scorecards (150-row CSV)
   </a>.
   Five source-checked $300M–$10B Phase 3 trial NCTs across <strong>three listed issuers
   (TRVI, LBRX, CYTK)</strong>, including OCEAN-1, OCEAN-2, NOVA-2, NOVA-3 and COMET-HF,
   with <strong>24 provisional pre-readout metric reviews and 126 missing metric reviews</strong>.
   NOVA-3 is a 52-week open-label safety study; COMET-HF is event-driven.
   Neither has a verified topline date, so the audit leaves that field blank.
   Capitalization snapshots are dated November 3, 2026 and become <strong>stale
   after seven calendar days</strong> without another verified quote.
   These are five sampled trials, <strong>not the complete current Pipeline</strong>.
   No trial here has an FDA-accepted NDA/BLA or source-verified PDUFA action date;
   no full 30/30 score, FDA probability or trade recommendation is available.
  </p>
  <p style={{fontSize:13,lineHeight:1.5,margin:"12px 0"}} data-raas-ten-trial-pilot-download="true">
   <strong>10-trial, 30-metric retrospective RAAS pilot:</strong>{" "}
   <a href="/raas-ten-trial-metric-pilot.csv" download
    style={{fontWeight:700,color:"#135b3b",textDecoration:"underline"}}>
    Download actual graded metrics and every missing item (300-row CSV)
   </a>.
   This is a deliberately chosen <strong>historical trial sample</strong>, not current
   PIPELINE eligibility or a holdout prediction test. The source-checked clinical,
   safety, and pre-decision manufacturing-risk metrics are individually graded.
   All other cells remain unscored, and no complete 30/30 RAAS or FDA probability is claimed.
   {" "}· <a href="/raas-historical-fda-application-outcomes.csv" download>
    Download historical FDA application outcomes (one event per NDA, not per trial)
   </a>. Known historical approval and CRL outcomes are NEVER used to claim
   prospective model prediction accuracy.
  </p>
  <p style={{fontSize:13,lineHeight:1.5,margin:"12px 0"}} data-raas-clinical-evidence-download="true">
   <a href="/raas-clinical-evidence-components.csv" download>Download clinical source-documentation grades</a>
   {" "}· <a href="/raas-primary-comparisons.csv" download>Primary statistical comparisons</a>
   {" "}· <a href="/raas-serious-event-rates.csv" download>Observed serious-event group rates</a>.
   Primary comparisons now include group titles exactly as reported by ClinicalTrials.gov,
   with unresolved names marked, not guessed. These are trial-matched facts and reporting
   completeness, never treatment-vs-placebo clinical grades or validated 30/30 RAAS ratings.
  </p>
  <p style={{fontSize:12,lineHeight:1.5,margin:"6px 0"}}>
   <strong>TOP/BOTTOM registry source coverage is calculated across every matched NCT.</strong>
   Percentages measure the share of 30 metric research weights with a mapped
   ClinicalTrials.gov source lead, not clinical success probability, stock return,
   or a numerical overall RAAS grade.
  </p>
 
  <div style={{display:"flex",gap:9,alignItems:"end",flexWrap:"wrap",margin:"12px 0"}}>
   <label style={{display:"flex",flexDirection:"column",gap:3,fontSize:12}}>
    Search all selected trials
    <input aria-label="Filter all RAAS trials" value={query}
     onChange={e=>{setQuery(e.target.value);setPage(0)}} placeholder="NCT, ticker, company, drug"
     style={{padding:8,minWidth:180}} maxLength={90}/>
   </label>
   <label style={{display:"flex",flexDirection:"column",gap:3,fontSize:12}}>
    Readout classification
    <select aria-label="Filter RAAS readout classification" value={stage}
     onChange={e=>{setStage(e.target.value as typeof stage);setPage(0)}} style={{padding:8}}>
     <option value="all">All stages</option>
     <option value="pre">TOP</option>
     <option value="post">BOTTOM</option>
     <option value="unverified">UNVERIFIED</option>
    </select>
   </label>
   <label style={{display:"flex",flexDirection:"column",gap:3,fontSize:12}}>
    Numerical component status
    <select aria-label="Filter RAAS numerical grading" value={rating}
     onChange={e=>{setRating(e.target.value as typeof rating);setPage(0)}} style={{padding:8}}>
     <option value="all">All trials</option>
     <option value="scored">Experimental metric available</option>
     <option value="missing">No numeric metric yet</option>
    </select>
   </label>
   <label style={{display:"flex",flexDirection:"column",gap:3,fontSize:12}}>
    Registry evidence review queue
    <select aria-label="Filter registry source evidence" value={registryFilter}
     onChange={e=>{setRegistryFilter(e.target.value as typeof registryFilter);setPage(0)}}
     style={{padding:8}}>
     <option value="all">All registry evidence states</option>
     <option value="posted">Results posted · BOTTOM review candidate</option>
     <option value="protocol">Protocol only · TOP review candidate</option>
     <option value="unavailable">Not in current registry snapshot</option>
    </select>
   </label>
   <button type="button" onClick={()=>{setQuery("");setStage("all");setRating("all");setRegistryFilter("all");setPage(0)}}
    style={{padding:"9px 12px",border:"1px solid #a9c8b3",borderRadius:7}}>Clear filters</button>
  </div>
  <p style={{fontSize:12,color:"#456f54"}} role="status">{short(filtered.length)} matching trial rows;
   {stats.numericallyGraded} of {assessments.length} have any numeric experimental metric;
   <strong> {stats.fullOverall} approved overall scores</strong> · {stats.aiSourceCrosschecks} AI source checks (not approved). Missing full scores are N/A.</p>
  <div style={{overflowX:"auto",maxWidth:"100%"}} role="region" aria-label="Entire selected RAAS trial assessment table" tabIndex={0}>
   <table style={{width:"100%",borderCollapse:"collapse",minWidth:810,fontSize:12}}>
    <thead><tr>{["Trial · company","Classification","Overall RAAS","Experimental component","Metrics graded","AI benchmark checks","Source / missing evidence","Raw trial-design grade","Clinical reporting grade","TOP source coverage","BOTTOM source coverage","Registry facts","All 30 metrics","History"].map(c=>
     <th key={c} scope="col" style={{...cell,textAlign:"left",borderBottom:"2px solid #98bda3"}}>{c}</th>)}</tr></thead>
    <tbody>{visible.map(x=><tr key={x.row.nctId} data-raas-nct={x.row.nctId}>
     <td style={cell}><strong>{x.row.ticker}</strong> · <a href={x.row.sourceUrl}
      target="_blank" rel="noopener noreferrer">{x.row.nctId}</a>
      <span style={{display:"block",color:"#507763",fontSize:11}}>{x.row.company}</span></td>
     <td style={cell}><strong>{stageLabel(x.stage)}</strong>
      <span style={{display:"block",fontSize:11}}>
       {x.stage?"Issuer readout evidence":"Stage source verification required"}</span>
      <span style={{display:"block",fontSize:11}}>
       {x.registry?.postedResults===true?"Registry results posted":
        x.registry?.postedResults===false?"Registry protocol only":"No current registry match"}</span></td>
     <td style={cell}><strong>{x.overallScore===null?"— /100":x.overallScore+"/100"}</strong>
      <span style={{display:"block",fontSize:11}}>{x.overallScore===null?"Not validated":"Approved / reviewed"}</span></td>
     <td style={cell}>{x.timing!==null?<><strong>{x.timing}/100</strong>
      <span style={{display:"block",fontSize:11}}>{x.stage==="pre"?"Timing specificity only":"Clinical contrast pilot only"}</span></>:
      <span>Not scored</span>}</td>
     <td style={cell}><strong>{x.stage?x.metricCount+"/30":"0 verified / 30"}</strong>
      <span style={{display:"block",fontSize:11}}>No missing input scored as zero</span></td>
     <td style={cell} data-raas-row-ai-crosschecks={x.row.nctId}>
      <strong>{x.aiSourceCrosschecks}/30</strong>
      <span style={{display:"block",fontSize:11}}>AI source crosschecks; {x.independentReviewedCount} independently reviewed; not a full RAAS score</span>
     </td>
     <td style={cell}>{x.sourceUrl?<a href={x.sourceUrl} target="_blank"
      rel="noopener noreferrer">Component source · {x.sourceDate}</a>:
      x.stage===null?"TOP and BOTTOM checklists available · public readout stage still unverified":
      "Source-backed rule and required inputs not yet available"}</td>
     <td style={cell} data-raas-raw-design-grade={x.row.nctId}>
      <strong>{x.rawDesignDiagnostic?.score===null||!x.rawDesignDiagnostic?"N/A":
       x.rawDesignDiagnostic.score+"/100"}</strong>
      <span style={{display:"block",fontSize:11}}>
       {x.rawDesignDiagnostic?x.rawDesignDiagnostic.knownFacets+"/4 documented criteria":"Source unavailable"}
       {" "}· study design only, NOT predictive RAAS
      </span>
      {x.rawDesignDiagnostic&&<span style={{display:"block",fontSize:11}}>
       Missing-data range: {x.rawDesignDiagnostic.lowerBound}–{x.rawDesignDiagnostic.upperBound}
      </span>}
     </td>
     <td style={cell} data-raas-clinical-reporting-grade={x.row.nctId}>
      <strong>{x.clinicalReportingDiagnostic?.score==null?"N/A":
       x.clinicalReportingDiagnostic.score+"/100"}</strong>
      <span style={{display:"block",fontSize:11}}>
       {x.clinicalReportingDiagnostic?.documentedOf5==null?
        "No posted results or source available":x.clinicalReportingDiagnostic.documentedOf5+"/5 reporting criteria"}
       {" "}· documentation only, NOT RAAS efficacy
      </span>
     </td>
     <td style={cell} data-raas-top-source-coverage={x.row.nctId}>
      <strong>{x.topRegistryCoverage===null?"N/A":x.topRegistryCoverage.sourceWeightPct+"%"}</strong>
      <span style={{display:"block",fontSize:11}}>Mapped source lead weights, not RAAS performance</span></td>
     <td style={cell} data-raas-bottom-source-coverage={x.row.nctId}>
      <strong>{x.bottomRegistryCoverage===null?"N/A":x.bottomRegistryCoverage.sourceWeightPct+"%"}</strong>
      <span style={{display:"block",fontSize:11}}>Posted primary/safety evidence, not RAAS performance</span></td>
     <td style={cell}><RaasRegistryEvidenceButton row={x.row}/></td>
     <td style={cell}><RaasMetricGradebook row={x.row} bucket={x.stage}/></td>
     <td style={cell}><RaasTrialHistoryButton row={x.row} bucket={x.stage}/></td>
    </tr>)}</tbody>
   </table>
  </div>
  {filtered.length===0&&<p role="status">No trials match these filters; the source universe has not been changed.</p>}
  <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",gap:8,margin:"12px 0"}}>
   <button type="button" disabled={currentPage===0} onClick={()=>setPage(p=>Math.max(0,p-1))}
    style={{padding:"8px 12px"}}>Previous 50</button>
   <span style={{fontSize:12}}>Page {pageCount?currentPage+1:0} of {pageCount}</span>
   <button type="button" disabled={currentPage>=pageCount-1}
    onClick={()=>setPage(p=>p+1)} style={{padding:"8px 12px"}}>Next 50</button>
  </div>
  <p className={css.disclaimer}>Trial History follows a unique NCT and therapy across TOP, BOTTOM and
   UNVERIFIED. Historical score timestamps begin when a calculation was genuinely
   recorded, not on an older company announcement date. The eligible scoring
   cohort cannot be expanded beyond the documented source universe without fresh
   verified source records.</p>
 </section>;
}
