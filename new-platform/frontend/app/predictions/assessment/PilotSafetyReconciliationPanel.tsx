import pilot from "../../../data/acacia-pilot-prediction-workup-20261108.json";
import {evaluateAcaciaSafetyResearch} from "../../../lib/acacia-safety-reconciliation";
export default function PilotSafetyReconciliationPanel({nct}:{nct:string}){
  if(nct!=="NCT06081894"||pilot.nct!==nct)return null;
  const result=evaluateAcaciaSafetyResearch(pilot);
  return <section aria-label="ACACIA independent safety-source reconciliation research" style={{border:"1px solid #a2c4bc",background:"#f4f8f8",borderRadius:11,padding:14,margin:"12px 0"}}>
    <h3 style={{margin:"3px 0 8px"}}>Source-specific safety uncertainty · reconciliation still open</h3>
    {!result?<p role="alert">Exact trial, source, or review-status mismatch: safety calculations withheld.</p>:<>
      <p style={{fontSize:13}}>Unadjusted source-reported counts, not causal findings, official 0–5 clinical grades or FDA probabilities. Source snapshot: {result.sourceSnapshot}.</p>
      <div style={{overflowX:"auto"}}>
        <table style={{borderCollapse:"collapse",minWidth:600,width:"100%",fontSize:12}}>
          <thead><tr>{["Source-specific outcome","Treated","Placebo","Difference (pp)","Risk ratio (approx. 95% CI)"].map(k=><th key={k} style={{textAlign:"left",padding:7,borderBottom:"2px solid #adbfbb"}}>{k}</th>)}</tr></thead>
          <tbody>{result.contrasts.map(r=><tr key={r.id}>
            <td style={{padding:7,borderBottom:"1px solid #dae6e1"}}><a href={r.sourceUrl} target="_blank" rel="noopener noreferrer">{r.label}</a>{r.kind==="PIVOTAL"?null:<div>Separate report — not reconciled</div>}</td>
            <td style={{padding:7}}>{r.a}/258</td><td style={{padding:7}}>{r.b}/259</td>
            <td style={{padding:7}}>+{r.differencePp}</td>
            <td style={{padding:7}}>{r.relativeRisk} ({r.approximate95[0]}–{r.approximate95[1]})</td>
          </tr>)}</tbody>
        </table>
      </div>
      <details style={{marginTop:12,padding:10,border:"1px solid #bdd3cd",borderRadius:8,background:"#fff"}}>
        <summary style={{cursor:"pointer",fontWeight:800}}>Investigate sponsor 12/3 versus secondary paper 11/1</summary>
        <p style={{fontSize:13}}>The October 12 sponsor release describes 2 treated heart-failure serious events associated with reduced LVEF plus 10 additional treated heart-failure serious events, internally totaling 12 treated participants versus 3 placebo participants.</p>
        <p style={{fontSize:13}}>The secondary report separately says 11 vs 1. Differing event coding, analysis populations or follow-up windows are possible, but unverified. These cannot be merged or called the same outcome. <strong>NOT RECONCILED.</strong></p>
        <p style={{fontSize:13}}>A printed treatment-interruption line of <strong>14 (2.7%)</strong> differs from 14/258 = <strong>{result.interruption.randomizedDenominatorPercent}%</strong>. The actual original safety denominator or correction is not established.</p>
      </details>
      <p style={{fontSize:12,marginBottom:0}}>Risk-ratio intervals use a simple approximate log/Katz formula and randomized counts; sparse placebo events produce uncertain estimates. Original safety sets, final locked SAP and qualified review are still required. <strong>Clinical grade: UNASSIGNED · FDA: ABSTAIN · Accuracy: NOT CALIBRATED.</strong></p>
    </>}
  </section>;
}
