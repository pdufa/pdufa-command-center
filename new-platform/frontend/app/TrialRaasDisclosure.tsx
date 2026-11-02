"use client";
import {useState} from "react";
import type {ReadoutRow} from "../lib/phase3-public-readout";
import type {BenefitFeed} from "../lib/benefit-assessments";
import {exactReadoutBenefit} from "../lib/phase3-readout-sort";
import type {readoutResearchCoverage} from "../lib/phase3-readout-sort";
import {ALL_RESEARCH_FIELD_DEFINITIONS} from "../lib/pipeline-research-view";
import {RAAS_METRIC_CATALOG,RAAS_PROVISIONAL_ANCHORS,RAAS_SPEC_VERSION,type RaasStage,type RaasMetric} from "../lib/raas-metric-specs";
import css from "./TrialRaasDisclosure.module.css";
import pilotData from "../data/raas-pilot-observations.json";
import {parseRaasPilotFeed,observationsForTrial,observedCalculation,computeRaasScore,type RaasObservation} from "../lib/raas-score-engine";

type ResearchStatus="idle"|"loading"|"ready"|"unavailable";
type Coverage=ReturnType<typeof readoutResearchCoverage>;
const fieldLabels=new Map<string,string>(ALL_RESEARCH_FIELD_DEFINITIONS.map(field=>[field.id,field.label]));
type Snapshot="ENTRY"|"CURRENT"|"EXIT";
const pilot=parseRaasPilotFeed(pilotData);
function PilotEvidence({observations,metricId,snapshot}:{observations:readonly RaasObservation[];metricId:string;snapshot:Snapshot}){
 const matching=observations.filter(o=>o.metricIds.includes(metricId));
 return <div className={css.pilotEvidence}>
   <strong>Source-backed measured facts · {snapshot}</strong>
   {snapshot!=="CURRENT"?<p>No dated {snapshot} evidence snapshot has been verified. Later findings are not retroactively applied to ENTRY or EXIT.</p>:
     matching.length===0?<p>No verified numerical pilot observation for this metric in the dated research snapshot. A metric score is not inferred.</p>:
     matching.map(o=>{const calc=observedCalculation(o);return <div className={css.pilotObservation} key={o.id}>
       <strong>{o.title}</strong>
       {calc&&<p className={css.pilotMeasured}><strong>{calc.value.toLocaleString("en-US",{maximumFractionDigits:2})} {calc.unit}</strong> · {calc.label}</p>}
       {o.valueText&&<p>Documented: {o.valueText}</p>}
       <p>Source published {o.assessmentDate} · Measurement as of {o.measurementDate}.</p>
       <p>Method: {o.method}</p>
       <p>{o.note}</p>
       <a href={o.sourceUrl} target="_blank" rel="noopener noreferrer">Open primary-source evidence</a>
     </div>})}
   <p className={css.evidenceCaution}>Clinical outcome values, corporate cash figures, and readout guidance are measurements, not RAAS 0–100 ratings.</p>
 </div>;
}
function MetricEvidence({metric,record,researchStatus}:{
 metric:RaasMetric;
 record:ReturnType<typeof exactReadoutBenefit>;
 researchStatus:ResearchStatus;
}){
 const related=metric.relatedFieldIds.map(id=>({id,fact:record?.facts[id]}));
 const available=related.filter(x=>!!x.fact);
 const verified=available.filter(x=>x.fact?.status==="VERIFIED").length;
 return <div className={css.metricEvidence}>
   <strong>Related research fields · not a metric score</strong>
   {researchStatus==="loading"||researchStatus==="idle"?
     <p>Checking source-backed research…</p>:
     researchStatus==="unavailable"?<p>Research feed unavailable. No result inferred.</p>:
     related.length===0?<p>No directly mapped research field. A dedicated market, SEC, regulatory, or timing feed is required.</p>:
     <><p>{verified} verified · {available.length-verified} modeled · {related.length-available.length} missing.</p>
       {related.map(({id,fact})=><div className={css.evidenceItem} key={id}>
         <span><strong>{fieldLabels.get(id)||id}</strong> · {fact?fact.status:"Not assessed"}</span>
         {fact&&<><span>Recorded: {String(fact.value)} · {fact.sourceDate} · {fact.confidence} confidence</span>
           <span>Method: {fact.method}</span>
           <a href={fact.sourceUrl} target="_blank" rel="noopener noreferrer">Open research source</a></>}
       </div>)}
     </>}
   <p className={css.evidenceCaution}>Related research input does not satisfy every requirement above or establish a numeric grade. The full metric must be independently validated.</p>
 </div>;
}
export default function TrialRaasDisclosure({row,bucket,researchStatus,coverage,benefitFeed,onResearchRequest}:{
 row:ReadoutRow;bucket:RaasStage;researchStatus:ResearchStatus;
 coverage:Coverage;benefitFeed:BenefitFeed|null;onResearchRequest:()=>void;
}){
 const isTop=bucket==="pre";
 const label=isTop?"TOP-RAAS":"BOTTOM-RAAS";
 const groups=RAAS_METRIC_CATALOG[bucket];
 const record=researchStatus==="ready"?exactReadoutBenefit(row,benefitFeed):null;
 const [snapshot,setSnapshot]=useState<Snapshot>("CURRENT");
 const pilotFacts=snapshot==="CURRENT"?observationsForTrial(pilot,{
   nctId:row.nctId,ticker:row.ticker,drug:row.evidence?.drug||"",indication:row.evidence?.indication||""
 },bucket,pilot.sourceAsOf):[];
 const grading=computeRaasScore({stage:bucket,snapshot,asOf:pilot.sourceAsOf,
   trial:{nctId:row.nctId,ticker:row.ticker},ratings:[],gates:[]});
 const groupName="raas-group-"+bucket+"-"+row.nctId;
 return <details className={css.raas} data-raas-phase={bucket} data-raas-trial={row.nctId}>
   <summary className={css.summary} onClick={onResearchRequest}
     aria-label={label+" · "+row.ticker+" "+row.nctId+" · expand or collapse proposed score ingredients"}>
     <span className={css.summaryText}><strong>{label}</strong>
       <small>— / 100 · Not scored</small></span>
     <span className={css.chevron} aria-hidden="true">▸</span>
   </summary>
   <div className={css.panel}>
     <p className={css.disclaimer}><strong>Research specification {RAAS_SPEC_VERSION}.</strong> Metric-level grading and weighted aggregation now enforce source, date and eligibility checks. The pilot evidence has {pilot.records.length} exactly identified trials and is dated {pilot.sourceAsOf}; it is not a live market feed. Scores remain unassigned until all phase-specific requirements and independent validation are met. Missing inputs are not zeros.</p>
     <div className={css.snapshots} aria-label={label+" score snapshots"}>
       {(["ENTRY","CURRENT","EXIT"] as const).map(period=>
         <button key={period} type="button" className={css.snapshotButton} aria-pressed={snapshot===period}
           onClick={()=>setSnapshot(period)}>
           <strong>{period}</strong><span>— / 100</span>
           <small>{period==="ENTRY"?(isTop?"Pre-readout signal":"Post-readout signal"):
             period==="CURRENT"?"Current assessment":isTop?"Before public Phase 3 data":"PDUFA − 3 days if verified"}</small>
         </button>)}
     </div>
     <p className={css.hint}><strong>{snapshot} · {grading.graded}/30 validated metric grades · {pilotFacts.length} dated observations.</strong> {grading.reason} Expand one weighted category, then one metric to the right for its evidence, numeric clinical measurement where available, scoring rules and failure case. All sections start retracted.</p>
     <div className={css.factors} aria-label={label+" six weighted ingredients"}>
       {groups.map((group,i)=><details key={group.id} name={groupName} className={css.factor} data-raas-factor={i+1}>
         <summary className={css.factorSummary}>
           <span className={css.factorName}><strong>{i+1}. {group.name}</strong><small>Weight {group.weight}% · grade — / 100 · {group.metrics.length} metrics</small></span>
           <span className={css.factorChevron} aria-hidden="true">▸</span>
         </summary>
         <div className={css.factorBody}>
           <strong className={css.metricIntro}>Individual metrics · open one for scoring evidence</strong>
           {group.metrics.map((metric,j)=><details key={metric.id} name={"raas-metric-"+bucket+"-"+row.nctId+"-"+group.id}
             className={css.metric} data-raas-metric={metric.id}>
             <summary className={css.metricSummary}>
               <span><strong>{j+1}. {metric.name}</strong><small>— / 100 · Evidence not graded</small></span>
               <span aria-hidden="true" className={css.metricChevron}>▸</span>
             </summary>
             <div className={css.metricBody}>
               <div className={css.metricStatus}><strong>Metric score: — / 100</strong><span>{snapshot} · Pending validated calculation</span></div>
               <div className={css.requirement}><strong>Evidence required</strong><p>{metric.requiredEvidence}</p></div>
               <div className={css.requirement}><strong>What improves this score?</strong><p>{metric.scoreRule}</p></div>
               <div className={css.requirement}><strong>Major downside or disqualification risk</strong><p>{metric.criticalRisk}</p></div>
               <details className={css.anchorDetails}>
                 <summary>Provisional 0–100 grading anchors ▸</summary>
                 <div>{RAAS_PROVISIONAL_ANCHORS.map(a=><p key={a.points}><strong>{a.points}/100 — {a.label}:</strong> {a.definition}</p>)}</div>
                 <p>These are interpretation anchors, not clinical thresholds or validated stock-return cutoffs. Benchmarks must be established separately for each metric.</p>
               </details>
               <PilotEvidence metricId={metric.id} observations={pilotFacts} snapshot={snapshot}/>
               <MetricEvidence metric={metric} record={record} researchStatus={researchStatus}/>
             </div>
           </details>)}
         </div>
       </details>)}
     </div>
     <div className={css.coverage} role="status">
       {researchStatus==="loading"?"Loading source-backed research inputs…":
        researchStatus==="unavailable"?"Research feed unavailable; no score inferred.":
        coverage?coverage.verified+" verified research inputs recorded; evidence coverage is not a RAAS score.":
        "Research inputs not yet assessed. The category weights do not establish trial success or upside."}
     </div>
     <p className={css.disclaimer}>{isTop?
       "TOP source-check evidence is historical; it does not verify a future readout date or that results remain unreleased.":
       "A positive Phase 3 readout does not establish FDA filing acceptance or an actionable PDUFA date."}</p>
   </div>
 </details>;
}
