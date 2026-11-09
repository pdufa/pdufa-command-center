import prospective from "../data/fdaPredictionDecisionAudit.json";
import originalIno from "../data/blindHistoricalForecasts2026.json";
import retrospectiveBepirovirsen from "../data/levelThreeHistoricalReconstruction2026.json";
import retrospectiveJoenja from "../data/levelThreePharHistorical2026.json";
import retrospectiveSkyrizi from "../data/levelThreeAbbvieHistorical2026.json";

type LevelRow={
  id:string;
  trial:string;
  stage:string;
  level:1|3;
  result:string;
  hindsight:boolean;
};

export default function AssessmentLevelChart(){
  const smmt=prospective.records.find(r=>r.predictionId==="HARMONI-SMMT-PDUFA-2026-11-14-V1");
  const ino=originalIno.records.find(r=>r.forecastId==="BLIND-INO3107-2026-10-30-V1");
  const bepi=retrospectiveBepirovirsen.records.find(r=>r.assessmentId==="HIST-2026-10-26-BEPIROVIRSEN-LEVEL3-001");
  const phar=retrospectiveJoenja.records.find(r=>r.assessmentId==="HIST-PHAR-JOENJA-2026-10-24-LEVEL3-001");
  const abbv=retrospectiveSkyrizi.records.find(r=>r.assessmentId==="HIST-ABBV-SKYRIZI-2026-10-23-LEVEL3-001");
  if(!smmt||!ino||!bepi||!phar||!abbv||
     abbv.assessmentLevelStyle!==3||abbv.assessmentDirection!=="APPROVAL"||
     abbv.actualOutcome!=="APPROVAL"||abbv.outcomeExposedBeforeAssessment!==true||
     abbv.excludedFromProspectiveAccuracy!==true||
     abbv.excludedFromRetrospectiveBlindValidation!==true||
     abbv.excludedFromCalibration!==true||phar.assessmentDirection!=="APPROVAL"||
     phar.actualOutcome!=="APPROVAL"||phar.outcomeExposedBeforeAssessment!==true||
     phar.excludedFromProspectiveAccuracy!==true||
     phar.excludedFromRetrospectiveBlindValidation!==true||
     phar.excludedFromCalibration!==true||smmt.predictedOutcome!=="CRL"||
     ino.predictedOutcome!=="CRL"||bepi.level3Prediction!=="APPROVAL"||
     bepi.outcomeExposedBeforeAssessment!==true){
    throw new Error("ASSESSMENT_LEVEL_CHART_SOURCE_MISMATCH");
  }
  const rows:LevelRow[]=[
    {id:smmt.predictionId,trial:"SMMT · HARMONi",stage:"Original preliminary review",
      level:1,result:"CRL lean",hindsight:false},
    {id:ino.forecastId,trial:"INO · INO-3107",stage:"Original preliminary review",
      level:1,result:"CRL lean",hindsight:false},
    {id:ino.forecastId+"-REASSESSMENT",trial:"INO · INO-3107",stage:"Later reassessment (FDA outcome known)",
      level:3,result:"Approval lean",hindsight:true},
    {id:bepi.assessmentId,trial:"GSK / IONS · Bepirovirsen",stage:"Historical review (FDA outcome exposed)",
      level:3,result:"Approval lean",hindsight:true},
    {id:phar.assessmentId,trial:"PHAR · Joenja",stage:"Historical review (FDA outcome known)",
      level:3,result:"Approval lean · FDA approved",hindsight:true},
    {id:abbv.assessmentId,trial:"ABBV · SKYRIZI",stage:"Historical review (FDA outcome known)",
      level:3,result:"Approval lean · FDA approved",hindsight:true}
  ];
  return <section data-testid="research-assessment-level-chart" aria-label="Assessment level chart by FDA review"
    style={{background:"#fff",border:"1px solid #b8d1c9",borderRadius:14,
      padding:"clamp(14px,2.2vw,22px)",margin:"0 0 22px"}}>
    <div style={{fontSize:11,letterSpacing:".09em",color:"#286358",fontWeight:800}}>
      ASSESSMENT LEVEL TRACKER · BY REVIEW
    </div>
    <h2 style={{fontSize:21,margin:"7px 0 5px"}}>Scientific review depth</h2>
    <p style={{fontSize:13,color:"#536c67",margin:"0 0 16px",lineHeight:1.5}}>
      Manual-style review levels shown separately from FDA accuracy.
      A later reassessment is a separate row, never a rewrite of the frozen original.
    </p>
    <div role="img" aria-label="SMMT original Level 1; INO original Level 1; INO revised after FDA outcome Level 3; GSK bepirovirsen historical Level 3; PHAR Joenja historical Level 3; ABBV SKYRIZI historical Level 3"
      style={{display:"grid",gap:11}}>
      {rows.map(row=><div key={row.id} data-testid={"assessment-level-row-"+(row.hindsight?"hindsight-":"")+row.id}
        style={{display:"grid",gridTemplateColumns:"minmax(0,1fr) minmax(120px,1.3fr)",columnGap:13,alignItems:"center",rowGap:5}}>
        <div style={{minWidth:0}}>
          <strong style={{display:"block",fontSize:13,color:"#21453f"}}>{row.trial}</strong>
          <span style={{fontSize:11,lineHeight:1.4,color:"#536e69"}}>{row.stage}</span>
        </div>
        <div style={{minWidth:0}}>
          <div style={{display:"flex",justifyContent:"space-between",fontSize:12,fontWeight:800,color:"#265b52",marginBottom:5}}>
            <span>Level {row.level}-style</span><span>{row.result}</span>
          </div>
          <div aria-hidden="true" style={{position:"relative",height:16,background:"#e7f0ed",borderRadius:6,overflow:"hidden"}}>
            <div style={{height:"100%",width:`${row.level/3*100}%`,
              background:row.hindsight?"#9a794a":"#267f70",borderRadius:6}}/>
          </div>
        </div>
      </div>)}
    </div>
    <div style={{display:"flex",gap:8,justifyContent:"space-between",paddingLeft:"45%",
      fontSize:11,color:"#627671",marginTop:6}}>
      <span>Level 0</span><span>Level 3 (chart scale)</span>
    </div>
    <p style={{fontSize:12,color:"#895e2c",lineHeight:1.5,margin:"14px 0 0"}}>
      These are approximate manual review-depth labels, <strong>not certified engine levels</strong>
      or completion percentages toward the planned 20-level / 800-assessment framework.
      The INO revised, GSK historical, PHAR historical and ABBV historical rows
      are outcome-aware, and none counts as a blind prediction or prospective accuracy.
    </p>
  </section>;
}
