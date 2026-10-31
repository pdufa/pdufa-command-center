/**
 * Patient population research scope for assessment #1.
 * Use only the immutable October 26, 2026 census with exact issuer/NCT
 * matches and documented $300M-$10B capitalization at census time.
 * Completed registry status is NOT proof of a favorable readout, an active
 * commercial program, approval, or a PDUFA target.
 */
import type { Phase3CensusRows, Phase3CensusTrial } from "./phase3-census-rows";
import {
  sourcesForPhase3Trial,
  type Phase3CensusSourceDirectory,
  type Phase3CompanySources,
} from "./phase3-census-sources";

export const PATIENT_POPULATION_ASSESSMENT = "#1";
export const PATIENT_POPULATION_MARKET_CAP_MIN = 300_000_000;
export const PATIENT_POPULATION_MARKET_CAP_MAX = 10_000_000_000;
export const PATIENT_POPULATION_BASELINE_TRIALS = 375;
export const PATIENT_POPULATION_BASELINE_COMPANIES = 76;

export type PostPhase3PopulationTrial = {
  trial: Phase3CensusTrial;
  companySources: Phase3CompanySources;
  diseasePopulation: number | null;
  eligibleUsPatients: number | null;
  eligibleGlobalPatients: number | null;
  populationEvidenceCompleteness: number | null;
  populationLastVerified: null;
};

export const PATIENT_POPULATION_DETAIL_SECTIONS = [
  { title: "Disease epidemiology", detail: "Prevalence versus annual incidence; age, sex, disease burden, source geography and calendar year." },
  { title: "Diagnosis rate", detail: "Diagnosed versus undiagnosed patients and the source-backed diagnostic access assumptions." },
  { title: "FDA indication eligibility", detail: "Candidate label, age, severity, line of therapy and biomarkers; distinguish anticipated from approved labeling." },
  { title: "Phase 3 enrollment criteria", detail: "Exact NCT study inclusion/exclusion, population, subgroup definitions and generalizability." },
  { title: "Patient exclusions", detail: "Contraindications, comorbidities, prior treatments and competing eligibility criteria." },
  { title: "U.S. geographic breakdown", detail: "National and regional patient estimates where reliable published evidence exists." },
  { title: "International populations", detail: "Country-level eligible populations with separate regulatory and access constraints." },
  { title: "Treatment demand", detail: "Untreated pool, new annual patients, treatment duration, repeat versus one-time therapy." },
  { title: "Competitor overlap", detail: "Currently treated population, alternative drugs, expected switching and potential double counting." },
  { title: "Low / base / high scenarios", detail: "Transparent sensitivity ranges across epidemiology, diagnosis, indications and exclusions." },
  { title: "Source verification", detail: "Dated CDC, NIH/NCI, FDA, trial registry, peer-reviewed epidemiology and issuer evidence with contradictory claims flagged." },
  { title: "Readiness and confidence", detail: "Per-field evidence completeness, uncertainty, missing-source reasons and independent review status." },
] as const;

/** Never promote unknown patient counts, status or dates into a numerical estimate. */
export function selectPostPhase3PopulationTrials(
  inventory: Phase3CensusRows, directory: Phase3CensusSourceDirectory,
): PostPhase3PopulationTrial[] {
  if (inventory.rows.length !== 741 || directory.trialCount !== 741
      || directory.scope !== "RESEARCH_POINTERS_ONLY") {
    throw new Error("Patient-population census could not be verified.");
  }
  const rows: PostPhase3PopulationTrial[] = [];
  const ncts = new Set<string>();
  for (const trial of inventory.rows) {
    if (trial.status !== "COMPLETED") continue;
    if (ncts.has(trial.nctId)
        || trial.pipelineQualification !== null
        || trial.fdaPdufaVerification !== false) {
      throw new Error("Patient-population trial identity failed validation.");
    }
    const companySources = sourcesForPhase3Trial(trial, directory);
    if (companySources.marketCapUsd < PATIENT_POPULATION_MARKET_CAP_MIN
        || companySources.marketCapUsd > PATIENT_POPULATION_MARKET_CAP_MAX
        || !companySources.nctIds.includes(trial.nctId)) {
      throw new Error("Patient-population market-cap or sponsor gate failed.");
    }
    ncts.add(trial.nctId);
    rows.push({
      trial, companySources,
      diseasePopulation: null, eligibleUsPatients: null,
      eligibleGlobalPatients: null, populationEvidenceCompleteness: null,
      populationLastVerified: null,
    });
  }
  if (rows.length !== PATIENT_POPULATION_BASELINE_TRIALS
      || new Set(rows.map(r => r.trial.ticker)).size !== PATIENT_POPULATION_BASELINE_COMPANIES) {
    throw new Error("Patient-population completed Phase 3 baseline drifted.");
  }
  return rows;
}
