"use client";

import { useEffect, useRef, useState } from "react";
import { buildScientificDepthReviewCsv, buildScientificReviewerHandoffCsv } from "../lib/scientific-depth-review-csv";
import { buildScientificEvidenceRequirementsCsv } from "../lib/scientific-evidence-requirements-csv";
import { auditScientificReviewerCsvs, buildScientificReviewerAuditReceipt, compareLocalSourceSha256Claims, compareTwoLocalSourcePdfSha256Claims, type LocalReviewerAuditReport, type LocalSourceByteMatch, type DualLocalSourceByteMatch } from "../lib/scientific-reviewer-local-audit";
import { compareLocalPdfWithCapturedArchive, summarizeCapturedScientificGates, buildScientificSourceReviewHandoff, type CapturedArchiveComparison, type CapturedScientificGateCoverage } from "../lib/scientific-captured-archive-check";
import { compareFourGateSourceHandoffs, type HandoffDrift } from "../lib/scientific-handoff-drift-check";

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
  const [reviewInventoryFile, setReviewInventoryFile] = useState<File | null>(null);
  const [reviewerAFile, setReviewerAFile] = useState<File | null>(null);
  const [reviewerBFile, setReviewerBFile] = useState<File | null>(null);
  const [localAudit, setLocalAudit] = useState<LocalReviewerAuditReport | null>(null);
  const [localAuditError, setLocalAuditError] = useState("");
  const [comparingFiles, setComparingFiles] = useState(false);
  const [localSourcePdf, setLocalSourcePdf] = useState<File | null>(null);
  const [localSourceTaskKey, setLocalSourceTaskKey] = useState("");
  const [localSourceByteMatch, setLocalSourceByteMatch] = useState<LocalSourceByteMatch | null>(null);
  const [localSourceByteError, setLocalSourceByteError] = useState("");
  const [hashingLocalPdf, setHashingLocalPdf] = useState(false);
  const [localReviewerBPdf, setLocalReviewerBPdf] = useState<File | null>(null);
  const [dualSourceBytes, setDualSourceBytes] = useState<DualLocalSourceByteMatch | null>(null);
  const [dualSourceError, setDualSourceError] = useState("");
  const [checkingDualSource, setCheckingDualSource] = useState(false);
  const [capturedArchiveCheck, setCapturedArchiveCheck] = useState<CapturedArchiveComparison | null>(null);
  const [capturedArchiveError, setCapturedArchiveError] = useState("");
  const [checkingCapturedArchive, setCheckingCapturedArchive] = useState(false);
  const [capturedBackendStatus, setCapturedBackendStatus] = useState("");
  const [capturedBackendChecking, setCapturedBackendChecking] = useState(false);
  const [capturedScientificGates, setCapturedScientificGates] = useState<CapturedScientificGateCoverage | null>(null);
  const [capturedHandoffJson, setCapturedHandoffJson] = useState<string | null>(null);
  const [earlierHandoffFile, setEarlierHandoffFile] = useState<File | null>(null);
  const [laterHandoffFile, setLaterHandoffFile] = useState<File | null>(null);
  const [handoffDrift, setHandoffDrift] = useState<HandoffDrift | null>(null);
  const [handoffDriftError, setHandoffDriftError] = useState("");
  const [comparingHandoffs, setComparingHandoffs] = useState(false);
  const [liveHandoffDrift, setLiveHandoffDrift] = useState<HandoffDrift | null>(null);
  const [liveHandoffError, setLiveHandoffError] = useState("");
  const [checkingLiveHandoff, setCheckingLiveHandoff] = useState(false);
  const handoffDriftRevision = useRef(0);
  const capturedBackendRevision = useRef(0);
  const auditRevision = useRef(0);
  const pending = useRef<AbortController | null>(null);
  const pendingConnection = useRef<AbortController | null>(null);

  useEffect(() => {
    auditRevision.current++;
    capturedBackendRevision.current++;
    setCapturedBackendStatus("");
    setCapturedBackendChecking(false);
    setCapturedScientificGates(null);
    setCapturedHandoffJson(null);
    handoffDriftRevision.current++;
    setEarlierHandoffFile(null);
    setLaterHandoffFile(null);
    setHandoffDrift(null);
    setHandoffDriftError("");
    setComparingHandoffs(false);
    setLiveHandoffDrift(null);
    setLiveHandoffError("");
    setCheckingLiveHandoff(false);
    setReviewInventoryFile(null);
    setReviewerAFile(null);
    setReviewerBFile(null);
    setLocalAudit(null);
    setLocalAuditError("");
    setComparingFiles(false);
    setLocalSourcePdf(null);
    setLocalSourceTaskKey("");
    setLocalSourceByteMatch(null);
    setCapturedArchiveCheck(null);
    setCapturedArchiveError("");
    setCheckingCapturedArchive(false);
    setLocalSourceByteError("");
    setHashingLocalPdf(false);
    setLocalReviewerBPdf(null);
    setDualSourceBytes(null);
    setDualSourceError("");
    setCheckingDualSource(false);
    pending.current?.abort();
    pendingConnection.current?.abort();
    setResult(null);
    setError("");
    setLoading(false);
    setCheckingConnection(false);
    setConnectionMessage("");
    return () => { pending.current?.abort(); pendingConnection.current?.abort(); };
  }, [exactId]);

  async function load() {
    if (!exactId || !/^TRIAL\|NCT[0-9]{8}$/.test(exactId)) return;
    pending.current?.abort();
    const controller = new AbortController();
    pending.current = controller;
    auditRevision.current++;
    capturedBackendRevision.current++;
    setCapturedBackendStatus("");
    setCapturedBackendChecking(false);
    setCapturedScientificGates(null);
    setCapturedHandoffJson(null);
    handoffDriftRevision.current++;
    setEarlierHandoffFile(null);
    setLaterHandoffFile(null);
    setHandoffDrift(null);
    setHandoffDriftError("");
    setComparingHandoffs(false);
    setLiveHandoffDrift(null);
    setLiveHandoffError("");
    setCheckingLiveHandoff(false);
    setLocalAudit(null);
    setLocalAuditError("");
    setComparingFiles(false);
    setLocalSourcePdf(null);
    setLocalSourceTaskKey("");
    setLocalSourceByteMatch(null);
    setCapturedArchiveCheck(null);
    setCapturedArchiveError("");
    setCheckingCapturedArchive(false);
    setLocalSourceByteError("");
    setHashingLocalPdf(false);
    setLocalReviewerBPdf(null);
    setDualSourceBytes(null);
    setDualSourceError("");
    setCheckingDualSource(false);
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

  /** Only reads three user-selected local CSV files in this browser. No API call. */
  async function compareLocalReviewerWorksheets() {
    setDualSourceBytes(null);
    setDualSourceError("");
    setLocalSourceByteMatch(null);
    setCapturedArchiveCheck(null);
    setCapturedArchiveError("");
    setCheckingCapturedArchive(false);
    setLocalSourceByteError("");
    if (!result?.investigation40 || !reviewInventoryFile || !reviewerAFile || !reviewerBFile) return;
    const token = ++auditRevision.current;
    setLocalAudit(null);
    setLocalAuditError("");
    setComparingFiles(true);
    try {
      if ([reviewInventoryFile, reviewerAFile, reviewerBFile].some(file => file.size > 1024 * 1024)) {
        throw new Error("Files must be 1 MB or smaller.");
      }
      const [inventoryCsv, aCsv, bCsv] = await Promise.all([
        reviewInventoryFile.text(), reviewerAFile.text(), reviewerBFile.text(),
      ]);
      const report = auditScientificReviewerCsvs(result.investigation40, inventoryCsv, aCsv, bCsv);
      if (token === auditRevision.current) setLocalAudit(report);
    } catch {
      if (token === auditRevision.current) setLocalAuditError(
        "Local worksheet comparison blocked: CSV files are malformed, mismatched or include unsupported reviewer status. No evidence was imported."
      );
    } finally {
      if (token === auditRevision.current) setComparingFiles(false);
    }
  }

  /** Local diagnostic download; creates no attestation or back-end write. */
  function downloadLocalReviewerAuditReceipt() {
    if (!result?.investigation40 || !localAudit) return;
    try {
      const body = buildScientificReviewerAuditReceipt(result.investigation40, localAudit);
      const blob = new Blob([body], { type: "application/json;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = result.investigation40.nctId + "_unverified_reviewer_ab_diagnostic.json";
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 2000);
    } catch {
      setLocalAuditError("Local reviewer audit receipt blocked: unverifiable diagnostic report.");
    }
  }

  /** Byte consistency only: SHA-256 equality to typed A/B CSV claims is NOT source authentication. */
  async function compareLocalSourcePdfBytes() {
    setDualSourceBytes(null);
    setDualSourceError("");
    if (!result?.investigation40 || !localAudit || !localSourcePdf
        || !localSourceTaskKey || !reviewInventoryFile || !reviewerAFile || !reviewerBFile) return;
    const token = ++auditRevision.current;
    setLocalSourceByteMatch(null);
    setCapturedArchiveCheck(null);
    setCapturedArchiveError("");
    setCheckingCapturedArchive(false);
    setLocalSourceByteError("");
    setHashingLocalPdf(true);
    try {
      if (localSourcePdf.size < 5 || localSourcePdf.size > 25 * 1024 * 1024
          || [reviewInventoryFile, reviewerAFile, reviewerBFile].some(f => f.size > 1024 * 1024)) {
        throw new Error("Unsupported local source PDF or reviewer worksheet size");
      }
      const [pdfBytes, inventoryCsv, aCsv, bCsv] = await Promise.all([
        localSourcePdf.arrayBuffer(), reviewInventoryFile.text(), reviewerAFile.text(), reviewerBFile.text(),
      ]);
      const header = new Uint8Array(pdfBytes, 0, 5);
      if (String.fromCharCode(...header) !== "%PDF-") throw new Error("Selected file is not a PDF");
      if (typeof crypto === "undefined" || !crypto.subtle) throw new Error("Secure browser SHA-256 unavailable");
      const digest = await crypto.subtle.digest("SHA-256", pdfBytes);
      const sha256 = Array.from(new Uint8Array(digest))
        .map(byte => byte.toString(16).padStart(2, "0")).join("");
      const comparison = compareLocalSourceSha256Claims(
        result.investigation40, inventoryCsv, aCsv, bCsv, localSourceTaskKey, sha256,
      );
      if (token === auditRevision.current) setLocalSourceByteMatch(comparison);
    } catch {
      if (token === auditRevision.current) setLocalSourceByteError(
        "PDF byte comparison blocked: invalid PDF, changed review worksheets, or unsupported task. No source authentication was performed."
      );
    } finally {
      if (token === auditRevision.current) setHashingLocalPdf(false);
    }
  }

  /** SHA-256 from actual local PDF bytes, with bounded size and PDF boundary checks. */
  async function sha256LocalPdf(file: File): Promise<string> {
    if (file.size < 32 || file.size > 25 * 1024 * 1024) throw new Error("Invalid local PDF size");
    const bytes = await file.arrayBuffer();
    const data = new Uint8Array(bytes);
    if (String.fromCharCode(...data.subarray(0, 5)) !== "%PDF-") throw new Error("PDF header missing");
    const tail = new TextDecoder("latin1").decode(data.subarray(Math.max(0, data.length - 1024)));
    if (!tail.includes("%%EOF")) throw new Error("PDF end marker missing");
    if (typeof crypto === "undefined" || !crypto.subtle) throw new Error("Secure SHA-256 unavailable");
    const digest = await crypto.subtle.digest("SHA-256", bytes);
    return Array.from(new Uint8Array(digest))
      .map(byte => byte.toString(16).padStart(2, "0")).join("");
  }

  /** Compare each actual local PDF with its own A/B claim, never accept scientific evidence. */
  async function compareTwoLocalPdfBytes() {
    if (!result?.investigation40 || !localAudit || !localSourcePdf || !localReviewerBPdf
        || !localSourceTaskKey || !reviewInventoryFile || !reviewerAFile || !reviewerBFile) return;
    const token = ++auditRevision.current;
    setDualSourceBytes(null);
    setDualSourceError("");
    setCheckingDualSource(true);
    try {
      if ([reviewInventoryFile, reviewerAFile, reviewerBFile].some(f => f.size > 1024 * 1024)) {
        throw new Error("CSV file too large");
      }
      const [digestA, digestB, inventoryCsv, aCsv, bCsv] = await Promise.all([
        sha256LocalPdf(localSourcePdf), sha256LocalPdf(localReviewerBPdf),
        reviewInventoryFile.text(), reviewerAFile.text(), reviewerBFile.text(),
      ]);
      const comparison = compareTwoLocalSourcePdfSha256Claims(
        result.investigation40, inventoryCsv, aCsv, bCsv, localSourceTaskKey, digestA, digestB,
      );
      if (token === auditRevision.current) setDualSourceBytes(comparison);
    } catch {
      if (token === auditRevision.current) setDualSourceError(
        "Two-PDF byte comparison blocked: invalid PDF, incomplete file or changed worksheet. No evidence was accepted."
      );
    } finally {
      if (token === auditRevision.current) setCheckingDualSource(false);
    }
  }

  /** Probe current pilot source manifest contract: no uploads or scientific promotion. */
  async function checkCapturedBackendAvailability() {
    if (exactId !== "TRIAL|NCT02142738") return;
    const revision = ++capturedBackendRevision.current;
    setCapturedBackendStatus("");
    setCapturedScientificGates(null);
    setCapturedHandoffJson(null);
    setCapturedBackendChecking(true);
    try {
      const response = await fetch(
        "/api/scientific-assessment/captured-source-manifest?nct_id=NCT02142738",
        { cache: "no-store" },
      );
      const body: unknown = await response.json();
      let message: string;
      if (response.ok) {
        const gateCoverage = summarizeCapturedScientificGates("NCT02142738", body);
        const handoffJson = buildScientificSourceReviewHandoff("NCT02142738", body);
        if (revision === capturedBackendRevision.current) {
          setCapturedScientificGates(gateCoverage);
          setCapturedHandoffJson(handoffJson);
        }
        message = gateCoverage.sourceDocumentCount === 0
          ? "Captured-source backend is responding, but the pilot has 0 archived PDF snapshots. Scientific source verification remains blocked."
          : "Captured-source backend is responding with "
            + gateCoverage.sourceDocumentCount
            + " checksum-checked archived PDF snapshot(s) across "
            + gateCoverage.gatesWithCapturedPdf
            + " of 4 evidence categories. Byte integrity ONLY; source authenticity and scientific review are NOT verified.";
      } else {
        const data = body && typeof body === "object" && !Array.isArray(body)
          ? body as Record<string, unknown> : {};
        message = response.status === 401
          ? "Dashboard session is not authorized. Sign in to check the isolated scientific backend."
          : data.reason === "CAPTURED_ROUTE_NOT_DEPLOYED"
            ? "Captured-source manifest route is NOT DEPLOYED on the isolated Render backend. The frontend is newer than the backend; no archive lookup is available."
          : data.reason === "ISOLATED_READ_KEY_REJECTED"
            ? "The isolated Render backend rejected the preview read-only key; credentials/configuration require review."
          : data.reason === "SCIENTIFIC_SERVICE_NOT_CONFIGURED"
            ? "Isolated Render scientific API or its dedicated read key is not configured for this preview."
          : data.reason === "ISOLATED_SCIENTIFIC_SERVICE_UNAVAILABLE"
            ? "The isolated Render backend is currently unavailable."
          : "Captured-source backend manifest is unavailable or failed its read-only safety contract.";
      }
      if (revision === capturedBackendRevision.current) setCapturedBackendStatus(message);
    } catch {
      if (revision === capturedBackendRevision.current) setCapturedBackendStatus(
        "Captured-source backend could not be verified. No scientific evidence has been accepted."
      );
    } finally {
      if (revision === capturedBackendRevision.current) setCapturedBackendChecking(false);
    }
  }

  /** Explicit local download of allowlisted unsigned evidence inventory only. */
  function downloadCapturedSourceHandoff() {
    if (!capturedHandoffJson || !capturedScientificGates
        || capturedScientificGates.nctId !== "NCT02142738"
        || exactId !== "TRIAL|NCT02142738") return;
    const blob = new Blob([capturedHandoffJson], { type: "application/json;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "NCT02142738_unverified_four_gate_source_handoff.json";
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 2000);
  }

  /** Local-only drift check across two UNSIGNED exports; file selection defines order. */
  async function compareSourceHandoffFiles() {
    if (exactId !== "TRIAL|NCT02142738" || !earlierHandoffFile || !laterHandoffFile) return;
    const revision = ++handoffDriftRevision.current;
    setHandoffDrift(null);
    setHandoffDriftError("");
    setLiveHandoffDrift(null);
    setLiveHandoffError("");
    setCheckingLiveHandoff(false);
    setComparingHandoffs(true);
    try {
      if ([earlierHandoffFile, laterHandoffFile].some(file => file.size > 256 * 1024)) {
        throw new Error("Handoff exceeds the 256 KiB local comparison limit.");
      }
      const [earlier, later] = await Promise.all([
        earlierHandoffFile.text(), laterHandoffFile.text(),
      ]);
      const report = compareFourGateSourceHandoffs(earlier, later);
      if (revision === handoffDriftRevision.current) setHandoffDrift(report);
    } catch {
      if (revision === handoffDriftRevision.current) setHandoffDriftError(
        "The local handoff comparison was blocked: wrong trial, changed schema, tampered evidence status or invalid document inventory. Neither file has been authenticated."
      );
    } finally {
      if (revision === handoffDriftRevision.current) setComparingHandoffs(false);
    }
  }

  /**
   * Compare the operator's UNSIGNED saved handoff to a NEW, authenticated
   * read-only response from the isolated server. The server has rehashed
   * captured bytes; neither side verifies original publisher authenticity.
   */
  async function compareSavedHandoffToLiveArchive() {
    if (exactId !== "TRIAL|NCT02142738" || !earlierHandoffFile) return;
    const revision = ++handoffDriftRevision.current;
    setLiveHandoffDrift(null);
    setLiveHandoffError("");
    setCheckingLiveHandoff(true);
    try {
      if (earlierHandoffFile.size < 1 || earlierHandoffFile.size > 256 * 1024) {
        throw new Error("Invalid local handoff size");
      }
      const saved = await earlierHandoffFile.text();
      // No fallbacks to ordinary dashboard APIs; the session-protected proxy
      // enforces exact NCT, dedicated preview key, schema and no-store.
      const response = await fetch(
        "/api/scientific-assessment/captured-source-manifest?nct_id=NCT02142738",
        { cache: "no-store" },
      );
      if (!response.ok) throw new Error("Live authenticated archive unavailable");
      const liveManifest: unknown = await response.json();
      const liveHandoff = buildScientificSourceReviewHandoff("NCT02142738", liveManifest);
      const comparison = compareFourGateSourceHandoffs(saved, liveHandoff);
      if (revision === handoffDriftRevision.current) setLiveHandoffDrift(comparison);
    } catch {
      if (revision === handoffDriftRevision.current) setLiveHandoffError(
        "Live archive comparison BLOCKED: sign in, restore the isolated read-only service, or select a valid exact-trial source handoff. A blocked check is NOT evidence of no change."
      );
    } finally {
      if (revision === handoffDriftRevision.current) setCheckingLiveHandoff(false);
    }
  }

  /** On-demand read-only pinned archive metadata: NEVER admits or certifies a source. */
  async function compareLocalPdfWithArchivedSnapshot() {
    if (!localSourceByteMatch || !localSourcePdf || !result?.investigation40
        || result.investigation40.nctId !== "NCT02142738") return;
    const token = ++auditRevision.current;
    setCapturedArchiveCheck(null);
    setCapturedArchiveError("");
    setCheckingCapturedArchive(true);
    try {
      const response = await fetch(
        "/api/scientific-assessment/captured-source-manifest?nct_id=NCT02142738",
        { cache: "no-store" },
      );
      if (!response.ok) throw new Error("Archived PDF metadata unavailable");
      const data: unknown = await response.json();
      const report = compareLocalPdfWithCapturedArchive(
        result.investigation40.nctId, localSourceByteMatch.calculatedSha256,
        localSourcePdf.size, data,
      );
      if (token === auditRevision.current) setCapturedArchiveCheck(report);
    } catch {
      if (token === auditRevision.current) setCapturedArchiveError(
        "Captured archive hash comparison unavailable or rejected. No PDF was uploaded or evidence accepted."
      );
    } finally {
      if (token === auditRevision.current) setCheckingCapturedArchive(false);
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
    {exactId === "TRIAL|NCT02142738" && <div aria-label="Captured-source backend deployment status">
      <button type="button" disabled={capturedBackendChecking}
        onClick={() => void checkCapturedBackendAvailability()}>
        {capturedBackendChecking ? "Checking captured-source backend…" : "Check captured-source backend deployment"}
      </button>
      <small> On-demand read-only check; distinguishes an undeployed route from an empty PDF archive. No file uploads or scientific approval.</small>
      {capturedBackendStatus && <p role="status">{capturedBackendStatus}</p>}
      {capturedScientificGates && capturedHandoffJson && <p>
        <button type="button" onClick={() => downloadCapturedSourceHandoff()}>
          Download unverified four-gate source review handoff (JSON)
        </button>
        <small> Source hashes, counts and next verification steps only. No raw PDF bytes, source URLs, reviewer names, signatures or scientific outcome claims.</small>
      </p>}
      <details aria-label="Compare earlier and later unsigned four-gate source inventory files">
        <summary><strong>Compare two saved source handoff inventories (browser only)</strong></summary>
        <p>Select two previously downloaded four-gate source handoff JSON files. Files remain local; the comparison detects reported changes in captured document IDs, hashes, sizes and gate assignments. Because packets are unsigned, their authenticity and actual chronological order cannot be established from the files.</p>
        <div>
          <label>Earlier handoff JSON
            <input type="file" accept=".json,application/json" aria-label="Choose earlier four-gate source handoff"
              onChange={event => {
                handoffDriftRevision.current++;
                setEarlierHandoffFile(event.target.files?.[0] ?? null);
                setHandoffDrift(null); setHandoffDriftError(""); setComparingHandoffs(false);
                setLiveHandoffDrift(null); setLiveHandoffError(""); setCheckingLiveHandoff(false);
              }} />
          </label>
        </div>
        <div>
          <label>Later handoff JSON
            <input type="file" accept=".json,application/json" aria-label="Choose later four-gate source handoff"
              onChange={event => {
                handoffDriftRevision.current++;
                setLaterHandoffFile(event.target.files?.[0] ?? null);
                setHandoffDrift(null); setHandoffDriftError(""); setComparingHandoffs(false);
                setLiveHandoffDrift(null); setLiveHandoffError(""); setCheckingLiveHandoff(false);
              }} />
          </label>
        </div>
        <button type="button" disabled={!earlierHandoffFile || !laterHandoffFile || comparingHandoffs || checkingLiveHandoff}
          onClick={() => void compareSourceHandoffFiles()}>
          {comparingHandoffs ? "Comparing local inventories…" : "Compare earlier and later source handoffs"}
        </button>
        <p>
          <button type="button" disabled={!earlierHandoffFile || checkingLiveHandoff || comparingHandoffs}
            onClick={() => void compareSavedHandoffToLiveArchive()}>
            {checkingLiveHandoff ? "Checking protected live PDF archive…" : "Compare saved handoff to LIVE captured archive"}
          </button>
          <small> Makes a fresh authenticated, read-only request to the isolated scientific backend. The saved JSON stays in this browser. No PDF contents are uploaded, and an unsigned file cannot prove authorship or chronological history.</small>
        </p>
        {liveHandoffError && <p role="alert">{liveHandoffError}</p>}
        {liveHandoffDrift && <section role="status" aria-label="Authenticated live captured archive comparison">
          <p><strong>Saved unsigned handoff versus currently rehashed isolated archive:</strong>{" "}
            {liveHandoffDrift.comparisonResult.replaceAll("_", " ")}.</p>
          <p>Saved captured PDFs: {liveHandoffDrift.priorDocumentCount}; live captured PDFs:
            {" "}{liveHandoffDrift.laterDocumentCount}. Added: {liveHandoffDrift.addedDocumentIds.length};
            {" "}removed: {liveHandoffDrift.removedDocumentIds.length};
            {" "}changed: {liveHandoffDrift.changedDocumentIds.length}.</p>
          <ul>{liveHandoffDrift.gates.map(gate => <li key={gate.gateId}>
            <strong>{gate.gateId.replaceAll("_", " ")}</strong>: saved {gate.priorCapturedPdfCount},
            {" "}live {gate.laterCapturedPdfCount} captured PDFs
          </li>)}</ul>
          <p><strong>Original source authenticated: NO. Independent reviewer adjudication: INCOMPLETE.
            {" "}FDA approval probability: NOT ASSIGNED.</strong></p>
          <small>The current isolated archive rehashes its stored bytes, but a matching digest does not independently authenticate the original publisher. The saved handoff is unsigned and cannot establish its capture date.</small>
        </section>}
        {handoffDriftError && <p role="alert">{handoffDriftError}</p>
        {handoffDrift && <section role="status" aria-label="Unverified source inventory comparison result">
          <p><strong>{handoffDrift.comparisonResult.replaceAll("_", " ")}</strong> — captured PDFs: {handoffDrift.priorDocumentCount} in selected earlier file, {handoffDrift.laterDocumentCount} in selected later file.</p>
          <p>Added IDs: {handoffDrift.addedDocumentIds.length}; removed IDs: {handoffDrift.removedDocumentIds.length}; changed metadata for existing IDs: {handoffDrift.changedDocumentIds.length}; unchanged entries: {handoffDrift.unchangedDocumentCount}.</p>
          <ul>{handoffDrift.gates.map(g => <li key={g.gateId}>
            <strong>{g.gateId.replaceAll("_", " ")}</strong>: {g.priorCapturedPdfCount} earlier / {g.laterCapturedPdfCount} later captured PDFs
          </li>)}</ul>
          {(["addedDocumentIds", "removedDocumentIds", "changedDocumentIds"] as const).map(key =>
            handoffDrift[key].length > 0 && <details key={key}>
              <summary>{key.replaceAll(/([A-Z])/g, " $1")} ({handoffDrift[key].length})</summary>
              <ul>{handoffDrift[key].map(id => <li key={id}><code>{id}</code></li>)}</ul>
            </details>
          )}
          <p><strong>Neither snapshot authenticated; independent scientific adjudication: NOT COMPLETE; FDA probability: NOT ASSIGNED.</strong></p>
          <small>A no-change result means only that two supplied unsigned files report the same inventory, not that the live archive is immutable or independently verified. Changed entries require separate origin and chronology checks.</small>
        </section>}
      </details>
      {capturedScientificGates && <section aria-label="Four independent scientific evidence gates captured source coverage">
        <p><strong>Captured PDF evidence categories: {capturedScientificGates.gatesWithCapturedPdf}/4.</strong>
          {" "}Independently verified categories: <strong>0/4</strong>.
        </p>
        <ul>
          {capturedScientificGates.gates.map(gate => <li key={gate.gateId}>
            <strong>{gate.label}</strong> — {gate.capturedPdfCount} captured PDF(s);
            {" "}{gate.status === "CAPTURED_UNVERIFIED" ? "captured, NOT independently verified" : "no captured PDF"}.
            <details>
              <summary>Required next source check</summary>
              <p>{gate.nextAction}</p>
            </details>
          </li>)}
        </ul>
        <p><strong>Scientific adjudication: NOT COMPLETE. Scientific score: NOT ASSIGNED. FDA probability: NOT ASSIGNED.</strong></p>
        <small>Captured document counts reflect authenticated, rehashed archive metadata only. They do not establish source authorship, verified clinical findings, independent reviewer decisions or a PDUFA outcome.</small>
      </section>}
    </div>}
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

      {result.investigation40 && <div>
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
        <details aria-label="Local A/B scientific worksheet comparison">
          <summary><strong>Compare returned A/B worksheets locally</strong> · 320-task audit</summary>
          <p>Choose the three exported CSVs for this exact trial. Files are read only inside your browser—not uploaded, stored or submitted. This is an untrusted worksheet consistency check, not source authentication or independent adjudication.</p>
          <div>
            <label>320-task inventory CSV <input type="file" accept=".csv,text/csv" aria-label="Choose inventory CSV"
              onChange={event => {
                auditRevision.current++;
                setReviewInventoryFile(event.target.files?.[0] ?? null);
                setLocalAudit(null); setLocalAuditError(""); setComparingFiles(false);
                setLocalSourceByteMatch(null);
    setCapturedArchiveCheck(null);
    setCapturedArchiveError("");
    setCheckingCapturedArchive(false); setLocalSourceByteError(""); setHashingLocalPdf(false);
                setDualSourceBytes(null); setDualSourceError(""); setCheckingDualSource(false);
              }} /></label>
          </div>
          <div>
            <label>Reviewer A worksheet CSV <input type="file" accept=".csv,text/csv" aria-label="Choose reviewer A CSV"
              onChange={event => {
                auditRevision.current++;
                setReviewerAFile(event.target.files?.[0] ?? null);
                setLocalAudit(null); setLocalAuditError(""); setComparingFiles(false);
                setLocalSourceByteMatch(null);
    setCapturedArchiveCheck(null);
    setCapturedArchiveError("");
    setCheckingCapturedArchive(false); setLocalSourceByteError(""); setHashingLocalPdf(false);
                setDualSourceBytes(null); setDualSourceError(""); setCheckingDualSource(false);
              }} /></label>
          </div>
          <div>
            <label>Reviewer B worksheet CSV <input type="file" accept=".csv,text/csv" aria-label="Choose reviewer B CSV"
              onChange={event => {
                auditRevision.current++;
                setReviewerBFile(event.target.files?.[0] ?? null);
                setLocalAudit(null); setLocalAuditError(""); setComparingFiles(false);
                setLocalSourceByteMatch(null);
    setCapturedArchiveCheck(null);
    setCapturedArchiveError("");
    setCheckingCapturedArchive(false); setLocalSourceByteError(""); setHashingLocalPdf(false);
                setDualSourceBytes(null); setDualSourceError(""); setCheckingDualSource(false);
              }} /></label>
          </div>
          <button type="button"
            disabled={!reviewInventoryFile || !reviewerAFile || !reviewerBFile || comparingFiles}
            onClick={() => void compareLocalReviewerWorksheets()}>
            {comparingFiles ? "Comparing worksheets…" : "Compare three CSV files (browser only)"}
          </button>
          {localAuditError && <p role="alert">{localAuditError}</p>}
          {localAudit && <section aria-label="Unverified local reviewer comparison result" role="status">
            <p><strong>{localAudit.validatedTaskRows} exact-trial task rows matched.</strong> No clinical review has been independently verified.</p>
            <p>Candidate entries with syntactically complete source claims: A {localAudit.candidateObservations.A}, B {localAudit.candidateObservations.B}.</p>
            <p>Incomplete source provenance: A {localAudit.missingProvenance.A}, B {localAudit.missingProvenance.B}.</p>
            <p>Missing reviewer names or findings: A {localAudit.incompleteObservations.A}, B {localAudit.incompleteObservations.B}.</p>
            <p>One-sided candidate observations: {localAudit.oneSidedObservations}. Conflicting candidate decisions: {localAudit.conflictingCandidateDecisions}.</p>
            {localAudit.conflictTaskKeys.length > 0 && <details>
              <summary>View disputed trial task keys (not resolved)</summary>
              <ul>{localAudit.conflictTaskKeys.map(key => <li key={key}><code>{key}</code></li>)}</ul>
            </details>}
            <p><strong>Independent adjudication: 0/320. Scientific score: NOT ASSIGNED. FDA approval probability: NOT ASSIGNED.</strong></p>
            <p>
              <button type="button" onClick={() => downloadLocalReviewerAuditReceipt()}>
                Download unverified A/B comparison receipt (JSON)
              </button>
              <small> Local, privacy-minimized diagnostic only; no reviewer identities, raw documents or statements are included. A receipt is not a scientific or regulatory signoff.</small>
            </p>
            <small>Reviewer names, document URLs, claimed hashes and worksheet signatures have not been authenticated; these observations cannot be promoted to verified evidence.</small>
            <details aria-label="Check local source PDF SHA-256 bytes">
              <summary><strong>Compare source PDF bytes with A/B worksheet SHA-256 claims</strong></summary>
              <p>Select one pending exact-trial task and one local source PDF. This computes a SHA-256 checksum in your browser and compares it with the digest claimed in each reviewer worksheet for that task. The PDF is not uploaded. A matching hash proves only byte consistency with an untrusted claim—not authenticity of the original document.</p>
              <label>Scientific task
                <select value={localSourceTaskKey} aria-label="Select scientific task for source PDF"
                  onChange={event => {
                    auditRevision.current++;
                    setLocalSourceTaskKey(event.target.value);
                    setLocalSourceByteMatch(null);
    setCapturedArchiveCheck(null);
    setCapturedArchiveError("");
    setCheckingCapturedArchive(false);
                    setLocalSourceByteError("");
                    setHashingLocalPdf(false);
                    setDualSourceBytes(null);
                    setDualSourceError("");
                    setCheckingDualSource(false);
                  }}>
                  <option value="">Select one task</option>
                  {result.investigation40!.depthReview.tasks.map(task => {
                    const key = task.assessmentId + ":" + task.depthLevel;
                    return <option key={key} value={key}>{key}</option>;
                  })}
                </select>
              </label>
              <label>Local PDF
                <input type="file" accept=".pdf,application/pdf" aria-label="Choose local source PDF"
                  onChange={event => {
                    auditRevision.current++;
                    setLocalSourcePdf(event.target.files?.[0] ?? null);
                    setLocalSourceByteMatch(null);
    setCapturedArchiveCheck(null);
    setCapturedArchiveError("");
    setCheckingCapturedArchive(false);
                    setLocalSourceByteError("");
                    setHashingLocalPdf(false);
                    setDualSourceBytes(null);
                    setDualSourceError("");
                    setCheckingDualSource(false);
                  }} />
              </label>
              <label>Reviewer B local PDF (optional)
                <input type="file" accept=".pdf,application/pdf" aria-label="Choose reviewer B local source PDF"
                  onChange={event => {
                    auditRevision.current++;
                    setLocalReviewerBPdf(event.target.files?.[0] ?? null);
                    setDualSourceBytes(null);
                    setDualSourceError("");
                    setCheckingDualSource(false);
                  }} />
              </label>
              <button type="button" disabled={!localSourcePdf || !localSourceTaskKey || hashingLocalPdf}
                onClick={() => void compareLocalSourcePdfBytes()}>
                {hashingLocalPdf ? "Checking local PDF SHA-256…" : "Compare PDF bytes with A/B hash claims"}
              </button>
              {localSourceByteError && <p role="alert">{localSourceByteError}</p>}
              <p>
                <button type="button"
                  disabled={!localSourcePdf || !localReviewerBPdf || !localSourceTaskKey
                    || hashingLocalPdf || checkingDualSource}
                  onClick={() => void compareTwoLocalPdfBytes()}>
                  {checkingDualSource ? "Checking two local source PDFs…" : "Compare reviewer A and B PDF bytes independently"}
                </button>
                <small> Both PDFs are hashed inside this browser and checked against their respective untrusted worksheet claims. Files are not uploaded or stored.</small>
              </p>
              {dualSourceError && <p role="alert">{dualSourceError}</p>}
              {dualSourceBytes && <section aria-label="Two local PDF byte comparison" role="status">
                <p><strong>Trial task:</strong> {dualSourceBytes.assessmentTaskKey}</p>
                <p>Reviewer A local PDF SHA-256: <code>{dualSourceBytes.reviewerAPdfSha256}</code></p>
                <p>Reviewer B local PDF SHA-256: <code>{dualSourceBytes.reviewerBPdfSha256}</code></p>
                <p>Reviewer A own hash claim: {dualSourceBytes.reviewerAClaim.replaceAll("_", " ")}.</p>
                <p>Reviewer B own hash claim: {dualSourceBytes.reviewerBClaim.replaceAll("_", " ")}.</p>
                <p><strong>PDF byte relationship: {dualSourceBytes.pdfByteRelation.replaceAll("_", " ")}.</strong></p>
                <small>Identical bytes do not prove independent review; different bytes may represent legitimate document versions. Original-source authentication, qualified reviewer identity, clinical adjudication and FDA predictions remain unverified.</small>
              </section>}
              {localSourceByteMatch && result.investigation40?.nctId === "NCT02142738" && <div>
                <button type="button" disabled={checkingCapturedArchive}
                  onClick={() => void compareLocalPdfWithArchivedSnapshot()}>
                  {checkingCapturedArchive ? "Checking captured archive hashes…" : "Compare local PDF against captured scientific archive (read-only)"}
                </button>
                <small> Checks a protected, rehashed PDF archive snapshot for this pilot trial, not reviewer-entered hashes. No local PDF bytes leave the browser. Archived capture alone does NOT establish original authorship or verified clinical evidence.</small>
              </div>}
              {capturedArchiveError && <p role="alert">{capturedArchiveError}</p>}
              {capturedArchiveCheck && <section aria-label="Unverified captured archive byte comparison" role="status">
                <p><strong>Archive comparison: {capturedArchiveCheck.status.replaceAll("_", " ")}.</strong></p>
                <p>Captured PDF snapshots: {capturedArchiveCheck.capturedSnapshotCount}. Exact byte matches: {capturedArchiveCheck.matches.length}.</p>
                {capturedArchiveCheck.matches.map(item =>
                  <p key={item.documentId}>Captured record <code>{item.documentId.slice(0, 8)}</code> ·
                    {" "}{item.gateId.replaceAll("_", " ")} · {item.sourceType.replaceAll("_", " ")}
                  </p>)}
                <p><strong>Source authorship authenticated: NO. Scientific review complete: NO. FDA probability: NOT ASSIGNED.</strong></p>
                <small>Archive snapshot integrity is not independent verification of clinical validity, regulatory provenance or reviewer qualifications.</small>
              </section>}
              {localSourceByteMatch && <div role="status">
                <p><strong>Exact trial task:</strong> {localSourceByteMatch.assessmentTaskKey}</p>
                <p><strong>Calculated local PDF SHA-256:</strong> <code>{localSourceByteMatch.calculatedSha256}</code></p>
                <p>Reviewer A digest claim: {localSourceByteMatch.reviewerA.replaceAll("_", " ")}.</p>
                <p>Reviewer B digest claim: {localSourceByteMatch.reviewerB.replaceAll("_", " ")}.</p>
                <p><strong>Original source authenticated: NO. Reviewer identity verified: NO. Scientific adjudication: 0.</strong></p>
                <small>Worksheet hashes may be incorrect or self-reported; this does not verify publication date, original authorship, trial results, clinical correctness, efficacy or FDA approval.</small>
              </div>}
            </details>
          </section>}
        </details>
      </div>}

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
