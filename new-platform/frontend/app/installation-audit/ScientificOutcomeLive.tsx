"use client";

import { useState } from "react";
import { safeHopDiagnostic } from "../../lib/hop-source-diagnostic";
import { auditOutcomeSources, auditMedicalInventory, type OutcomeSourceStatus, type MedicalInventoryStatus } from "../../lib/installation-analysis-readiness";

const display = (v: number | null) => v === null ? "Not verified" : v.toLocaleString("en-US");

type EvidenceState<T> = { data: T | null; error: string };
export default function ScientificOutcomeLive() {
  const [science, setScience] = useState<EvidenceState<MedicalInventoryStatus>>({data:null,error:""});
  const [outcome, setOutcome] = useState<EvidenceState<OutcomeSourceStatus>>({data:null,error:""});
  const [checked, setChecked] = useState("");
  const [busy, setBusy] = useState(false);

  async function check() {
    if (busy) return;
    setBusy(true);
    setScience({data:null,error:""});
    setOutcome({data:null,error:""});
    setChecked("");
    const read = async (url: string, isHop = false) => {
      const response = await fetch(url, { cache:"no-store", signal: AbortSignal.timeout(50000) });
      if (!response.ok) {
        // The HOP proxy emits only an allowlisted, non-sensitive reason code.
        // Never render arbitrary upstream error/JSON text from the service.
        const payload: unknown = isHop ? await response.json().catch(() => null) : null;
        throw new Error(isHop
          ? safeHopDiagnostic(response.status, payload)
          : response.status === 401
          ? "Sign in to the dashboard to view protected evidence"
          : "Evidence endpoint unavailable (HTTP " + response.status + ")");
      }
      return response.json() as Promise<unknown>;
    };
    const [s, o] = await Promise.allSettled([
      read("/api/preview/deep-medical-intelligence").then(auditMedicalInventory),
      read("/api/hop/readiness", true).then(auditOutcomeSources),
    ]);
    setScience(s.status === "fulfilled" ? {data:s.value,error:""} : {data:null,error:s.reason instanceof Error ? s.reason.message : "Unable to verify scientific evidence"});
    setOutcome(o.status === "fulfilled" ? {data:o.value,error:""} : {data:null,error:o.reason instanceof Error ? o.reason.message : "Unable to verify historical outcome evidence"});
    setChecked(new Date().toISOString());
    setBusy(false);
  }
  return <section aria-label="SCIENCE and OUTCOME live evidence checks" style={{padding:"16px",border:"1px solid #39717b",borderRadius:10,background:"#0b3040",marginTop:22}}>
    <h2>SCIENCE and OUTCOME — protected evidence checks</h2>
    <p>Independent medical investigation and public FDA source readiness are separate from this page's dated installation snapshot. This check only reads evidence inventories; it does not start scans, replace completed installation records or certify a prediction.</p>
    <button type="button" disabled={busy} onClick={() => void check()} style={{cursor:busy?"wait":"pointer",border:"1px solid #5aa9ae",borderRadius:8,background:"#0b625c",padding:"10px 14px",color:"#e7f9fc",fontWeight:650}}>
      {busy ? "Checking source evidence…" : "Verify current SCIENCE + OUTCOME evidence"}
    </button>
    {checked && <p role="status">Check requested {new Date(checked).toLocaleString()} · results shown separately below. A successful API response does not certify scientific accuracy.</p>}
    <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(min(100%,320px),1fr))",gap:14,marginTop:14}}>
      <section aria-label="SCIENCE evidence status" style={{border:"1px solid #39717b",background:"#0a2c3b",padding:14,borderRadius:8}}>
        <h3>Deep Medical Intelligence · independent investigation</h3>
        <p><strong>Certification: NOT VERIFIED.</strong> Inventory coverage does not certify medical interpretation, application-level conclusions, or completion of the independent investigation.</p>
        {science.error && <p role="alert"><strong>Live evidence unavailable:</strong> {science.error}. No completion count is inferred.</p>}
        {science.data && <>
          <p><strong>POOL trials:</strong> {display(science.data.poolTrials)} · <strong>FOCUS trials:</strong> {display(science.data.focusTrials)} · <strong>Application targets:</strong> {display(science.data.applications)}.</p>
          <p><strong>Metadata screened:</strong> {display(science.data.metadataScreenedTrials)} · <strong>Source-extracted:</strong> {display(science.data.sourceExtractedTrials)} · <strong>Fully reviewed:</strong> {display(science.data.fullyReviewedTrials)}.</p>
          <p><strong>Incomplete trial investigations:</strong> {display(science.data.incompleteTrials)} · <strong>Completed candidate decisions:</strong> {display(science.data.completedDecisions)} · <strong>Cited documents:</strong> {display(science.data.sourceDocuments)}.</p>
          <p><small>Evidence snapshot: {science.data.asOf}. These are processing and source counts, not ratings or certified FDA outcomes.</small></p>
          <p><a href="/preview/deep-medical-intelligence">Open the independent medical evidence preview</a></p>
        </>}
        {!science.error && !science.data && <p>Live data not checked. Scientific completion cannot be inferred.</p>}
      </section>
      <section aria-label="OUTCOME evidence status" style={{border:"1px solid #39717b",background:"#0a2c3b",padding:14,borderRadius:8}}>
        <h3>OUTCOME · historical FDA validation</h3>
        <p><strong>Certification: NOT VALIDATED.</strong> FDA research archives are not a complete historical decision cohort. Approval probabilities must remain withheld until complete, source-supported FDA action-cycle labels, chronological holdouts, leakage checks and calibration pass.</p>
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
