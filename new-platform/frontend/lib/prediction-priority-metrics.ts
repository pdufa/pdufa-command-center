/**
 * Proposed research-prediction priority catalog, kept separate from the
 * existing 7-category P/J/G research scores. Ranking is provisional,
 * NOT learned feature importance or validated FDA model weights.
 */
export type PredictionMetricSpec = Readonly<{
  rank: number;
  label: string;
  unit: "rating" | "count" | "diagnostic";
}>;

const proposed: ReadonlyArray<readonly [string, PredictionMetricSpec["unit"]]> = [
  // Critical factors: visible without a click (1–12).
  ["Primary endpoint success", "rating"],
  ["Clinical effect size", "rating"],
  ["Statistical power and multiplicity", "rating"],
  ["Randomization, blinding and controls", "rating"],
  ["Serious adverse events and deaths", "rating"],
  ["Manufacturing and quality readiness (CMC)", "rating"],
  ["Primary endpoint suitability", "rating"],
  ["FDA communications and prior regulatory concerns", "rating"],
  ["Confidence intervals and statistical precision", "rating"],
  ["Protocol execution and missing-data handling", "rating"],
  ["Patient selection and eligibility quality", "rating"],
  ["Information available before prediction date", "count"],

  // Major safety, regulatory and evidence factors: collapsed (13–24).
  ["Overall adverse-event burden", "rating"],
  ["Treatment-related discontinuations", "rating"],
  ["FDA application and filing readiness", "rating"],
  ["Consistency and replication across trials", "rating"],
  ["Durability and clinical meaningfulness", "rating"],
  ["Dose- and exposure-related safety", "rating"],
  ["Long-term and subgroup safety", "rating"],
  ["Labeling and postmarketing risk management", "rating"],
  ["Verification of primary sources", "count"],
  ["Critical missing evidence", "count"],
  ["Conflicting scientific findings", "count"],
  ["Open manufacturing or inspection concerns", "count"],

  // Historical forecasting and quality controls: collapsed (25–36).
  ["Historical disease/indication similarity", "rating"],
  ["Historical endpoint and statistical similarity", "rating"],
  ["Historical efficacy similarity", "rating"],
  ["Historical safety similarity", "rating"],
  ["Historical FDA pathway and precedent similarity", "rating"],
  ["Overall historical comparator quality", "rating"],
  ["Effective historical sample size", "count"],
  ["Approval and nonapproval outcome distribution", "count"],
  ["Historical prediction accuracy and calibration", "diagnostic"],
  ["Prediction stability under sensitivity tests", "diagnostic"],
  ["Prediction uncertainty", "diagnostic"],
  ["Clinical evidence versus FDA precedent agreement", "rating"],

  // Supporting biology and clinical context: collapsed (37–48).
  ["Secondary endpoint results", "rating"],
  ["FDA designations and development pathways", "rating"],
  ["Historical patient-population similarity", "rating"],
  ["Historical trial-design similarity", "rating"],
  ["Historical mechanism-of-action similarity", "rating"],
  ["Biomarker and target engagement", "rating"],
  ["Mechanism-of-action strength", "rating"],
  ["Biological target validation", "rating"],
  ["Pharmacokinetics, exposure and delivery", "rating"],
  ["Preclinical toxicity and therapeutic window", "rating"],
  ["Unmet medical need", "rating"],
  ["Disease severity", "rating"],

  // Background science and commercial context: collapsed (49–60).
  ["Disease subtypes and biomarkers", "rating"],
  ["Existing treatment effectiveness", "rating"],
  ["Animal-model translation", "rating"],
  ["Preclinical reproducibility", "rating"],
  ["Laboratory efficacy", "rating"],
  ["Mechanistic differentiation", "rating"],
  ["Competitive treatment positioning", "rating"],
  ["Reimbursement and adoption outlook", "rating"],
  ["Intellectual property and exclusivity", "rating"],
  ["Commercial manufacturing scalability", "rating"],
  ["Addressable treatment population", "rating"],
  ["Disease prevalence and incidence", "rating"],
];

export const PREDICTION_METRICS: ReadonlyArray<PredictionMetricSpec> =
  proposed.map(([label, unit], index) => ({rank: index + 1, label, unit}));

export const PRIMARY_PREDICTION_METRICS = PREDICTION_METRICS.slice(0, 12);
export const SECONDARY_PREDICTION_GROUPS = [
  {title:"Safety, regulatory and evidence risks", start:13, end:24},
  {title:"Historical comparisons and forecast reliability", start:25, end:36},
  {title:"Supporting clinical and biological context", start:37, end:48},
  {title:"Background science and commercial context", start:49, end:60},
] as const;

export function proposedMetricValue(metric: PredictionMetricSpec): string {
  // This catalog has no validated per-trial ratings. Never join the 7-category
  // heuristic score to a distinct 60-slot factor without adjudicated mapping.
  return metric.unit === "rating" ? "— / 100" :
    metric.unit === "count" ? "— / —" : "Not validated";
}
