import Link from "next/link";
import {MAIN_DAILY_EVIDENCE} from "../../lib/main-daily-evidence";
import {calculateProgress} from "../../lib/daily-system-progress";
import {MAIN_DAILY_EVIDENCE} from "../../lib/main-daily-evidence";

const history = MAIN_DAILY_EVIDENCE.history;
const current = history.at(-1) ?? null;
const previous = history.at(-2) ?? null;

/** A missing independently verified denominator is NOT a zero-percent result. */
const systems = [
  {name:"SCIENCE",description:"40 source-verified scientific investigations per exact trial",reason:"The complete trial-by-trial SCIENCE-40 numerator and denominator are not independently certified."},
  {name:"OUTCOME",description:"Model-eligible FDA decision review cycles in a complete historical cohort",reason:"A complete historical review-cycle denominator and validated prediction outcomes are not established."},
  {name:"MAIN",description:"Verified gates in the fixed MAIN / Core Platform inventory of 31 checks",reason:"The MAIN baseline is withheld if any inventory identity, dated observation or deployment proof fails validation."},
] as const;

export default function DailySystemProgress() {
  return <section aria-labelledby="daily-system-progress" style={{border:"2px solid #334155",borderRadius:12,padding:18,background:"#f8fafc",margin:"20px 0"}}>
    <h2 id="daily-system-progress" style={{marginTop:0}}>Daily progress · SCIENCE / OUTCOME / MAIN</h2>
    <p>Each percentage counts verified units in its stated inventory. MAIN uses 31 Core Platform gates across 8 sections; it measures documented gate verification, not engineering effort. Daily change requires matching inventories on adjacent Pacific dates. Missing verification is <strong>not 0%</strong>.</p>
    <p style={{border:"1px solid #94a3b8",padding:12,borderRadius:8,background:"#fff"}}><strong>MAIN verified gate baseline:</strong> {MAIN_DAILY_EVIDENCE.valid ? (MAIN_DAILY_EVIDENCE.verified / MAIN_DAILY_EVIDENCE.total * 100).toFixed(1)+"%" : "Not verified"} · {MAIN_DAILY_EVIDENCE.verified}/{MAIN_DAILY_EVIDENCE.total} gates verified · {MAIN_DAILY_EVIDENCE.total-MAIN_DAILY_EVIDENCE.verified}/{MAIN_DAILY_EVIDENCE.total} gates remain open · {MAIN_DAILY_EVIDENCE.acceptedSections}/{MAIN_DAILY_EVIDENCE.sections} sections fully accepted · 2026-10-26. Daily change awaits a comparable prior-day snapshot. This dated research-only evidence does not automatically refresh; it is not total MAIN completion.</p>
    <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(min(100%,240px),1fr))",gap:12}}>
      {systems.map(s=>{const progress = calculateProgress(s.name,previous,current,history); return <article key={s.name} aria-label={s.name+" daily completion"} style={{background:"#fff",border:"1px solid #cbd5e1",borderRadius:9,padding:14}}>
        <h3 style={{margin:"0 0 8px"}}>{s.name}</h3>
        <p style={{fontSize:28,fontWeight:750,margin:"4px 0"}}>{progress.percent === null ? "Not verified" : progress.percent.toFixed(1)+"%"}</p>
        <p><strong>Today:</strong> {progress.percent === null ? "—" : progress.percent.toFixed(1)+"%"} &nbsp; <strong>Change:</strong> {progress.changePp === null ? "—" : (progress.changePp >= 0 ? "+" : "")+progress.changePp.toFixed(1)+" pp"}</p>
        <p><strong>Remaining to 100%:</strong> {progress.remainingPp === null ? "Not verified" : progress.remainingPp.toFixed(1)+" pp"}</p>
        <p><strong>Estimated time to 100%:</strong> {progress.etaDays === null ? "Not available — requires at least 7 days of comparable, verified progress." : progress.etaDays+" days (approx. "+progress.etaDate+")"}</p>
        <p style={{fontSize:13}}>{s.description}</p>
        {s.name === "MAIN" && MAIN_DAILY_EVIDENCE.valid ? <>
          <p><strong>{MAIN_DAILY_EVIDENCE.verified}/{MAIN_DAILY_EVIDENCE.total} gates verified</strong> · {MAIN_DAILY_EVIDENCE.total-MAIN_DAILY_EVIDENCE.verified}/{MAIN_DAILY_EVIDENCE.total} remain open.</p>
          <p style={{fontSize:13}}>Saved baseline: <time dateTime={current!.asOf}>{current!.asOf}</time> · Pacific. {MAIN_DAILY_EVIDENCE.acceptedSections}/{MAIN_DAILY_EVIDENCE.sections} sections fully accepted. {progress.changePp === null ? "Daily change awaits a comparable prior-day snapshot." : "Daily change compares verified gates."}</p>
          <details><summary>Evidence and remaining MAIN checks</summary>
            <p>{MAIN_DAILY_EVIDENCE.signals} code/deployment signals · {MAIN_DAILY_EVIDENCE.partial} partial · {MAIN_DAILY_EVIDENCE.unverified} unverified. Only the exact production deployment gate is verified by this baseline.</p>
            <p>This dated snapshot does not automatically refresh. A new observation requires its own dated proof; the existing nightly scan schedule is unchanged.</p>
            <div style={{overflowX:"auto"}}><table style={{fontSize:12,borderCollapse:"collapse",minWidth:360,width:"100%"}}>
              <thead><tr><th scope="col" style={{textAlign:"left",padding:6}}>MAIN check</th><th scope="col" style={{textAlign:"left",padding:6}}>Dated status</th></tr></thead>
              <tbody>{MAIN_DAILY_EVIDENCE.observations.map(o => <tr key={o.id}>
                <th scope="row" style={{textAlign:"left",padding:6,borderTop:"1px solid #e2e8f0",fontWeight:500}}><a href={o.evidenceUri} target="_blank" rel="noopener noreferrer">{o.id}</a><div style={{fontWeight:400}}>{o.note}</div></th>
                <td style={{padding:6,borderTop:"1px solid #e2e8f0",verticalAlign:"top"}}>{o.status}</td>
              </tr>)}</tbody>
            </table></div>
          </details>
        </> : <details><summary>Why no percentage?</summary><p>{s.reason}</p>{s.name === "MAIN" ? <p>{MAIN_DAILY_EVIDENCE.reason}</p> : null}</details>}
      </article>})}
    </div>
    <p style={{fontSize:13,marginBottom:0}}>ETA requires eight comparable daily observations spanning seven days, with positive progress and no regression. It is an extrapolation, not a deadline. Prediction accuracy is separate and remains <strong>not validated</strong>. <Link href="/prediction-pilot">View the sourced GEM research pilot</Link>.</p>
  </section>;
}
