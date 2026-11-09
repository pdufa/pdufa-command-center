import frozen from "../data/levelThreeAznFrozen2026.json";
import compared from "../data/levelThreeAznHistoricalComparison2026.json";

export default function UltomirisHistoricalLevelThreePanel(){
  const r=frozen.records[0],o=compared.records[0];
  if(!r||!o||
     frozen.dataset!=="FROZEN_MANUAL_LEVEL3_HISTORICAL_RECONSTRUCTION"||
     compared.dataset!=="OUTCOME_AWARE_POST_FREEZE_HISTORICAL_COMPARISON_NOT_BLIND"||
     r.assessmentId!=="HIST-AZN-ULTOMIRIS-2026-10-21-LEVEL3-V1"||
     o.assessmentId!==r.assessmentId||
     r.frozenResearchCommit!==o.frozenResearchCommit||
     o.frozenRecordCommit!=="0f1b06505535199e9ef8804fb195fa0c3e468620"||
     r.predictedOutcome!=="APPROVAL"||
     r.actualOutcome!==null||
     r.officialDecisionCompared!==false||
     o.predictedOutcome!==r.predictedOutcome||
     o.actualOutcome!=="APPROVAL"||
     o.actualApprovalType!=="ACCELERATED"||
     o.actualFdaActionDate!=="2026-10-21"||
     o.outcomeExposedBeforeFreeze!==true||o.blind!==false||
     o.excludedFromProspectiveAccuracy!==true||
     o.excludedFromRetrospectiveBlindValidation!==true||
     o.excludedFromCalibration!==true){
    throw new Error("AZN_FROZEN_LEVEL3_HISTORICAL_COMPARISON_INTEGRITY_FAILURE");
  }
  const green="#096c5c";
  return <section data-testid="historical-level3-azn-ultomiris"
    aria-label="AstraZeneca Ultomiris Oct 21 historical assessment and FDA decision"
    style={{border:"1px solid #bed6cb",borderRadius:13,background:"#f8fcfa",
      padding:"clamp(14px,2vw,20px)",margin:"0 0 20px",color:"#143e37"}}>
    <div style={{fontSize:11,letterSpacing:".09em",color:"#29675b",fontWeight:800}}>
      EARLIER 2026 FDA ACTION · PREDECISION SOURCE-CUTOFF · FROZEN THEN VERIFIED
    </div>
    <h2 style={{fontSize:21,margin:"8px 0 5px"}}>
      AZN · Ultomiris (ravulizumab) · IgA nephropathy
    </h2>
    <p data-testid="azn-assessment-level" style={{fontSize:13,color:"#25675a",fontWeight:800,margin:"6px 0"}}>
      Assessment level: Level 3-style · Manual three-layer evidence review
      (not certified engine maturity)
    </p>
    <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(185px,1fr))",
      gap:10,margin:"12px 0"}}>
      <div style={{background:"#fff",border:"1px solid #d1e2d9",padding:12,borderRadius:8}}>
        <div style={{fontSize:11,color:"#547169"}}>Frozen research judgment</div>
        <strong style={{fontSize:20,color:green,display:"block",marginTop:5}}>Approval lean</strong>
        <span style={{fontSize:11,color:"#627870"}}>Accelerated-approval pathway · no calibrated probability</span>
      </div>
      <div style={{background:"#fff",border:"1px solid #d1e2d9",padding:12,borderRadius:8}}>
        <div style={{fontSize:11,color:"#547169"}}>Verified FDA decision</div>
        <strong data-testid="azn-actual-outcome" style={{fontSize:20,color:green,display:"block",marginTop:5}}>
          Accelerated approval
        </strong>
        <span style={{fontSize:11,color:"#627870"}}>October 21, 2026 · BLA 761108/S-046</span>
      </div>
    </div>
    <p style={{fontSize:13,lineHeight:1.6,margin:"8px 0"}}>
      <strong>Exact trial:</strong> I CAN, NCT06291376 (Phase 3).
      {" "}<strong>Original disclosed PDUFA window:</strong> Q4 2026.
      The precise October 21 target date was not independently established in the June 15
      predecision company announcement; October 21 is the verified FDA action date.
    </p>
    <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(175px,1fr))",
      gap:8,margin:"12px 0"}}>
      {[
        ["1 · Trial data","Prespecified Phase 3 interim analysis: 43.4% placebo-adjusted lower proteinuria at week 34 (p<0.0001)."],
        ["2 · Benefit and risk","Relevant surrogate reduction; kidney-function results pending and meningococcal infection risk requires management."],
        ["3 · Regulatory review","Priority Review of indication extension with established drug experience; accelerated approval with confirmatory study most plausible."]
      ].map(([heading,detail])=><div key={heading} style={{padding:11,background:"#fff",
        border:"1px solid #d3e3db",borderRadius:8}}>
        <strong style={{fontSize:12}}>{heading}</strong>
        <p style={{fontSize:12,lineHeight:1.5,color:"#526e66",margin:"6px 0 0"}}>{detail}</p>
      </div>)}
    </div>
    <p style={{fontSize:12,lineHeight:1.6,color:"#8a5d26",fontWeight:800,margin:"9px 0"}}>
      OUTCOME-EXPOSED, NOT A BLIND PREDICTION. The historical calendar revealed
      the approval before the judgment was frozen. The research freeze preceded
      the separate official FDA decision check, but this match does not count
      toward prospective or blind retrospective accuracy.
    </p>
    <p style={{fontSize:12,lineHeight:1.7,margin:"10px 0 0"}}>
      <a href={o.frozenRecordUrl} target="_blank" rel="noopener noreferrer"
        style={{color:green,fontWeight:700}}>Original timestamped research freeze</a>
      {" · "}
      <a href={o.officialDecisionSourceUrl} target="_blank" rel="noopener noreferrer"
        style={{color:green}}>FDA accelerated approval letter</a>
      {" · "}
      <a href={o.sponsorDecisionAnnouncementUrl} target="_blank" rel="noopener noreferrer"
        style={{color:green}}>October 21 sponsor decision announcement</a>
      {" · "}
      <a href="https://github.com/pdufa/pdufa-command-center/blob/main/new-platform/frontend/docs/2026-oct21-azn-ultomiris-level3-frozen-reconstruction.md"
        target="_blank" rel="noopener noreferrer" style={{color:green}}>Predecision-only scientific rationale</a>
    </p>
  </section>;
}
