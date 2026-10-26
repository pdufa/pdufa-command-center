import Link from "next/link";

/** A missing independently verified denominator is NOT a zero-percent result. */
const systems = [
  {name:"SCIENCE",description:"40 source-verified scientific investigations per exact trial",reason:"The complete trial-by-trial SCIENCE-40 numerator and denominator are not independently certified."},
  {name:"OUTCOME",description:"Model-eligible FDA decision review cycles in a complete historical cohort",reason:"A complete historical review-cycle denominator and validated prediction outcomes are not established."},
  {name:"MAIN",description:"Accepted production requirements in a frozen versioned inventory",reason:"The production acceptance inventory has not been fully certified against a fixed denominator."},
] as const;

export default function DailySystemProgress() {
  return <section aria-labelledby="daily-system-progress" style={{border:"2px solid #334155",borderRadius:12,padding:18,background:"#f8fafc",margin:"20px 0"}}>
    <h2 id="daily-system-progress" style={{marginTop:0}}>Daily progress · SCIENCE / OUTCOME / MAIN</h2>
    <p>Verified completion percentages and day-over-day changes will appear only when dated evidence snapshots use the same audited scope and denominator. Missing verification is <strong>not 0%</strong>.</p>
    <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(min(100%,240px),1fr))",gap:12}}>
      {systems.map(s=><article key={s.name} aria-label={s.name+" daily completion"} style={{background:"#fff",border:"1px solid #cbd5e1",borderRadius:9,padding:14}}>
        <h3 style={{margin:"0 0 8px"}}>{s.name}</h3>
        <p style={{fontSize:28,fontWeight:750,margin:"4px 0"}}>Not verified</p>
        <p><strong>Today:</strong> — &nbsp; <strong>Change:</strong> —</p>
        <p><strong>Remaining to 100%:</strong> Not verified</p>
        <p><strong>Estimated time to 100%:</strong> Not available — requires a verified completion baseline and sustained measured daily progress.</p>
        <p style={{fontSize:13}}>{s.description}</p>
        <details><summary>Why no percentage?</summary><p>{s.reason}</p></details>
      </article>)}
    </div>
    <p style={{fontSize:13,marginBottom:0}}>ETA is not a deadline or promise; it will only be calculated from comparable, dated measurements with positive observed progress. Prediction accuracy is separate and remains <strong>not validated</strong>. The previous 40% reasoning-maturity estimate is subjective and must not be displayed as verified completion. <Link href="/prediction-pilot">View the sourced GEM research pilot</Link>.</p>
  </section>;
}
