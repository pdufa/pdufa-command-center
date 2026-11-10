import manifest from "../data/focus29Level3ProvisionalResearch20261110.json";
import checks from "../data/focusNearTermPdufaSourceChecks20261110.json";

const readingLabels:Record<string,string>={
  APPROVAL_LEAN:"Research approval lean",
  CRL_LEAN:"Research CRL lean",
  ABSTAIN:"Research abstain",
  ALREADY_APPROVED:"Already decided (not forecast)"
};

/** Read-only original-issuer goal-date evidence; no regulatory decision or model output. */
export default function FocusNearTermPdufaSourceChecks(){
  if(checks.schemaVersion!==1||
     checks.documentType!=="ISSUER_PRIMARY_SOURCE_PDUFA_GOAL_READBACK_NOT_FDA_OUTCOME"||
     checks.primaryIssuerGoalReadbacks!==3||
     checks.validatedBlindPredictionCount!==0||
     checks.independentlyFDAConfirmedGoalDates!==0||
     checks.entries.length!==3||manifest.cycles.length!==23){
    throw new Error("FOCUS_NEAR_TERM_GOAL_SOURCE_GUARD");
  }
  const cycles=new Map(manifest.cycles.map(c=>[c.cycleId,c]));
  const used=new Set<string>();
  for(const entry of checks.entries){
    const matched=cycles.get(entry.cycleId);
    if(!matched||used.has(entry.cycleId)||matched.ticker!==entry.ticker||
       matched.reportedPdufaGoal!==entry.reportedGoalDate||
       matched.call==="ALREADY_APPROVED"||
       entry.reportedGoalDate<checks.asOf||
       entry.sourcePublicationDate>checks.asOf||
       !entry.primarySourceUrl.startsWith("https://www.sec.gov/Archives/edgar/")||
       entry.sourceStatus!=="ISSUER_REPORTED_GOAL_CORROBORATED"||
       entry.fdaDecisionObserved!==false||
       entry.independentlyFdaConfirmed!==false||
       entry.clinicalScientificSignoff!==false){
      throw new Error("FOCUS_NEAR_TERM_GOAL_CROSSWALK_MISMATCH_"+entry.cycleId);
    }
    used.add(entry.cycleId);
  }
  const priority=[...checks.entries].sort((a,b)=>a.reportedGoalDate.localeCompare(b.reportedGoalDate));
  const earliest=[...manifest.cycles].filter(c=>c.reportedPdufaGoal&&
    c.reportedPdufaGoal>=checks.asOf).sort((a,b)=>
      a.reportedPdufaGoal!.localeCompare(b.reportedPdufaGoal!)).slice(0,3);
  if(earliest.length!==3||earliest.some((c,i)=>c.cycleId!==priority[i].cycleId)){
    throw new Error("FOCUS_NEAR_TERM_SOURCE_CHECKS_NOT_EARLIEST_GOALS");
  }
  return <section data-testid="focus-near-term-issuer-goals"
    aria-label="Near-term source-checked PDUFA review targets"
    style={{border:"1px solid #bad4ce",borderRadius:13,background:"#f8fcfa",
      padding:"clamp(13px,2vw,20px)",marginBottom:21,color:"#22423a"}}>
    <div style={{fontSize:11,fontWeight:900,letterSpacing:".06em",color:"#236e60"}}>
      NEXT 3 REVIEW TARGETS · ORIGINAL ISSUER SOURCE READBACKS
    </div>
    <h2 style={{fontSize:20,margin:"7px 0 5px"}}>
      Earliest reported PDUFA goals · as of {checks.asOf}
    </h2>
    <p style={{fontSize:12,lineHeight:1.6,margin:"4px 0 13px",color:"#52675d"}}>
      <strong>3/23 application cycles</strong> have this added issuer-source goal-date readback.
      These sources confirm what issuers publicly reported, not a direct FDA
      confirmation, decision, independent scientific signoff, or validated prediction.
      The remaining cycles have not received this particular three-case source check.
    </p>
    <div style={{overflowX:"auto",borderRadius:9,border:"1px solid #d5e1dc",background:"#fff"}}>
      <table data-testid="focus-near-term-goal-table"
        style={{width:"100%",minWidth:660,borderCollapse:"collapse",fontSize:12}}>
        <thead style={{background:"#edf4f1"}}>
          <tr>{["Goal date","Ticker / application","Current research call","Issuer source evidence"].map(x=>
            <th key={x} scope="col" style={{padding:"10px 9px",textAlign:"left",
              borderBottom:"1px solid #c4d8d0"}}>{x}</th>)}</tr>
        </thead>
        <tbody>{priority.map(entry=>{
          const cycle=cycles.get(entry.cycleId)!;
          return <tr key={entry.cycleId} data-cycle={entry.cycleId}>
            <td style={{padding:10,verticalAlign:"top",borderBottom:"1px solid #e2ebe7",whiteSpace:"nowrap"}}>
              <strong>{entry.reportedGoalDate}</strong>
            </td>
            <td style={{padding:10,verticalAlign:"top",borderBottom:"1px solid #e2ebe7"}}>
              <strong>{entry.ticker}</strong> · {entry.drug}
              <div style={{fontSize:11,color:"#60746b",marginTop:4}}>{entry.indication}</div>
            </td>
            <td style={{padding:10,verticalAlign:"top",borderBottom:"1px solid #e2ebe7"}}>
              <strong>{readingLabels[cycle.call]}</strong>
              <div style={{fontSize:11,color:"#6a746c",marginTop:4}}>
                Preliminary · not independently validated
              </div>
            </td>
            <td style={{padding:10,verticalAlign:"top",borderBottom:"1px solid #e2ebe7"}}>
              <div style={{lineHeight:1.5}}>{entry.verifiedSourceClaim}</div>
              <a href={entry.primarySourceUrl} target="_blank"
                rel="noopener noreferrer" style={{display:"inline-block",marginTop:5,
                  color:"#075f55",fontWeight:750}}>
                View dated {entry.sourceType.replaceAll("_"," ")} ({entry.sourcePublicationDate})
              </a>
            </td>
          </tr>;
        })}</tbody>
      </table>
    </div>
    <p style={{fontSize:11,color:"#687469",lineHeight:1.6,margin:"10px 0 0"}}>
      Actual FDA action, review-clock extensions, or CMC findings must be checked
      separately if new evidence arrives. Nothing here updates the production
      approval/CRL engine, scientific grades or prediction accuracy.
    </p>
  </section>;
}
