"use client";

import { useEffect, useRef, useState } from "react";

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
type GradePair = {
  nctId: string;
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
  depthReview: { requiredTasks: number; completedTasks: 0 };
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

function validGradePair(value: unknown, nctId: string): value is GradePair {
  if (!object(value) || !object(value.analysisReadiness)
      || !object(value.scientificReluctance) || value.nctId !== nctId
      || value.externalEvidenceVerified !== false
      || value.scientificScore !== null || value.fdaApprovalProbability !== null) return false;
  const a = value.analysisReadiness;
  const r = value.scientificReluctance;
  return typeof a.grade === "string" && /^[A-F]$/.test(a.grade)
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
  return v.required_assessments === 40 && v.verified_assessments === 0
    && v.ready_for_analysis === false && v.scientific_score === null
    && v.approval_probability === null
    && d.requiredTasks === 320 && d.completedTasks === 0
    && value.layers.every((layer: unknown) => object(layer)
      && typeof layer.id === "string"
      && Array.isArray(layer.assessments) && layer.assessments.length === 5
      && layer.assessments.every((a: unknown) => typeof a === "string"));
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
  const domains = source.domains;
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
  const pending = useRef<AbortController | null>(null);

  useEffect(() => {
    pending.current?.abort();
    setResult(null);
    setError("");
    setLoading(false);
    return () => pending.current?.abort();
  }, [exactId]);

  async function load() {
    if (!exactId || !/^TRIAL\|NCT[0-9]{8}$/.test(exactId)) return;
    pending.current?.abort();
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

  const valid = /^TRIAL\|NCT[0-9]{8}$/.test(exactId);
  return <section aria-label="Scientific Assessment">
    <button type="button" disabled={!valid || loading} onClick={() => void load()}>
      {loading ? "Checking scientific evidence…" : "Scientific Assessment · 20 levels / 40 assessments"}
    </button>
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

      {result.investigation40 ? <details>
        <summary><strong>8 scientific layers · 40 assessments</strong>
          {" · "} {result.investigation40.verification.verified_assessments}/40 independently verified
        </summary>
        {result.investigation40.layers.map(layer =>
          <details key={layer.id}>
            <summary>{pretty(layer.id)} · {layer.assessments.length} assessments</summary>
            <ol>{layer.assessments.map(item =>
              <li key={item}>{pretty(item)} · independent review pending</li>)}</ol>
          </details>
        )}
        <p>{result.investigation40.depthReview.completedTasks}/{result.investigation40.depthReview.requiredTasks} planned in-depth review tasks completed.</p>
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
