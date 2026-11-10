import audit from "../data/august2026Level3HistoricalResearch.json";

export default function August2026HistoricalAuditPanel(){
  const rows=audit.rows;
  const matches=rows.filter(r=>r.retrospectiveDirectionMatch).length;
  const misses=rows.length-matches;
  const percent=(100*matches/rows.length).toFixed(1);
  const expected=audit.summary;
  if(audit.dataset!=="AUGUST_2026_FDA_ACTION_DATE_LEVEL_3_OUTCOME_AWARE_RESEARCH"||
    rows.length!==12||matches!==11||misses!==1||
    expected.level3ResearchReviews!==12||expected.retrospectiveMatches!==11||
    expected.retrospectiveMisses!==1||expected.alwaysApproveBaseline!==12||
    expected.validatedAccuracy!==null||expected.validBlindForecasts!==0||
    !audit.warnings.thisIsNotPredictionAccuracy||!audit.warnings.allCasesFDAApproved||
    rows.some(r=>!r.date.startsWith("2026-08-")||
      r.actualFdaDisposition!=="APPROVAL"||
      r.formalScientificGrade!==null||
      r.outcomeKnownToResearcher!==true||
      r.evidenceFrozenBeforeResearch!==false||
      r.independentPublicationClockVerified!==false||
      r.datedPublicEvidence.sourceDate>=r.date||
      !r.datedPublicEvidence.url.startsWith("https://")||
      r.retrospectiveDirectionMatch!==(r.level3ResearchCall==="APPROVAL"))){
    throw new Error("AUG26_HISTORICAL_OUTCOME_AWARE_GATES_INVALID");
  }
  const green="#2f806b",tan="#b47b3a",ink="#214d44";
  return <section data-testid="august-2026-historical-audit" id="august-2026-historical-audit"
    aria-label="August 2026 Level 3 FDA retrospective study" style={{
      border:"1px solid #c7d9d2",borderRadius:14,background:"#fff",
      padding:"clamp(13px,2vw,22px)",margin:"0 0 22px",color:ink
    }}>
    <p style={{margin:0,fontSize:11,fontWeight:800,letterSpacing:".1em",color:green}}>
      AUGUST 2026 · HISTORICAL TESTING · MANUAL LEVEL 3 · OUTCOME-AWARE
    </p>
    <h2 style={{fontSize:21,margin:"7px 0 8px"}}>August FDA case comparisons</h2>
    <p style={{fontSize:13,lineHeight:1.6,margin:"0 0 14px",color:"#546e65"}}>
      <strong>12 August FDA approval actions</strong> have predecision-dated, three-level
      retrospective research. These are action dates, not a complete calendar of
      August PDUFA goals, CRLs or withdrawals. The assessor already knew these
      approvals when reconstructing the research; no blind prediction accuracy is measurable.
    </p>
    <div style={{display:"flex",alignItems:"center",flexWrap:"wrap",gap:17,
      border:"1px solid #e3ebe6",borderRadius:11,padding:14,
      background:"#f8faf9",margin:"0 0 15px"}}>
      <div role="img" data-testid="august-2026-historical-chart"
        aria-label={`${matches} of ${rows.length} retrospective directional judgments agree with FDA, ${misses} mismatch; not a blind accuracy estimate.`}
        style={{width:148,height:148,borderRadius:"50%",flex:"0 0 148px",display:"grid",placeItems:"center",
          background:`conic-gradient(${green} 0 ${100*matches/rows.length}%, ${tan} ${100*matches/rows.length}% 100%)`}}>
        <div style={{width:110,height:110,borderRadius:"50%",background:"#fff",display:"flex",
          flexDirection:"column",justifyContent:"center",alignItems:"center"}}>
          <strong style={{fontSize:29,color:ink}}>{percent}%</strong>
          <span style={{fontSize:10,color:"#667a71",fontWeight:800}}>MATCH ONLY</span>
        </div>
      </div>
      <div style={{display:"grid",gap:7,flex:"1 1 240px",fontSize:13}}>
        <strong style={{fontSize:16}}>12 assessed · 12 FDA approvals</strong>
        <div><strong style={{color:green}}>11 matched</strong> · <strong style={{color:tan}}>1 missed</strong> (REPL)</div>
        <div>Always-approval comparator: <strong>12/12 = 100%</strong></div>
        <div style={{fontWeight:800,color:"#925d24"}}>Genuinely blind predictions: 0 · FDA accuracy: NOT VALIDATED</div>
      </div>
    </div>
    <div style={{padding:"10px 12px",background:"#fff8ed",borderRadius:9,marginBottom:14,
      fontSize:12,fontWeight:750,lineHeight:1.6,color:"#915d2b"}}>
      WARNING: Approval-only cases were selected after their outcomes became known.
      Reconstructed August evidence leans cannot be used as independent prospective
      accuracy or model calibration. The all-approval baseline beats the {percent}%
      retrospective match in this biased sample.
    </div>
    <div style={{overflowX:"auto",border:"1px solid #e0e9e5",borderRadius:10}}>
      <table data-testid="august-2026-historical-table" style={{borderCollapse:"collapse",minWidth:980,width:"100%",fontSize:12}}>
        <thead><tr style={{background:"#eaf3ee",textAlign:"left"}}>
          {["Action","Sponsor / drug","Phase","Level 3 lean","FDA decision","Compare","Evidence"].map(h=>
            <th scope="col" key={h} style={{padding:"9px 8px",borderBottom:"1px solid #d2e0d8",whiteSpace:"nowrap"}}>{h}</th>)}
        </tr></thead>
        <tbody>{rows.map((r,i)=><tr key={r.id} style={{background:i%2?"#f9fbfa":"#fff"}}>
          <td style={{padding:9,whiteSpace:"nowrap"}}>{r.date}</td>
          <td style={{padding:9,minWidth:185}}><strong>{r.ticker}</strong> · {r.drug}<small style={{display:"block",color:"#647b70"}}>{r.application}</small></td>
          <td style={{padding:9}}>{r.phaseFirst.replaceAll("_"," ").toLowerCase()}</td>
          <td style={{padding:9,fontWeight:750,color:r.level3ResearchCall==="CRL"?tan:green}}>{r.level3ResearchCall} lean</td>
          <td style={{padding:9,fontWeight:750}}>APPROVED</td>
          <td style={{padding:9,fontWeight:750,color:r.retrospectiveDirectionMatch?green:tan}}>{r.retrospectiveDirectionMatch?"Match":"Miss"}</td>
          <td style={{padding:9,minWidth:200}}>
            <a href={r.datedPublicEvidence.url} target="_blank" rel="noopener noreferrer"
              style={{color:"#147766"}}>Predecision source</a> · <a href={r.fdaSource} target="_blank" rel="noopener noreferrer" style={{color:"#147766"}}>FDA index</a>
            <details style={{marginTop:5}}>
              <summary style={{cursor:"pointer",fontWeight:750}}>Three-level assessment</summary>
              <p><strong>Level 1:</strong> {r.datedPublicEvidence.clinical}</p>
              <p><strong>Level 2:</strong> {r.datedPublicEvidence.benefitRisk}</p>
              <p><strong>Level 3:</strong> {r.datedPublicEvidence.regulatory}</p>
              <p><strong>Outstanding:</strong> {r.datedPublicEvidence.unresolved}</p>
            </details>
          </td>
        </tr>)}</tbody>
      </table>
    </div>
    <p style={{fontSize:12,color:"#6a7c71",lineHeight:1.6}}>
      Primary-source version timestamps, clinical statistical plans, formal signed assessments
      and genuine before-outcome freezing remain unverified; no production FDA forecast is modified.
      The August PDUFA goal-date calendar is a different cohort.
    </p>
  </section>;
}
