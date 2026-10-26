/**
 * Read-only source INPUT dependency crosswalk for the 800-task plan.
 * Links assessment layers to the pre-existing sixteen archived/independent
 * evidence requirements, without asserting that any review was completed.
 */
import { buildScientificDepthReviewCsv, type ScientificDepthMatrix } from "./scientific-depth-review-csv";
import {
  buildScientificEvidenceRequirementsCsv,
  type ScientificInputAudit,
  type ScientificInputRequirement,
} from "./scientific-evidence-requirements-csv";

/**
 * Dependencies are deliberately at the LAYER level, not fabricated
 * claim-by-claim source adjudications. Multiple layers can share a gate.
 */
export const SCIENTIFIC_800_SOURCE_DEPENDENCIES = [
  ["trial_design", [
    "archive_integrity", "design", "eligibility", "interventions",
    "enrollment", "registered_primary", "protocol_sap",
  ]],
  ["efficacy", ["registered_primary", "primary_analysis", "published_results"]],
  ["safety", ["safety_denominators", "published_results", "participant_flow"]],
  ["biological_rationale", ["indication", "independent_replication"]],
  ["statistical_integrity", [
    "enrollment", "primary_analysis", "participant_flow", "baseline", "protocol_sap",
  ]],
  ["evidence_reproducibility", [
    "archive_integrity", "published_results", "independent_replication",
  ]],
  ["regulatory", ["official_regulatory", "protocol_sap"]],
  ["timeline_and_uncertainty", ["timeline", "published_results", "official_regulatory"]],
] as const;

const ALL_REQUIREMENTS = new Set([
  "archive_integrity", "indication", "design", "eligibility", "interventions",
  "enrollment", "timeline", "registered_primary", "primary_analysis",
  "safety_denominators", "participant_flow", "baseline", "protocol_sap",
  "published_results", "independent_replication", "official_regulatory",
]);

export type Scientific800LayerEvidence = {
  layerId: string;
  assessmentIds: string[];
  pendingTasks: 100;
  independentlyReviewedTasks: 0;
  sourceInputsPresent: number;
  sourceInputsRequired: number;
  dependencies: Array<Pick<ScientificInputRequirement,
    "id" | "label" | "available" | "evidenceLevel" | "nextAction">>;
};

export type Scientific800EvidenceMap = {
  nctId: string;
  totalPendingTasks: 800;
  independentlyReviewedTasks: 0;
  independentlyVerifiedEvidenceSources: 0;
  readyForScientificConclusion: false;
  fdaApprovalProbability: null;
  layers: Scientific800LayerEvidence[];
};

/** Never infer source availability from the task plan. Validate the LIVE
 * archived input audit independently and refuse mismatched exact NCT IDs.
 */
export function buildScientific800EvidenceMap(
  matrix: ScientificDepthMatrix,
  audit: ScientificInputAudit,
): Scientific800EvidenceMap {
  // Existing strict checks prohibit forged scientific scores, pseudo-verified
  // archival fields, missing tasks and fake review or grade promotion.
  buildScientificDepthReviewCsv(matrix);
  buildScientificEvidenceRequirementsCsv(audit);
  if (matrix.nctId !== audit.nctId
      || SCIENTIFIC_800_SOURCE_DEPENDENCIES.length !== 8
      || matrix.layers.length !== 8) {
    throw new Error("Scientific 800 evidence map blocked: exact trial or layer mismatch.");
  }

  const requirements = new Map(audit.requirements.map(r => [r.id, r]));
  const observedIds = new Set<string>();
  const layers: Scientific800LayerEvidence[] = [];
  for (let i = 0; i < SCIENTIFIC_800_SOURCE_DEPENDENCIES.length; i++) {
    const [layerId, requiredIds] = SCIENTIFIC_800_SOURCE_DEPENDENCIES[i];
    const sourceLayer = matrix.layers[i];
    if (sourceLayer.id !== layerId
        || sourceLayer.assessments.length !== 5
        || new Set(requiredIds).size !== requiredIds.length) {
      throw new Error("Scientific 800 evidence map blocked: catalog mismatch.");
    }
    const dependencies = requiredIds.map(id => {
      const source = requirements.get(id);
      if (!source) throw new Error("Scientific 800 evidence map blocked: source requirement missing.");
      observedIds.add(id);
      return {
        id: source.id,
        label: source.label,
        available: source.available,
        evidenceLevel: source.evidenceLevel,
        nextAction: source.nextAction,
      };
    });
    layers.push({
      layerId,
      assessmentIds: sourceLayer.assessments.map(a => layerId + "." + a),
      pendingTasks: 100,
      independentlyReviewedTasks: 0,
      sourceInputsPresent: dependencies.filter(d => d.available).length,
      sourceInputsRequired: dependencies.length,
      dependencies,
    });
  }
  if (observedIds.size !== ALL_REQUIREMENTS.size
      || [...observedIds].some(id => !ALL_REQUIREMENTS.has(id))
      || layers.reduce((n, l) => n + l.pendingTasks, 0) !== 800) {
    throw new Error("Scientific 800 evidence map blocked: incomplete source coverage.");
  }
  return {
    nctId: matrix.nctId,
    totalPendingTasks: 800,
    independentlyReviewedTasks: 0,
    independentlyVerifiedEvidenceSources: 0,
    readyForScientificConclusion: false,
    fdaApprovalProbability: null,
    layers,
  };
}
