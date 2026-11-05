import type {Metadata} from "next";
import Link from "next/link";
import accepted from "../../data/raas-current-accepted-fda-applications.json";
import leads from "../../data/raas-v2-top8-2026-source-intake.json";
import phase3 from "../../data/raas-current-pipeline-pre-candidate-snapshots.json";
import allTrial from "../../data/raas-all-trials-partial-metric-ratings-status.json";
import accuracy from "../../data/raas-fda-three-way-accuracy-site-snapshot.json";
import {buildRaasPredictionQueue,summarizeRaasPredictionQueue} from "../../lib/raas-prediction-queue";
import {buildThreeWayFDAFreezePreflightPlan}
 from "../../lib/raas-fda-three-way-freeze-preflight";
import {currentRaasFdaForecastFreezeReceiptAudit}
 from "../../lib/raas-fda-forecast-freeze-receipt-audit";
import {currentRaasFdaOriginalGoalOutcomeAudit}
 from "../../lib/raas-fda-original-goal-outcome-audit";
import {currentRaasFdaThreeWayResearchScorecard}
 from "../../lib/raas-fda-three-way-research-scorecard";

export const metadata:Metadata={
 title:"RAAS Predictions — FDA PASS / CRL / EXTENSION | PDUFA",
 description:"Exact-application research queues, trial-level RAAS score coverage, FDA forecast validation and evidence blockers."
};
const queue=buildRaasPredictionQueue(accepted.applications,leads.records,accepted.issuer.ticker);
const summary=summarizeRaasPredictionQueue(queue);
const freezePreflight=buildThreeWayFDAFreezePreflightPlan();
const preflightByCase=new Map(freezePreflight.records.map(x=>[x.caseKey,x]));
const receiptAudit=currentRaasFdaForecastFreezeReceiptAudit();
const originalGoalAudit=currentRaasFdaOriginalGoalOutcomeAudit();
const outcomeCaseByKey=new Map(originalGoalAudit.cases.map(x=>[x.caseKey,x]));
const threeWayScorecard=currentRaasFdaThreeWayResearchScorecard();
const panel={border:"1px solid #c6d7cc",background:"#fff",borderRadius:10,padding:"14px"} as const;
const muted={fontSize:13,color:"#455c50",lineHeight:1.5} as const;
const stats={display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(165px,1fr))",gap:10,margin:"15px 0"} as const;
function Fact({label,value}:{label:string;value:string|number}){
 return <div style={panel}><strong style={{display:"block",fontSize:25,fontVariantNumeric:"tabular-nums"}}>{value}</strong>
  <span style={muted}>{label}</span></div>;
}
export default function PredictionsPage(){
 return <main className="shell" style={{maxWidth:1200,margin:"0 auto",padding:"18px 12px 44px"}}>
  <div className="topline">PDUFA · RAAS FORECAST CONTROL</div>
  <h1>RAAS Predictions · PASS / CRL / EXTENSION</h1>
  <p><strong>Operational FDA verdict: ABSTAIN for every tracked application.</strong>
    There is currently no independently calibrated three-class probability model or completed 30/30 reviewed RAAS stage score.
    Source leads and study-design ratings are evidence, not predictions.</p>
  <div style={{display:"flex",gap:14,flexWrap:"wrap",fontSize:13,margin:"12px 0"}}>
   <Link href="/raas-scan">All 762 trials, source grades and RAAS score history</Link>
   <Link href="/raas-worklist#raas-fda-prediction-accuracy">FDA three-way accuracy validation</Link>
   <Link href="/prediction-pilot">COGT PEAK detailed trial pilot</Link>
  </div>
  <div style={stats} data-raas-prediction-overview="true">
   <Fact value={allTrial.researchTrials} label="NCTs in registry research universe"/>
   <Fact value={allTrial.uniqueNctsWithActualProvisionalMetricScores} label="Trials with source-backed partial metric grades"/>
   <Fact value={allTrial.fullValidatedRaasScores} label="Fully validated 30/30 RAAS scores"/>
   <Fact value={accuracy.predecisionThreeWayIndependentlyVerifiedForecasts} label="Independently verified three-way forecasts"/>
  </div>
  <section style={{...panel,marginBottom:15}}
   data-raas-fda-threeway-scorecard="UNVALIDATED">
   <h2>Prospective FDA three-way accuracy · independent scorecard</h2>
   <div style={stats}>
    <Fact value={threeWayScorecard.researchPairedCases}
     label="Original-goal forecast/outcome research pairs"/>
    <Fact value={threeWayScorecard.researchRosterCases}
     label="Tracked research application leads, excluding Phase 2"/>
    <Fact value={threeWayScorecard.researchStatistics?
     threeWayScorecard.researchStatistics.topClassAccuracyPct+"%":"Not measurable"}
     label="Three-way descriptive accuracy (not a certified rating)"/>
    <Fact value={threeWayScorecard.independentValidatedAccuracyPct===null?
     "Not validated":threeWayScorecard.independentValidatedAccuracyPct+"%"}
     label="Independent FDA PASS / CRL / EXTENSION model accuracy"/>
   </div>
   <p style={muted}>
    A forecast can be measured only after it was independently witnessed
    before the original deadline and paired to the correct FDA review-cycle
    outcome. The research calculator supports confusion matrices, balanced
    accuracy, multiclass Brier score, log loss, calibration error, and a
    same-cohort always-PASS comparison. No missing predictions or outcomes are
    counted as incorrect: the accuracy rate remains unavailable.
   </p>
   <details>
    <summary style={{cursor:"pointer",fontWeight:700}}>
     Show {threeWayScorecard.readinessGates.length} measurement gates
    </summary>
    <ul style={{paddingLeft:21}}>
     {threeWayScorecard.readinessGates.map(g=><li key={g.id}
      style={{marginBottom:8}}>
      <strong>{g.passed?"Research gate satisfied":"Evidence missing"}</strong>
      {" "}· {g.description} ({g.achieved}/{g.required})
     </li>)}
    </ul>
    <p style={muted}>Passing these structural research gates
     would still require independent authentication of actual evidence
     and does not automatically approve a forecast model.</p>
   </details>
   <p style={muted}>
    <a href="/api/raas-fda-threeway-scorecard">
     Open FDA three-way research scorecard (JSON)</a>.
    {" "}The <a href="https://github.com/pdufa/pdufa-command-center/actions/workflows/raas-fda-decision-accuracy.yml"
     target="_blank" rel="noopener noreferrer">existing nightly FDA accuracy workflow</a>
    {" "}also publishes a dated per-application evidence-gap JSON report and CSV worklist.
    This page uses saved source snapshots, not the latest workflow artifact or
    a live FDA-action feed. Research holdout results are never automatically certified,
    and no RAAS trading signal is released by this audit.
   </p>
  </section>
  <section style={{...panel,marginBottom:15}}
   data-raas-fda-freeze-receipt-audit="PENDING_INDEPENDENT_VALIDATION">
   <h2>Prospective forecast freeze receipt audit</h2>
   <div style={stats}>
    <Fact value={receiptAudit.submitted} label="Submitted forecast freeze receipt metadata"/>
    <Fact value={receiptAudit.pendingIndependentAuthentication}
     label="Structurally complete; independent authentication outstanding"/>
    <Fact value={receiptAudit.blocked} label="Blocked: identity, chronology, duplicate, or probability error"/>
    <Fact value={receiptAudit.independentlyAuthenticatedForecasts}
     label="Independently authenticated prospective FDA forecasts"/>
   </div>
   <p style={muted}>RAAS now checks an immutable-identity three-class freeze receipt
    against the exact application and original deadline, source snapshot,
    dated witness evidence, duplicated case submissions, and probabilities
    totaling 100%. Even a structurally complete receipt is not a certified
    freeze or an accuracy result without external authentication.
   </p>
   <p style={muted}>
    <a href="/api/raas-fda-freeze-receipt-audit">
     Open the saved FDA freeze receipt audit (JSON)</a>.
    No website entry, unsigned template, or recorded checksum proves a
    historical prediction was actually published before a decision.
   </p>
  </section>
  <section style={{...panel,marginBottom:15}}
   data-raas-fda-original-goal-outcome-audit="UNADJUDICATED">
   <h2>FDA original-goal outcome review · independent evidence queue</h2>
   <div style={stats}>
    <Fact value={originalGoalAudit.exactReviewCycleResearchCases}
     label="Distinct application/review-cycle source leads"/>
    <Fact value={originalGoalAudit.pendingNoEvidence}
     label="Original-goal outcome evidence not submitted"/>
    <Fact value={originalGoalAudit.blockedResearchCases}
     label="Outcome-source submissions blocked for review"/>
    <Fact value={originalGoalAudit.independentlyAdjudicatedOriginalGoalLabels}
     label="Independently adjudicated original-goal FDA outcomes"/>
   </div>
   <p style={muted}>
    A later FDA approval cannot automatically be recorded as PASS at the original
    goal. RAAS preserves the original goal separately from revised target dates,
    checks exact NDA/BLA/supplement identity and evidence publication chronology,
    and requires independent verification of PASS, CRL, or EXTENSION. These
    postdecision documents cannot be used to retroactively create forecasts.
   </p>
   <p style={muted}>
    <a href="/api/raas-fda-original-goal-outcomes">
     Open FDA outcome evidence review audit (JSON)</a>.
    {" "}{originalGoalAudit.qualifiedForecastOutcomePairs} qualified prospective
    forecast/outcome pairs; three-way predictive accuracy remains unvalidated.
   </p>
  </section>
  <section style={{...panel,marginBottom:15}} data-raas-fda-forecast-cohort="true">
   <h2>FDA decision queue · {summary.total} distinct application/cycle leads</h2>
   <p style={muted}>Dated sources: accepted-application research {accepted.sourceAsOf}; issuer-goal lead research {leads.asOf}.
    This is a saved research snapshot, not a verified live FDA outcome feed.
    A ticker may have multiple separate applications. No provisional numbers are substituted for a missing probability.</p>
   <p data-raas-fda-threeway-freeze-preflight="unsigned" style={muted}>
    <strong>Original-deadline forecast preflight:</strong> {freezePreflight.total} exact
    application/cycle research records; {freezePreflight.phase2Excluded} Phase 2
    exclusions; {freezePreflight.originalGoalElapsed} original deadlines already elapsed
    in the saved evidence snapshot; {freezePreflight.unverifiedApplicationOrCycle}
    unverified review-cycle leads. The remaining
    {" "}{freezePreflight.needsExactCycleAndCalibration} Phase 3 source lead(s) still
    lack independent FDA-cycle and model calibration proof.
    Every forecast is ABSTAIN. This is a dated source audit, not a live FDA check.
   </p>
   <div style={stats}>
    <Fact value={summary.phase3SourceEligible} label="Accepted NDA with Phase 3 supporting trial in this source"/>
    <Fact value={summary.phase2Excluded} label="Accepted NDAs excluded under Phase 3 minimum"/>
    <Fact value={summary.researchLeadsUnverified} label="Other original-goal leads requiring eligibility review"/>
    <Fact value={summary.certifiedThreeWayForecasts} label="Certified three-class forecasts"/>
   </div>
   {queue.map((r,i)=><details key={r.key}
       style={{border:"1px solid #d5e4da",borderRadius:8,padding:"12px",margin:"9px 0"}}
       data-raas-fda-case={r.key}>
     <summary style={{cursor:"pointer",display:"flex",gap:8,justifyContent:"space-between",alignItems:"center",flexWrap:"wrap",listStyle:"auto"}}>
       <span><strong>{i+1}. {r.ticker}</strong> · {r.drug}<small style={{display:"block",color:"#486054"}}>{r.targetDate} target · {r.kind==="ACCEPTED_NDA_SOURCE"?"Issuer-reported accepted NDA":"Issuer original-goal source lead"}</small></span>
       <strong style={{fontSize:13}}>ABSTAIN · {r.eligible==="PHASE3_SOURCE_ELIGIBLE"?"Phase 3 source":r.eligible==="PHASE2_EXCLUDED"?"Phase 2 excluded":"Eligibility unverified"}</strong>
     </summary>
     <div style={{padding:"10px 4px 2px"}}>
       <p><strong>Three-way decision:</strong> PASS — · CRL — · EXTENSION —. No validated probabilities and no definitive verdict.</p>
       <p><strong>Exact key:</strong> <code>{r.key}</code></p>
       <p><strong>Study:</strong> {r.trialName??"Not linked to an exact verified trial in this queue"}{r.trialNctId&&<>
        {" · "}<Link href={"/trial/"+r.trialNctId}>{r.trialNctId}</Link></>}</p>
       {preflightByCase.has(r.key)&&<div data-raas-fda-exact-freeze-preflight={r.key}
        style={{border:"1px solid #d6e5dc",borderRadius:8,padding:11,margin:"10px 0"}}>
        <p style={{margin:"0 0 8px"}}><strong>Original-goal freeze preflight:</strong>{" "}
         {preflightByCase.get(r.key)!.preflightStatus.replaceAll("_"," ").toLowerCase()}.
         {" "}First announced goal {preflightByCase.get(r.key)!.originalFirstGoalDate};
         listed goal {preflightByCase.get(r.key)!.listedTargetDate}.
         {preflightByCase.get(r.key)!.goalHasFormalRevision?
          " Formal goal revision exists; do not freeze against the revised date as if it were a new original cycle.":""}
        </p>
        <p style={{margin:"0 0 8px"}}>
         <a href={"/api/raas-fda-threeway-preflight?"+
          new URLSearchParams({case:r.key}).toString()} download>
          Download this case’s unsigned seven-check forecast preflight (JSON)
         </a>
        </p>
        <p style={muted}>Recorded prospective receipts for this case:{" "}
         {receiptAudit.checks.filter(x=>x.caseKey===r.key).length}.
         {" "}No recorded receipt is automatically authenticated or approved.</p>
        <details>
         <summary style={{cursor:"pointer",fontWeight:700}}>Show seven source and calibration requirements</summary>
         <ul style={{paddingLeft:20}}>
          {preflightByCase.get(r.key)!.requiredProof.map(proof=>
           <li key={proof.id} style={{margin:"7px 0"}}>
            <strong>{proof.label}</strong>
            {" "}· {proof.status.replaceAll("_"," ").toLowerCase()}.
            {" "}{proof.note}
           </li>)}
         </ul>
         <p style={muted}>
          This is not a frozen prediction. All PASS/CRL/EXTENSION fields are null;
          no independent calibration, FDA outcome adjudication, or trading signal
          has been approved.
         </p>
        </details>
       </div>}
       {outcomeCaseByKey.has(r.key)&&<div
        data-raas-fda-exact-original-goal-outcome={r.key}
        style={{border:"1px solid #d6e5dc",borderRadius:8,padding:11,margin:"10px 0"}}>
        <p style={{margin:"0 0 8px"}}>
         <strong>Original FDA goal outcome:</strong>{" "}
         {outcomeCaseByKey.get(r.key)!.status.replaceAll("_"," ").toLowerCase()}.
         {" "}Confirmed PASS / CRL / EXTENSION: <strong>none adjudicated</strong>.
        </p>
        <p style={{margin:"0 0 8px"}}>
         <a href={"/api/raas-fda-original-goal-outcomes?"+
          new URLSearchParams({case:r.key}).toString()} download>
          Download this application’s seven-step original-goal outcome review (JSON)
         </a>
        </p>
        <p style={muted}>Evidence candidates submitted for this case:{" "}
         {outcomeCaseByKey.get(r.key)!.recordedEvidenceCount}.
         {" "}Even a sourced candidate cannot automatically validate an FDA
         action or previously unsigned RAAS forecast.</p>
       </div>}
       <p><strong>Blockers and why RAAS abstains:</strong></p>
       <ul style={{paddingLeft:22}}>{r.blockers.map(b=><li key={b} style={{marginBottom:5}}>{b}</li>)}</ul>
       <p style={muted}><a href={r.sourceUrl} target="_blank" rel="noopener noreferrer">Original application or deadline disclosure</a>
       {r.outcomeEvidenceUrl&&<> · <a href={r.outcomeEvidenceUrl} target="_blank" rel="noopener noreferrer">Clinical outcome evidence</a></>}</p>
     </div>
   </details>)}
  </section>
  <section style={{...panel,marginBottom:15}} data-raas-pre-readout-phase3="true">
   <h2>Phase 3 development queue · {phase3.trialSnapshots.length} researched NCTs</h2>
   <p style={muted}>These are six source-checked pre-readout Phase 3 trials. They do not currently have an accepted application or verified PDUFA target in this research snapshot. They cannot receive FDA PASS/CRL/EXTENSION predictions yet.
    Their inclusion does not establish the complete live Pipeline.</p>
   {phase3.trialSnapshots.map(r=><details key={r.nctId}
     style={{border:"1px solid #d5e4da",borderRadius:8,padding:"11px",margin:"8px 0"}}>
      <summary style={{cursor:"pointer",fontWeight:700}}>{r.ticker} · {r.trialName} · {r.nctId} · PRE-READOUT / NO PDUFA</summary>
      <p><strong>Indication:</strong> {r.indication} · <strong>Expected data:</strong> {r.readoutExpectedWindow??"No verified topline window"}</p>
      <p><strong>FDA decision:</strong> ABSTAIN · no accepted NDA/BLA or PDUFA target for this trial.</p>
      <p style={muted}>{r.warnings}</p>
      <a href={r.clinicalRegistryUrl} target="_blank" rel="noopener noreferrer">Official trial registry</a>
      {" · "}<Link href={"/trial/"+r.nctId}>Trial detail</Link>
    </details>)}
  </section>
  <section style={panel} data-raas-validation-control="true">
   <h2>RAAS model accuracy · independent review</h2>
   <div style={stats}>
    <Fact value={accuracy.legacyRetrospectiveAccuracyPct+"%"} label="Older retrospective directional benchmark"/>
    <Fact value={accuracy.alwaysApproveRetrospectiveAccuracyPct+"%"} label="Always-approval baseline on same cases"/>
    <Fact value={accuracy.historicalExtensions} label="Extension outcomes in legacy benchmark"/>
    <Fact value="Not validated" label="Independent three-class accuracy"/>
   </div>
   <p style={muted}>The historical model was correct in {accuracy.legacyCorrect} of {accuracy.legacyRetrospectiveCases} selected cases, versus {accuracy.alwaysApproveCorrect} when always predicting approval. No extension outcomes were scored. This is not a prospective model validation.</p>
   <p><strong>Requirements before numeric predictions:</strong> exact FDA application/review-cycle identity; dated source evidence available at forecast time; complete and independently checked 30-metric scores; a frozen three-class prediction; issuer-disjoint chronological validation including extensions; and adjudicated actual FDA outcomes.</p>
   <p style={muted}>No missing metric is set to zero, 50, or a guessed success probability. Scoring and event evidence are kept independent from historical and future FDA action labels.</p>
  </section>
 </main>;
}
