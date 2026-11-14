import Link from "next/link";

/** Shared disclosure only. This must not be mistaken for live trial scoring. */
export default function ScientificStepsReadiness({cohort}:{cohort:"POOL"|"FOCUS"|"PAST"}) {
 const steps=[
  ["1","Trial phase and status","Registry phase/status and chronological source verification"],
  ["2","Phase-appropriate evidence","Expected, missing, not-yet-expected, and unreviewed source inventory"],
  ["3","Endpoint scientific review","Endpoint definition and evidence-backed scientific judgments"],
 ];
 return <section aria-label="Scientific assessment steps 1 through 3" data-testid="scientific-steps-readiness"
  style={{border:"1px solid #b9cebe",borderRadius:8,padding:14,margin:"16px 0",color:"#173d2b"}}>
  <h2 style={{fontSize:18,margin:"0 0 8px"}}>Scientific assessment · Steps 1–3</h2>
  <p style={{margin:"0 0 10px"}}><strong>{cohort}:</strong> Integration pending. The backend has a phase-first intake framework; this page does not yet receive verified per-trial Level 1 results. No score or FDA prediction is implied.</p>
  <ol style={{margin:"0 0 10px",paddingLeft:22}}>
   {steps.map(([n,name,description])=><li key={n} style={{marginBottom:6}}><strong>{name} — Not live</strong><span style={{display:"block",fontSize:13}}>{description}</span></li>)}
  </ol>
  <p style={{fontSize:13,margin:0}}>Activation requires exact-NCT data binding, phase-appropriate source review, passing tests, and production verification. <Link href="/analyze-now">Research workspace</Link> may show separate saved research; it does not establish these steps are active.</p>
 </section>;
}
