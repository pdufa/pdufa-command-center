import september from "../data/september2026HistoricalAuditRoster.json";

const green="#2f806b",amber="#b47b3a",muted="#566e69",dark="#214d44";

export default function September2026HistoricalAuditPanel(){
  const entries=september.cases;
  const assessed=entries.filter(x=>x.level3ResearchCall!==null);
  const verified=entries.filter(x=>x.decisionIndependentlyVerified);
  const blind=entries.filter(x=>x.eligibleForBlindAccuracy);
  if(september.dataset!=="SEPTEMBER_2026_CALENDAR_CANDIDATES_UNASSESSED"||
    entries.length!==23||september.calendarRows!==23||
    september.validatedLevel3Cases!==0||september.validatedBlindCases!==0||
    september.blindAccuracy!==null||september.directionalAgreement!==null||
    september.provisionalResearchForecastCount!==0||
    september.affectsActivePredictions!==false||september.affectsFocusRoster!==false||
    assessed.length!==0||verified.length!==0||blind.length!==0||
    entries.some(x=>x.eligibleForDirectionalAgreement||x.officialDecisionUrl!==null||
      x.predecisionEvidenceUrl!==null||x.level3ResearchCall!==null)){
    throw new Error("SEPTEMBER_2026_RESEARCH_GUARD_INVALID");
  }
  return <section data-testid="september-2026-historical-audit"
    aria-label="September 2026 historical Level 3 research cohort"
    style={{background:"#fff",border:"1px solid #c7d9d2",borderRadius:14,
      padding:"clamp(13px,2vw,22px)",margin:"0 0 22px",color:dark}}>
    <div style={{fontSize:11,letterSpacing:".1em",fontWeight:800,color:"#317566"}}>
      SEPTEMBER 2026 · HISTORICAL TESTING · LEVEL 3 INTAKE
    </div>
    <h2 style={{fontSize:21,margin:"7px 0 6px"}}>September FDA review comparisons</h2>
    <p style={{fontSize:13,lineHeight:1.6,color:muted,margin:"0 0 15px"}}>
      The same monthly chart format used for October, beginning with
      <strong> 23 entries from a November 9 third-party calendar snapshot</strong>.
      These are provisional, not 23 verified unique FDA application cycles.
      The independent evidence-before-outcome Level 3 reconstructions have
      <strong> not been performed</strong>; no comparison or numerical accuracy is asserted.
    </p>
    <div style={{display:"flex",flexWrap:"wrap",alignItems:"center",gap:18,
      border:"1px solid #e1eae7",borderRadius:12,background:"#f7faf8",
      padding:"15px 18px",marginBottom:15}}>
      <div role="img" data-testid="september-historical-progress-chart"
        aria-label="Zero of 23 provisional calendar entries have completed Level 3 evidence reconstructions; no accuracy number"
        style={{height:146,width:146,flex:"0 0 146px",borderRadius:"50%",
          background:"conic-gradient(#c7d2ce 0% 100%)",display:"grid",placeItems:"center"}}>
        <div style={{height:110,width:110,background:"#fff",borderRadius:"50%",
          display:"flex",flexDirection:"column",alignItems:"center",justifyContent:"center"}}>
          <strong style={{fontSize:29,color:dark}}>0 / 23</strong>
          <span style={{fontSize:10,color:muted,fontWeight:800,textAlign:"center"}}>
            LEVEL 3 REVIEWS
          </span>
        </div>
      </div>
      <div style={{display:"grid",gap:7,flex:"1 1 220px"}}>
        <strong style={{fontSize:15}}>September cohort identified · 23 candidate entries</strong>
        <div style={{fontSize:13}}>0 independently confirmed review cycles · 0 completed historical Level 3 assessments</div>
        <div style={{fontSize:12,color:amber,lineHeight:1.5,fontWeight:700}}>
          Historical directional agreement: NOT YET MEASURABLE.
          Genuine blind forecasts: 0.
        </div>
        <div style={{fontSize:12,color:muted}}>
          Shared sponsor entries and quarter-only dates need deduplication and
          exact dated original FDA application documents.
        </div>
      </div>
    </div>
    <div style={{overflowX:"auto",border:"1px solid #e2eae7",borderRadius:9}}>
      <table data-testid="september-historical-case-table"
        style={{borderCollapse:"collapse",minWidth:880,width:"100%",fontSize:12}}>
        <thead><tr style={{textAlign:"left",background:"#eaf3ef"}}>
          {["Calendar date","Ticker · treatment","Depth","Predecision assessment","FDA decision verification","Comparison","Source"].map(h=>
            <th scope="col" key={h} style={{padding:"9px 8px",whiteSpace:"nowrap",
              borderBottom:"1px solid #d2e0d8",color:dark}}>{h}</th>)}
        </tr></thead>
        <tbody>{entries.map((item,i)=>
          <tr key={item.id} style={{background:i%2?"#f9fbfa":"#fff"}}>
            <td style={{padding:"8px",whiteSpace:"nowrap"}}>{item.calendarDate}</td>
            <td style={{padding:"8px",minWidth:230}}><strong>{item.ticker}</strong> · {item.drug}</td>
            <td style={{padding:"8px",whiteSpace:"nowrap"}}>Level 3 · pending</td>
            <td style={{padding:"8px"}}>Not reconstructed</td>
            <td style={{padding:"8px"}}>Calendar-reported only</td>
            <td style={{padding:"8px",fontWeight:700,color:amber}}>Unscored</td>
            <td style={{padding:"8px"}}>
              <a href={item.sourceCalendarUrl} rel="noopener noreferrer" target="_blank" style={{color:green}}>Calendar lead</a>
            </td>
          </tr>)}</tbody>
      </table>
    </div>
    <p style={{fontSize:12,color:muted,lineHeight:1.7,margin:"12px 0 0"}}>
      Exact matching to the October format means: establish dated original sources, perform
      case-specific predecision Level 3 scientific interpretation, retain a frozen research
      record, verify official FDA disposition separately, and only then compare direction.
      Every result remains explicitly outcome-exposed unless genuinely sealed before the
      decision. No row in this intake modifies FOCUS, production scoring or calibration.
    </p>
    <p style={{fontSize:12,margin:"10px 0 0"}}>
      <a href={september.sourceCalendarUrl} target="_blank" rel="noopener noreferrer"
        style={{color:green,fontWeight:750}}>September calendar source (November 9 snapshot)</a>
      {" · "}
      <a href="https://github.com/pdufa/pdufa-command-center/blob/research/2026-september-level3-historical-audit/new-platform/frontend/data/september2026HistoricalAuditRoster.json"
        target="_blank" rel="noopener noreferrer" style={{color:green}}>Research intake file</a>
    </p>
  </section>;
}
