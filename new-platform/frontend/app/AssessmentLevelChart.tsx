import prospective from "../data/fdaPredictionDecisionAudit.json";
import frozenUltomiris from "../data/levelThreeAznFrozen2026.json";
import actualUltomiris from "../data/levelThreeAznHistoricalComparison2026.json";

type LevelRow={
  id:string;
  trial:string;
  stage:string;
  level:1|3;
  result:string;
  outcomeAware:boolean;
};

/**
 * The active chart deliberately excludes earlier outcome-exposed historical
 * assessments. Their original frozen and source records remain in
 * read-only repository archives and must never be promoted into live accuracy.
 *
 * AZN is the one explicit user-authorized, outcome-exposed historical example.
 * SMMT remains the only prospective preliminary research pilot.
 */
export default function AssessmentLevelChart(){
  const smmt=prospective.records.find(r=>r.predictionId==="HARMONI-SMMT-PDUFA-2026-11-14-V1");
  const azn=frozenUltomiris.records.find(r=>r.assessmentId==="HIST-AZN-ULTOMIRIS-2026-10-21-LEVEL3-V1");
  const aznCompared=actualUltomiris.records.find(r=>r.assessmentId==="HIST-AZN-ULTOMIRIS-2026-10-21-LEVEL3-V1");
  if(!smmt||!azn||!aznCompared||
     smmt.predictedOutcome!=="CRL"||smmt.actualOutcome!=="PENDING"||
     azn.predictedOutcome!=="APPROVAL"||azn.actualOutcome!==null||
     azn.assessmentLevelStyle!==3||
     aznCompared.actualOutcome!=="APPROVAL"||
     aznCompared.frozenRecordCommit!=="0f1b06505535199e9ef8804fb195fa0c3e468620"||
     aznCompared.outcomeExposedBeforeFreeze!==true||
     aznCompared.excludedFromProspectiveAccuracy!==true||
     aznCompared.excludedFromRetrospectiveBlindValidation!==true||
     aznCompared.excludedFromCalibration!==true){
    throw new Error("ASSESSMENT_LEVEL_CHART_SOURCE_MISMATCH");
  }
  const rows:LevelRow[]=[
    {id:smmt.predictionId,trial:"SMMT · HARMONi",stage:"Original preliminary research; FDA action pending",
      level:1,result:"CRL lean",outcomeAware:false},
    {id:azn.assessmentId,trial:"AZN · Ultomiris",
      stage:"Retained historical example only · outcome already known",
      level:3,result:"Approval lean · FDA accelerated approval",outcomeAware:true}
  ];
  return <section data-testid="research-assessment-level-chart" aria-label="Assessment level chart by FDA review"
    style={{background:"#fff",border:"1px solid #b8d1c9",borderRadius:14,
      padding:"clamp(14px,2.2vw,22px)",margin:"0 0 22px"}}>
    <div style={{fontSize:11,letterSpacing:".09em",color:"#286358",fontWeight:800}}>
      ASSESSMENT LEVEL TRACKER · ACTIVE DISPLAY ONLY
    </div>
    <h2 style={{fontSize:21,margin:"7px 0 5px"}}>Scientific review depth</h2>
    <p style={{fontSize:13,color:"#536c67",margin:"0 0 16px",lineHeight:1.5}}>
      Only the original prospective SMMT pilot and the user-retained AZN historical
      example appear here. Earlier outcome-exposed assessments are removed from
      the program display and reserved as read-only historical files.
    </p>
    <div role="img" aria-label="SMMT original Level 1; AZN Ultomiris retained historical Level 3"
      style={{display:"grid",gap:11}}>
      {rows.map(row=><div key={row.id} data-testid={"assessment-level-row-"+(row.outcomeAware?"hindsight-":"")+row.id}
        style={{display:"grid",gridTemplateColumns:"minmax(0,1fr) minmax(120px,1.3fr)",
          columnGap:13,alignItems:"center",rowGap:5}}>
        <div style={{minWidth:0}}>
          <strong style={{display:"block",fontSize:13,color:"#21453f"}}>{row.trial}</strong>
          <span style={{fontSize:11,lineHeight:1.4,color:"#536e69"}}>{row.stage}</span>
        </div>
        <div style={{minWidth:0}}>
          <div style={{display:"flex",justifyContent:"space-between",fontSize:12,fontWeight:800,
            color:"#265b52",marginBottom:5}}>
            <span>Level {row.level}-style</span><span>{row.result}</span>
          </div>
          <div aria-hidden="true" style={{position:"relative",height:16,background:"#e7f0ed",
            borderRadius:6,overflow:"hidden"}}>
            <div style={{height:"100%",width:`${row.level/3*100}%`,
              background:row.outcomeAware?"#9a794a":"#267f70",borderRadius:6}}/>
          </div>
        </div>
      </div>)}
    </div>
    <div style={{display:"flex",gap:8,justifyContent:"space-between",paddingLeft:"45%",
      fontSize:11,color:"#627671",marginTop:6}}>
      <span>Level 0</span><span>Level 3 (chart scale)</span>
    </div>
    <p style={{fontSize:12,color:"#895e2c",lineHeight:1.5,margin:"14px 0 0"}}>
      Levels describe approximate manual review depth, not validated 20-level engine maturity.
      AZN remains solely by user request, is <strong>outcome-aware, not blind</strong>,
      and is excluded from prospective accuracy and calibration.
    </p>
  </section>;
}
