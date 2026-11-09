import blind from "../data/blindHistoricalForecasts2026.json";

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
    <p style={{fontSize:13,lineHeight:1.6,fontWeight:750,color:"#895923",margin:"9px 0"}}>
      FDA OUTCOME SEALED — NOT CONSULTED. This prediction was reconstructed
      after the original target date from earlier documents. It must not be
      included in the prospectively validated accuracy pie or performance line.
      No numerical confidence is assigned.
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
      The SMMT prospective case remains separate and unchanged. Actual
      FDA outcome comparison requires your later explicit instruction.
    </p>
  </section>;
}
