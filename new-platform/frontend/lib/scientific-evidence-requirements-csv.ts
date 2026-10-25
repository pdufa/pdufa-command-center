/**
 * Read-only exact-NCT evidence-input inventory for the isolated science preview.
 * This is NOT an assessment result, review attestation or approval prediction.
 * Every independently reviewed gate is explicitly NOT COMPLETE.
 */
export type ScientificInputRequirement = {
  id: string;
  label: string;
  available: boolean;
  evidenceLevel: "archive_verified" | "registry_field_present" | "missing_in_archive" | "independent_review_not_loaded";
  sourcePath: string | null;
  nextAction: string;
  independentlyVerified: false;
};

export type ScientificInputAudit = {
  nctId: string;
  requirements: ScientificInputRequirement[];
  missingRequirementIds: string[];
  analysisReadiness: {
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
    verdict: string;
  };
  externalEvidenceVerified: false;
  scientificScore: null;
  fdaApprovalProbability: null;
};

const REQUIREMENT_IDS = [
  "archive_integrity", "indication", "design", "eligibility", "interventions",
  "enrollment", "timeline", "registered_primary", "primary_analysis",
  "safety_denominators", "participant_flow", "baseline", "protocol_sap",
  "published_results", "independent_replication", "official_regulatory",
] as const;

function reject(): never {
  throw new Error("Scientific input checklist export blocked: incomplete or unverified data.");
}

function csvCell(value: string | number): string {
  let safe = String(value).replace(/[\u0000-\u001f\u007f]+/g, " ");
  // Spreadsheet formula injection may follow leading Unicode/ASCII spaces.
  if (/^\s*[=+\-@]/u.test(safe)) safe = "'" + safe;
  return '"' + safe.replaceAll('"', '""') + '"';
}

/** Validate independently again at download time; do not trust prior UI display. */
export function buildScientificEvidenceRequirementsCsv(audit: ScientificInputAudit): string {
  if (!audit || !/^NCT[0-9]{8}$/.test(audit.nctId)
      || audit.externalEvidenceVerified !== false
      || audit.scientificScore !== null || audit.fdaApprovalProbability !== null
      || !Array.isArray(audit.requirements) || audit.requirements.length !== 16
      || !Array.isArray(audit.missingRequirementIds)
      || audit.analysisReadiness?.requirementsTotal !== 16
      || audit.analysisReadiness.readyForFullScientificConclusion !== false
      || audit.analysisReadiness.verdict !== "NOT_READY"
      || audit.analysisReadiness.passFail !== "FAIL_INCOMPLETE_INPUTS"
      || audit.scientificReluctance?.grade !== "F"
      || audit.scientificReluctance.level !== "CRITICAL"
      || audit.scientificReluctance.reluctanceToConclude !== "MAXIMUM"
      || audit.scientificReluctance.verdict !== "WITHHOLD_SCIENTIFIC_CONCLUSION") reject();

  const rows: string[] = [[
    "nct_id", "requirement_number", "requirement_id", "evidence_requirement",
    "input_status", "source_evidence_level", "archive_source_field", "next_review_action",
    "independently_verified", "scientific_score", "fda_approval_probability",
  ].map(csvCell).join(",")];
  let inputsPresent = 0;
  const missingIds: string[] = [];
  for (let i = 0; i < REQUIREMENT_IDS.length; i++) {
    const req = audit.requirements[i];
    if (!req || req.id !== REQUIREMENT_IDS[i]
        || typeof req.label !== "string" || !req.label.trim() || req.label.length > 180
        || typeof req.nextAction !== "string" || !req.nextAction.trim()
        || req.nextAction.length > 600 || typeof req.available !== "boolean"
        || req.independentlyVerified !== false) reject();
    const external = i >= 12;
    let status = "MISSING_IN_ARCHIVE";
    if (external) {
      if (req.available !== false || req.evidenceLevel !== "independent_review_not_loaded"
          || req.sourcePath !== null) reject();
      status = "INDEPENDENT_REVIEW_NOT_COMPLETE";
    } else {
      if (typeof req.sourcePath !== "string" || !req.sourcePath.trim()
          || req.sourcePath.length > 300
          || req.evidenceLevel !== (i === 0 ? "archive_verified"
            : req.available ? "registry_field_present" : "missing_in_archive")
          || (i === 0 && req.available !== true)) reject();
      if (req.available) status = "ARCHIVE_INPUT_PRESENT_NOT_SCIENTIFICALLY_VERIFIED";
    }
    if (req.available) inputsPresent++;
    else missingIds.push(req.id);
    rows.push([
      audit.nctId, i + 1, req.id, req.label, status, req.evidenceLevel,
      req.sourcePath ?? "", req.nextAction, "FALSE", "NOT_ASSIGNED", "NOT_ASSIGNED",
    ].map(csvCell).join(","));
  }
  if (audit.missingRequirementIds.length !== missingIds.length
      || !audit.missingRequirementIds.every((id, i) => id === missingIds[i])
      || audit.analysisReadiness.requirementsCovered !== inputsPresent
      || !Number.isInteger(audit.analysisReadiness.coveragePercent)
      || Math.abs(audit.analysisReadiness.coveragePercent - inputsPresent * 100 / 16) > 0.5) reject();

  return rows.join("\r\n") + "\r\n";
}
