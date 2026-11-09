import historical from "../data/levelThreeHistoricalReconstruction2026.json";

const teal="#096f63";

export default function BepirovirsenHistoricalLevelThreePanel(){
  const caseFile=historical.records[0];
  if(!caseFile || historical.dataset!=="OUTCOME_EXPOSED_HISTORICAL_LEVEL3_RECONSTRUCTION" ||
     caseFile.status!=="HISTORICAL_RECONSTRUCTION_NOT_BLIND" ||
     caseFile.level3Prediction!=="APPROVAL" ||
     caseFile.outcomeExposedBeforeAssessment!==true ||
     caseFile.actualOutcome!==null ||
     caseFile.outcomeCompared!==false ||
     caseFile.excludedFromProspectiveAccuracy!==true ||
     caseFile.excludedFromRetrospectiveBlindValidation!==true ||
     caseFile.excludedFromCalibration!==true){
    throw new Error("HISTORICAL_LEVEL3_SCIENTIFIC_PROVENANCE_INTEGRITY_FAILURE");
  }
  return <section data-testid="historical-level3-bepirovirsen"
      aria-label="Bepirovirsen October 2026 retrospective three-level assessment"
      style={{border:"1px solid #bed2ce",borderRadius:13,padding:"clamp(14px,2vw,20px)",
        background:"#f9fcfa",margin:"0 0 20px",color:"#163f3b"}}>
    <div style={{fontSize:11,letterSpacing:".09em",fontWeight:800,color:"#285e56"}}>
      NEXT EARLIER PDUFA · THREE-LEVEL HISTORICAL RECONSTRUCTION
    </div>
    <h2 style={{fontSize:21,margin:"8px 0 6px"}}>GSK / IONS · Bepirovirsen · Chronic hepatitis B</h2>
    <p style={{fontSize:14,lineHeight:1.6,margin:"6px 0"}}>
      <strong>Reconstructed direction: Approval lean.</strong>
      {" "}Original FDA action target: <strong>October 26, 2026</strong>.
      {" "}Pivotal trials: <strong>NCT05630807</strong> and <strong>NCT05630820</strong>.
    </p>
    <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(180px,1fr))",gap:8,margin:"13px 0"}}>
      {[
        ["1 · Trial evidence","Two randomized Phase 3 trials; functional cure approximately 20% and 19% vs 0%."],
        ["2 · Benefit / safety","Meaningful functional cure; grade 3+ treatment events 16% vs 3%."],
        ["3 · Regulatory review","Accepted NDA, priority review and Breakthrough Therapy designation."]
      ].map(([heading,detail])=><div key={heading} style={{padding:11,border:"1px solid #d4e4df",
         borderRadius:8,background:"#fff"}}>
        <strong style={{fontSize:12}}>{heading}</strong>
        <p style={{fontSize:12,lineHeight:1.5,color:"#4b6662",margin:"5px 0 0"}}>{detail}</p>
      </div>)}
    </div>
    <p style={{fontSize:12,lineHeight:1.6,fontWeight:700,color:"#885920",margin:"9px 0"}}>
      HISTORICAL, NOT BLIND: The outcome had appeared in search results before this
      reconstruction. This review uses only dated predecision evidence, but cannot
      be scored as an independent accurate prediction. No numerical probability
      or verified scientific level-20 assessment has been produced.
    </p>
    <p style={{fontSize:12,lineHeight:1.7,margin:"9px 0 0"}}>
      <a href={caseFile.sourceFreezeUrl} target="_blank" rel="noopener noreferrer" style={{color:teal,fontWeight:700}}>
        Timestamped three-level research record
      </a>
      {" · "}
      <a href="https://github.com/pdufa/pdufa-command-center/blob/main/new-platform/frontend/docs/2026-oct26-bepirovirsen-level3-reconstruction.md"
         target="_blank" rel="noopener noreferrer" style={{color:teal,fontWeight:700}}>
        Full clinical and regulatory analysis
      </a>
      {" · "}
      <a href={caseFile.pivotalPaperUrl} target="_blank" rel="noopener noreferrer" style={{color:teal}}>
        Phase 3 publication
      </a>
    </p>
    <p style={{fontSize:12,lineHeight:1.5,color:"#4b6662",margin:"8px 0 0"}}>
      Original INO-3107 and SMMT predictions are unchanged; this case is not
      included in the prospective accuracy pies or charts.
    </p>
  </section>;
}
