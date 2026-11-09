import blind from "../data/blindHistoricalForecasts2026.json";
import compared from "../data/blindHistoricalComparisons2026.json";

const ink="#173c3a";
const muted="#516b69";
const primary="#096f63";

export default function BlindHistoricalPredictionPanel(){
  const record=blind.records[0];
  if(!record||record.status!=="FROZEN_BLIND_AWAITING_USER_AUTHORIZED_COMPARISON"||
     record.actualOutcome!==null||record.actualDecisionDate!==null||
     record.actualDecisionSourceUrl!==null||record.outcomeViewed!==false){
    throw new Error("BLIND_HISTORICAL_RESEARCH_SEAL_INVALID");
  }
  const result=compared.records.find(x=>x.forecastId===record.forecastId);
  if(!result||result.originalFreezeCommit!==record.sourceFreezeCommit||
     result.frozenPredictedOutcome!==record.predictedOutcome||
     result.trialId!==record.exactNcts[0]||
     result.actualOutcome!=="APPROVAL"||result.outcomeMatch!=="NOT_ACCURATE"||
     result.actualFdaActionDate!=="2026-10-30"||
     result.excludedFromProspectiveAccuracy!==true||
     result.excludedFromProspectiveCalibration!==true||
     Date.parse(result.originalForecastCreatedAt)<=Date.parse(result.actualFdaActionDate+"T23:59:59Z")){
    throw new Error("BLIND_HISTORICAL_COMPARISON_INTEGRITY_ERROR");
  }
  return <section aria-label="Retrospective blind historical PDUFA outcome comparison"
    data-testid="blind-2026-pdufa-forecast"
    style={{border:"1px solid #9cb7b3",borderRadius:13,padding:"clamp(14px,2vw,20px)",
      background:"#f6faf9",margin:"0 0 20px",color:ink}}>
    <div style={{fontSize:11,letterSpacing:".09em",fontWeight:800,color:"#285e56"}}>
      BLIND 2026 FDA REVIEW · HISTORICAL RESEARCH CHALLENGE · REVEALED
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
    <p style={{fontSize:14,lineHeight:1.7,fontWeight:800,color:"#aa4b38",margin:"9px 0"}} data-testid="ino-blind-comparison-verdict">
      NOT ACCURATE — FDA APPROVED VOCERYQ on October 30, 2026.
    </p>
    <p style={{fontSize:13,lineHeight:1.6,color:"#516b69",margin:"9px 0"}}>
      FDA application: <strong>{result.fdaApplicationId}</strong>.
      This was <strong>accelerated approval</strong> for reducing surgical
      papilloma excisions in adults with RRP. The original frozen research
      call was CRL lean and was made after the FDA action, so its error
      is only a <strong>retrospective blind-test miss (0 correct of 1)</strong>.
      It does not affect prospective hit-rate pies or performance lines.
    </p>
    <p style={{fontSize:12,color:muted,margin:"9px 0"}}>
      <a href={result.actualFdaDecisionSourceUrl} target="_blank" rel="noopener noreferrer"
        style={{color:primary,fontWeight:700}}>FDA announcement (October 30)</a>
      {" · "}
      <a href={result.officialFdaProductUrl} target="_blank" rel="noopener noreferrer"
        style={{color:primary,fontWeight:700}}>Official FDA product and approval record</a>
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
      The original INO-3107 freeze remains unchanged; this verified result is
      stored separately following your request to compare. SMMT remains pending.
    </p>
  </section>;
}
