import historical from "../data/levelThreePharHistorical2026.json";

export default function JoenjaHistoricalLevelThreePanel(){
  const row=historical.records[0];
  if(!row||
     historical.dataset!=="OUTCOME_AWARE_HISTORICAL_LEVEL3_COMPARISON_NOT_BLIND"||
     row.assessmentId!=="HIST-PHAR-JOENJA-2026-10-24-LEVEL3-001"||
     row.assessmentLevelStyle!==3||
     row.assessmentDirection!=="APPROVAL"||
     row.actualOutcome!=="APPROVAL"||
     row.originalPdufaDate!=="2026-10-24"||
     row.actualFdaActionDate!=="2026-09-11"||
     row.outcomeExposedBeforeAssessment!==true||
     row.excludedFromProspectiveAccuracy!==true||
     row.excludedFromRetrospectiveBlindValidation!==true||
     row.excludedFromCalibration!==true){
    throw new Error("JOENJA_LEVEL3_RETROSPECTIVE_INTEGRITY_FAILURE");
  }
  const linkColor="#087365";
  return <section data-testid="historical-level3-phar-joenja"
    aria-label="Joenja pediatric APDS Level 3 historical PDUFA comparison"
    style={{border:"1px solid #bfd7cb",borderRadius:13,
      background:"#f8fcfa",padding:"clamp(14px,2vw,20px)",margin:"0 0 20px",color:"#143f37"}}>
    <div style={{fontSize:11,color:"#286559",letterSpacing:".09em",fontWeight:800}}>
      PREVIOUS SCHEDULED PDUFA · OCTOBER 24, 2026 · HISTORICAL LEVEL 3 RECONSTRUCTION
    </div>
    <h2 style={{fontSize:21,margin:"7px 0 6px"}}>
      PHAR · Joenja (leniolisib) · Pediatric APDS
    </h2>
    <p data-testid="phar-assessment-level" style={{fontSize:13,margin:"7px 0",fontWeight:800,color:"#286559"}}>
      Assessment level: Level 3-style · Manual three-part evidence review (not independently certified).
    </p>
    <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(185px,1fr))",gap:10,margin:"12px 0"}}>
      <div style={{padding:12,background:"#fff",border:"1px solid #d0e2d8",borderRadius:8}}>
        <div style={{fontSize:11,color:"#58746b"}}>Reconstructed assessment</div>
        <strong style={{display:"block",fontSize:20,color:"#146c56",marginTop:5}}>Approval lean</strong>
        <div style={{fontSize:11,color:"#687d74",marginTop:3}}>Manual Level 3-style, no calibrated probability</div>
      </div>
      <div style={{padding:12,background:"#fff",border:"1px solid #d0e2d8",borderRadius:8}}>
        <div style={{fontSize:11,color:"#58746b"}}>True FDA decision</div>
        <strong data-testid="phar-actual-outcome" style={{display:"block",fontSize:20,color:"#146c56",marginTop:5}}>
          Approved
        </strong>
        <div style={{fontSize:11,color:"#687d74",marginTop:3}}>September 11, 2026 · 43 days ahead of PDUFA</div>
      </div>
    </div>
    <p style={{fontSize:13,lineHeight:1.6,margin:"8px 0"}}>
      <strong>Original goal:</strong> October 24, 2026.
      {" "}<strong>Exact pediatric Phase 3 trial:</strong> NCT05438407.
      {" "}<strong>Application:</strong> NDA 217759/S-006.
      The FDA expanded Joenja to children 4–11 years weighing at least 27 kg.
    </p>
    <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(170px,1fr))",gap:8,margin:"12px 0"}}>
      {[
        ["1 · Phase and design","Single-arm pediatric Phase 3; earlier adult/adolescent efficacy precedent."],
        ["2 · Benefit and safety","Targeted therapy for serious APDS, with dose/exposure and limited pediatric safety uncertainties."],
        ["3 · Regulatory challenge","January CRL cited low-weight underexposure and analytical tests; resubmission narrowed to ≥27 kg and supplied new methods data."]
      ].map(([heading,description])=><div key={heading} style={{padding:11,background:"#fff",
        border:"1px solid #d5e4dd",borderRadius:8}}>
        <strong style={{fontSize:12}}>{heading}</strong>
        <p style={{fontSize:12,lineHeight:1.5,color:"#506b62",margin:"6px 0 0"}}>{description}</p>
      </div>)}
    </div>
    <p style={{fontSize:12,lineHeight:1.6,color:"#895d2b",fontWeight:700,margin:"8px 0"}}>
      DIRECTION MATCHED, NOT A BLIND PREDICTION. The actual September 11 FDA decision
      was already public before this November 9 retrospective review. This case
      does not enter predictive accuracy, calibration, or success-rate charts.
    </p>
    <p style={{fontSize:12,lineHeight:1.7,margin:"9px 0 0"}}>
      <a href={row.fdaOutcomeSourceUrl} target="_blank" rel="noopener noreferrer"
        style={{color:linkColor,fontWeight:700}}>Official FDA approval notice</a>
      {" · "}
      <a href={row.officialFdaLetterUrl} target="_blank" rel="noopener noreferrer"
        style={{color:linkColor}}>FDA supplemental approval letter</a>
      {" · "}
      <a href="https://github.com/pdufa/pdufa-command-center/blob/main/new-platform/frontend/docs/2026-oct24-phar-joenja-level3-retrospective.md"
        target="_blank" rel="noopener noreferrer" style={{color:linkColor}}>Predecision-evidence reasoning and chronology</a>
    </p>
  </section>;
}
