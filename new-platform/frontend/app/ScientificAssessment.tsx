"use client";

import { useEffect, useRef, useState } from "react";
import { buildScientificDepthReviewCsv, buildScientificReviewerHandoffCsv } from "../lib/scientific-depth-review-csv";
import { buildScientificEvidenceRequirementsCsv } from "../lib/scientific-evidence-requirements-csv";
import { reconcileLocalReviewerWorksheets, type LocalReviewAudit } from "../lib/scientific-reviewer-local-audit";

/**
 * Scientific input coverage, not an FDA decision prediction. Every numeric
 * outcome remains absent until independent evidence validation is implemented.
 */
type Domain = {
  score: number | null;
  verified: boolean;
  verified_fields: number;
  required_fields: number;
  missing_fields: string[];
};
type EvidenceRequirement = {
  id: string;
  label: string;
  available: boolean;
  evidenceLevel: "archive_verified" | "registry_field_present" | "missing_in_archive" | "independent_review_not_loaded";
  sourcePath: string | null;
  nextAction: string;
  independentlyVerified: false;
};
type GradePair = {
  nctId: string;
  requirements: EvidenceRequirement[];
  missingRequirementIds: string[];
  analysisReadiness: {
    grade: string;
    coveragePercent: number;
    requirementsCovered: number;
    requirementsTotal: number;
    readyForFullScientificConclusion: false;
    verdict: "NOT_READY";
    passFail: "FAIL_INCOMPLETE_INPUTS";
  };
  scientificReluctance: {
    grade: string;
    level: string;
    reluctanceToConclude: string;
    verdict: "WITHHOLD_SCIENTIFIC_CONCLUSION";
  };
  externalEvidenceVerified: false;
  scientificScore: null;
  fdaApprovalProbability: null;
};
type InvestigationLevel = {
  level: number;
  title: string;
  status: string;
  sourceEvidenceCount: number;
  sourceFieldCount: number;
  requiresExternalReview: boolean;
  scientificallyVerified: false;
  score: null;
  caution: string;
};
type Investigation20 = {
  nctId: string;
  levelCount: 20;
  scientificallyVerifiedLevels: 0;
  overallScore: null;
  fdaApprovalProbability: null;
  levels: InvestigationLevel[];
};
type DepthTask = {
  assessmentId: string;
  depthLevel: number;
  depthId: string;
  status: "pending_independent_review";
  independentlyVerified: false;
  scientificScore: null;
};
type Investigation40 = {
  nctId: string;
  layers: { id: string; assessments: string[] }[];
  verification: {
    required_assessments: 40;
    verified_assessments: 0;
    ready_for_analysis: false;
    scientific_score: null;
    approval_probability: null;
  };
  depthReview: {
    requiredTasks: 320;
    completedTasks: 0;
    depthLevels: { level: number; id: string; objective: string }[];
    tasks: DepthTask[];
    readyForScientificConclusion: false;
    approvalProbability: null;
  };
};
type Assessment = {
  exactId: string;
  assessment: {
    overall_score: number | null;
    status: string;
    domains: Record<string, Domain>;
  };
  readinessGrades: GradePair | null;
  investigation20: Investigation20 | null;
  investigation40: Investigation40 | null;
};

const object = (value: unknown): value is Record<string, unknown> =>
  value !== null && typeof value === "object" && !Array.isArray(value);

const count = (value: unknown): value is number =>
  typeof value === "number" && Number.isInteger(value) && value >= 0;

const EXPECTED_REQUIREMENT_IDS = [
  "archive_integrity", "indication", "design", "eligibility", "interventions",
  "enrollment", "timeline", "registered_primary", "primary_analysis",
  "safety_denominators", "participant_flow", "baseline", "protocol_sap",
  "published_results", "independent_replication", "official_regulatory",
] as const;

