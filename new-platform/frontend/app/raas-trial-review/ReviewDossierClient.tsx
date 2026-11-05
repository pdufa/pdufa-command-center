"use client";
import {useMemo,useState} from "react";
import type {RaasStage} from "../../lib/raas-metric-specs";
import type {TrialMetricReviewDossier,TrialMetricReview}
 from "../../lib/raas-trial-metric-review-dossier";
import css from "./ReviewDossierClient.module.css";
type EvidenceFilter="all"|"provisional"|"source"|"missing";
export default function ReviewDossierClient({dossier}:{
 dossier:TrialMetricReviewDossier
}){
 const [stage,setStage]=useState<RaasStage>(
  dossier.trial.stage==="post"?"post":"pre");
 const [selected,setSelected]=useState("pre-1-1");
 const [filter,setFilter]=useState<EvidenceFilter>("all");
 const data=dossier.perStage[stage];
 const categories=useMemo(()=>data.categories.map(category=>({
  ...category,metrics:category.metrics.filter(m=>filter==="all"||
   (filter==="provisional"&&!!m.provisionalReview)||
   (filter==="source"&&m.registryLeadCount>0)||
   (filter==="missing"&&!m.provisionalReview))
 })).filter(c=>c.metrics.length>0),[data,filter]);
 const all=data.categories.flatMap(c=>c.metrics);
 const metric=all.find(x=>x.metricId===selected)||
  categories[0]?.metrics[0]||null;
 const raw=metric?.registryLeads??[];
 const chooseStage=(value:RaasStage)=>{
  setStage(value);setSelected(value+"-1-1");setFilter("all");
 };
 const search=new URLSearchParams({nctId:dossier.trial.nctId,ticker:dossier.trial.ticker});
 return <section className={css.root}
  data-raas-60-metric-trial-dossier={dossier.trial.nctId}>
  <div className={css.stats}>
   {([
    [dossier.trial.ticker+" · "+dossier.trial.nctId,"Exact registered trial"],
    [data.reviewCount+"/30","Provisional metric reviews · selected stage"],
    [data.withRegistryLeads+"/30","Metrics with original registry leads"],
    [dossier.sourceIntegrityFlagCount,"Source-interpretation checks"],
    [dossier.certifiedMetrics,"Authenticated external metric sign-offs"],
    [dossier.approvedScores,"Approved composite RAAS scores"]
   ] as const).map(([n,label])=><div className={css.stat} key={label}>
    <strong>{n}</strong><span>{label}</span>
   </div>)}
  </div>
  <div className={dossier.ambiguousProgramReviews?css.warn:css.info}>
   <p><strong>Readout research stage:</strong>{" "}
    {dossier.trial.stage==="unverified"?
     "Not verified by separate dated public-readout evidence. TOP and BOTTOM are candidate worklists only.":
     dossier.trial.stage==="pre"?
     "TOP candidate source evidence is documented; review its date before using it prospectively.":
     "BOTTOM candidate source evidence is documented; do not infer FDA approval."}
    {" "}Registry snapshot {dossier.registrySnapshotAsOf}.
    {" "}Provisional metric review feed {dossier.provisionalReviewFeedAsOf}.
    {" "}These figures are not an approved 30/30 rating or an FDA probability.</p>
   {dossier.acceptedStageSource&&<p><strong>Separate stage lead:</strong>{" "}
    <a href={dossier.acceptedStageSource.url} target="_blank"
     rel="noopener noreferrer">Original dated {dossier.acceptedStageSource.stage.toUpperCase()} source</a>
    {" "}({dossier.acceptedStageSource.date}). Verify program identity and freshness.</p>}
   {dossier.ambiguousProgramReviews&&<p><strong>Program identity hold:</strong>
    Multiple drug/indication research review identities are attached to this
    trial. Provisional grades have been withheld to prevent mixing programs.
    Confirm the exact asset and indication before adjudication.</p>}
  </div>
  <div className={css.controls}>
   <label className={css.control}>
    Research review requirements
    <select aria-label="Select TOP or BOTTOM 30-metric worklist" value={stage}
     onChange={e=>chooseStage(e.target.value as RaasStage)}>
     <option value="pre">TOP — 30 pre-readout metrics</option>
     <option value="post">BOTTOM — 30 post-readout metrics</option>
    </select>
   </label>
   <label className={css.control}>
    Metric review filter
    <select aria-label="Filter trial metric review status" value={filter}
     onChange={e=>setFilter(e.target.value as EvidenceFilter)}>
     <option value="all">All 30 requirements</option>
     <option value="provisional">Provisional source-reviewed findings</option>
     <option value="source">Has ungraded registry source leads</option>
     <option value="missing">Without provisional review</option>
    </select>
   </label>
   <a className={css.link} href={"/api/raas-trial-review-dossier?"+search.toString()}
    download data-raas-download-exact-review-dossier="true">
    Download all 60 metric source-review packets (JSON)
   </a>
  </div>
  <div className={css.panels}>
   <section className={css.left} aria-label="RAAS metric selection">
    <p style={{fontWeight:750,fontSize:13,margin:"0 0 10px",color:"#21503a"}}>
     {stage.toUpperCase()} · {categories.reduce((a,c)=>a+c.metrics.length,0)}
     {" "}matching metric requirements · choose a row to open details at right
    </p>
    {categories.map((category,i)=><details key={category.id} open={filter!=="all"||i===0}
     className={css.category}>
     <summary>{category.name} · category weight {category.weight}%
      {" "}· {category.metrics.length} matching
     </summary>
     {category.metrics.map(m=><button type="button" key={m.metricId}
      data-raas-metric-review-select={m.metricId}
      aria-pressed={metric?.metricId===m.metricId}
      className={css.metric+" "+(metric?.metricId===m.metricId?css.metricSelected:"")}
      onClick={()=>setSelected(m.metricId)}>
      <span className={css.metricTitle}>{m.metricId} · {m.name}</span>
      <span className={css.metricMeta}>
       {m.provisionalReview?"Provisional research "+m.provisionalReview.researchBand+"/100":
        "N/A · not provisionally reviewed"}
       {" "}· {m.registryLeadCount} raw registry lead(s)
      </span>
     </button>)}
    </details>)}
    {categories.length===0&&<p>No metrics match this filter. Try All 30 requirements.</p>}
   </section>
   <section className={css.right} aria-label="Selected RAAS metric source details"
    data-raas-selected-metric-review={metric?.metricId||"none"}>
    {metric?<MetricDetails metric={metric} trial={dossier.trial.nctId}
     sourceHash={dossier.trial.sourceHash}
     sourceIntegrityFlagCount={dossier.sourceIntegrityFlagCount}
     stageSourceVerified={dossier.trial.stage===stage}/>:
     <p>No source-backed metric matches the selected filter.</p>}
   </section>
  </div>
  <div className={css.info}>
   <p><strong>What prevents approval?</strong> A documented original-source
    clinical/financial assessment against a relevant independent benchmark,
    identification of uncertainty and critical risks, an authenticated external
    expert sign-off, exact-program and readout-stage verification, and separate
    prospective FDA outcome calibration. A registry lead, a provisional AI grade,
    or a passing software test does not satisfy those requirements.</p>
  </div>
 </section>;
}
function MetricDetails({metric:m,trial,sourceHash,sourceIntegrityFlagCount,
 stageSourceVerified}:{
 metric:TrialMetricReview;trial:string;sourceHash:string;
 sourceIntegrityFlagCount:number;stageSourceVerified:boolean
}){
 const report=m.provisionalReview;
 return <div className={css.details}>
  <h2>{m.metricId} · {m.name}</h2>
  <div className={css.info}>
   <strong>{report?"Provisional source-reviewed research band: "+report.researchBand+"/100":
    "N/A — no source-reviewed research grade"}
   </strong>
   <p>{report?"Not approved; no authenticated independent sign-off.":
    "Missing is N/A, never 0 or a neutral 50. Registered source facts do not become a grade."}
    {" "}Metric weight within this stage: {m.metricWeightPercent}%.
    {" "}Public-readout stage independently established for this worklist:{" "}
    {stageSourceVerified?"separate dated lead available (recheck)":"not established"}.</p>
  </div>
  <div className={css.rule}>
   <h3>1 · Required source evidence</h3>
   <p>{m.requiredEvidence}</p>
   <h3>2 · Scoring criterion</h3>
   <p>{m.scoreRule}</p>
   <h3>3 · Critical risk to challenge</h3>
   <p>{m.criticalRisk}</p>
  </div>
  {report&&<div className={css.warn} data-raas-provisional-review={m.metricId}>
   <strong>Existing source-backed provisional review · {report.finding.replaceAll("_"," ")}</strong>
   <p><strong>Exact asset:</strong> {report.drug} · {report.indication}.
    {" "}Assessed {report.assessedAt}; primary source dated {report.sourceDate}.
    {" "}Feed review class: {report.feedReviewClass}.
    This status does not document authenticated external clinical sign-off.</p>
   <p><strong>Observed finding:</strong> {report.observedResult}</p>
   <p><strong>Independent benchmark context:</strong> {report.benchmarkContext}</p>
   <p><strong>Uncertainty:</strong> {report.uncertaintyReview}</p>
   <p><strong>Critical counterarguments:</strong> {report.criticalRiskReview}</p>
   <p><strong>Method:</strong> {report.reviewerMethod}</p>
   <p><a href={report.sourceUrl} target="_blank" rel="noopener noreferrer">
     Original source</a> ·
    {" "}<a href={report.benchmarkSourceUrl} target="_blank" rel="noopener noreferrer">
     Benchmark publication/source</a></p>
  </div>}
  <div className={css.rule} data-raas-metric-source-evidence={m.metricId}>
   <h3>4 · Original registry research leads ({m.registryLeadCount})</h3>
   <p>Every observation below is attached to exact trial {trial} and
    source checksum {sourceHash.slice(0,14)}…. The data may have been
    posted after the original public readout; historical predictions
    must not use later evidence. Unadjusted contrast and serious-event
    observations are not treatment-benefit, safety or clinical grades.</p>
   {sourceIntegrityFlagCount>0&&<p className={css.warn}>
    This NCT has {sourceIntegrityFlagCount} source-interpretation flag(s)
    to resolve against the original registry before grading.
   </p>}
   {!m.registryLeads.length?<p><strong>Not available in the saved original
    registry snapshot.</strong> This metric still requires exact-program
    primary sources and an independent comparator.</p>:
    m.registryLeads.slice(0,15).map(f=><div key={f.id} className={css.source}>
     <strong>{f.kind.replaceAll("_"," ").toLowerCase()}</strong>
     <span>Source date {f.sourceDate}
      {f.resultsFirstPosted?" · registry results first posted "+f.resultsFirstPosted:""}</span>
     <span>{f.description}</span>
     {f.measurementValue!==null&&<span><strong>Raw reported observation:</strong>{" "}
      {f.measurementLabel}: {f.measurementValue} {f.measurementUnit}</span>}
     <a href={f.sourceUrl} target="_blank" rel="noopener noreferrer">
      Open original ClinicalTrials.gov result/protocol</a>
    </div>)}
   {m.registryLeads.length>15&&<p>Showing 15 of {m.registryLeads.length}
    source leads. The downloaded exact-trial JSON includes every original
    clinical lead and its provenance.</p>}
  </div>
  <div className={css.warn}>
   <strong>5 · Independent approval gate — NOT MET</strong>
   <p>Authenticated external human signoff: none.
    Approved RAAS metric grade: N/A. Stage-wide independently
    validated 30/30 score: unavailable. Calibrated FDA
    PASS/CRL/EXTENSION probability: unavailable.</p>
  </div>
 </div>;
}
