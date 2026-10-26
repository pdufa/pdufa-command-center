"use client";

import { useEffect, useRef, useState } from "react";
import { buildScientific800ReviewerHandoffCsv } from "../lib/scientific-800-reviewer-handoff";
import { compareScientific800ReviewerCsvs, type Scientific800LocalPairAudit } from "../lib/scientific-800-local-pair-audit";
import type { ScientificDepthMatrix } from "../lib/scientific-depth-review-csv";
import type { ScientificInputAudit } from "../lib/scientific-evidence-requirements-csv";

type ValidatedHandoff = {
  matrix: ScientificDepthMatrix;
  audit: ScientificInputAudit;
};

function record(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

/**
 * Preview-only, browser-local, blank review handoffs. There are no reviewer
 * credentials, uploads, signatures, source certification or scoring actions.
 */
export default function Scientific800Handoff({ exactId }: { exactId: string }) {
  const [validated, setValidated] = useState<ValidatedHandoff | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const current = useRef<AbortController | null>(null);
  const [reviewerAFile, setReviewerAFile] = useState<File | null>(null);
  const [reviewerBFile, setReviewerBFile] = useState<File | null>(null);
  const [localAudit, setLocalAudit] = useState<Scientific800LocalPairAudit | null>(null);
  const [localAuditError, setLocalAuditError] = useState("");
  const [comparingFiles, setComparingFiles] = useState(false);
  const auditRevision = useRef(0);
  const exactNct = /^TRIAL\|NCT[0-9]{8}$/.test(exactId);

  useEffect(() => {
    current.current?.abort();
    auditRevision.current++;
    setValidated(null);
    setReviewerAFile(null);
    setReviewerBFile(null);
    setLocalAudit(null);
    setLocalAuditError("");
    setComparingFiles(false);
    setLoading(false);
    setError("");
    return () => {
      current.current?.abort();
      auditRevision.current++;
    };
  }, [exactId]);

  async function inspectSourceInputs() {
    if (!exactNct) return;
    current.current?.abort();
    auditRevision.current++;
    setLocalAudit(null);
    setLocalAuditError("");
    setComparingFiles(false);
    const controller = new AbortController();
    current.current = controller;
    setValidated(null);
    setError("");
    setLoading(true);
    try {
      const response = await fetch(
        "/api/scientific-assessment?exact_id=" + encodeURIComponent(exactId),
        { cache: "no-store", signal: controller.signal },
      );
      if (response.status === 401) {
        throw new Error("Sign in to the PDUFA dashboard before requesting reviewer templates.");
      }
      if (!response.ok) {
        throw new Error("Isolated scientific source assessment unavailable (" + response.status + ").");
      }
      const responseJson: unknown = await response.json();
      if (!record(responseJson)
          || responseJson.exactId !== exactId
          || !record(responseJson.assessment)
          || responseJson.assessment.overall_score !== null
          || !record(responseJson.assessment.domains)
          || !Object.values(responseJson.assessment.domains).every(
            d => record(d) && d.score === null,
          )
          || !record(responseJson.investigation40)
          || !record(responseJson.readinessGrades)) {
        throw new Error("Scientific source integrity or exact trial identity was not verified.");
      }

      // Both full validators must accept the SAME exact-NCT archive. Their
      // output remains an unscored inventory, not independent human review.
      const matrix = responseJson.investigation40 as ScientificDepthMatrix;
      const audit = responseJson.readinessGrades as ScientificInputAudit;
      buildScientific800ReviewerHandoffCsv(matrix, audit, "A");
      buildScientific800ReviewerHandoffCsv(matrix, audit, "B");
      if (!controller.signal.aborted) setValidated({ matrix, audit });
    } catch {
      if (!controller.signal.aborted) {
        setError("Reviewer handoff unavailable: current exact-trial evidence inventory could not be validated.");
      }
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }

  function downloadBlank(slot: "A" | "B") {
    if (!validated) return;
    try {
      const csv = buildScientific800ReviewerHandoffCsv(validated.matrix, validated.audit, slot);
      const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = validated.matrix.nctId + "_scientific_800_reviewer_" + slot + "_blank.csv";
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 2000);
    } catch {
      setValidated(null);
      setError("Reviewer worksheet download blocked: source evidence validation failed.");
    }
  }

  /** Only reads user-selected files in this browser. No upload or saved review. */
  async function compareLocal800Worksheets() {
    if (!validated || !reviewerAFile || !reviewerBFile || comparingFiles) return;
    const token = ++auditRevision.current;
    setLocalAudit(null);
    setLocalAuditError("");
    setComparingFiles(true);
    try {
      const files = [reviewerAFile, reviewerBFile];
      if (files.some(file => file.size > 3 * 1024 * 1024 || file.size === 0)) {
        throw new Error("Worksheet file too large or empty.");
      }
      const [csvA, csvB] = await Promise.all(files.map(file => file.text()));
      if (token !== auditRevision.current) return;
      const comparison = compareScientific800ReviewerCsvs(
        validated.matrix, validated.audit, csvA, csvB,
      );
      if (token === auditRevision.current) setLocalAudit(comparison);
    } catch {
      if (token === auditRevision.current) {
        setLocalAuditError(
          "Comparison rejected: files are incomplete, cross-trial, malformed or contain altered verification claims.",
        );
      }
    } finally {
      if (token === auditRevision.current) setComparingFiles(false);
    }
  }

  return <section aria-label="Independent 800-point reviewer handoff" className="panel">
    <details>
      <summary><strong>Independent 800-point reviewer handoff</strong> · two blank source-linked worksheets</summary>
      <p>Each reviewer slot has 800 pending depth-method tasks across 40 scientific assessments,
        linked to the 16 evidence-input requirements. Reviewer names, qualifications,
        original-source hashes and signatures are not yet verified or submitted.</p>
      <button type="button" onClick={() => void inspectSourceInputs()}
        disabled={!exactNct || loading}>
        {loading ? "Checking current archive…" : "Verify trial inventory for blank reviewer worksheets"}
      </button>
      {error && <p role="alert">{error}</p>}
      {validated && <div>
        <p>Exact trial matched and the pending source-input inventory passed technical checks.
          This does not independently verify the clinical data or qualify a reviewer.</p>
        <button type="button" onClick={() => downloadBlank("A")}>
          Download 800-point reviewer A worksheet (CSV)
        </button>
        <button type="button" onClick={() => downloadBlank("B")}>
          Download 800-point reviewer B worksheet (CSV)
        </button>
        <details aria-label="Local 800-point dual-review comparison">
          <summary><strong>Compare 800-point A/B worksheets locally</strong></summary>
          <p>Choose the returned Reviewer A and Reviewer B CSVs for this exact NCT.
            Files stay in your browser. Comparison flags differing untrusted claims,
            missing original document references and possible reviewer-name reuse.
            It cannot prove actual reviewer independence or source authenticity.</p>
          <label>Reviewer A worksheet CSV
            <input type="file" accept=".csv,text/csv"
              aria-label="Choose 800-point reviewer A CSV"
              onChange={event => {
                auditRevision.current++;
                setReviewerAFile(event.target.files?.[0] ?? null);
                setLocalAudit(null); setLocalAuditError(""); setComparingFiles(false);
              }} />
          </label>
          <label>Reviewer B worksheet CSV
            <input type="file" accept=".csv,text/csv"
              aria-label="Choose 800-point reviewer B CSV"
              onChange={event => {
                auditRevision.current++;
                setReviewerBFile(event.target.files?.[0] ?? null);
                setLocalAudit(null); setLocalAuditError(""); setComparingFiles(false);
              }} />
          </label>
          <button type="button" disabled={!reviewerAFile || !reviewerBFile || comparingFiles}
            onClick={() => void compareLocal800Worksheets()}>
            {comparingFiles ? "Comparing 800 tasks…" : "Compare reviewer A/B consistency"}
          </button>
          {localAuditError && <p role="alert">{localAuditError}</p>}
          {localAudit && <div aria-label="800-point local comparison findings">
            <p><strong>800 of 800 task identities checked.</strong>
              {" "}Reviewers are NOT authenticated. Sources and signatures are NOT verified.</p>
            <p>Candidate decisions: A {localAudit.candidateDecisions.A};
              B {localAudit.candidateDecisions.B}.
              Missing original source provenance: A {localAudit.missingOriginalSourceProvenance.A};
              B {localAudit.missingOriginalSourceProvenance.B}.</p>
            <p>One-sided decisions: {localAudit.oneSidedDecisions}.
              Conflicting candidate decisions: {localAudit.conflictingCandidateDecisions}.
              Conflicting document references: {localAudit.conflictingDocumentReferences}.
              Matching claimed reviewer names: {localAudit.matchingClaimedReviewerNames}.</p>
            {localAudit.conflictTaskKeys.length > 0 && <details>
              <summary>Inspect up to 25 conflicting task keys</summary>
              <ol>{localAudit.conflictTaskKeys.map(key => <li key={key}>{key}</li>)}</ol>
            </details>}
            <small>Scientific adjudication: 0/800. Scientific score and FDA approval
              probability remain unassigned. This consistency audit does not approve
              any reviewer, verify source bytes, or submit scientific findings.</small>
          </div>}
        </details>
      </div>}
      <small>No source uploads, database writes, scores, FDA approval probabilities,
        trading, scans or reviewer signoffs occur. The existing 320-task A/B
        comparison remains separate; these 800-row templates are not an
        authenticated adjudication workflow.</small>
    </details>
  </section>;
}
