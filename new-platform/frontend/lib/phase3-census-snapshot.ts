/**
 * Dated exact-lead-sponsor Phase 3 census. A conservative, source-backed
 * RESEARCH SNAPSHOT and explicitly NOT the qualified PDUFA Pipeline count.
 * Keep independent market-cap/sponsor/eligibility evidence gates in place.
 *
 * Source: data/phase3_all_years_300m_10b_status.json, generated 2026-10-26.
 */
export const PHASE3_CENSUS_SOURCE = "https://github.com/pdufa/pdufa-command-center/blob/main/data/phase3_all_years_300m_10b_status.json";
export const PHASE3_CENSUS_SNAPSHOT = {
  generated_at: "2026-10-26T12:21:15.972309+00:00",
  registry_phase3_industry_trials_examined: 25020,
  unique_phase3_trials_in_verified_market_cap_range: 741,
  unique_companies_with_matching_trials: 130,
  registry_companies: 717,
  market_cap_eligible_tickers: 182,
  market_cap_unavailable_tickers: 300,
  trial_records_with_unavailable_market_cap: 10,
  ambiguous_sponsor_records: 0,
  complete_registry_pagination: true,
  scope: "All years, Phase 3 interventional trials, industry lead sponsor matched exactly to currently US-listed company, market cap $300M-$10B",
  coverage_note: "Conservative lower bound: exact lead-sponsor matching only. Collaborator/licensing trials, renamed subsidiaries, and missing market caps not included; not a fully exhaustive company-associated census.",
} as const;

type RecordLike = Record<string, unknown>;
function record(value: unknown): value is RecordLike {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}
function whole(value: unknown): value is number {
  return typeof value === "number" && Number.isSafeInteger(value) && value >= 0;
}

export type Phase3CensusSummary = {
  asOf: string;
  industryPhase3Examined: number;
  matchedPhase3Trials: number;
  matchedCompanies: number;
  eligibleMarketCapTickers: number;
  unavailableMarketCapTickers: number;
  unavailableMarketCapTrialRecords: number;
  qualifiedPipelineTotal: null;
  completePipelineQualification: false;
  qualifiedFdaDesignationCount: null;
  source: typeof PHASE3_CENSUS_SOURCE;
};

/** Refuse edited, internally conflicting or misleading source totals. */
export function auditPhase3CensusSnapshot(value: unknown): Phase3CensusSummary {
  if (!record(value)
      || value.scope !== PHASE3_CENSUS_SNAPSHOT.scope
      || value.complete_registry_pagination !== true
      || value.coverage_note !== PHASE3_CENSUS_SNAPSHOT.coverage_note
      || typeof value.generated_at !== "string"
      || Number.isNaN(Date.parse(value.generated_at))
      || !/^\d{4}-\d{2}-\d{2}T/.test(value.generated_at)
      || ["registry_phase3_industry_trials_examined",
          "unique_phase3_trials_in_verified_market_cap_range",
          "unique_companies_with_matching_trials", "registry_companies",
          "market_cap_eligible_tickers", "market_cap_unavailable_tickers",
          "trial_records_with_unavailable_market_cap",
          "ambiguous_sponsor_records"].some(id => !whole(value[id]))) {
    throw new Error("Phase 3 census snapshot refused: incomplete or invalid source.");
  }

  const total = value.registry_phase3_industry_trials_examined as number;
  const trials = value.unique_phase3_trials_in_verified_market_cap_range as number;
  const companies = value.unique_companies_with_matching_trials as number;
  const eligible = value.market_cap_eligible_tickers as number;
  const listed = value.registry_companies as number;
  const missingTickers = value.market_cap_unavailable_tickers as number;
  const missingTrials = value.trial_records_with_unavailable_market_cap as number;
  const ambiguous = value.ambiguous_sponsor_records as number;

  if (trials > total || companies > eligible || eligible > listed
      || missingTickers > listed || missingTrials > total || ambiguous > total
      || Object.prototype.hasOwnProperty.call(value, "qualifiedPipelineTotal")
      || Object.prototype.hasOwnProperty.call(value, "pipelineQualifiedTrials")
      || Object.prototype.hasOwnProperty.call(value, "fdaDesignationCount")) {
    throw new Error("Phase 3 census snapshot refused: false Pipeline qualification or totals.");
  }

  return {
    asOf: value.generated_at,
    industryPhase3Examined: total,
    matchedPhase3Trials: trials,
    matchedCompanies: companies,
    eligibleMarketCapTickers: eligible,
    unavailableMarketCapTickers: missingTickers,
    unavailableMarketCapTrialRecords: missingTrials,
    qualifiedPipelineTotal: null,
    completePipelineQualification: false,
    qualifiedFdaDesignationCount: null,
    source: PHASE3_CENSUS_SOURCE,
  };
}
