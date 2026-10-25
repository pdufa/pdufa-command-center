"use client";

import { useState } from "react";
import { auditOutcomeStatus, auditScienceIndex, type OutcomeStatus, type ScienceStatus } from "../../lib/science-outcome-gates";

const display = (v: number | null) => v === null ? "Not verified" : v.toLocaleString("en-US");

type EvidenceState<T> = { data: T | null; error: string };
export default function ScientificOutcomeLive() {
  const [science, setScience] = useState<EvidenceState<ScienceStatus>>({data:null,error:""});
  const [outcome, setOutcome] = useState<EvidenceState<OutcomeStatus>>({data:null,error:""});
  const [checked, setChecked] = useState("");
  const [busy, setBusy] = useState(false);

  async function check() {
    if (busy) return;
    setBusy(true);
    setScience({data:null,error:""});
    setOutcome({data:null,error:""});
    setChecked("");
    const read = async (url: string) => {
      const response = await fetch(url, { cache:"no-store", signal: AbortSignal.timeout(50000) });
      if (!response.ok) throw new Error(response.status === 401 ? "Sign in to the dashboard to view protected evidence" : "Evidence endpoint unavailable (HTTP " + response.status + ")");
      return response.json() as Promise<unknown>;
    };
    const [s, o] = await Promise.allSettled([
      read("/api/assessments").then(auditScienceIndex),
      read("/api/hop/readiness").then(auditOutcomeStatus),
    ]);
    setScience(s.status === "fulfilled" ? {data:s.value,error:""} : {data:null,error:s.reason instanceof Error ? s.reason.message : "Unable to verify scientific evidence"});
    setOutcome(o.status === "fulfilled" ? {data:o.value,error:""} : {data:null,error:o.reason instanceof Error ? o.reason.message : "Unable to verify historical outcome evidence"});
    setChecked(new Date().toISOString());
    setBusy(false);
  }
  return <section aria-label="SCIENCE and OUTCOME live evidence checks" style={{padding:"16px 0",borderTop:"1px solid #cbd5e1",marginTop:22}}>
    <h2>SCIENCE and OUTCOME — protected evidence checks</h2>
    <p>The current scientific scoring index and historical FDA readiness are separate from this page's dated installation snapshot. Running this check only reads protected data: it does not start scans, write scores, change FS/FA presets or place orders.</p>
    <button type="button" disabled={busy} onClick={() => void check()} style={{cursor:busy?"wait":"pointer",border:"1px solid #334155",borderRadius:8,background:"#f1f5f9",padding:"10px 14px",color:"#0f172a",fontWeight:650}}>
      {busy ? "Checking source evidence…" : "Verify current SCIENCE + OUTCOME evidence"}
    </button>
    {checked && <p role="status">Check requested {new Date(checked).toLocaleString()} · results shown separately below. A successful API response does not certify scientific accuracy.</p>}
    <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(min(100%,320px),1fr))",gap:14,marginTop:14}}>
      <section aria-label="SCIENCE evidence status" style={{border:"1px solid #cbd5e1",padding:14,borderRadius:8}}>
        <h3>SCIENCE · 40 investigations</h3>
        <p><strong>Certification: NOT VERIFIED.</strong> The existing three seven-category research scores do not establish completion of the separately required 40 scientific investigations or independent clinical review.</p>
        {science.error && <p role="alert"><strong>Live evidence unavailable:</strong> {science.error}. No completion count is inferred.</p>}
        {science.data && <>
          <p><strong>Exact candidate IDs:</strong> {display(science.data.total)} · <strong>Registry-linked:</strong> {display(science.data.registryLinked)} · <strong>Unlinked:</strong> {display(science.data.registryMissing)}.</p>
          <p><strong>Existing score coverage (not SCIENCE-40):</strong></p>
          <table style={{width:"100%",borderCollapse:"collapse"}}>
            <thead><tr><th scope="col" style={{textAlign:"left"}}>Model</th><th scope="col">Complete</th><th scope="col">Partial</th><th scope="col">Missing</th></tr></thead>
            <tbody>{(["PIPELINE","GEM_JR","GEM"] as const).map(stage => <tr key={stage}><th scope="row" style={{textAlign:"left"}}>{stage.replaceAll("_"," ")}</th><td style={{textAlign:"center"}}>{display(science.data!.scores[stage].complete)}</td><td style={{textAlign:"center"}}>{display(science.data!.scores[stage].partial)}</td><td style={{textAlign:"center"}}>{display(science.data!.scores[stage].missing)}</td></tr>)}</tbody>
          </table>
          <p><small>Snapshot: {science.data.asOf}; computed {science.data.computedAt}. Analyst-review source: {science.data.reviewSource}. Counts are score coverage, not verified trial outcomes.</small></p>
        </>}
        {!science.error && !science.data && <p>Live data not checked. Scientific completion cannot be inferred.</p>}
      </section>
      <section aria-label="OUTCOME evidence status" style={{border:"1px solid #cbd5e1",padding:14,borderRadius:8}}>
        <h3>OUTCOME · historical FDA validation</h3>
        <p><strong>Certification: NOT VALIDATED.</strong> FDA research archives are not a complete historical decision cohort. Approval probabilities must remain withheld until independent review-cycle labels, chronological holdouts, leakage checks and calibration pass.</p>
        {outcome.error && <p role="alert"><strong>Live evidence unavailable:</strong> {outcome.error}. Historical verification counts are withheld.</p>}
        {outcome.data && <>
          <p><strong>Published FDA letters:</strong> {display(outcome.data.publishedLetters)} · <strong>Approved-product registry records:</strong> {display(outcome.data.approvedApplications)}.</p>
          <p><strong>FDA page-review worklist:</strong> {display(outcome.data.sourcePageReviewRows)} · <strong>Independently verified review-cycle outcomes:</strong> {display(outcome.data.independentlyVerifiedReviewCycles)}.</p>
          <p><strong>Model-eligible review cycles:</strong> 0 · <strong>Calibrated prediction:</strong> BLOCKED.</p>
          <p><small>Evidence checked {new Date(outcome.data.checkedAt).toLocaleString()}. Source counts cannot be used as an approval denominator.</small></p>
        </>}
        {!outcome.error && !outcome.data && <p>Live FDA evidence not checked. No calibrated outcome is inferred.</p>}
      </section>
    </div>
  </section>;
}
