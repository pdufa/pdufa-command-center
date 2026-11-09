import historical from "../data/levelThreeAbbvieHistorical2026.json";

export default function SkyriziHistoricalLevelThreePanel(){
  const record=historical.records[0];
  if(!record||
     historical.dataset!=="OUTCOME_AWARE_HISTORICAL_LEVEL3_COMPARISON_NOT_BLIND"||
     record.assessmentId!=="HIST-ABBV-SKYRIZI-2026-10-23-LEVEL3-001"||
     record.assessmentLevelStyle!==3||
     record.assessmentDirection!=="APPROVAL"||
     record.actualOutcome!=="APPROVAL"||
     record.actualFdaActionDate!=="2026-10-23"||
     record.trackerListedPdufaDate!=="2026-10-23"||
     record.pdufaDateVerification!=="THIRD_PARTY_TRACKER_ONLY_PREDECISION_SPONSOR_GOAL_NOT_CONFIRMED"||
     record.outcomeExposedBeforeAssessment!==true||
     record.excludedFromProspectiveAccuracy!==true||
     record.excludedFromRetrospectiveBlindValidation!==true||
     record.excludedFromCalibration!==true){
      throw new Error("SKYRIZI_HISTORICAL_RESEARCH_INTEGRITY_FAILURE");
  }
  const linkColor="#087365";
  return <section data-testid="historical-level3-abbv-skyrizi"
      aria-label="AbbVie SKYRIZI Level 3 October 2026 historical FDA action comparison"
      style={{border:"1px solid #bfd7cb",borderRadius:13,background:"#f8fcfa",
        padding:"clamp(14px,2vw,20px)",margin:"0 0 20px",color:"#143f37"}}>
    <div style={{fontSize:11,color:"#286559",letterSpacing:".09em",fontWeight:800}}>
      NEXT EARLIER TRACKED OCTOBER 2026 FDA CASE · HISTORICAL RECONSTRUCTION
    </div>
    <h2 style={{fontSize:21,margin:"7px 0 6px"}}>
      ABBV · SKYRIZI · Crohn's disease SC induction
    </h2>
    <p data-testid="abbv-assessment-level" style={{fontSize:13,margin:"7px 0",
      fontWeight:800,color:"#286559"}}>
      Assessment level: Level 3-style · Manual clinical, benefit-risk and regulatory review
      (not independently certified).
    </p>
    <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(185px,1fr))",
      gap:10,margin:"12px 0"}}>
      <div style={{padding:12,background:"#fff",border:"1px solid #d0e2d8",borderRadius:8}}>
        <div style={{fontSize:11,color:"#58746b"}}>Reconstructed assessment</div>
        <strong style={{display:"block",fontSize:20,color:"#146c56",marginTop:5}}>Approval lean</strong>
        <div style={{fontSize:11,color:"#687d74",marginTop:3}}>
          Manual Level 3-style, no calibrated probability
        </div>
      </div>
      <div style={{padding:12,background:"#fff",border:"1px solid #d0e2d8",borderRadius:8}}>
        <div style={{fontSize:11,color:"#58746b"}}>Actual FDA decision</div>
        <strong data-testid="abbv-actual-outcome" style={{display:"block",
          fontSize:20,color:"#146c56",marginTop:5}}>Approved</strong>
        <div style={{fontSize:11,color:"#687d74",marginTop:3}}>
          October 23, 2026 · BLA 761105/S-053
        </div>
      </div>
    </div>
    <p style={{fontSize:13,lineHeight:1.6,margin:"8px 0"}}>
      <strong>Tracker-listed PDUFA date:</strong> October 23, 2026.
      {" "}<strong>FDA action date:</strong> October 23, 2026.
      {" "}<strong>Phase 3 trial:</strong> NCT06063967 (AFFIRM).
      The original predecision sponsor-announced PDUFA target date
      has not been independently verified.
    </p>
    <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(170px,1fr))",
      gap:8,margin:"12px 0"}}>
      {[
        ["1 · Phase and evidence","Randomized Phase 3 AFFIRM met week-12 clinical remission and endoscopic response co-primary endpoints."],
        ["2 · Benefit and safety","At-home subcutaneous induction; established molecule and Crohn's safety profile, no new trial safety risks reported."],
        ["3 · Regulatory assessment","Positive route-specific Phase 3 and existing drug approval favor authorization; CMC and device details are evidence gaps."]
      ].map(([title,description])=><div key={title} style={{padding:11,background:"#fff",
        border:"1px solid #d5e4dd",borderRadius:8}}>
        <strong style={{fontSize:12}}>{title}</strong>
        <p style={{fontSize:12,lineHeight:1.5,color:"#506b62",margin:"6px 0 0"}}>{description}</p>
      </div>)}
    </div>
    <p style={{fontSize:12,lineHeight:1.6,color:"#895d2b",fontWeight:700,margin:"8px 0"}}>
      DIRECTION MATCHED, NOT A BLIND PREDICTION. The FDA outcome was publicly known
      before this historical reconstruction. This result does not change independent
      forecasting accuracy or calibration.
    </p>
    <p style={{fontSize:12,lineHeight:1.7,margin:"9px 0 0"}}>
      <a href={record.fdaOutcomeSourceUrl} target="_blank" rel="noopener noreferrer"
        style={{color:linkColor,fontWeight:700}}>AbbVie FDA decision announcement</a>
      {" · "}
      <a href={record.fdaLabelUrl} target="_blank" rel="noopener noreferrer"
        style={{color:linkColor}}>FDA revised label</a>
      {" · "}
      <a href="https://github.com/pdufa/pdufa-command-center/blob/main/new-platform/frontend/docs/2026-oct23-abbv-skyrizi-level3-retrospective.md"
        target="_blank" rel="noopener noreferrer" style={{color:linkColor}}>
        Dated evidence and full reasoning
      </a>
    </p>
  </section>;
}
