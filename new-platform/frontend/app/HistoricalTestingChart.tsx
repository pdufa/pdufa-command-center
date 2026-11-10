import freeze from "../data/levelThreeOutcomeAwareRerunFreeze2026.json";
import compared from "../data/levelThreeOutcomeAwareRerunComparison2026.json";
import quarantine from "../data/historicalOutcomeAwareQuarantine2026.json";
import ChartTrendInset,{cumulativeDatedAgreement} from "./ChartTrendInset";

const spreadsheetUrl="https://docs.google.com/spreadsheets/d/1erY_z62b4mHhx5s_3HgJxXoJEslbLngMuQNfhcuSviU/edit";
const ink="#23463f";
const muted="#536b66";

function labelDirection(value:string):string{
  return value==="APPROVAL"?"Approval":value==="CRL"?"CRL":value;
}

/**
 * Isolated audit visualization only.
 *
 * The user expressly requested a separate historical testing chart on Nov 9.
 * This does not feed the active assessment level chart, FOCUS scoring,
 * prediction accuracy, calibration, or any scan/prediction worker.
 */
export default function HistoricalTestingChart(){
  if(freeze.dataset!=="POST_OUTCOME_EVIDENCE_CUTOFF_LEVEL3_REASSESSMENTS_EXCLUDED"||
     freeze.blind!==false||
     freeze.validForIndependentPredictionAccuracy!==false||
     compared.notBlind!==true||
     compared.notValidForAccuracy!==true||
     compared.notValidForCalibration!==true||
     compared.assessmentFreezeCommit!=="19aefeff35590a32f6ca9e6988c536368c421b2c"||
     quarantine.quarantined.length!==4){
    throw new Error("HISTORICAL_TESTING_MUST_REMAIN_UNVALIDATED_AUDIT_ONLY");
  }
  const rows=freeze.caseStudies.map(item=>{
    const observed=compared.caseComparisons.find(x=>x.caseId===item.caseId);
    if(!observed||observed.ticker!==item.ticker||
       observed.frozenPrediction!==item.prediction||
       item.actualOutcome!==null||
       item.actualActionDate!==null||
       item.excludedFromProspectiveAccuracy!==true||
       item.excludedFromRetrospectiveBlindValidation!==true||
       item.excludedFromCalibration!==true||
       observed.didMatch!==(observed.fdaDecision===item.prediction)||
       !quarantine.quarantined.some(x=>x.ticker===item.ticker)){
      throw new Error("HISTORICAL_TESTING_CASE_IDENTITY_OR_QUARANTINE_ERROR");
    }
    return {research:item,actual:observed};
  });
  const matches=rows.filter(x=>x.actual.didMatch).length;
  const misses=rows.length-matches;
  if(rows.length!==4||matches!==compared.rawMatches||rows.length!==compared.total){
    throw new Error("HISTORICAL_TESTING_TOTALS_INVALID");
  }
  const pct=Math.round(matches/rows.length*100);
  const archiveTrend=cumulativeDatedAgreement(rows.map(x=>({date:x.actual.fdaActionDate,matched:x.actual.didMatch})));
  return <section aria-label="Historical Testing Level 3 retrospective chart and data"
    data-testid="historical-testing-chart"
    style={{border:"1px solid #c6d9d3",background:"#fff",borderRadius:14,
      padding:"clamp(14px,2.5vw,22px)",margin:"0 0 22px",color:ink}}>
    <div style={{fontSize:11,letterSpacing:".08em",fontWeight:800,color:"#357565"}}>
      HISTORICAL TESTING · SEPARATE RESEARCH-ONLY DISPLAY
    </div>
    <h2 style={{fontSize:21,margin:"7px 0 5px"}}>Level 3 retrospective comparisons</h2>
    <p style={{fontSize:13,lineHeight:1.6,color:muted,margin:"0 0 12px"}}>
      Four manual Level 3-style assessments made using predecision-dated evidence.
      The FDA outcomes were already known to the evaluator, so these are
      <strong> not blind predictions</strong>. The figures below are directional
      agreement only, not validated model accuracy.
    </p>
    <div style={{display:"flex",flexWrap:"wrap",gap:20,alignItems:"center",
      background:"#f8fbfa",border:"1px solid #e2eae6",padding:15,
      borderRadius:11,margin:"12px 0 18px"}}>
      <div role="img" aria-label={`Retrospective direction match chart: ${matches} matched and ${misses} missed of ${rows.length}; not blind`}
        data-testid="historical-testing-donut"
        style={{width:150,height:150,borderRadius:"50%",flexShrink:0,
          background:`conic-gradient(#2f806b 0deg ${matches/rows.length*360}deg, #bd8b47 ${matches/rows.length*360}deg 360deg)`,
          display:"grid",placeItems:"center"}}>
        <div style={{width:114,height:114,borderRadius:"50%",background:"#fff",
          display:"flex",flexDirection:"column",alignItems:"center",justifyContent:"center"}}>
          <strong style={{fontSize:31,color:"#285a4e",lineHeight:1.1}}>{pct}%</strong>
          <span style={{fontSize:10,color:"#6a7a75",fontWeight:800,textAlign:"center"}}>RETROSPECTIVE MATCH</span>
        </div>
      </div>
      <div style={{display:"grid",gap:9,flex:"1 1 250px"}}>
        <div style={{display:"flex",gap:8,alignItems:"center",fontSize:14}}>
          <span aria-hidden="true" style={{width:13,height:13,borderRadius:3,background:"#2f806b"}}/>
          <strong>{matches} matched</strong><span style={{color:muted}}>FDA direction</span>
        </div>
        <div style={{display:"flex",gap:8,alignItems:"center",fontSize:14}}>
          <span aria-hidden="true" style={{width:13,height:13,borderRadius:3,background:"#bd8b47"}}/>
          <strong>{misses} missed</strong><span style={{color:muted}}>FDA direction</span>
        </div>
        <div style={{fontSize:12,color:"#916126",lineHeight:1.5,fontWeight:750}}>
          Validated blind accuracy: NOT ESTABLISHED · 0 valid blind cases
        </div>
      </div>
    </div>
    <ChartTrendInset title="Archived four-case cumulative Level 3 trend"
      testId="four-case-historical-donut-trend" kind="retrospective" points={archiveTrend}
      emptyText="Fewer than two dated FDA decisions are available in this archived group."/>
    <div style={{overflowX:"auto",borderRadius:9,border:"1px solid #e2eae6"}}>
      <table data-testid="historical-testing-data"
        style={{width:"100%",borderCollapse:"collapse",fontSize:12,minWidth:760}}>
        <thead>
          <tr style={{background:"#edf3f1",textAlign:"left"}}>
            {["Trial / ticker","Review level","Frozen direction","FDA decision","FDA action","Direction match","Source"].map(h=>
              <th key={h} scope="col" style={{padding:"10px 8px",color:"#355b52",fontWeight:800,
                borderBottom:"1px solid #d4e1db",whiteSpace:"nowrap"}}>{h}</th>)}
          </tr>
        </thead>
        <tbody>
          {rows.map(({research,actual},idx)=>
            <tr key={research.caseId} style={{background:idx%2?"#f8fbfa":"#fff"}}>
              <td style={{padding:"11px 8px",borderBottom:"1px solid #e9eeeb"}}>
                <strong style={{display:"block"}}>{research.ticker} · {research.drug}</strong>
                <span style={{fontSize:11,color:muted}}>{research.trialIds.join(", ")}</span>
              </td>
              <td style={{padding:"11px 8px",whiteSpace:"nowrap",borderBottom:"1px solid #e9eeeb"}}>Level 3-style</td>
              <td style={{padding:"11px 8px",fontWeight:700,borderBottom:"1px solid #e9eeeb"}}>
                {labelDirection(research.prediction)} lean
              </td>
              <td style={{padding:"11px 8px",borderBottom:"1px solid #e9eeeb"}}>
                {labelDirection(actual.fdaDecision)}
              </td>
              <td style={{padding:"11px 8px",whiteSpace:"nowrap",borderBottom:"1px solid #e9eeeb"}}>
                {actual.fdaActionDate}
              </td>
              <td style={{padding:"11px 8px",fontWeight:800,
                color:actual.didMatch?"#246f52":"#a05b2c",borderBottom:"1px solid #e9eeeb"}}>
                {actual.didMatch?"Match":"Miss"}
              </td>
              <td style={{padding:"11px 8px",borderBottom:"1px solid #e9eeeb"}}>
                <a href={actual.fdaSource} target="_blank" rel="noopener noreferrer"
                   style={{color:"#137565",whiteSpace:"nowrap"}}>FDA result</a>
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
    <p style={{fontSize:12,lineHeight:1.6,color:"#8b5e25",margin:"12px 0 0",fontWeight:700}}>
      The {pct}% historical agreement is not an estimate of future approval-prediction reliability,
      and it is never added to FOCUS outcomes, live forecast accuracy or calibration.
    </p>
    <p style={{fontSize:12,lineHeight:1.7,margin:"10px 0 0"}}>
      <a href={spreadsheetUrl} target="_blank" rel="noopener noreferrer" style={{color:"#137565",fontWeight:700}}>
        Open Historical Testing data in PDUFA Master Scan Data
      </a>
      {" · "}
      <a href={compared.assessmentFreezeUrl} target="_blank" rel="noopener noreferrer"
        style={{color:"#137565"}}>Timestamped original review freeze</a>
    </p>
  </section>;
}
