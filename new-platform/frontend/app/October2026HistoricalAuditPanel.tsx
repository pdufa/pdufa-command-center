import october from "../data/october2026RetrospectiveFdaComparison.json";
import original from "../data/october2026EvidenceCutoffFreeze.json";
import illumya from "../data/october2026IlumyaEvidenceReconstruction.json";

const sheetLink="https://docs.google.com/spreadsheets/d/1erY_z62b4mHhx5s_3HgJxXoJEslbLngMuQNfhcuSviU/edit#gid=2026420899";
const green="#2f806b", amber="#b47b3a", muted="#566e69", dark="#214d44";

export default function October2026HistoricalAuditPanel(){
  const cases=october.cases;
  const sourceIds=new Set(original.predecisionAssessmentCases.map(x=>x.id));
  sourceIds.add(illumya.caseId);
  const matches=cases.filter(x=>x.sameDirection===true);
  const misses=cases.filter(x=>x.sameDirection===false);
  const withdrawals=cases.filter(x=>x.actualOutcome==="WITHDRAWN");
  const scoreable=matches.length+misses.length;
  if(original.predecisionAssessmentCases.length!==17||sourceIds.size!==18||
     cases.length!==18||october.countTotal!==18||
     october.countMatches!==16||october.countMisses!==1||
     october.countWithdrawals!==1||matches.length!==16||
     misses.length!==1||withdrawals.length!==1||scoreable!==17||
     october.isBlind!==false||october.assessorKnewDecisions!==true||
     october.blindAccuracy!==null||october.affectsActivePredictions!==false||
     october.affectsFocusRoster!==false||october.usesHistoricalQuarantineOnly!==true||
     Math.abs(october.directionalAgreement-16/17)>0.00001||
     cases.some(x=>!sourceIds.has(x.id)||x.eligibleForBlindAccuracy!==false||
       x.sameDirection!==(x.actualOutcome==="WITHDRAWN"?null:x.prediction===x.actualOutcome))){
    throw new Error("OCTOBER_2026_AUDIT_COUNTS_OR_SEPARATION_INVALID");
  }
  const percent=(100*matches.length/scoreable).toFixed(1);
  return <section aria-label="October 2026 historical FDA PDUFA research audit"
    data-testid="october-2026-historical-audit"
    style={{background:"#fff",border:"1px solid #c7d9d2",
      borderRadius:14,padding:"clamp(13px,2vw,22px)",margin:"0 0 22px",color:dark}}>
    <div style={{fontSize:11,letterSpacing:".1em",fontWeight:800,color:"#317566"}}>
      OCTOBER 2026 · HISTORICAL TESTING · MANUAL LEVEL 3
    </div>
    <h2 style={{fontSize:21,margin:"7px 0 6px"}}>
      October FDA review comparisons
    </h2>
    <p style={{fontSize:13,lineHeight:1.6,color:muted,margin:"0 0 15px"}}>
      Sourced October-tracked cases with clinical/regulatory evidence review and
      separately recorded FDA outcomes. This is an <strong>outcome-aware historical reconstruction,
      not a genuine blind prediction test</strong>. Not all rows are independently verified October
      PDUFA target dates; some FDA decisions occurred early or followed non-October goals.
    </p>
    <div style={{display:"flex",flexWrap:"wrap",alignItems:"center",gap:18,
      border:"1px solid #e1eae7",borderRadius:12,background:"#f7faf8",
      padding:"15px 18px",marginBottom:15}}>
      <div role="img" data-testid="october-historical-direction-chart"
        aria-label={`Among ${scoreable} FDA decisions, ${matches.length} match the retrospective research direction and ${misses.length} do not; ${withdrawals.length} withdrawal is excluded`}
        style={{height:146,width:146,flex:"0 0 146px",borderRadius:"50%",
          background:`conic-gradient(${green} 0 ${100*matches.length/scoreable}%, ${amber} ${100*matches.length/scoreable}% 100%)`,
          display:"grid",placeItems:"center"}}>
        <div style={{height:110,width:110,background:"#fff",borderRadius:"50%",
          display:"flex",flexDirection:"column",alignItems:"center",justifyContent:"center"}}>
          <strong style={{fontSize:29,color:"#245d4d"}}>{percent}%</strong>
          <span style={{fontSize:10,color:muted,fontWeight:800,textAlign:"center"}}>
            DIRECTIONAL AGREEMENT
          </span>
        </div>
      </div>
      <div style={{display:"grid",gap:7,flex:"1 1 220px"}}>
        <strong style={{fontSize:15}}>18 cases reviewed · 17 FDA decisions</strong>
        <div style={{fontSize:13}}><span style={{color:green,fontWeight:800}}>16 matched</span>
          {" · "}<span style={{color:amber,fontWeight:800}}>1 missed</span>
          {" · "}<span style={{color:muted}}>1 withdrawn (excluded)</span></div>
        <div style={{fontSize:12,color:"#98631d",lineHeight:1.5,fontWeight:700}}>
          Valid blind accuracy: not established. Zero blind cases.
        </div>
        <div style={{fontSize:12,color:muted}}>
          Directional match = 16 ÷ 17; withdrawal excluded from the denominator.
        </div>
      </div>
    </div>
    <div style={{display:"flex",justifyContent:"space-between",flexWrap:"wrap",
      gap:8,alignItems:"center",margin:"0 0 12px"}}>
      <strong style={{fontSize:13}}>All 18 case outcomes</strong>
      <a href={sheetLink} target="_blank" rel="noopener noreferrer"
        style={{fontSize:13,fontWeight:700,color:"#127464"}}>
        Open October 2026 Testing spreadsheet
      </a>
    </div>
    <div style={{overflowX:"auto",border:"1px solid #e2eae7",borderRadius:9}}>
      <table data-testid="october-historical-data-table"
        style={{borderCollapse:"collapse",minWidth:1000,width:"100%",fontSize:12}}>
        <thead><tr style={{textAlign:"left",background:"#eaf3ef"}}>
          {["Tracked date","Ticker · treatment","Level","Forecast","FDA result","FDA action / note","Comparison","Source"].map(h=>
            <th scope="col" key={h} style={{padding:"9px 8px",whiteSpace:"nowrap",
              borderBottom:"1px solid #d2e0d8",color:dark}}>{h}</th>)}
        </tr></thead>
        <tbody>{cases.map((item,i)=>
          <tr key={item.id} style={{background:i%2?"#f9fbfa":"#fff"}}>
            <td style={{padding:"8px",whiteSpace:"nowrap"}}>{item.trackedOctoberDate}</td>
            <td style={{padding:"8px",minWidth:220}}>
              <strong style={{display:"block"}}>{item.ticker} · {item.drug}</strong>
              {item.calendarRole==="OCTOBER_FDA_ACTION_NOT_OCTOBER_GOAL"?
                <span style={{fontSize:10,color:"#90651c"}}>2027 original goal</span>:null}
            </td>
            <td style={{padding:"8px",whiteSpace:"nowrap"}}>3 · manual</td>
            <td style={{padding:"8px",fontWeight:700}}>
              {item.prediction==="CRL"?"CRL lean":"Approval lean"}
            </td>
            <td style={{padding:"8px"}}>
              {item.actualOutcome==="WITHDRAWN"?"Withdrawn (no FDA decision)":
               item.actualOutcome==="APPROVAL"?"Approved":item.actualOutcome}
            </td>
            <td style={{padding:"8px",whiteSpace:"nowrap"}}>
              {item.actualFdaActionDate??("decisionAnnouncementDate" in item?item.decisionAnnouncementDate:item.withdrawalDate)}
              {item.id==="OCT26-18-SUN"?" (announced)":null}
            </td>
            <td style={{padding:"8px",fontWeight:800,
              color:item.sameDirection===true?green:item.sameDirection===false?amber:muted}}>
              {item.sameDirection===true?"Matched":item.sameDirection===false?"Missed":"Excluded"}
            </td>
            <td style={{padding:"8px"}}>
              <a href={item.decisionSource} rel="noopener noreferrer" target="_blank"
                style={{color:"#147766",whiteSpace:"nowrap"}}>FDA decision evidence</a>
            </td>
          </tr>)}</tbody>
      </table>
    </div>
    <p style={{fontSize:12,lineHeight:1.6,color:"#98631d",margin:"13px 0 0",fontWeight:700}}>
      94.1% retrospective agreement is not proven FDA prediction accuracy.
      The evaluator already knew the historical outcomes before making these assessments.
      No October result is added to prospective accuracy, calibration, or active FOCUS scoring.
    </p>
    <p style={{fontSize:12,lineHeight:1.6,color:muted,margin:"8px 0 0"}}>
      <a href="https://github.com/pdufa/pdufa-command-center/commit/9ec4e1d564496f05aae05fcb1b98c0aa69db6410"
        rel="noopener noreferrer" target="_blank" style={{color:"#147766"}}>Original 17-case evidence archive</a>
      {" · "}
      <a href="https://github.com/pdufa/pdufa-command-center/commit/bbab5a783e149d3889018878fac4ed6212f2f5ef"
        rel="noopener noreferrer" target="_blank" style={{color:"#147766"}}>ILUMYA supplement</a>
    </p>
  </section>;
}
