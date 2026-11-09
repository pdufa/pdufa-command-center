import blind from "../data/blindHistoricalForecasts2026.json";
import comparisons from "../data/blindHistoricalOutcomeComparisons2026.json";

const ink="#173c3a";
const muted="#516b69";
const primary="#096f63";

export default function BlindHistoricalPredictionPanel(){
  const record=blind.records[0];
  const outcome=comparisons.comparisons.find(item=>item.forecastId===record?.forecastId);
  if(!record||record.status!=="FROZEN_BLIND_AWAITING_USER_AUTHORIZED_COMPARISON"||
     record.actualOutcome!==null||record.actualDecisionDate!==null||
     record.actualDecisionSourceUrl!==null||record.outcomeViewed!==false){
    throw new Error("BLIND_HISTORICAL_RESEARCH_SEAL_INVALID");
  }
  if(!outcome||outcome.originalPredictionCommit!==record.sourceFreezeCommit||
    outcome.predictedOutcome!==record.predictedOutcome||
    outcome.actualOutcome!=="APPROVAL"||outcome.verdict!=="NOT_ACCURATE"||
    outcome.verified!==true||outcome.retrospective!==true||
    outcome.prospectiveScoringEligible!==false||
    Date.parse(record.forecastCreatedAt)<=Date.parse(outcome.actualDecisionDate+"T23:59:59Z")){
    throw new Error("BLIND_HISTORICAL_OUTCOME_COMPARISON_INVALID");
  }
  return <section aria-label="Sealed blind historical PDUFA challenge"
    data-testid="blind-2026-pdufa-forecast"
    style={{border:"1px solid #9cb7b3",borderRadius:13,padding:"clamp(14px,2vw,20px)",
      background:"#f6faf9",margin:"0 0 20px",color:ink}}>
    <div style={{fontSize:11,letterSpacing:".09em",fontWeight:800,color:"#285e56"}}>
      BLIND 2026 FDA REVIEW · HISTORICAL RESEARCH CHALLENGE
    </div>
    <h2 style={{fontSize:22,margin:"7px 0 5px"}}>
      INOVIO (INO) · INO-3107 · RRP
    </h2>
    <p style={{fontSize:14,lineHeight:1.65,margin:"7px 0"}}>
      <strong>Frozen prediction: CRL lean</strong>. Original reported FDA goal:
      {" "}<strong>October 30, 2026</strong>.
      Exact trial: <strong>{record.exactNcts[0]}</strong> (Phase 1/2).
    </p>
    <p style={{fontSize:13,lineHeight:1.6,margin:"7px 0"}}>
      <strong>Predecision evidence:</strong> a small nonrandomized trial found
      substantial reductions in repeat surgeries, but an already approved RRP
      treatment and an unresolved accelerated-approval eligibility issue
      created significant FDA review risk.
    </p>
    <div style={{padding:"12px 14px",background:"#fff4eb",border:"1px solid #dcb497",
      borderRadius:9,margin:"12px 0"}}>
      <p style={{fontWeight:850,color:"#9b402d",margin:"0 0 5px"}}>
        NOT ACCURATE · HISTORICAL BLIND CHALLENGE
      </p>
      <p style={{fontSize:13,lineHeight:1.6,margin:0}}>
        Original forecast: <strong>CRL lean</strong>.
        Verified FDA decision: <strong>Accelerated Approval, October 30, 2026</strong>
        {" · "}{outcome.applicationId}.
        <a href={outcome.officialFdaAnnouncement} target="_blank" rel="noopener noreferrer"
          style={{marginLeft:6,color:primary,fontWeight:700}}>
          Read the official FDA announcement
        </a>
      </p>
    </div>
    <p style={{fontSize:13,lineHeight:1.6,fontWeight:700,color:"#895923",margin:"9px 0"}}>
      The original forecast was frozen after the historical FDA date, without
      consulting the outcome. The FDA result was verified in a separate subsequent
      record. This is 0 correct of 1 retrospective blind reconstruction,
      NOT a measurement of prospective prediction accuracy.
      No numerical confidence or model calibration was assigned.
    </p>
    <p style={{fontSize:12,color:muted,margin:"9px 0 0",lineHeight:1.7}}>
      <a href={record.sourceFreezeUrl} target="_blank" rel="noopener noreferrer"
        style={{color:primary,fontWeight:700}}>Timestamped blind forecast freeze</a>
      {" · "}
      <a href="https://github.com/pdufa/pdufa-command-center/blob/main/new-platform/frontend/docs/2026-blind-ino3107-historical-challenge.md"
        target="_blank" rel="noopener noreferrer" style={{color:primary,fontWeight:700}}>
        Full scientific and regulatory rationale
      </a>
      {" · "}
      <a href={record.primaryEvidenceUrl} target="_blank" rel="noopener noreferrer"
        style={{color:primary,fontWeight:700}}>Predecision SEC filing</a>
    </p>
    <p style={{fontSize:12,lineHeight:1.5,color:muted,margin:"9px 0 0"}}>
      The SMMT prospective forecast remains separate and unchanged. The
      original historical forecast is immutable; the FDA outcome is recorded
      in a separate adjudication file and never counted in the prospective
      accuracy pie or trend.
    </p>
  </section>;
}
