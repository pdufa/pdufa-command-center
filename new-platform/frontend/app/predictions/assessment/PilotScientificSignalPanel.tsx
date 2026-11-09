import pilot from "../../../data/acacia-pilot-prediction-workup-20261108.json";
import {evaluatePilotScientificSignals} from "../../../lib/acacia-quantitative-science";

const frame={border:"1px solid #a5c3bc",borderRadius:12,padding:14,background:"#fff",margin:"12px 0"} as const;
const soft={border:"1px solid #d0e0dc",borderRadius:9,padding:10,background:"#f6faf9"} as const;
export default function PilotScientificSignalPanel({nct}:{nct:string}){
  if(nct!=="NCT06081894"||pilot.nct!==nct)return null;
  const report=evaluatePilotScientificSignals(pilot);
  return <section style={{...frame,background:"#f3f9f7"}} aria-label="Provisional quantitative scientific evidence analysis">
    <h3 style={{margin:"2px 0 8px"}}>Quantitative scientific evidence · first two research methods</h3>
    <p style={{fontSize:13,margin:"4px 0 12px"}}>
      Evidence from the <strong>published Phase III study</strong> is analyzed separately from
      the five-gate documentary-readiness scores. These numbers are <strong>reproducible
      descriptive findings, not independent clinical grades or FDA probabilities</strong>.
    </p>
    {!report?<p role="alert" style={{fontWeight:700}}>SOURCE MISMATCH: quantitative research analysis withheld. Verify original trial, source identity, denominators and review state.</p>:
    <>
      <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(230px,1fr))",gap:10}}>
        <article style={soft}>
          <strong>Assessment 5.1 · Scientific method 12</strong>
          <p style={{fontSize:12,margin:"5px 0"}}>Published co-primary endpoint estimates and confidence intervals</p>
          <div style={{fontSize:27,fontWeight:850,color:"#1e5b50"}}>{report.positivePublishedEndpointSignals} / {report.primaryEndpointSignalsOutOf}</div>
          <p style={{fontSize:12,margin:"0 0 8px"}}>Published endpoint confidence intervals exclude zero in the reported favorable direction, and reported P values meet the sponsor's stated 0.025 criterion. This is a <strong>directional statistical count, not a 0–5 efficacy grade</strong>.</p>
          <table style={{width:"100%",fontSize:12,borderCollapse:"collapse"}}>
            <thead><tr><th style={{textAlign:"left"}}>Endpoint</th><th style={{textAlign:"right"}}>Effect (95% CI)</th></tr></thead>
            <tbody>{report.endpoints.map(e=><tr key={e.id}>
              <td style={{padding:"6px 3px"}}>{e.label}</td>
              <td style={{textAlign:"right",padding:"6px 3px"}}>+{e.estimate} [{e.ci95[0]}, {e.ci95[1]}] {e.unit}<div>P={e.reportedP}</div></td>
            </tr>)}</tbody>
          </table>
          <details style={{fontSize:12,marginTop:7}}>
            <summary style={{cursor:"pointer",fontWeight:700}}>Method, uncertainty and original publication</summary>
            {report.endpoints.map(e=><p key={e.id}>{e.label}: approximate standard error {e.approximateStandardError} {e.unit}, calculated from the rounded 95% interval width ÷ 3.92. This cannot reproduce the exact SAP-based standard error.</p>)}
            <a href={report.endpoints[0].sourceUrl} target="_blank" rel="noopener noreferrer">Read peer-reviewed primary report</a>
          </details>
        </article>
        <article style={soft}>
          <strong>Assessment 5.3 · Scientific method 19</strong>
          <p style={{fontSize:12,margin:"5px 0"}}>Exact-arm safety percentages and unadjusted differences</p>
          <div style={{fontSize:27,fontWeight:850,color:"#955121"}}>{report.treatedArmExcessInDescriptiveSafety} / {report.safetyOutOf}</div>
          <p style={{fontSize:12,margin:"0 0 8px"}}>Two prespecified descriptive safety categories have numerically higher treated-arm frequencies. This is <strong>not a causal risk score or a statistical significance test</strong>.</p>
          <table style={{width:"100%",fontSize:12,borderCollapse:"collapse"}}>
            <thead><tr><th style={{textAlign:"left"}}>Safety outcome</th><th style={{textAlign:"right"}}>Treated / placebo</th></tr></thead>
            <tbody>{report.safety.map(s=><tr key={s.id}>
              <td style={{padding:"6px 3px"}}>{s.id==="LVEF_BELOW_50_PERCENT"?"LVEF below 50%":"Any serious AE"}</td>
              <td style={{textAlign:"right",padding:"6px 3px"}}>
                {s.treated}/{s.treatedN} vs {s.control}/{s.controlN}
                <div>{s.treatedRatePercent}% vs {s.controlRatePercent}%</div>
                <strong>+{s.absoluteDifferencePp} pp</strong>
              </td>
            </tr>)}</tbody>
          </table>
          <p style={{fontSize:12,margin:"8px 0 0"}}><strong>Unresolved HF SAE reports:</strong> 11/1 vs 12/3 across separate sources. Not added to this count pending event definition and follow-up reconciliation.</p>
          <a href={report.safety[0].sourceUrl} target="_blank" rel="noopener noreferrer" style={{fontSize:12}}>Read published safety outcomes</a>
        </article>
      </div>
      <details style={{...frame,marginBottom:0,background:"#fff"}} aria-label="Scientific signal validation gates">
        <summary style={{fontWeight:750,cursor:"pointer"}}>Why official 0–5 scientific grades are still withheld</summary>
        <ul>{report.limitations.map((v,i)=><li key={i} style={{fontSize:13,margin:"5px 0"}}>{v}</li>)}</ul>
        <p style={{fontSize:12,marginBottom:0}}>
          Current phase reported: Phase III, independent phase signoff still pending. Final locked SAP
          verified: NO. Independent clinical-importance review: NO.
          <strong> Official clinical method grade: UNSCORED. Final FDA prediction: ABSTAIN.
          Calibrated accuracy: NOT AVAILABLE.</strong> The dated research snapshot is {report.asOf}.
        </p>
      </details>
    </>}
  </section>;
}