/** Presence of registry fields is not independent confirmation of the science. */
function validRequirementList(value: Record<string, unknown>, analysis: Record<string, unknown>): boolean {
  const rows = value.requirements;
  const missing = value.missingRequirementIds;
  if (!Array.isArray(rows) || rows.length !== 16 || !Array.isArray(missing)) return false;
  let present = 0;
  const missingIds: string[] = [];
  for (let i = 0; i < EXPECTED_REQUIREMENT_IDS.length; i++) {
    const row: unknown = rows[i];
    if (!object(row) || row.id !== EXPECTED_REQUIREMENT_IDS[i]
        || typeof row.label !== "string" || !row.label.trim() || row.label.length > 180
        || typeof row.nextAction !== "string" || !row.nextAction.trim()
        || row.nextAction.length > 600 || typeof row.available !== "boolean"
        || row.independentlyVerified !== false) return false;
    const external = i >= 12;
    if (external) {
      // The current implementation has NO independently authenticated evidence.
      if (row.available !== false || row.evidenceLevel !== "independent_review_not_loaded"
          || row.sourcePath !== null) return false;
    } else {
      if (typeof row.sourcePath !== "string" || !row.sourcePath.trim()
          || row.sourcePath.length > 300) return false;
      const expectedLevel = i === 0 ? "archive_verified"
        : row.available ? "registry_field_present" : "missing_in_archive";
      if (row.evidenceLevel !== expectedLevel || (i === 0 && row.available !== true)) return false;
    }
    if (row.available) present++;
    else missingIds.push(row.id as string);
  }
  return missing.length === missingIds.length
    && missing.every((id: unknown, i: number) => id === missingIds[i])
    && analysis.requirementsTotal === 16 && analysis.requirementsCovered === present
    && typeof analysis.coveragePercent === "number"
    && Math.abs(analysis.coveragePercent - present * 100 / 16) <= 0.5;
}

function validGradePair(value: unknown, nctId: string): value is GradePair {
  if (!object(value) || !object(value.analysisReadiness)
      || !object(value.scientificReluctance) || value.nctId !== nctId
      || value.externalEvidenceVerified !== false
      || value.scientificScore !== null || value.fdaApprovalProbability !== null) return false;
  const a = value.analysisReadiness;
  const r = value.scientificReluctance;
  return validRequirementList(value, a)
    && typeof a.grade === "string" && /^[A-F]$/.test(a.grade)
    && count(a.coveragePercent) && a.coveragePercent <= 100
    && count(a.requirementsCovered) && a.requirementsTotal === 16
    && a.requirementsCovered <= a.requirementsTotal
    && a.readyForFullScientificConclusion === false
    && a.verdict === "NOT_READY" && a.passFail === "FAIL_INCOMPLETE_INPUTS"
    && r.grade === "F" && r.level === "CRITICAL"
    && r.reluctanceToConclude === "MAXIMUM"
    && r.verdict === "WITHHOLD_SCIENTIFIC_CONCLUSION";
}

function valid20(value: unknown, nctId: string): value is Investigation20 {
  if (!object(value) || value.nctId !== nctId || value.levelCount !== 20
      || value.scientificallyVerifiedLevels !== 0
      || value.overallScore !== null || value.fdaApprovalProbability !== null
      || !Array.isArray(value.levels) || value.levels.length !== 20) return false;
  return value.levels.every((item: unknown, i: number) => {
    if (!object(item)) return false;
    return item.level === i + 1 && typeof item.title === "string"
      && item.title.length <= 160 && typeof item.status === "string"
      && count(item.sourceEvidenceCount) && count(item.sourceFieldCount)
      && item.sourceEvidenceCount <= item.sourceFieldCount
      && typeof item.requiresExternalReview === "boolean"
      && typeof item.caution === "string" && item.caution.length <= 600
      && item.scientificallyVerified === false && item.score === null;
  });
}

