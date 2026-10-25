/** Strict read-only contract for the historical KEYNOTE-024 scientific pilot. */

export const KEYNOTE024_NCT = "NCT02142738";

export const EIGHT_SCIENCE_DOMAINS = [
  "disease_biology",
  "mechanism_of_action",
  "preclinical_evidence",
  "clinical_design",
  "clinical_results",
  "competitive_landscape",
  "regulatory_analysis",
  "advanced_inference",
] as const;

type ScienceDomain = typeof EIGHT_SCIENCE_DOMAINS[number];
type NoScoreDomain = { score: null; status: string };

export type PilotAnalysis = {
  analysis_id: string;
  publication_date: string;
  data_cutoff_date?: string;
  source_id: string;
  source_url: string;
  nct_id: string;
  report_type: string;
  methodological_caveats: string[];
  primary_endpoint?: string;
  effects?: {
    progression_free_survival?: {
      pembrolizumab: number;
      chemotherapy: number;
      hazard_ratio: number;
      hazard_ratio_95pct_ci: number[];
      p_value: string;
      analysis_role: string;
    };
    overall_survival?: {
      pembrolizumab?: number;
      chemotherapy?: number;
      hazard_ratio: number;
      hazard_ratio_95pct_ci: number[];
      five_year_kaplan_meier_survival_percent?: {
        pembrolizumab: number;
        chemotherapy: number;
      };
    };
    objective_response_rate?: { pembrolizumab: number; chemotherapy: number };
  };
  safety?: {
    treatment_related_adverse_events_grade_3_to_5_percent: {
      pembrolizumab: number;
      chemotherapy: number;
    };
    denominator_note: string;
  };
  outcomes?: {
    quality_of_life_week15_change: {
      between_group_difference: number;
      difference_95pct_ci: number[];
      nominal_p_value: string;
      analysis_role: string;
    };
  };
  effective_crossover_percent_from_chemotherapy?: number;
};

export type PilotResponse = {
  pilot: { nct_id: typeof KEYNOTE024_NCT; trial_name: string };
  dossier: {
    nct_id: typeof KEYNOTE024_NCT;
    assessment_status: "incomplete";
    overall_score: null;
    fda_approval_probability: null;
    domains: Record<ScienceDomain, NoScoreDomain>;
  };
  publishedResults: {
    nct_id: typeof KEYNOTE024_NCT;
    analysis_snapshots: PilotAnalysis[];
    corroborating_sources: {
      source_url: string;
      source_type: string;
      supported_observation: string;
      scope_note: string;
    }[];
    unresolved_tasks: string[];
    overall_score: null;
    fda_approval_probability: null;
    scientific_review_status: "source_reported_requires_independent_appraisal";
    domain_scores: Record<ScienceDomain, null>;
    read_only: true;
    trading_actions_enabled: false;
  };
  scoringModified: false;
  qualificationPresetsModified: false;
  researchOnly: true;
};

function obj(value: unknown): value is Record<string, unknown> {
  return Boolean(value && typeof value === "object" && !Array.isArray(value));
}

function finiteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function pair(value: unknown): value is { pembrolizumab: number; chemotherapy: number } {
  return obj(value) && finiteNumber(value.pembrolizumab) && finiteNumber(value.chemotherapy);
}

function ci(value: unknown): value is number[] {
  return Array.isArray(value) && value.length === 2
    && value.every(finiteNumber) && value[0] <= value[1];
}

function strings(value: unknown): value is string[] {
  return Array.isArray(value) && value.every(v => typeof v === "string");
}

const PUBLICATION_IDS: Record<string, string> = {
  keynote024_initial_2016: "27718847",
  keynote024_pros_2017: "29129441",
  keynote024_five_year_2021: "33872070",
};

/**
 * Fail closed instead of displaying a corrupt, mixed-trial, scored or
 * unexplained payload as verified science. This is display validation;
 * published results still require independent critical appraisal.
 */
