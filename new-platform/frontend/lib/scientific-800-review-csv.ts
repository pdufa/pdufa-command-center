/**
 * Separate 40-assessment × 20-method, 800-row review INVENTORY.
 * No source content, scientific grade or FDA probability is assigned.
 * Intentionally preserves the legacy eight-depth/320-task A/B workflow.
 */
import { buildScientificDepthReviewCsv, type ScientificDepthMatrix } from "./scientific-depth-review-csv";

const DEPTHS = [
  ["document_reading", "Document Reading"],
  ["hypothesis_understanding", "Hypothesis Understanding"],
  ["biological_investigation", "Biological Investigation"],
  ["evidence_validation", "Evidence Validation"],
  ["critical_challenge", "Critical Challenge"],
  ["cross_disciplinary_integration", "Cross-Disciplinary Integration"],
  ["predictive_modeling", "Predictive Modeling"],
  ["scientific_synthesis", "Scientific Synthesis"],
  ["causal_inference", "Causal Inference"],
  ["systems_biology_modeling", "Systems Biology Modeling"],
  ["adversarial_review", "Adversarial Review"],
  ["multi_model_adjudication", "Multi-Model Adjudication"],
  ["quantitative_pharmacology", "Quantitative Pharmacology"],
  ["patient_heterogeneity", "Patient Heterogeneity"],
  ["bayesian_integration", "Bayesian Integration"],
  ["external_validity", "External Validity"],
  ["historical_failure_analysis", "Historical Failure Analysis"],
  ["regulatory_counterfactual", "Regulatory Counterfactual"],
  ["reproducibility_audit", "Reproducibility Audit"],
  ["red_team_adjudication", "Red-Team Adjudication"],
] as const;

function cell(value: string | number): string {
  let safe = String(value).replace(/[\r\n\t]+/g, " ");
  if (/^\s*[=+\-@]/.test(safe)) safe = "'" + safe;
  return '"' + safe.replaceAll('"', '""') + '"';
}

/** Exports only a blank review plan after the source API's existing
 * unverified 320-task inventory has passed strict structural validation.
 * This cannot convert an archive presence flag into reviewed evidence.
 */
export function buildScientific800ReviewCsv(matrix: ScientificDepthMatrix): string {
  // The legacy validator rejects incomplete/forged 40-assessment matrices.
  buildScientificDepthReviewCsv(matrix);
  if (DEPTHS.length !== 20
      || new Set(DEPTHS.map(([id]) => id)).size !== 20) {
    throw new Error("Scientific 800 review export blocked: method catalog drift.");
  }
  const fields = [
    "nct_id", "assessment_id", "depth_level", "depth_id", "depth_name",
    "review_status", "primary_source_url", "source_sha256", "public_source_date",
    "reviewer_a_identity", "reviewer_b_identity", "qualified_review_status",
    "scientific_score", "fda_approval_probability",
  ];
  const rows: string[] = [fields.map(cell).join(",")];
  const seen = new Set<string>();
  for (const layer of matrix.layers) {
    for (const assessment of layer.assessments) {
      const assessmentId = layer.id + "." + assessment;
      for (let index = 0; index < DEPTHS.length; index++) {
        const [depthId, name] = DEPTHS[index];
        const key = assessmentId + ":" + (index + 1);
        if (seen.has(key)) {
          throw new Error("Scientific 800 review export blocked: duplicate task.");
        }
        seen.add(key);
        rows.push([
          matrix.nctId, assessmentId, index + 1, depthId, name,
          "PENDING_INDEPENDENT_REVIEW", "", "", "",
          "NOT_ASSIGNED", "NOT_ASSIGNED", "NOT_VERIFIED",
          "NOT_ASSIGNED", "NOT_ASSIGNED",
        ].map(cell).join(","));
      }
    }
  }
  if (seen.size !== 800 || rows.length !== 801) {
    throw new Error("Scientific 800 review export blocked: missing tasks.");
  }
  return rows.join("\r\n") + "\r\n";
}