function valid40(value: unknown, nctId: string): value is Investigation40 {
  if (!object(value) || !object(value.verification) || !object(value.depthReview)
      || value.nctId !== nctId || !Array.isArray(value.layers)
      || value.layers.length !== 8) return false;
  const v = value.verification;
  const d = value.depthReview;
  if (v.required_assessments !== 40 || v.verified_assessments !== 0
      || v.ready_for_analysis !== false || v.scientific_score !== null
      || v.approval_probability !== null || d.requiredTasks !== 320
      || d.completedTasks !== 0 || d.readyForScientificConclusion !== false
      || d.approvalProbability !== null) return false;
  if (!value.layers.every((layer: unknown) => object(layer)
      && typeof layer.id === "string" && /^[a-z][a-z0-9_]*$/.test(layer.id)
      && Array.isArray(layer.assessments) && layer.assessments.length === 5
      && layer.assessments.every((a: unknown) =>
        typeof a === "string" && /^[a-z][a-z0-9_]*$/.test(a)))) return false;
  const layers = value.layers as Investigation40["layers"];
  const expected = new Set(layers.flatMap(layer =>
    layer.assessments.map(assessment => layer.id + "." + assessment)));
  if (expected.size !== 40 || !Array.isArray(d.depthLevels)
      || d.depthLevels.length !== 8 || !Array.isArray(d.tasks)
      || d.tasks.length !== 320) return false;
  const depthLevels = d.depthLevels;
  if (!depthLevels.every((item: unknown, index: number) =>
      object(item) && item.level === index + 1
      && typeof item.id === "string" && /^[a-z][a-z0-9_]*$/.test(item.id)
      && typeof item.objective === "string" && item.objective.length > 0
      && item.objective.length <= 300)) return false;
  const seen = new Set<string>();
  for (const item of d.tasks) {
    if (!object(item) || typeof item.assessmentId !== "string"
        || !expected.has(item.assessmentId)
        || !count(item.depthLevel) || item.depthLevel < 1 || item.depthLevel > 8
        || item.depthId !== (depthLevels[item.depthLevel - 1] as {id: string}).id
        || item.status !== "pending_independent_review"
        || item.independentlyVerified !== false || item.scientificScore !== null) return false;
    const key = item.assessmentId + ":" + item.depthLevel;
    if (seen.has(key)) return false;
    seen.add(key);
  }
  return seen.size === 320;
}

function verifiedPayload(value: unknown, exactId: string): Assessment {
  if (!object(value) || value.exactId !== exactId || !object(value.assessment)
      || !object(value.assessment.domains) || typeof value.assessment.status !== "string") {
    throw new Error("Scientific response identity or structure failed verification.");
  }
  const source = value.assessment;
  if (source.overall_score !== null) {
    // No numeric score should be shown through the unadjudicated archive view.
    throw new Error("An unverified scientific score was returned. Display blocked.");
  }
  const domains = source.domains as Record<string, unknown>;
  for (const item of Object.values(domains)) {
    if (!object(item) || item.score !== null || !count(item.verified_fields)
        || !count(item.required_fields) || item.verified_fields > item.required_fields
        || !Array.isArray(item.missing_fields) || !item.missing_fields.every((x: unknown) => typeof x === "string")) {
      throw new Error("Scientific evidence status failed validation.");
    }
  }
  const nctId = exactId.startsWith("TRIAL|") ? exactId.slice(6) : "";
  const grades = validGradePair(value.readinessGrades, nctId) ? value.readinessGrades : null;
  const twenty = valid20(value.investigation20, nctId) ? value.investigation20 : null;
  const forty = valid40(value.investigation40, nctId) ? value.investigation40 : null;
  // If any assembled registry-based analysis is malformed, do not present part of it.
  if ((value.readinessGrades !== null && value.readinessGrades !== undefined && !grades)
      || (value.investigation20 !== null && value.investigation20 !== undefined && !twenty)
      || (value.investigation40 !== null && value.investigation40 !== undefined && !forty)) {
    throw new Error("Scientific source coverage failed validation. No grades displayed.");
  }
  return {
    exactId,
    assessment: {
      overall_score: null,
      status: source.status as string,
      domains: domains as Record<string, Domain>,
    },
    readinessGrades: grades,
    investigation20: twenty,
    investigation40: forty,
  };
}

const pretty = (value: string) => value.replaceAll("_", " ");

