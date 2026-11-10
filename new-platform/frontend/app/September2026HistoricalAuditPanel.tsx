import ledger from "../data/september2026FdaActionsResearch.json";

export default function September2026HistoricalAuditPanel(){
  const rows=ledger.rows;
  if(ledger.dataset!=="SEPTEMBER_2026_FDA_ACTION_DATE_SOURCE_LEDGER_UNSCORED_LEVEL3"||
    rows.length!==20||ledger.expected.sourceListedDecisions!==20||
    ledger.expected.level3ReconstructedCalls!==1||ledger.expected.comparableLevel3Pairs!==1||
    ledger.accuracy!==null||ledger.researchBlind!==false||
    rows.some(x=>!x.actionDate.startsWith("2026-09-")||x.observedDisposition!=="APPROVAL"||
      !x.fdaSourceUrl.startsWith("https://")||
      (x.ticker==="PHAR"?
       (x.reconstructedLevel3Call!=="APPROVAL"||x.match!==true||
        x.eligibleForDirectionalAgreement!==true||
        x.level3AssessmentState!=="OUTCOME_AWARE_HISTORICAL_RECONSTRUCTION"||
        !x.historicalResearchSourceUrl?.startsWith("https://")):
       (x.reconstructedLevel3Call!==null||x.match!==null||
        x.level3AssessmentState!=="NOT_PERFORMED"||x.eligibleForDirectionalAgreement!==false)))){
    throw new Error("SEPTEMBER_2026_RESEARCH_NO_FALSE_ACCURACY_GUARD");
  }
  const approvals=rows.filter(x=>x.observedDisposition==="APPROVAL").length;
  const reconstructed=rows.filter(x=>x.reconstructedLevel3Call!==null);
  if(reconstructed.length!==1||reconstructed[0]?.ticker!=="PHAR")throw new Error("SEPTEMBER_CROSS_MONTH_RECONSTRUCTION_COUNT_FAILURE");
  return <section id="september-2026-historical-audit"
    aria-label="September 2026 FDA historical decisions and pending Level 3 research comparisons"
    data-testid="september-2026-historical-audit"
    style={{background:"#fff",border:"1px solid #c7d9d2",borderRadius:14,
      padding:"clamp(13px,2vw,22px)",margin:"0 0 22px",color:"#214d44"}}>
    <div style={{fontSize:11,letterSpacing:".1em",fontWeight:800,color:"#317566"}}>
      SEPTEMBER 2026 · HISTORICAL TESTING · LEVEL 3 · EXISTING RETROSPECTIVE CROSS-MONTH COMPARISON
    </div>
    <h2 style={{fontSize:21,margin:"7px 0 6px"}}>September FDA action comparisons</h2>
    <p style={{fontSize:13,lineHeight:1.6,color:"#566e69",margin:"0 0 15px"}}>
      This is the September counterpart to the October historical chart. The initial
      date-scoped FDA-outcome ledger contains 20 distinct September <strong>action-date</strong>
      approvals with linked regulator letters, not a complete census or a September
      PDUFA <em>goal-date</em> cohort. October and September cohort definitions must not
      be merged without explicit normalization. One previously documented <strong>PHAR Joenja</strong> Level 3-style
      research reconstruction has been cross-referenced from the October target-date
      study, because its actual FDA action was September 11. The evaluator already
      knew the outcome, and the other 19 actions remain unassessed.
    </p>
    <div style={{display:"flex",flexWrap:"wrap",gap:18,alignItems:"center",
      border:"1px solid #e1eae7",borderRadius:12,background:"#f7faf8",
      padding:"15px 18px",marginBottom:15}}>
      <div role="img" data-testid="september-historical-outcome-chart"
        aria-label={`${approvals} FDA approvals verified; one prior outcome-aware Level 3 reconstruction matches, 19 unassessed; not a predictive accuracy chart`}
        style={{height:146,width:146,flex:"0 0 146px",borderRadius:"50%",background:"#2f806b",
          display:"grid",placeItems:"center"}}>
        <div style={{height:110,width:110,background:"#fff",borderRadius:"50%",
          display:"flex",alignItems:"center",flexDirection:"column",justifyContent:"center"}}>
          <strong style={{fontSize:30,color:"#245d4d"}}>{approvals}</strong>
          <span style={{fontSize:11,color:"#566e69",fontWeight:800,textAlign:"center"}}>FDA APPROVALS</span>
        </div>
      </div>
      <div style={{display:"grid",gap:8,flex:"1 1 230px",fontSize:13}}>
        <div><strong>20</strong> confirmed September FDA approval actions</div>
        <div><strong>1</strong> existing Level 3-style historical research call (PHAR)</div>
        <div><strong>1</strong> retrospective directional match; 19 unassessed</div>
        <div style={{color:"#98631d",fontWeight:800}}>Research-only match: 1/1 · NOT predictive accuracy</div>
        <div style={{fontSize:12}}>No blind predictions and no calibrated historical accuracy.</div>
      </div>
    </div>
    <div style={{overflowX:"auto",border:"1px solid #e2eae7",borderRadius:9}}>
      <table data-testid="september-historical-data-table"
        style={{borderCollapse:"collapse",minWidth:920,width:"100%",fontSize:12}}>
        <thead><tr style={{textAlign:"left",background:"#eaf3ef"}}>
          {["FDA action date","Ticker · treatment","Application","Level 3 research call","FDA disposition","Comparison","Original FDA letter"].map(h=>
            <th key={h} scope="col" style={{padding:"9px 8px",whiteSpace:"nowrap",
              borderBottom:"1px solid #d2e0d8"}}>{h}</th>)}
        </tr></thead>
        <tbody>{rows.map((x,i)=><tr key={x.id}
          style={{background:i%2?"#f9fbfa":"#fff"}}>
          <td style={{padding:9,whiteSpace:"nowrap"}}>{x.actionDate}</td>
          <td style={{padding:9,minWidth:190}}><strong>{x.ticker}</strong> · {x.drug}</td>
          <td style={{padding:9,whiteSpace:"nowrap"}}>{x.applicationId}</td>
          <td style={{padding:9,color:"#926e32",fontWeight:700}}>{x.reconstructedLevel3Call==="APPROVAL"?"Approval lean (nonblind)":"Unassessed"}</td>
          <td style={{padding:9,color:"#28735d",fontWeight:700}}>Approved</td>
          <td style={{padding:9,color:"#6f776f"}}>{x.match===true?"Matched (historical)":"Not scoreable"}</td>
          <td style={{padding:9}}><a href={x.fdaSourceUrl} target="_blank" rel="noopener noreferrer"
            style={{color:"#147766"}}>FDA letter</a></td>
        </tr>)}</tbody>
      </table>
    </div>
    <p style={{fontSize:12,color:"#97651f",lineHeight:1.6,margin:"12px 0 0",fontWeight:700}}>
      FDA actions do not substitute for date-frozen predecision evidence assessments.
      Do not infer 100% predictive accuracy from one matched reconstruction or all observed approvals. Any later September
      Level 3 reconstructions will remain outcome-aware, isolated from live forecasting,
      and must be compared against an always-approval baseline.
    </p>
    <p style={{fontSize:12,margin:"7px 0 0"}}>
      <a href={ledger.sourceDecisionIndex} target="_blank" rel="noopener noreferrer" style={{color:"#147766"}}>
        Regulator-linked decision index</a>
      {" · "}
      <a href={ledger.sourceCalendar} target="_blank" rel="noopener noreferrer" style={{color:"#147766"}}>
        Separate September goal-date calendar</a>
    </p>
  </section>;
}
