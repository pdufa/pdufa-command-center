/** Read-only, fail-closed presentation of the HOP backend source audit.
 * A published CRL archive or approved-product registry is NOT a complete cohort.
 */
export type HopSourceReadiness = {
  status: "RESEARCH_ONLY" | "SOURCE_UNAVAILABLE";
  checkedAt: string;
  publishedLetters: number | null;
  publishedLetterExportDate: string | null;
  approvedApplications: number | null;
  approvedRegistryExportDate: string | null;
  stagedHistoricalCases: number | null;
  sourcePageReviewRows: number | null;
  independentlyVerifiedReviewCycles: number | null;
  modelEligibleReviewCycles: number | null;
  modelValidated: false;
  predictionAvailable: false;
  probability: null;
  denominatorComplete: false;
};

function obj(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? value as Record<string, unknown> : {};
}
function count(value: unknown): number | null {
  return typeof value === "number" && Number.isSafeInteger(value) && value >= 0 ? value : null;
}
function isoDate(value: unknown): string | null {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return null;
  const parsed = new Date(value + "T00:00:00.000Z");
  return Number.isFinite(parsed.getTime()) && parsed.toISOString().slice(0, 10) === value ? value : null;
}

/** Invalid or newly enabled model outputs are never silently passed through. */
export function normalizeHopReadiness(payload: unknown, checkedAt = new Date().toISOString()): HopSourceReadiness {
  const data = obj(payload);
  if (data.status !== "RESEARCH_ONLY" && data.status !== "SOURCE_UNAVAILABLE") {
    throw new Error("Unrecognized HOP audit status");
  }
  if (data.model_validated !== false || data.prediction_available !== false || data.prediction_probability != null) {
    throw new Error("HOP prediction gate changed; independent review required");
  }
  const healthy = data.status === "RESEARCH_ONLY";
  const letters = obj(data.published_crl_source);
  const approved = obj(data.approved_registry_source);
  const pages = obj(data.fda_page_review_worksheet);
  const eligible = count(data.historical_model_eligible);
  // This display is approved only for a quarantined, zero-training cohort.
  if (healthy && eligible !== 0) throw new Error("Unreviewed HOP training data eligibility");
  if (healthy && (data.historical_training_data_connected !== false
      || (letters.published_letter_records != null && count(letters.published_letter_records) === null)
      || (approved.application_records != null && count(approved.application_records) === null))) {
    throw new Error("Invalid HOP source evidence state");
  }
  return {
    status: data.status,
    checkedAt,
    publishedLetters: healthy ? count(letters.published_letter_records) : null,
    publishedLetterExportDate: healthy ? isoDate(letters.fda_export_date) : null,
    approvedApplications: healthy ? count(approved.application_records) : null,
    approvedRegistryExportDate: healthy ? isoDate(approved.source_export_date) : null,
    stagedHistoricalCases: healthy ? count(data.historical_staged) : null,
    sourcePageReviewRows: healthy ? count(pages.published_letter_review_rows) : null,
    independentlyVerifiedReviewCycles: healthy ? count(pages.independently_verified_review_cycle_outcomes) : null,
    modelEligibleReviewCycles: healthy ? eligible : null,
    modelValidated: false,
    predictionAvailable: false,
    probability: null,
    denominatorComplete: false,
  };
}