export default function ScientificAssessment({ exactId }: { exactId: string }) {
  const [result, setResult] = useState<Assessment | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [checkingConnection, setCheckingConnection] = useState(false);
  const [connectionMessage, setConnectionMessage] = useState("");
  const [reviewerAFile, setReviewerAFile] = useState<File | null>(null);
  const [reviewerBFile, setReviewerBFile] = useState<File | null>(null);
  const [localAuditResult, setLocalAuditResult] = useState<LocalReviewAudit | null>(null);
  const [localAuditError, setLocalAuditError] = useState("");
  const [localAuditRunning, setLocalAuditRunning] = useState(false);
  const [localAuditEpoch, setLocalAuditEpoch] = useState(0);
  const localAuditRequest = useRef(0);
  const pending = useRef<AbortController | null>(null);
  const pendingConnection = useRef<AbortController | null>(null);

  useEffect(() => {
    pending.current?.abort();
    pendingConnection.current?.abort();
    setResult(null);
    setError("");
    setLoading(false);
    setCheckingConnection(false);
    setConnectionMessage("");
    localAuditRequest.current += 1;
    setReviewerAFile(null);
    setReviewerBFile(null);
    setLocalAuditResult(null);
    setLocalAuditError("");
    setLocalAuditRunning(false);
    setLocalAuditEpoch(epoch => epoch + 1);
    return () => { pending.current?.abort(); pendingConnection.current?.abort(); localAuditRequest.current += 1; };
  }, [exactId]);

  async function load() {
    if (!exactId || !/^TRIAL\|NCT[0-9]{8}$/.test(exactId)) return;
    pending.current?.abort();
    localAuditRequest.current += 1;
    setReviewerAFile(null);
    setReviewerBFile(null);
    setLocalAuditResult(null);
    setLocalAuditError("");
    setLocalAuditRunning(false);
    setLocalAuditEpoch(epoch => epoch + 1);
    const controller = new AbortController();
    pending.current = controller;
    setLoading(true);
    setResult(null);
    setError("");
    try {
      const response = await fetch(
        "/api/scientific-assessment?exact_id=" + encodeURIComponent(exactId),
        { cache: "no-store", signal: controller.signal },
      );
      if (!response.ok) throw new Error("Scientific assessment unavailable (" + response.status + ")");
      const body: unknown = await response.json();
      const validated = verifiedPayload(body, exactId);
      if (!controller.signal.aborted) setResult(validated);
    } catch (e) {
      if (!controller.signal.aborted) setError(e instanceof Error ? e.message : "Scientific assessment unavailable.");
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }

  async function checkConnection() {
    if (!/^TRIAL\|NCT[0-9]{8}$/.test(exactId)) return;
    pendingConnection.current?.abort();
    const controller = new AbortController();
    pendingConnection.current = controller;
    setCheckingConnection(true);
    setConnectionMessage("");
    try {
      const response = await fetch(
        "/api/scientific-assessment/connection?exact_id=" + encodeURIComponent(exactId),
        { cache: "no-store", signal: controller.signal },
      );
      if (response.status === 401) throw new Error("Dashboard sign-in required to check the scientific service.");
      if (response.status === 502) throw new Error("Scientific API access key was rejected. Check the isolated service configuration.");
      if (response.status === 503) {
        const diagnosis: unknown = await response.json().catch(() => null);
        if (object(diagnosis) && diagnosis.connection === "scientific_backend_contract_mismatch") {
          throw new Error("Scientific Render service runs an older backend release. The integrated scientific backend must be deployed before this check can pass.");
        }
      }
      if (!response.ok) throw new Error("Scientific service connection is not verified (" + response.status + ").");
      const data: unknown = await response.json();
      if (!object(data) || data.connection !== "connected"
          || data.exactTrialIdentityMatched !== true
          || typeof data.archivedRecordPresent !== "boolean"
          || data.approvalProbability !== null
          || data.scoresAssignedByConnectionTest !== false) {
        throw new Error("Scientific service connection response failed validation.");
      }
      if (!controller.signal.aborted) setConnectionMessage(
        "Connected to the isolated scientific API for this exact trial. "
        + (data.archivedRecordPresent ? "Archived registry source is present. " : "Archived registry source is not yet loaded. ")
        + "Independent scientific verification and FDA outcome prediction remain unavailable."
      );
    } catch (e) {
      if (!controller.signal.aborted) setConnectionMessage(
        e instanceof Error ? e.message : "Scientific service connection could not be verified."
      );
    } finally {
      if (!controller.signal.aborted) setCheckingConnection(false);
    }
  }

  /** Strict local-only comparison: neither raw file nor clinical claims leave the browser. */
  async function auditSelectedReviewerWorksheets() {
    if (!result?.investigation40 || !reviewerAFile || !reviewerBFile || localAuditRunning) return;
    const run = ++localAuditRequest.current;
    const matrix = result.investigation40;
    const trialId = exactId;
    setLocalAuditRunning(true);
    setLocalAuditResult(null);
    setLocalAuditError("");
    try {
      if (reviewerAFile.size > 1024 * 1024 || reviewerBFile.size > 1024 * 1024) {
        throw new Error("Worksheet exceeds the 1 MB local-audit size limit.");
      }
      const [a, b] = await Promise.all([reviewerAFile.text(), reviewerBFile.text()]);
      const audit = reconcileLocalReviewerWorksheets(matrix, a, b);
      if (localAuditRequest.current === run && exactId === trialId) setLocalAuditResult(audit);
    } catch {
      if (localAuditRequest.current === run && exactId === trialId) {
        setLocalAuditError("Local reviewer audit blocked: invalid, altered, or incomplete A/B worksheet.");
      }
    } finally {
      if (localAuditRequest.current === run && exactId === trialId) setLocalAuditRunning(false);
    }
  }

  /** Browser-local report of source-input gaps. Never signs a clinical review. */
  function downloadEvidenceRequirementsCsv() {
    if (!result?.readinessGrades) return;
    try {
      const csv = buildScientificEvidenceRequirementsCsv(result.readinessGrades);
      const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = result.readinessGrades.nctId + "_scientific_16_evidence_requirements.csv";
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 2000);
    } catch {
      setError("Scientific input checklist export blocked: incomplete or unverified data.");
    }
  }

  /** Browser-local export of ONLY pending tasks from a validated archived inventory. */
  function downloadDepthReviewCsv(reviewerSlot?: "A" | "B") {
    if (!result?.investigation40) return;
    try {
      const csv = reviewerSlot
        ? buildScientificReviewerHandoffCsv(result.investigation40, reviewerSlot)
        : buildScientificDepthReviewCsv(result.investigation40);
      const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = result.investigation40.nctId + (reviewerSlot
        ? "_scientific_reviewer_" + reviewerSlot + "_320_tasks.csv"
        : "_scientific_320_depth_review.csv");
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      // Keep the object URL alive briefly for iOS Safari to begin the download.
      window.setTimeout(() => URL.revokeObjectURL(url), 2000);
    } catch {
      setError("Scientific review matrix export blocked: inventory incomplete or unverified.");
    }
  }

  const valid = /^TRIAL\|NCT[0-9]{8}$/.test(exactId);
  return <section aria-label="Scientific Assessment">
    <button type="button" disabled={!valid || loading} onClick={() => void load()}>
      {loading ? "Checking scientific evidence…" : "Scientific Assessment · 20 levels / 40 assessments"}
    </button>
    <button type="button" disabled={!valid || checkingConnection}
      onClick={() => void checkConnection()}>
      {checkingConnection ? "Checking isolated scientific API…" : "Verify scientific service connection"}
    </button>
    {connectionMessage && <p role="status">{connectionMessage}</p>}
    {error && <p role="alert">{error}</p>}
    {result && <div>
      <p><strong>Trial:</strong> {result.exactId}</p>
      <p role="status">Scientific outcome and FDA approval probability: <strong>NOT ASSIGNED</strong>. Archived registry inputs do not establish efficacy.</p>
      {result.readinessGrades ? <section aria-label="Two evidence readiness grades">
        <h3>Two evidence-readiness grades</h3>
        <p><strong>Analysis readiness: {result.readinessGrades.analysisReadiness.grade}</strong>
          {" · "} {result.readinessGrades.analysisReadiness.coveragePercent}% of 16 input checks present
          {" · "} {result.readinessGrades.analysisReadiness.passFail.replaceAll("_", " ")}.
        </p>
        <p><strong>Reluctance grade: {result.readinessGrades.scientificReluctance.grade}</strong>
          {" · "} Maximum reluctance to draw a scientific conclusion.
        </p>
        <small>These grade the completeness of evidence inputs and the need to withhold judgment. A reluctance F does NOT mean the drug failed. Neither grade predicts FDA approval.</small>
        <p>
          <button type="button" onClick={() => downloadEvidenceRequirementsCsv()}>
            Download 16-requirement evidence checklist (CSV)
          </button>
          <small> Archived source fields and required next actions only. Independent scientific review is not certified by this download.</small>
        </p>
        <details aria-label="Scientific input requirement checklist">
          <summary><strong>Scientific evidence input checklist</strong> · {result.readinessGrades.analysisReadiness.requirementsCovered}/16 source inputs available · 4 independent reviews required</summary>
          <p>Archived source presence is not independent scientific verification. Missing requirements and next actions are shown separately for this exact trial.</p>
          <ol>{result.readinessGrades.requirements.map((requirement, i) =>
            <li key={requirement.id}>
              <details>
                <summary><strong>{requirement.label}</strong>{" · "}
                  {i >= 12 ? "Independent review not completed"
                    : requirement.available ? "Source input available; not scientifically verified" : "Input missing in archive"}
                </summary>
                <p>Evidence level: {pretty(requirement.evidenceLevel)}.</p>
                {requirement.sourcePath && <p>Source field or integrity reference: <code>{requirement.sourcePath}</code></p>}
                <p>Required next action: {requirement.nextAction}</p>
                <small>Independently verified: NO. This requirement does not establish clinical efficacy or FDA approval.</small>
              </details>
            </li>)}</ol>
        </details>
      </section> : <p>Both evidence-readiness grades are unavailable until a verified archived record is loaded.</p>}

      {result.investigation20 ? <details>
        <summary><strong>20 investigation levels</strong> · source inventory, not completed reviews</summary>
        <ol>{result.investigation20.levels.map(level =>
          <li key={level.level}>
            <details>
              <summary><strong>Level {level.level}: {level.title}</strong>
                {" · "} {level.sourceEvidenceCount}/{level.sourceFieldCount} registry fields present
                {" · "} {pretty(level.status)}
              </summary>
              <p>{level.caution}</p>
              <small>Independent scientific verification: not complete. Level score: not assigned.</small>
            </details>
          </li>
        )}</ol>
      </details> : <p>20-level investigation: no checksum-verified trial archive available.</p>}

      {result.investigation40 && <p>
        <button type="button" disabled={!result.investigation40}
          onClick={() => downloadDepthReviewCsv()}>
          Download 320-task review matrix (CSV)
        </button>
        <small> Read-only pending-task export for independent review. No reviewer attestation or scientific decision is created by downloading.</small>
        <details>
          <summary><strong>Independent reviewer handoff — two blank worksheets</strong></summary>
          <p>Generate distinct, unsubmitted worksheets for two independent reviewer slots.
            They include all 320 pending tasks, blank document provenance and reviewer fields.
            Slots A and B are not verified reviewer identities or approved decisions.</p>
          <button type="button" onClick={() => downloadDepthReviewCsv("A")}>
            Download reviewer A worksheet (CSV)
          </button>
          <button type="button" onClick={() => downloadDepthReviewCsv("B")}>
            Download reviewer B worksheet (CSV)
          </button>
          <small>These local CSV files do not authenticate anyone, sign a review,
            upload evidence, or change scientific completion counts. Genuine independent
            identity checks, document review, signed disagreement reconciliation and release approval remain outstanding.</small>
        </details>
        <details aria-label="Local A/B reviewer worksheet audit">
          <summary><strong>Local A/B reviewer worksheet audit</strong> · compare both returned 320-task files</summary>
          <p>Select the two reviewer worksheets for this trial. No files are uploaded; all checks run inside this browser session, and no reviewer identity, source, signature, scientific score, or FDA probability can be verified here.</p>
          <p>
            <label>Reviewer A worksheet
              <input key={exactId + "-A-" + localAuditEpoch} type="file" accept=".csv,text/csv"
                onChange={event => {
                  localAuditRequest.current += 1;
                  setReviewerAFile(event.target.files?.[0] ?? null);
                  setLocalAuditResult(null);
                  setLocalAuditError("");
                  setLocalAuditRunning(false);
                }} />
            </label>
          </p>
          <p>
            <label>Reviewer B worksheet
              <input key={exactId + "-B-" + localAuditEpoch} type="file" accept=".csv,text/csv"
                onChange={event => {
                  localAuditRequest.current += 1;
                  setReviewerBFile(event.target.files?.[0] ?? null);
                  setLocalAuditResult(null);
                  setLocalAuditError("");
                  setLocalAuditRunning(false);
                }} />
            </label>
          </p>
          <button type="button" disabled={!reviewerAFile || !reviewerBFile || localAuditRunning}
            onClick={() => void auditSelectedReviewerWorksheets()}>
            {localAuditRunning ? "Checking reviewer worksheets…" : "Audit A/B worksheets locally"}
          </button>
          {localAuditError && <p role="alert">{localAuditError}</p>}
          {localAuditResult && <section aria-label="Unverified reviewer candidate comparison">
            <p role="status"><strong>Local worksheet audit: BLOCKED for scientific approval.</strong> Exact trial {localAuditResult.exactNctId}; independent evidence verification remains unavailable.</p>
            <p>Candidate observations with syntactically complete fields: reviewer A {localAuditResult.candidateA}/320; reviewer B {localAuditResult.candidateB}/320.</p>
            <p>Unverified or incomplete source provenance: A {localAuditResult.missingProvenanceA}, B {localAuditResult.missingProvenanceB}. Missing reviewer identity or notes: A {localAuditResult.incompleteNotesA}, B {localAuditResult.incompleteNotesB}.</p>
            <p>Tasks with only one candidate: {localAuditResult.oneSidedObservations}. Conflicting candidate decisions: {localAuditResult.candidateDisagreementCount}.</p>
            {localAuditResult.disagreementTaskIds.length > 0 && <details>
              <summary>Show disputed task identifiers (first 20)</summary>
              <ol>{localAuditResult.disagreementTaskIds.slice(0, 20).map(id => <li key={id}>{id}</li>)}</ol>
            </details>}
            <p><strong>Independent adjudications: 0. Scientific score: NOT ASSIGNED. FDA approval probability: NOT ASSIGNED.</strong></p>
            <small>Typed names, signatures and supplied SHA-256 strings are not independently authenticated. Source bytes are not fetched. The review ledger and production system are unchanged.</small>
          </section>}
        </details>
      </p>}

      {result.investigation40 ? <details>
        <summary><strong>8 scientific layers · 40 assessments</strong>
          {" · "} {result.investigation40.verification.verified_assessments}/40 independently verified
        </summary>
        {result.investigation40.layers.map(layer =>
          <details key={layer.id}>
            <summary>{pretty(layer.id)} · {layer.assessments.length} assessments</summary>
            <ol>{layer.assessments.map(item =>
              <li key={item}>
                <details>
                  <summary>{pretty(item)} · 0/8 in-depth reviews independently complete</summary>
                  <ol>{result.investigation40!.depthReview.tasks
                    .filter(task => task.assessmentId === layer.id + "." + item)
                    .map(task => <li key={task.depthLevel}>
                      <strong>Depth {task.depthLevel}: {pretty(task.depthId)}</strong>
                      {" · "}{result.investigation40!.depthReview.depthLevels[task.depthLevel - 1].objective}
                      {" · "}{pretty(task.status)} · score not assigned
                    </li>)}</ol>
                </details>
              </li>)}</ol>
          </details>
        )}
        <p>{result.investigation40.depthReview.completedTasks}/{result.investigation40.depthReview.requiredTasks} planned in-depth review tasks completed. Open a layer and then an assessment to inspect each of the 320 pending tasks.</p>
        <small>All values are inventory or coverage states. They cannot establish efficacy or an approval probability.</small>
      </details> : <p>Eight-layer scientific investigation: no verified source inventory loaded.</p>}

      <details>
        <summary>Original six-domain evidence gate · not a clinical rating</summary>
        {Object.entries(result.assessment.domains).map(([name, domain]) =>
          <details key={name}>
            <summary>{pretty(name)} · {domain.verified_fields}/{domain.required_fields} verified</summary>
            <p>Domain score: not assigned</p>
            <p>Missing evidence: {domain.missing_fields.join(", ") || "None recorded"}</p>
          </details>)}
      </details>
      <small>No PIPELINE, GEM JR, GEM, WT, qualification FS/FA preset, trading, or scanning setting is changed by these read-only views.</small>
    </div>}
  </section>;
}
