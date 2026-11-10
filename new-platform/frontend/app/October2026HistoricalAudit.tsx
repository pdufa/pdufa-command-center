import frozen from "../data/october2026EvidenceCutoffFreeze.json";
import compared from "../data/october2026OfficialOutcomeComparison.json";

type ComparedRow=typeof compared.caseComparisons[number];
const sourceSheetUrl="https://docs.google.com/spreadsheets/d/1erY_z62b4mHhx5s_3HgJxXoJEslbLngMuQNfhcuSviU/edit#gid=1737882570";
function shortDecision(value:string){
  if(value==="APPROVAL")return "Approval";
  if(value==="CRL")return "CRL";
  if(value==="WITHDRAWN_NO_FDA_DECISION")return "Withdrawn (no decision)";
  return value;
}
export default function October2026HistoricalAudit(){
  if(frozen.dataset!=="OCTOBER_2026_EXPOSED_EVIDENCE_CUTOFF_ASSESSMENT_FREEZE"||
     frozen.independentOutcomeBlind!==false||
     frozen.validForAccuracy!==false||
     frozen.validForCalibration!==false||
     compared.dataset!=="OCTOBER_2026_OUTCOME_VERIFICATION_AFTER_OUTCOME_EXPOSED_FREEZE"||
     compared.freezeCommitSha!=="9ec4e1d564496f05aae05fcb1b98c0aa69db6410"||
     compared.independentBlind!==false||
     compared.validForIndependentPredictionAccuracy!==false||
     compared.validatedBlindAccuracy!==null||
     compared.validBlindPredictionCount!==0||
     compared.cohortCount!==17||
     frozen.predecisionAssessmentCases.length!==17){
    throw new Error("OCT26_HISTORICAL_AUDIT_INTEGRITY_FAILURE");
  }
  const rows=frozen.predecisionAssessmentCases.map(a=>{
    const b:ComparedRow|undefined=compared.caseComparisons.find(x=>x.caseId===a.id);
    if(!b||b.ticker!==a.ticker||b.drug!==a.drug||b.predecisionPrediction!==a.prediction||
       a.actualFdaDecision!==null||a.actualFdaActionDate!==null||a.officialPostdecisionSource!==null||
       a.knownOutcomesExposedToAuthorBeforeResearch!==true||
       a.scoreEligibleForBlindAccuracy!==false||
       b.directionMatch!==(b.eligibleForBinaryAgreement?(b.observedDisposition===a.prediction):null)){
      throw new Error("OCT26_CROSS_FILE_RESEARCH_OUTCOME_MISMATCH");
    }
    return {a,b};
  });
  const decided=rows.filter(({b})=>b.eligibleForBinaryAgreement);
  const matches=decided.filter(({b})=>b.directionMatch).length;
  const misses=decided.length-matches;
  const withdrawn=rows.length-decided.length;
  const baseline=decided.filter(({b})=>b.observedDisposition==="APPROVAL").length;
  if(decided.length!==compared.binaryScoredCases||
     matches!==compared.directionalMatches||
     misses!==compared.directionalMisses||
     withdrawn!==compared.nonDecisionWithdrawals||
     baseline!==compared.alwaysApproveBaselineMatches||
     decided.length!==16||matches!==15||misses!==1||withdrawn!==1){
    throw new Error("OCT26_HISTORICAL_AUDIT_DENOMINATOR_MISMATCH");
  }
  const pct=(100*matches/decided.length).toFixed(2);
  return <section id="october-2026-historical-audit" data-testid="october-2026-historical-audit"
    aria-label="October 2026 FDA retrospective monthly research and decisions"
    style={{border:"1px solid #bfdbd1",borderRadius:14,background:"#fff",
      padding:"clamp(14px,2.2vw,23px)",margin:"0 0 22px",color:"#23483e"}}>
    <p style={{fontSize:11,fontWeight:850,letterSpacing:".08em",color:"#327362",margin:0}}>
      OCTOBER 2026 · HISTORICAL MONTHLY REVIEW · RESEARCH-ONLY
    </p>
    <h2 style={{fontSize:22,margin:"7px 0 8px"}}>October FDA case comparisons</h2>
    <p style={{fontSize:13,lineHeight:1.6,color:"#546e65",margin:"0 0 14px"}}>
      A documented <strong>17-case October FDA target/action cohort</strong>:
      15 from a source calendar plus two additional prior-cycle cases.
      These are not claimed to be a comprehensive industry-wide regulatory calendar.
      October FDA action is not always the original PDUFA target.
    </p>
    <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(160px,1fr))",
      gap:11,margin:"0 0 15px"}}>
      {[
        ["Retrospective agreement",`${pct}%`,"15 matched of 16 FDA decisions"],
        ["Missed directions",String(misses),"INO-3107 predicted CRL; FDA approved"],
        ["Withdrawn / unscored",String(withdrawn),"No FDA Approval or CRL decision"],
        ["Genuinely blind cases","0","Accuracy not independently established"]
      ].map(([name,value,note])=>
        <div key={name} style={{padding:13,borderRadius:10,border:"1px solid #d9e8e1",background:"#f7faf8"}}>
          <span style={{fontSize:11,color:"#5b746b"}}>{name}</span>
          <strong style={{fontSize:25,display:"block",margin:"6px 0",color:"#235f50"}}>{value}</strong>
          <span style={{fontSize:11,color:"#5b746b",lineHeight:1.4}}>{note}</span>
        </div>
      )}
    </div>
    <div style={{display:"flex",alignItems:"center",gap:17,flexWrap:"wrap",border:"1px solid #e3ebe6",
      borderRadius:10,padding:13,marginBottom:13}}>
      <div role="img" data-testid="october-2026-agreement-chart"
        aria-label={`Of 16 decided October cases, ${matches} direction matches and ${misses} misses; 1 withdrawal excluded; not blind accuracy`}
        style={{height:136,width:136,borderRadius:"50%",display:"grid",placeItems:"center",
        background:`conic-gradient(#317e68 0 ${matches/decided.length*360}deg, #bd8755 ${matches/decided.length*360}deg 360deg)`}}>
        <div style={{height:103,width:103,borderRadius:"50%",background:"#fff",display:"flex",
          alignItems:"center",justifyContent:"center",flexDirection:"column"}}>
          <strong style={{fontSize:25,color:"#256854"}}>{pct}%</strong>
          <span style={{fontSize:10,color:"#65776f"}}>MATCH ONLY</span>
        </div>
      </div>
      <div style={{flex:"1 1 210px",fontSize:13,lineHeight:1.75}}>
        <div><strong>{matches}</strong> matched Approval/CRL direction</div>
        <div><strong>{misses}</strong> missed Approval/CRL direction</div>
        <div><strong>{withdrawn}</strong> voluntarily withdrawn, no FDA decision, excluded</div>
        <div style={{fontWeight:750,color:"#935c25"}}>Unbiased predictive accuracy: NOT MEASURABLE</div>
      </div>
    </div>
    <p style={{fontSize:12,lineHeight:1.6,color:"#90622c",fontWeight:750,
      padding:"10px 12px",background:"#fff8ed",borderRadius:9,margin:"0 0 12px"}}>
      OUTCOME-AWARE, NOT BLIND. The evaluator already knew October FDA outcomes before
      the date-restricted reconstructions. The {pct}% is not real forecast skill:
      always guessing APPROVAL would have matched {baseline} of {decided.length}
      decided cases ({(100*baseline/decided.length).toFixed(0)}%) in this
      heavily approval-selected cohort. Do not use for independent prediction accuracy or calibration.
    </p>
    <div style={{overflowX:"auto",border:"1px solid #e0e9e5",borderRadius:9}}>
      <table data-testid="october-2026-historical-case-data"
        style={{borderCollapse:"collapse",width:"100%",minWidth:940,fontSize:12}}>
        <thead>
          <tr style={{background:"#eaf3ee",textAlign:"left"}}>
            {["October date","Sponsor / drug","Phase / review depth","Reconstructed call",
              "FDA disposition","FDA action","Match","Source"].map(h=>
              <th key={h} scope="col"
                style={{padding:"10px 8px",whiteSpace:"nowrap",color:"#285a49",
                  borderBottom:"1px solid #dae7e0"}}>{h}</th>)}
          </tr>
        </thead>
        <tbody>
          {rows.map(({a,b},i)=><tr key={a.id}
            style={{background:i%2?"#f7faf8":"#fff"}}>
            <td style={{padding:"9px 8px",whiteSpace:"nowrap",borderBottom:"1px solid #e9f0eb"}}>
              {a.trackedOctoberDate}
            </td>
            <td style={{padding:"9px 8px",borderBottom:"1px solid #e9f0eb"}}>
              <strong style={{display:"block"}}>{a.ticker} · {a.drug}</strong>
              <span style={{fontSize:11,color:"#6a7f74"}}>{a.nct.join(", ")||"Trial record unavailable"}</span>
            </td>
            <td style={{padding:"9px 8px",borderBottom:"1px solid #e9f0eb"}}>
              <strong>Level 3-style</strong>
              <span style={{display:"block",fontSize:10,color:"#687970"}}>{a.phaseFirstVerified.replaceAll("_"," ")}</span>
            </td>
            <td style={{padding:"9px 8px",borderBottom:"1px solid #e9f0eb",fontWeight:750}}>
              {shortDecision(a.prediction)} lean
            </td>
            <td style={{padding:"9px 8px",borderBottom:"1px solid #e9f0eb"}}>
              {shortDecision(b.observedDisposition)}
            </td>
            <td style={{padding:"9px 8px",whiteSpace:"nowrap",borderBottom:"1px solid #e9f0eb"}}>
              {b.actualFdaActionDate??"—"}
            </td>
            <td style={{padding:"9px 8px",fontWeight:750,borderBottom:"1px solid #e9f0eb",
              color:b.directionMatch===true?"#257b59":b.directionMatch===false?"#ad6736":"#82766b"}}>
              {b.directionMatch===null?"Unscored":b.directionMatch?"Match":"Miss"}
            </td>
            <td style={{padding:"9px 8px",borderBottom:"1px solid #e9f0eb",whiteSpace:"nowrap"}}>
              <a href={b.decisionSourceUrl} target="_blank" rel="noopener noreferrer"
                style={{color:"#147763"}}>Outcome</a>
              {" · "}
              <a href={a.predecisionUrls[0]} target="_blank" rel="noopener noreferrer"
                style={{color:"#147763"}}>Predecision</a>
            </td>
          </tr>)}
        </tbody>
      </table>
    </div>
    <p style={{fontSize:12,color:"#556b60",lineHeight:1.6,margin:"11px 0 0"}}>
      Frozen point-in-time research uses documents dated before each action; the original
      FDA decision was not withheld from this evaluator. The FDA actions for ANKTIVA and
      Jemperli occurred in October despite originally announced 2027 PDUFA goals;
      Welireg/Lenvima and Joenja were approved before their October goals.
      One withdrawn application is unscored.
    </p>
    <p style={{fontSize:12,margin:"10px 0 0",lineHeight:1.7}}>
      <a href="https://docs.google.com/spreadsheets/d/1erY_z62b4mHhx5s_3HgJxXoJEslbLngMuQNfhcuSviU/edit"
        target="_blank" rel="noopener noreferrer" style={{color:"#147763",fontWeight:750}}>
        Open October 2026 Audit in PDUFA Master Scan Data</a>
      {" · "}
      <a href={compared.freezeCommitUrl} target="_blank" rel="noopener noreferrer"
        style={{color:"#147763"}}>Predecision-evidence assessment freeze</a>
      {" · "}
      <a href="https://www.pdufa.bio/calendar" target="_blank" rel="noopener noreferrer"
        style={{color:"#147763"}}>Calendar coverage source</a>
    </p>
  </section>;
}
