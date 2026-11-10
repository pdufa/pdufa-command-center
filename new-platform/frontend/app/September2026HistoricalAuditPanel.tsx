import ledger from "../data/september2026FdaActionsResearch.json";

export default function September2026HistoricalAuditPanel(){
  const cases=ledger.rows;
  const matches=cases.filter(r=>r.match===true).length;
  const misses=cases.filter(r=>r.match===false).length;
  const total=matches+misses;
  const rate=(100*matches/total).toFixed(1);
  const alwaysApprove=cases.filter(r=>r.observedDisposition==="APPROVAL").length;
  if(cases.length!==20||total!==20||matches!==19||misses!==1||
    ledger.expected.level3ReconstructedCalls!==20||
    ledger.expected.comparableLevel3Pairs!==20||
    ledger.expected.retrospectiveMatches!==matches||
    ledger.expected.retrospectiveMisses!==misses||
    ledger.expected.alwaysApproveComparatorMatches!==20||
    ledger.expected.validBlindCases!==0||ledger.accuracy!==null||
    ledger.researchBlind!==false||alwaysApprove!==20||
    cases.filter(r=>r.reconstructedLevel3Call==="CRL").length!==1||
    cases.find(r=>r.reconstructedLevel3Call==="CRL")?.ticker!=="INCY/MIRM"||
    cases.some(r=>!r.actionDate.startsWith("2026-09-")||
      r.historicalResearchEvidenceCutoff>=r.actionDate||
      !r.historicalResearchSourceUrl?.startsWith("https://")||
      !r.fdaSourceUrl.startsWith("https://")||
      !r.level1TrialAndEfficacy||!r.level2SafetyAndCounterevidence||!r.level3RegulatoryFit||
      r.level3AssessmentState!=="OUTCOME_AWARE_LEVEL3_STYLE_DESK_RECONSTRUCTION"||
      r.researchBlind!==false||r.bonaFidePriorForecast!==false||
      r.match!==(r.reconstructedLevel3Call===r.observedDisposition))){
    throw new Error("SEPT26_LEVEL3_NONBLIND_AUDIT_INTEGRITY_FAILURE");
  }
  return <section id="september-2026-historical-audit"
    aria-label="September 2026 historical Level 3 assessment"
    data-testid="september-2026-historical-audit"
    style={{padding:"clamp(14px,2vw,24px)",border:"1px solid #c9dad2",borderRadius:14,
      background:"white",margin:"0 0 22px",color:"#214d44"}}>
    <div style={{fontSize:11,fontWeight:850,letterSpacing:".1em",color:"#317566"}}>
      SEPTEMBER 2026 · MANUAL LEVEL 3 · HISTORICAL RESEARCH ONLY
    </div>
    <h2 style={{margin:"8px 0",fontSize:22}}>September FDA decision comparisons</h2>
    <p style={{fontSize:13,lineHeight:1.6,color:"#566e69"}}>
      All 20 source-listed September FDA <strong>action-date</strong> approvals have
      an outcome-aware Level 3-style reconstruction based on publicly dated older
      sources. This is not the census of September PDUFA goal dates. It is not a blind test.
    </p>
    <div style={{display:"flex",gap:18,flexWrap:"wrap",alignItems:"center",
      margin:"15px 0",padding:15,background:"#f7faf8",borderRadius:12}}>
      <div role="img" data-testid="september-historical-direction-chart"
        aria-label={`Retrospective agreement ${matches} of 20; ${misses} miss; zero genuinely blind cases`}
        style={{height:144,width:144,flex:"0 0 144px",borderRadius:"50%",
          background:`conic-gradient(#2f806b 0 ${100*matches/total}%,#b47b3a ${100*matches/total}% 100%)`,
          display:"grid",placeItems:"center"}}>
        <div style={{width:108,height:108,borderRadius:"50%",background:"white",
          display:"flex",flexDirection:"column",alignItems:"center",justifyContent:"center"}}>
          <strong style={{fontSize:29}}>{rate}%</strong>
          <span style={{fontSize:9}}>RETROSPECTIVE MATCH</span>
        </div>
      </div>
      <div style={{display:"grid",gap:6,flex:"1 1 220px",fontSize:13}}>
        <strong>20 of 20 Level 3 desk reconstructions completed</strong>
        <div><strong>{matches} matches</strong> · {misses} miss (Atebrioz)</div>
        <div>All-approval baseline: <strong>20/20 (100%)</strong></div>
        <div>Genuinely blind cases: <strong>0</strong></div>
        <div style={{color:"#97651f",fontWeight:750}}>Validated prediction accuracy: NOT AVAILABLE</div>
      </div>
    </div>
    <p style={{fontSize:12,background:"#fff8eb",padding:12,borderRadius:9,
      color:"#83571f",lineHeight:1.6,fontWeight:700}}>
      WARNING — OUTCOME AWARE: The assessor knew all actual FDA decisions before
      reconstructing these calls. The 95% is retrospective directional agreement,
      NOT predictive accuracy or demonstrated skill. The always-APPROVAL rule did
      better on this approval-only selection (100%). Nothing is added to
      live calibrated forecasts or FOCUS grading.
    </p>
    <div style={{overflowX:"auto",border:"1px solid #e2eae7",borderRadius:9,marginTop:13}}>
      <table data-testid="september-historical-data-table"
        style={{borderCollapse:"collapse",minWidth:960,width:"100%",fontSize:12}}>
        <thead><tr style={{background:"#eaf3ef",textAlign:"left"}}>
          {["FDA date","Ticker · drug / evidence","Level","Research call","FDA outcome","Match","Sources"].map(v=>
            <th key={v} style={{padding:"10px 8px",whiteSpace:"nowrap"}}>{v}</th>)}
        </tr></thead>
        <tbody>{cases.map((r,i)=><tr key={r.id} style={{background:i%2?"#f9fbfa":"white"}}>
          <td style={{padding:9,whiteSpace:"nowrap"}}>{r.actionDate}</td>
          <td style={{padding:9,minWidth:210}}>
            <strong>{r.ticker} · {r.drug}</strong>
            <details style={{marginTop:5}}>
              <summary style={{cursor:"pointer",fontWeight:750,color:"#147766"}}>
                Expand research (L1–L3)</summary>
              <div style={{fontSize:11,lineHeight:1.6}}>
                <p><strong>Phase first:</strong> {r.phaseFirstContext}</p>
                <p><strong>L1 — Efficacy:</strong> {r.level1TrialAndEfficacy}</p>
                <p><strong>L2 — Safety:</strong> {r.level2SafetyAndCounterevidence}</p>
                <p><strong>L3 — Regulatory:</strong> {r.level3RegulatoryFit}</p>
                <p>Research evidence strength: {r.researchConfidence} · Nonblind</p>
              </div>
            </details>
          </td>
          <td style={{padding:9}}>3</td>
          <td style={{padding:9,fontWeight:700}}>{r.reconstructedLevel3Call==="CRL"?"CRL lean":"Approval lean"}</td>
          <td style={{padding:9}}>Approved</td>
          <td style={{padding:9,color:r.match?"#2f806b":"#b47b3a",fontWeight:850}}>
            {r.match?"Match":"Miss"}</td>
          <td style={{padding:9,whiteSpace:"nowrap"}}>
            <a target="_blank" rel="noopener noreferrer" href={r.historicalResearchSourceUrl}
              style={{color:"#147766"}}>Older evidence ({r.historicalResearchEvidenceCutoff})</a>
            {" · "}
            <a target="_blank" rel="noopener noreferrer" href={r.fdaSourceUrl}
              style={{color:"#147766"}}>FDA letter</a>
          </td>
        </tr>)}</tbody>
      </table>
    </div>
    <p style={{fontSize:12,lineHeight:1.6,color:"#566e69"}}>
      Source posting dates precede the actions, but original historical source versions
      have not been independently sealed. Supplemental indications, single-arm studies,
      Phase 2 rare-disease pathways and biosimilars must not be treated as Phase 3 trials.
    </p>
    <p style={{fontSize:12}}>
      <a href={ledger.sourceDecisionIndex} target="_blank" rel="noopener noreferrer"
        style={{color:"#147766"}}>FDA approval-letter index</a>{" · "}
      <a href={ledger.sourceCalendar} target="_blank" rel="noopener noreferrer"
        style={{color:"#147766"}}>PDUFA goal-date calendar</a>
    </p>
  </section>;
}
