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
import historicalCases from "../data/raas-historical-cases.json";
import retrospectiveExamples from "../data/raas-retrospective-source-cases.json";
import historicalMetricSnapshots from "../data/raas-historical-metric-snapshots.json";
import {parseRaasPilotFeed,observationsForTrial,observedCalculation,computeRaasScore,type RaasObservation} from "../lib/raas-score-engine";
import {RAAS_THRESHOLD_PROFILES,thresholdProfile,provisionalGradesForTrial} from "../lib/raas-threshold-profiles";
import reviewedSnapshots from "../data/raas-reviewed-snapshots.json";
import approvedCalibrations from "../data/raas-approved-calibrations.json";
import {parseRaasCalibrations,parseRaasReviewedLedger,reviewedScoreForTrial} from "../lib/raas-reviewed-score-ledger";
import {contextualClinicalBenchmark} from "../lib/raas-clinical-benchmarks";
import {evaluateHistoricalFeed,parseHistoricalFeed,walkForwardFolds,RAAS_HISTORICAL_MIN_INDEPENDENT_PROGRAMS} from "../lib/raas-historical-backtest";
import {evaluateMetricHistory,parseMetricHistory} from "../lib/raas-metric-backtest";
import {parseRetrospectiveFeed,retrospectiveResults} from "../lib/raas-retrospective-intake";

