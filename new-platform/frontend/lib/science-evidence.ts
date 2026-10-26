/** SCIENCE v1: evidence-gated research contract. Independent of the 21 legacy list scores. */
export const SCIENCE_SCHEMA_VERSION = "science-evidence-v1" as const;
export const SCIENCE_LAYERS = [
  "Clinical efficacy", "Statistical integrity", "Trial design", "Safety",
  "Reproducibility", "Regulatory pathway", "Manufacturing and quality",
  "External validity and comparators",
] as const;
export const SCIENCE_ASSESSMENTS_PER_LAYER = 5;
export const SCIENCE_ASSESSMENT_COUNT = 40;
export const SCIENCE_DEPTH_LEVELS = 20;
export type ScienceList = "GEM_JR" | "GEM" | "WT";
export type ScienceEvidence = {
  sourceUrl: string;
  publishedAt: string;
  verifiedAt: string | null;
  verified: boolean;
  note: string;
};
export type ScienceAssessment = {
  id: string;
  layer: number;
  depthLevel: number;
  score: number | null;
  confidence: number | null;
  evidence: ScienceEvidence[];
  missingEvidence: string[];
};
export type ScienceDossier = {
  schemaVersion: typeof SCIENCE_SCHEMA_VERSION;
  programId: string;
  list: ScienceList;
  cutoffDate: string;
  assessments: ScienceAssessment[];
};
export type ScienceReadiness = {
  status: "READY_FOR_ANALYSIS" | "RELUCTANT";
  evidenceComplete: boolean;
  missing: string[];
  verifiedAssessments: number;
  totalAssessments: number;
  approvalProbability: null;
};
const validDate = (v: string) => /^\\d{4}-\\d{2}-\\d{2}$/.test(v) && Number.isFinite(Date.parse(v));
const bounded = (v: number | null) => v === null || (Number.isFinite(v) && v >= 0 && v <= 100);
/** Conservative gate: coverage never becomes a predicted FDA probability. */
export function assessScienceReadiness(dossier: ScienceDossier): ScienceReadiness {
  const missing: string[] = [];
  if (dossier.schemaVersion !== SCIENCE_SCHEMA_VERSION) missing.push("Unsupported schema");
  if (!dossier.programId) missing.push("Missing program identity");
  if (!["GEM_JR", "GEM", "WT"].includes(dossier.list)) missing.push("Unsupported list");
  if (!validDate(dossier.cutoffDate)) missing.push("Invalid evidence cutoff");
  if (dossier.assessments.length !== SCIENCE_ASSESSMENT_COUNT) missing.push("40 assessments required");
  const ids = new Set<string>();
  let verifiedAssessments = 0;
  for (const a of dossier.assessments) {
    if (ids.has(a.id)) missing.push("Duplicate assessment: " + a.id);
    ids.add(a.id);
    const structural = !!a.id && Number.isInteger(a.layer) && a.layer >= 1 && a.layer <= SCIENCE_LAYERS.length &&
      Number.isInteger(a.depthLevel) && a.depthLevel >= 1 && a.depthLevel <= SCIENCE_DEPTH_LEVELS &&
      bounded(a.score) && bounded(a.confidence);
    if (!structural) missing.push("Invalid assessment: " + a.id);
    const sourcesValid = a.evidence.length > 0 && a.evidence.every(e =>
      e.verified === true && !!e.sourceUrl && validDate(e.publishedAt) &&
      !!e.verifiedAt && validDate(e.verifiedAt) &&
      validDate(dossier.cutoffDate) && e.publishedAt <= dossier.cutoffDate &&
      e.verifiedAt <= dossier.cutoffDate);
    if (!sourcesValid || a.score === null || a.confidence === null || a.missingEvidence.length > 0)
      missing.push("Unverified or incomplete evidence: " + a.id);
    else if (structural) verifiedAssessments++;
  }
  return {
    status: missing.length === 0 ? "READY_FOR_ANALYSIS" : "RELUCTANT",
    evidenceComplete: missing.length === 0,
    missing, verifiedAssessments, totalAssessments: SCIENCE_ASSESSMENT_COUNT,
    approvalProbability: null,
  };
}
