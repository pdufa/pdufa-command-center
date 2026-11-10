import ledger from "../data/september2026FdaActionsResearch.json";

const forest="#2f806b",amber="#b47b3a",dark="#214d44",muted="#566e69";
function callName(value:string){
  if(value==="APPROVAL")return "Approval lean";
  if(value==="CRL")return "CRL lean";
  return "Abstain";
}

export default function September2026HistoricalAuditPanel(){
  const rows=ledger.rows;
  const expected=ledger.expected;
  const directional=rows.filter(x=>x.eligibleForDirectionalAgreement);
  const matches=directional.filter(x=>x.match===true).length;
  const misses=directional.filter(x=>x.match===false).length;
  const abstains=rows.filter(x=>x.reconstructedLevel3Call==="ABSTAIN").length;
  const percent=(100*matches/directional.length).toFixed(1);
  if(ledger.dataset!=="SEPTEMBER_2026_FDA_ACTION_DATE_SOURCE_LEDGER_UNSCORED_LEVEL3"||
    rows.length!==20||expected.level3AssessedCases!==20||
    expected.level3ReconstructedCalls!==20||directional.length!==16||
    matches!==15||misses!==1||abstains!==4||
    expected.level3ApprovalLeans!==15||expected.level3CrlLeans!==1||
    expected.retrospectiveMatches!==matches||expected.retrospectiveMisses!==misses||
    expected.alwaysApproveBaselineMatches!==directional.length||
    ledger.accuracy!==null||ledger.researchBlind!==false||
    ledger.validatedBlindForecasts!==0||ledger.affectsActiveForecasts!==false||
    rows.some(x=>!x.actionDate.startsWith("2026-09-")||
      x.observedDisposition!=="APPROVAL"||
      x.researchState!=="COMPLETE_OUTCOME_AWARE_DESK_RECONSTRUCTION"||
      x.levelStyle!==3||
      !x.predecision.sourceUrl.startsWith("https://")||
      x.predecision.sourceDate>=x.actionDate||
      x.predecision.originalSourceVersionIndependentlyVerified!==false||
      x.match!==(x.reconstructedLevel3Call==="ABSTAIN"?null:
        x.reconstructedLevel3Call===x.observedDisposition))){
    throw new Error("SEPTEMBER_2026_LEVEL3_RESEARCH_INTEGRITY_INVALID");
  }
  return <section id="september-2026-historical-audit" data-testid="september-2026-historical-audit"
    aria-label="September 2026 FDA historical Level 3 research comparisons"
    style={{background:"#fff",border:"1px solid #c7d9d2",borderRadius:14,
      padding:"clamp(13px,2vw,22px)",margin:"0 0 22px",color:dark}}>
    <div style={{fontSize:11,fontWeight:800,letterSpacing:".1em",color:"#317566"}}>
      SEPTEMBER 2026 · HISTORICAL TESTING · MANUAL LEVEL 3 · NOT BLIND
    </div>
    <h2 style={{fontSize:21,margin:"7px 0 6px"}}>September FDA Level 3 retrospective comparisons</h2>
    <p style={{fontSize:13,lineHeight:1.6,color:muted,margin:"0 0 15px"}}>
      All <strong>20 FDA approval-action records</strong> now have evidence-date-restricted, phase-first
      Level 1/2/3 desk research. These cases were selected by their September FDA
      <strong> action date</strong>, not September PDUFA goal date, and are an
      approval-only source-listed sample, not a comprehensive outcome cohort.
      The assessor already knew the decisions: <strong>no blind accuracy is established</strong>.
    </p>
    <div style={{display:"flex",flexWrap:"wrap",gap:18,alignItems:"center",
      border:"1px solid #e1eae7",borderRadius:12,background:"#f7faf8",
      padding:"15px 18px",marginBottom:15}}>
      <div role="img" data-testid="september-historical-direction-chart"
        aria-label={`Of 16 outcome-aware September Level 3 directional research leans, 15 match and 1 miss; four abstain. Not a blind prediction accuracy metric.`}
        style={{height:146,width:146,flex:"0 0 146px",borderRadius:"50%",
          background:`conic-gradient(${forest} 0 ${100*matches/directional.length}%, ${amber} ${100*matches/directional.length}% 100%)`,
          display:"grid",placeItems:"center"}}>
        <div style={{height:110,width:110,background:"#fff",borderRadius:"50%",
          display:"flex",flexDirection:"column",alignItems:"center",justifyContent:"center"}}>
          <strong style={{fontSize:29,color:"#245d4d"}}>{percent}%</strong>
          <span style={{fontSize:10,color:muted,fontWeight:800,textAlign:"center"}}>RESEARCH MATCH</span>
        </div>
      </div>
      <div style={{display:"grid",gap:7,flex:"1 1 240px"}}>
        <strong style={{fontSize:15}}>20 research reviews · 16 directional calls</strong>
        <div style={{fontSize:13}}><span style={{color:forest,fontWeight:800}}>15 matched</span>
          {" · "}<span style={{color:amber,fontWeight:800}}>1 missed</span>
          {" · "}<span style={{color:muted}}>4 abstained</span></div>
        <div style={{fontSize:12,color:"#98631d",lineHeight:1.5,fontWeight:800}}>
          Historical agreement only; valid blind forecast accuracy: NOT MEASURABLE.
        </div>
        <div style={{fontSize:12,color:muted}}>
          Simple always-APPROVAL baseline: 16/16 (100%) among these same
          directional comparison cases. The Level 3 result does not outperform it.
        </div>
      </div>
    </div>
    <p style={{fontSize:12,color:"#925d24",fontWeight:750,background:"#fff8ed",
      padding:12,borderRadius:8,lineHeight:1.5,margin:"0 0 12px"}}>
      METHOD WARNING: 20/20 decisions in this selected cohort were FDA approvals.
      The historical reviewer was already outcome-exposed. The displayed {percent}%
      is not prospectively validated FDA accuracy. One earlier October target-date
      case (PHAR) is also a September action-date case, so do not add monthly totals
      without reconciling overlapping application identities.
    </p>
    <div style={{overflowX:"auto",border:"1px solid #e2eae7",borderRadius:9}}>
      <table data-testid="september-historical-data-table"
        style={{borderCollapse:"collapse",minWidth:1020,width:"100%",fontSize:12}}>
        <thead><tr style={{textAlign:"left",background:"#eaf3ef"}}>
          {["FDA action date","Ticker · treatment","Research depth","Level 3 lean","FDA result","Match","Original evidence / FDA"].map(h=>
            <th key={h} scope="col" style={{padding:"9px 8px",borderBottom:"1px solid #d2e0d8",
              whiteSpace:"nowrap"}}>{h}</th>)}
        </tr></thead>
        <tbody>{rows.map((x,i)=><tr key={x.id} style={{background:i%2?"#f9fbfa":"#fff"}}>
          <td style={{padding:9,whiteSpace:"nowrap"}}>{x.actionDate}</td>
          <td style={{padding:9,minWidth:190}}><strong>{x.ticker}</strong> · {x.drug}
            <span style={{display:"block",fontSize:10,color:muted}}>{x.applicationId}</span>
          </td>
          <td style={{padding:9,whiteSpace:"nowrap"}}>Level 3 · retrospective</td>
          <td style={{padding:9,color:x.reconstructedLevel3Call==="CRL"?amber:dark,fontWeight:800}}>
            {callName(x.reconstructedLevel3Call)}
          </td>
          <td style={{padding:9,color:forest,fontWeight:700}}>Approved</td>
          <td style={{padding:9,color:x.match===true?forest:amber,fontWeight:800}}>
            {x.match===true?"Match":x.match===false?"Miss":"Abstained"}
          </td>
          <td style={{padding:9,minWidth:250}}>
            <a href={x.predecision.sourceUrl} rel="noopener noreferrer" target="_blank"
              style={{color:"#147766"}}>Predecision ({x.predecision.sourceDate})</a>
            {" · "}
            <a href={x.fdaSourceUrl} rel="noopener noreferrer" target="_blank"
              style={{color:"#147766"}}>FDA decision</a>
            <details style={{marginTop:5}}>
              <summary style={{cursor:"pointer",fontWeight:750}}>Expand 3 levels</summary>
              <p><strong>Level 1 — {x.predecision.phaseFirst}:</strong> {x.predecision.level1ClinicalEvidence}</p>
              <p><strong>Level 2 — benefit/risk:</strong> {x.predecision.level2BenefitRisk}</p>
              <p><strong>Level 3 — regulatory fit:</strong> {x.predecision.level3RegulatoryFit}</p>
              <p><strong>Unresolved:</strong> {x.predecision.criticalUnverified}</p>
            </details>
          </td>
        </tr>)}</tbody>
      </table>
    </div>
    <p style={{fontSize:12,lineHeight:1.6,color:muted,margin:"13px 0 0"}}>
      Each research note is dated to a publicly identifiable predecision source,
      but original source-publication versions are not independently authenticated.
      No scientific grade or prospectively calibrated approval probability was created.
      The original September FDA outcomes remain read-only.
    </p>
    <p style={{fontSize:12,margin:"7px 0 0"}}>
      <a href={ledger.sourceDecisionIndex} target="_blank" rel="noopener noreferrer" style={{color:"#147766"}}>
        Regulator-linked decision index</a>
      {" · "}
      <a href={ledger.sourceCalendar} target="_blank" rel="noopener noreferrer" style={{color:"#147766"}}>
        Separate goal-date PDUFA calendar</a>
    </p>
  </section>;
}