export function parseKeynote024Pilot(value: unknown): PilotResponse {
  if (!obj(value) || value.researchOnly !== true || value.scoringModified !== false
      || value.qualificationPresetsModified !== false) {
    throw new Error("Invalid read-only scientific pilot response");
  }
  const pilot = value.pilot, dossier = value.dossier, published = value.publishedResults;
  if (!obj(pilot) || !obj(dossier) || !obj(published)
      || pilot.nct_id !== KEYNOTE024_NCT
      || dossier.nct_id !== KEYNOTE024_NCT
      || published.nct_id !== KEYNOTE024_NCT
      || pilot.trial_name !== "KEYNOTE-024"
      || dossier.assessment_status !== "incomplete"
      || dossier.overall_score !== null || dossier.fda_approval_probability !== null
      || published.overall_score !== null || published.fda_approval_probability !== null
      || published.read_only !== true || published.trading_actions_enabled !== false
      || published.scientific_review_status !== "source_reported_requires_independent_appraisal"
      || !obj(dossier.domains) || !obj(published.domain_scores)) {
    throw new Error("Scientific pilot identity or evidence status mismatch");
  }
  for (const domain of EIGHT_SCIENCE_DOMAINS) {
    if (!obj(dossier.domains[domain]) || dossier.domains[domain].score !== null
        || typeof dossier.domains[domain].status !== "string"
        || published.domain_scores[domain] !== null) {
      throw new Error("Scientific pilot has unexpected or scored domains");
    }
  }
  const snapshots = published.analysis_snapshots;
  if (!Array.isArray(snapshots) || snapshots.length !== 3) {
    throw new Error("Scientific pilot analyses are incomplete");
  }
  const byId = new Map<string, Record<string, unknown>>();
  for (const row of snapshots) {
    if (!obj(row) || typeof row.analysis_id !== "string" || byId.has(row.analysis_id)
        || !(row.analysis_id in PUBLICATION_IDS)
        || row.nct_id !== KEYNOTE024_NCT
        || row.source_id !== PUBLICATION_IDS[row.analysis_id]
        || row.source_url !== "https://pubmed.ncbi.nlm.nih.gov/" + row.source_id + "/"
        || typeof row.publication_date !== "string"
        || !/^\d{4}-\d{2}-\d{2}$/.test(row.publication_date)
        || !strings(row.methodological_caveats)) {
      throw new Error("Scientific pilot publication provenance invalid");
    }
    byId.set(row.analysis_id, row);
  }
  if (byId.size !== 3) throw new Error("Scientific pilot publications missing");

  const initial = byId.get("keynote024_initial_2016")!;
  const fiveYear = byId.get("keynote024_five_year_2021")!;
  const pros = byId.get("keynote024_pros_2017")!;
  const initialEffects = obj(initial.effects) ? initial.effects : null;
  const followupEffects = obj(fiveYear.effects) ? fiveYear.effects : null;
  const pfs = initialEffects && obj(initialEffects.progression_free_survival)
    ? initialEffects.progression_free_survival : null;
  const orr = initialEffects?.objective_response_rate;
  const initialSafety = obj(initial.safety) ? initial.safety : null;
  const severeAes = initialSafety?.treatment_related_adverse_events_grade_3_to_5_percent;
  const longOs = followupEffects && obj(followupEffects.overall_survival)
    ? followupEffects.overall_survival : null;
  const fiveYearRates = longOs?.five_year_kaplan_meier_survival_percent;
  const quality = obj(pros.outcomes) && obj(pros.outcomes.quality_of_life_week15_change)
    ? pros.outcomes.quality_of_life_week15_change : null;
  if (!pfs || !pair(pfs) || !finiteNumber(pfs.hazard_ratio) || !ci(pfs.hazard_ratio_95pct_ci)
      || typeof pfs.p_value !== "string" || pfs.analysis_role !== "prespecified_primary"
      || !pair(orr) || !pair(severeAes)
      || !longOs || !pair(longOs) || !finiteNumber(longOs.hazard_ratio)
      || !ci(longOs.hazard_ratio_95pct_ci) || !pair(fiveYearRates)
      || !finiteNumber(fiveYear.effective_crossover_percent_from_chemotherapy)
      || !quality || !finiteNumber(quality.between_group_difference)
      || !ci(quality.difference_95pct_ci)
      || typeof quality.nominal_p_value !== "string"
      || quality.analysis_role !== "prespecified_exploratory"
      || !Array.isArray(published.corroborating_sources)
      || !strings(published.unresolved_tasks)) {
    throw new Error("Scientific pilot endpoint data incomplete");
  }
  for (const source of published.corroborating_sources) {
    if (!obj(source) || typeof source.source_url !== "string"
        || !/^https:\/\/(www\.cancer\.gov|academic\.oup\.com)\//.test(source.source_url)
        || typeof source.scope_note !== "string"
        || typeof source.supported_observation !== "string"
        || typeof source.source_type !== "string") {
      throw new Error("Scientific pilot corroborating source invalid");
    }
  }
  return value as PilotResponse;
}
