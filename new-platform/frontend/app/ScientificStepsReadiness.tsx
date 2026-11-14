import Link from "next/link";

/** Shared disclosure only. This must not be mistaken for live trial scoring. */
export type PhaseFirstIntake = {
 executionStatus:"INTAKE_ONLY"|"BLOCKED_UNVERIFIED_PHASE";
 phase:string|null;
 trialStatus:string|null;
 evidenceInventory:Record<string,string>;
 notYetExpected:string[];
 missingEvidence:string[];
 endpointQuality:{definitionCompleteness:string;reviewCoverage?:{status:string};scientificScoreStatus:string};
 fdaPrediction:"ABSTAIN";
};

/** Optional data is accepted only when bound to the exact trial by the caller. */
export default function ScientificStepsReadiness({cohort,trial}:{cohort:"POOL"|"FOCUS"|"PAST";trial?:{nctId:string;intake:PhaseFirstIntake}}) {
 const intake=trial?.intake;
 const phaseVerified=intake?.executionStatus==="INTAKE_ONLY";
 const steps=[
  ["1","Trial phase and status",phaseVerified? `${intake.phase} · ${intake.trialStatus}`:"Registry phase/status and chronological source verification"],
  ["2","Phase-appropriate evidence",intake?Object.entries(intake.evidenceInventory).map(([name,status])=>`${name}: ${status}`).join("; "):"Expected, missing, not-yet-expected, and unreviewed source inventory"],
  ["3","Endpoint scientific review",intake?`Definition: ${intake.endpointQuality.definitionCompleteness}; review: ${intake.endpointQuality.reviewCoverage?.status??"NOT_REVIEWED"}; score: ${intake.endpointQuality.scientificScoreStatus}`:"Endpoint definition and evidence-backed scientific judgments"],
 ];
 return <section aria-label="Scientific assessment steps 1 through 3" data-testid="scientific-steps-readiness"
  style={{border:"1px solid #b9cebe",borderRadius:8,padding:14,margin:"16px 0",color:"#173d2b"}}>
  <h2 style={{fontSize:18,margin:"0 0 8px"}}>Scientific assessment · Steps 1–3</h2>
  <p style={{margin:"0 0 10px"}}><strong>{cohort}:</strong> {intake&&trial?
    `Exact trial ${trial.nctId} · ${phaseVerified?"Registry intake available; scientific validation pending":"Phase verification blocked"} · FDA prediction ABSTAIN.`:
    "Integration pending. The backend has a phase-first intake framework; this page does not yet receive verified per-trial Level 1 results. No score or FDA prediction is implied."}</p>
  <ol style={{margin:"0 0 10px",paddingLeft:22}}>
   {steps.map(([n,name,description])=><li key={n} style={{marginBottom:6}}><strong>{name} — {intake?"Intake only; not scientifically validated":"Not live"}</strong><span style={{display:"block",fontSize:13}}>{description}</span></li>)}
  </ol>
  {intake&&<p style={{fontSize:13}}>Not yet expected: {intake.notYetExpected.join("; ")||"None listed"}. Missing: {intake.missingEvidence.join("; ")||"None recorded"}.</p>}
  <p style={{fontSize:13,margin:0}}>Activation requires exact-NCT data binding, phase-appropriate source review, passing tests, and production verification. <Link href="/analyze-now">Research workspace</Link> may show separate saved research; it does not establish these steps are active.</p>
 </section>;
}