type ResearchStatus="idle"|"loading"|"ready"|"unavailable";
type Coverage=ReturnType<typeof readoutResearchCoverage>;
const fieldLabels=new Map<string,string>(ALL_RESEARCH_FIELD_DEFINITIONS.map(field=>[field.id,field.label]));
type Snapshot="ENTRY"|"CURRENT"|"EXIT";
const pilot=parseRaasPilotFeed(pilotData);
const historicalFeed=parseHistoricalFeed(historicalCases);
const historicalValidation=evaluateHistoricalFeed(historicalFeed);
const retrospectiveFeed=parseRetrospectiveFeed(retrospectiveExamples);
const retrospectiveWindows=retrospectiveResults(retrospectiveFeed);
const metricHistoryReview=evaluateMetricHistory(historicalFeed,historicalValidation,parseMetricHistory(historicalMetricSnapshots));
const calibrationRegistry=parseRaasCalibrations(approvedCalibrations);
const reviewedLedger=parseRaasReviewedLedger(reviewedSnapshots);
function PilotEvidence({observations,metricId,snapshot,drug,indication}:{observations:readonly RaasObservation[];metricId:string;snapshot:Snapshot;drug:string;indication:string}){
 const matching=observations.filter(o=>o.metricIds.includes(metricId));
 return <div className={css.pilotEvidence}>
   <strong>Source-backed measured facts · {snapshot}</strong>
   {snapshot!=="CURRENT"?<p>No dated {snapshot} evidence snapshot has been verified. Later findings are not retroactively applied to ENTRY or EXIT.</p>:
     matching.length===0?<p>No verified numerical pilot observation for this metric in the dated research snapshot. A metric score is not inferred.</p>:
     matching.map(o=>{const calc=observedCalculation(o);
       const clinicalBenchmark=o.kind==="active_control_mean_change"?contextualClinicalBenchmark(drug,indication,o.unit):null;
       return <div className={css.pilotObservation} key={o.id}>
       <strong>{o.title}</strong>
       {calc&&<p className={css.pilotMeasured}><strong>{calc.value.toLocaleString("en-US",{maximumFractionDigits:2})} {calc.unit}</strong> · {calc.label}</p>}
       {o.valueText&&<p>Documented: {o.valueText}</p>}
       {clinicalBenchmark&&<div className={css.benchmarkContext}>
         <strong>Published clinical interpretation benchmark · not a RAAS grade</strong>
         <p>{clinicalBenchmark.endpoint} within-patient minimal important difference: {clinicalBenchmark.min}–{clinicalBenchmark.max} {clinicalBenchmark.unit}. This refers to individual patient change, not the placebo-adjusted treatment contrast.</p>
         <p>{clinicalBenchmark.notApplicableTo}</p>
         <a href={clinicalBenchmark.sourceUrl} target="_blank" rel="noopener noreferrer">Read published clinical benchmark</a>
       </div>}
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
 const historicalStage=historicalValidation.byStage.find(x=>x.stage===bucket)!;
 const historicalFolds=walkForwardFolds(historicalValidation.accepted,bucket);
 const comparableResearch=retrospectiveWindows.filter(example=>example.stage===bucket);
 const historyMetrics=metricHistoryReview.filter(m=>m.stage===bucket);
 const label=isTop?"TOP-RAAS":"BOTTOM-RAAS";
 const groups=RAAS_METRIC_CATALOG[bucket];
 const record=researchStatus==="ready"?exactReadoutBenefit(row,benefitFeed):null;
 const [snapshot,setSnapshot]=useState<Snapshot>("CURRENT");
 const pilotFacts=snapshot==="CURRENT"?observationsForTrial(pilot,{
   nctId:row.nctId,ticker:row.ticker,drug:row.evidence?.drug||"",indication:row.evidence?.indication||""
 },bucket,pilot.sourceAsOf):[];
 const pilotGrades=provisionalGradesForTrial(pilot,{
   nctId:row.nctId,ticker:row.ticker,drug:row.evidence?.drug||"",indication:row.evidence?.indication||""
 },bucket,snapshot,pilot.sourceAsOf);
 const scoreSnapshots=(["ENTRY","CURRENT","EXIT"] as const).map(period=>({
   period,reviewed:reviewedScoreForTrial(reviewedLedger,calibrationRegistry,{
     nctId:row.nctId,ticker:row.ticker,drug:row.evidence?.drug||"",indication:row.evidence?.indication||""
   },bucket,period,reviewedLedger.sourceAsOf,metricHistoryReview)
 }));
 const reviewed=scoreSnapshots.find(s=>s.period===snapshot)?.reviewed??null;
 const grading=reviewed?.score??computeRaasScore({stage:bucket,snapshot,asOf:pilot.sourceAsOf,
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
     <p className={css.disclaimer}><strong>Research specification {RAAS_SPEC_VERSION}.</strong> {RAAS_THRESHOLD_PROFILES.length} metric scoring profiles registered; {calibrationRegistry.entries.length} validated scoring calibrations approved. The dated pilot has {pilot.records.length} identified trials as of {pilot.sourceAsOf}. Exploratory grades are separate and <strong>never</strong> contribute to RAAS. The approved-grade ledger preserves exact-trial ENTRY / CURRENT / EXIT assessments without backfilling future evidence. Missing inputs are not zeros.</p>
     <div className={css.snapshots} aria-label={label+" score snapshots"}>
       {(["ENTRY","CURRENT","EXIT"] as const).map(period=>
         <button key={period} type="button" className={css.snapshotButton} aria-pressed={snapshot===period}
           onClick={()=>setSnapshot(period)}>
           <strong>{period}</strong><span>{scoreSnapshots.find(s=>s.period===period)?.reviewed?.score.score??"—"} / 100</span>
           <small>{period==="ENTRY"?(isTop?"Pre-readout signal":"Post-readout signal"):
             period==="CURRENT"?"Current assessment":isTop?"Before public Phase 3 data":"PDUFA − 3 days if verified"}</small>
         </button>)}
     </div>
     <details className={css.anchorDetails}>
       <summary>Historical appreciation validation · {historicalStage.independentPrograms}/{RAAS_HISTORICAL_MIN_INDEPENDENT_PROGRAMS} independent program minimum ▸</summary>
       <div className={css.historicalStatus}>
         <p><strong>{label} validation:</strong> {historicalStage.cases} eligible historical trade windows; {historicalStage.independentPrograms} independent company/therapy/indication opportunities; {historicalStage.predictionCoverage}% documented return forecasts.</p>
         <p>Return forecast error: {historicalStage.maePercent===null?"Not calculable":historicalStage.maePercent+" percentage points mean absolute error"}; score versus realized-return rank correlation: {historicalStage.spearmanRaasVsReturn===null?"Not calculable":historicalStage.spearmanRaasVsReturn}.</p>
         <p>Out-of-sample review folds: {historicalFolds.length}; metric histories meeting the minimum review sample floor: {historyMetrics.filter(m=>m.status==="REVIEW_ELIGIBLE_NOT_APPROVED").length}/30; calibration-approved RAAS scoring profiles: {calibrationRegistry.entries.filter(x=>x.stage===bucket).length}/30.</p>
         <p><strong>Current status:</strong> {historicalStage.reason}</p>
         <p>Historic outcome cases must use timestamped pre-entry sources, exact asset identity and verified readout or FDA target. Two NCTs of one drug cannot become two independent opportunities.</p>
         <p>Historical case ledger as of {historicalCases.sourceAsOf}. This is not a live quote, automated historical backfill, or backtest with validated predictive performance.</p>
       </div>
     </details>
     <details className={css.anchorDetails}>
       <summary>Historical source-checked price examples · {comparableResearch.length} · research only ▸</summary>
       <div className={css.historicalStatus}>
         {comparableResearch.length===0?<p>No real-price research examples yet for this phase. Do not confuse a missing example with a zero return.</p>:
           comparableResearch.map(example=>{const original=retrospectiveFeed.records.find(r=>r.id===example.id)!;
             return <div key={example.id} className={css.pilotObservation}>
               <strong>{example.ticker} · {original.drug} · {original.indication}</strong>
               <p><strong>Research-only, selected retrospectively.</strong> {original.nctIds.length} Phase 3 trial identifiers, one investment program. This is not a historical RAAS buy signal.</p>
               <p>Close on {example.entryDate}: ${example.entryClose.toFixed(2)}; close on {example.exitDate}: ${example.exitClose.toFixed(2)}.</p>
               <p>Observed gross close-to-close change: <strong>{example.observedGrossChangePercent>=0?"+":""}{example.observedGrossChangePercent.toFixed(2)}%</strong>. Entry-date vendor market capitalization: ${example.marketCapUsdMillions.toLocaleString("en-US")} million.</p>
               <p>PDUFA target {original.pdufaDate} · minus-three-day cutoff {example.calendarCutoff}; actual FDA decision {original.realizedFDAAction.date} is future knowledge relative to entry.</p>
               <p>Closing-price adjustment, execution friction and exchange-holiday validation are pending. There is no archived pre-entry RAAS prediction or qualified performance forecast.</p>
               <a href={original.entry.sourceUrl} target="_blank" rel="noopener noreferrer">Historical closing-price source</a>
               <a href={original.marketCapAtEntry.sourceUrl} target="_blank" rel="noopener noreferrer">Historical market capitalization source</a>
               {original.verifiedBeforeEntry.map(item=><a key={item.kind+item.date} href={item.sourceUrl} target="_blank" rel="noopener noreferrer">{item.kind.replaceAll("_"," ")} · {item.date}</a>)}
               <a href={original.realizedFDAAction.sourceUrl} target="_blank" rel="noopener noreferrer">Subsequent FDA decision source (outcome only)</a>
             </div>;
           })}
         <p>These examples are held in a separate retrospective research ledger. They do not enter the qualified, timestamped RAAS scoring or return-validation calculations.</p>
       </div>
     </details>
     <p className={css.hint}><strong>{snapshot} · {grading.graded}/30 approved metric grades · {pilotGrades.length} exploratory research score · {pilotFacts.length} dated observations.</strong> {grading.reason} Open a category and a metric to see numerical observations, threshold requirements, sources and downside risks. Only complete approved metric sets can produce an overall RAAS.</p>
     <div className={css.factors} aria-label={label+" six weighted ingredients"}>
       {groups.map((group,i)=><details key={group.id} name={groupName} className={css.factor} data-raas-factor={i+1}>
         <summary className={css.factorSummary}>
           <span className={css.factorName}><strong>{i+1}. {group.name}</strong><small>Weight {group.weight}% · grade {grading.categories[i]?.score??"—"} / 100 · {grading.categories[i]?.graded??0}/{group.metrics.length} approved</small></span>
           <span className={css.factorChevron} aria-hidden="true">▸</span>
         </summary>
         <div className={css.factorBody}>
           <strong className={css.metricIntro}>Individual metrics · open one for scoring evidence</strong>
           {group.metrics.map((metric,j)=>{const exploratory=pilotGrades.find(g=>g.metricId===metric.id);
             const profile=thresholdProfile(bucket,metric.id);
             const metricBacktest=historyMetrics.find(m=>m.metricId===metric.id);
             const qualified=reviewed?.acceptedRatings.find(r=>r.metricId===metric.id&&!grading.missing.includes(metric.id));
             return <details key={metric.id} name={"raas-metric-"+bucket+"-"+row.nctId+"-"+group.id}
             className={css.metric} data-raas-metric={metric.id}>
             <summary className={css.metricSummary}>
               <span><strong>{j+1}. {metric.name}</strong><small>{qualified?qualified.score+" / 100 · APPROVED":exploratory?exploratory.score+" / 100 · EXPLORATORY ONLY":"— / 100 · Evidence not graded"}</small></span>
               <span aria-hidden="true" className={css.metricChevron}>▸</span>
             </summary>
             <div className={css.metricBody}>
               <div className={css.metricStatus}><strong>Qualified RAAS metric score: {qualified?.score??"—"} / 100</strong><span>{snapshot} · {qualified?"Approved, source-dated metric assessment":"Pending validated calculation"}</span>
                 {qualified&&<><span>Benchmark: {qualified.benchmarkId} · Assessed {qualified.assessedAt}</span><a href={qualified.sourceUrl} target="_blank" rel="noopener noreferrer">Open approved score evidence</a></>}</div>
               {exploratory&&<div className={css.exploratoryGrade}>
                 <strong>{exploratory.score}/100 · {exploratory.label}</strong>
                 <p>RESEARCH-ONLY · This is a provisional timing-specificity grade, <strong>not</strong> a validated appreciation or scientific-success score.</p>
                 <p><strong>Source input:</strong> {exploratory.inputs} · {exploratory.sourceDate}</p>
                 <p>{exploratory.explanation}</p>
                 <p><strong>Limitations:</strong> {exploratory.limitations}</p>
                 <a href={exploratory.sourceUrl} target="_blank" rel="noopener noreferrer">Source for timing guidance</a>
               </div>}
               <div className={css.requirement}><strong>Metric-specific threshold calibration</strong>
                 <p>{profile?.status==="PROVISIONAL_NOT_CALIBRATED"?"Provisional nonvalidated research rule; excluded from RAAS":"BENCHMARK REQUIRED · No calibrated numeric score"}</p>
                 <p><strong>Data needed:</strong> {profile?.minimumInputs}</p>
                 <p><strong>Benchmark needed:</strong> {profile?.benchmarkRequired}</p>
               </div>
               <div className={css.requirement}><strong>Historical investment-performance validation</strong>
                 <p>{metricBacktest?.independentPrograms??0} independently observed program/return pairs; score-return rank correlation: {metricBacktest?.spearmanScoreToReturn??"Not available"}.</p>
                 <p>High-score minus low-score mean realized return: {metricBacktest?.meanHighMinusLowPercent==null?"Not available":metricBacktest?.meanHighMinusLowPercent+" percentage points"}.</p>
                 <p>{metricBacktest?.reason||"Missing historical metric review."} No score becomes approved solely from this descriptive backtest.</p>
               </div>
               <div className={css.requirement}><strong>Evidence required</strong><p>{metric.requiredEvidence}</p></div>
               <div className={css.requirement}><strong>What improves this score?</strong><p>{metric.scoreRule}</p></div>
               <div className={css.requirement}><strong>Major downside or disqualification risk</strong><p>{metric.criticalRisk}</p></div>
               <details className={css.anchorDetails}>
                 <summary>Provisional 0–100 grading anchors ▸</summary>
                 <div>{RAAS_PROVISIONAL_ANCHORS.map(a=><p key={a.points}><strong>{a.points}/100 — {a.label}:</strong> {a.definition}</p>)}</div>
                 <p>These are interpretation anchors, not clinical thresholds or validated stock-return cutoffs. Benchmarks must be established separately for each metric.</p>
               </details>
               <PilotEvidence metricId={metric.id} observations={pilotFacts} snapshot={snapshot}
                 drug={row.evidence?.drug||""} indication={row.evidence?.indication||""}/>
               <MetricEvidence metric={metric} record={record} researchStatus={researchStatus}/>
             </div>
           </details>;})}
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
