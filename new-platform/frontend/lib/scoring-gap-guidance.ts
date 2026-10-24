/** Evidence requirements for the four saved-score gaps.
 * Guidance NEVER substitutes for a verified numeric score, independent public
 * probability, FDA hard-gate clearance, or a dated financing PASS.
 */
export type ScoringGapGuidance = {
  dataset: string;
  datasetUrl: string;
  nextCheck: string;
  caveat: string;
};
const base = "https://github.com/pdufa/pdufa-command-center/blob/main/";
const requirements: Record<string, { path: string; nextCheck: string; caveat: string }> = {
  "Trade Score coverage": {
    path: "data/pdufa_candidates.csv",
    nextCheck: "For each exact event, collect a separately defined and dated trade_score with its methodology and evidence. Do not rename the clinical science/regulatory/safety/CMC average as a verified trading score.",
    caveat: "No saved trade score is verified merely because a stock price or clinical grade is present.",
  },
  "Public PoA coverage": {
    path: "data/pdufa_candidates.csv",
    nextCheck: "For the matching drug/application and review cycle, obtain an attributable public approval estimate, its publication date, and its source; populate public_approval_probability only after identity and provenance checks.",
    caveat: "An internal estimate cannot be copied into the public PoA field as an independent forecast.",
  },
  "FDA V3 calculated probability": {
    path: "data/fda_review_engine.csv",
    nextCheck: "Review the exact FDA application and its statistics, clinical, safety, CMC, inspection, labeling, and freshness gates. Calculate fda_probability only if the model's required gates and evidence are valid.",
    caveat: "Missing agency-review evidence and REVIEW gates remain unresolved; they do not imply a 0% probability.",
  },
  "Post Phase 3 entry gates": {
    path: "data/step7_financing_review.csv",
    nextCheck: "Verify the exact trial and Phase 3 outcome, dated financing closes from SEC/issuer documents, dilution risk, and any separately required price/volume checks. Record an explicit gate PASS only for the individual requirement supported.",
    caveat: "A historical financing claim or a completed offering alone does not clear all entry gates or authorize a trade.",
  },
};
export function scoringGapGuidance(check: { Test: string; Status: string }): ScoringGapGuidance | null {
  if (check.Status !== "DATA GAP" && check.Status !== "REVIEW") return null;
  const item = requirements[check.Test];
  if (!item) return null;
  return {
    dataset: item.path,
    datasetUrl: base + item.path,
    nextCheck: item.nextCheck,
    caveat: item.caveat,
  };
}
