/**
 * Historical KEYNOTE-024 pilot boundary. Accept only the known unscored
 * trial identity and source-linked analyses; never promote publication facts
 * to GEM / GEM JR / Pipeline or an FDA-approval probability.
 */
import { validSourceEvidenceAudit, type SourceEvidenceAudit } from "./trial-science-evidence-audit";
import { validSafetyChronology, type SafetyChronology } from "./trial-science-safety-chronology";
import { validPublishedInterimDesign, type PublishedInterimDesign } from "./trial-science-interim-design";
import { validEuProtocolCrosscheck, type EuProtocolCrosscheck } from "./trial-science-eu-crosscheck";
import { validHistoricalRegulatoryTimeline, type HistoricalRegulatoryTimeline } from "./trial-science-regulatory-timeline";

export const PILOT_NCT = "NCT02142738";

export const SCIENCE_DOMAIN_LABELS = {
  disease_biology: "Disease biology",
  mechanism_of_action: "Mechanism of action",
  preclinical_evidence: "Preclinical evidence",
  clinical_design: "Clinical design",
  clinical_results: "Clinical results",
  competitive_landscape: "Competitive landscape",
  regulatory_analysis: "Regulatory analysis",
  advanced_inference: "Advanced inference",
} as const;
export type ScienceDomain = keyof typeof SCIENCE_DOMAIN_LABELS;
const SCIENCE_DOMAINS = Object.keys(SCIENCE_DOMAIN_LABELS) as ScienceDomain[];

export type TrialEffect = {
  metric?: string;
  pembrolizumab?: number;
  chemotherapy?: number;
  hazard_ratio?: number;
  hazard_ratio_95pct_ci?: number[];
  p_value?: string;
  nominal_p_value?: string;
  analysis_role?: string;
  between_group_difference?: number;
  difference_95pct_ci?: number[];
  five_year_kaplan_meier_survival_percent?: {
    pembrolizumab: number;
    chemotherapy: number;
  };
};
export type StudySnapshot = {
  analysis_id: string;
  report_type: string;
  publication_date: string;
  data_cutoff_date?: string;
  source_id: string;
  source_url: string;
  nct_id: string;
  effects?: Record<string, TrialEffect>;
  outcomes?: Record<string, TrialEffect>;
  safety?: Record<string, unknown>;
  methodological_caveats: string[];
  source_evidence_status: string;
  effective_crossover_percent_from_chemotherapy?: number;
};
export type ScientificReadinessCheck = {
  id: string;
  title: string;
  status: "SOURCE_SUPPORTED" | "REVIEW_REQUIRED" | "BLOCKED";
  critical: boolean;
  finding: string;
  next_action: string;
  sources: { url: string; locator: string }[];
};

export type ScientificReadiness = {
  modelVersion: "scientific-readiness-two-grade-v1";
  nctId: typeof PILOT_NCT;
  protocol: {
    url: string;
    documentDate: "2017-12-20";
    interimDataCutoff: "2016-05-09";
    amendment: "024-11";
    regionalScope: string;
    afterInterimDataCutoff: true;
    notProofOf2016Prespecification: true;
  };
  inputReadiness: {
    grade: "PASS" | "FAIL";
    status: string;
    criteriaTotal: number;
    sourceSupported: number;
    unresolved: number;
    unresolvedIds: string[];
    meaning: string;
  };
  reluctance: {
    grade: "LOW" | "MODERATE" | "ELEVATED" | "HIGH";
    status: string;
    criticalBlockedIds: string[];
    criticalReviewIds: string[];
    meaning: string;
  };
  checks: ScientificReadinessCheck[];
  readOnly: true;
  scientificScore: null;
  fdaApprovalProbability: null;
  fullTwentyLevelAnalysisCompleted: false;
  preliminarySourceReviewAllowed: true;
  independentReanalysisPerformed: false;
  approvalForecastProduced: false;
  fsFaModified: false;
  tradingActionsEnabled: false;
  disclaimer: string;
};

export type TrialSciencePilot = {
  pilot: {
    nct_id: string;
    trial_name: string;
    phase: string;
    enrollment: number;
    program: string;
    condition: string;
    domains: Record<ScienceDomain, { status: string }>;
  };
  dossier: {
    nct_id: string;
    exact_program_id: string;
    source_sha256: string;
    source_url: string;
    domains: Record<ScienceDomain, { status: string; score: null; claims: unknown[] }>;
    overall_score: null;
    fda_approval_probability: null;
    read_only: true;
  };
  scientificReadiness?: ScientificReadiness;
  sourceEvidenceAudit?: SourceEvidenceAudit;
  publishedSafetyReconciliation?: SafetyChronology;
  publishedInterimDesign?: PublishedInterimDesign;
  europeanRegistryCrosscheck?: EuProtocolCrosscheck;
  historicalRegulatoryTimeline?: HistoricalRegulatoryTimeline;
  publishedResults: {
    nct_id: string;
    randomized_population: number;
    analysis_snapshots: StudySnapshot[];
    corroborating_sources: { source_type: string; source_url: string; supported_observation: string; scope_note: string }[];
    domain_scores: Record<ScienceDomain, null>;
    overall_score: null;
    fda_approval_probability: null;
    scientific_review_status: string;
    unresolved_tasks: string[];
    read_only: true;
    trading_actions_enabled: false;
  };
  assessmentStatus: string;
  scoringModified: false;
  qualificationPresetsModified: false;
  researchOnly: true;
};

function object(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}
function str(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0 && value.length <= 3000;
}
function strings(value: unknown): value is string[] {
  return Array.isArray(value) && value.length <= 30 && value.every(str);
}
function finite(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}
export function safePilotSource(url: string): boolean {
  try {
    const parsed = new URL(url);
    return parsed.protocol === "https:" && !parsed.username && !parsed.password
      && parsed.port === ""
      && ["pubmed.ncbi.nlm.nih.gov", "clinicaltrials.gov", "academic.oup.com",
          "www.cancer.gov", "ascopubs.org"].includes(parsed.hostname);
  } catch {
    return false;
  }
}
function exactDomains(input: unknown, scoreField: boolean): boolean {
  if (!object(input) || Object.keys(input).length !== SCIENCE_DOMAINS.length) return false;
  return SCIENCE_DOMAINS.every(domain => {
    const item = input[domain];
    if (scoreField) return object(item) && str(item.status) && item.score === null
      && Array.isArray(item.claims);
    return object(item) && str(item.status);
  });
}

const APPROVED_READINESS_SOURCES = new Set([
  "https://clinicaltrials.gov/study/NCT02142738",
  "https://cdn.clinicaltrials.gov/large-docs/38/NCT02142738/Prot_SAP_000.pdf",
  "https://pubmed.ncbi.nlm.nih.gov/27718847/",
  "https://pubmed.ncbi.nlm.nih.gov/29129441/",
  "https://pubmed.ncbi.nlm.nih.gov/33872070/",
  "https://pmc.ncbi.nlm.nih.gov/articles/PMC5679831/",
]);

/** An input grade is valid only if it agrees with every sourced check. */
export function validScientificReadiness(input: unknown): input is ScientificReadiness {
  if (!object(input) || !object(input.protocol) || !object(input.inputReadiness)
      || !object(input.reluctance) || !Array.isArray(input.checks)
      || input.modelVersion !== "scientific-readiness-two-grade-v1"
      || input.nctId !== PILOT_NCT
      || input.protocol.url !== "https://cdn.clinicaltrials.gov/large-docs/38/NCT02142738/Prot_SAP_000.pdf"
      || input.protocol.documentDate !== "2017-12-20"
      || input.protocol.interimDataCutoff !== "2016-05-09"
      || input.protocol.amendment !== "024-11"
      || input.protocol.afterInterimDataCutoff !== true
      || input.protocol.notProofOf2016Prespecification !== true
      || !str(input.protocol.regionalScope)
      || input.readOnly !== true || input.scientificScore !== null
      || input.fdaApprovalProbability !== null
      || input.fullTwentyLevelAnalysisCompleted !== false
      || input.preliminarySourceReviewAllowed !== true
      || input.independentReanalysisPerformed !== false
      || input.approvalForecastProduced !== false
      || input.fsFaModified !== false || input.tradingActionsEnabled !== false
      || !str(input.disclaimer)
      || input.checks.length !== 12) return false;

  const identifiers = new Set<string>();
  const unresolved: string[] = [];
  const criticalBlocked: string[] = [];
  const criticalPending: string[] = [];
  let sourceSupported = 0;
  for (const item of input.checks) {
    if (!object(item) || !str(item.id) || !/^[a-z][a-z0-9_]{2,63}$/.test(item.id)
        || identifiers.has(item.id)
        || !str(item.title) || !str(item.finding)
        || !str(item.next_action) || typeof item.critical !== "boolean"
        || !["SOURCE_SUPPORTED", "REVIEW_REQUIRED", "BLOCKED"].includes(String(item.status))
        || !Array.isArray(item.sources) || item.sources.length < 1
        || item.sources.length > 5) return false;
    identifiers.add(item.id);
    for (const ref of item.sources) {
      if (!object(ref) || !str(ref.url) || !APPROVED_READINESS_SOURCES.has(ref.url)
          || !str(ref.locator)) return false;
    }
    if (item.status === "SOURCE_SUPPORTED") sourceSupported += 1;
    else {
      unresolved.push(item.id);
      if (item.critical && item.status === "BLOCKED") criticalBlocked.push(item.id);
      if (item.critical && item.status === "REVIEW_REQUIRED") criticalPending.push(item.id);
    }
  }
  // Known blockers are immutable until a new reviewed model version
  // explicitly replaces their historical source evidence.
  if (!criticalBlocked.includes("pre_cutoff_protocol") ||
      !criticalBlocked.includes("full_regulatory_cmc")) return false;
  const { inputReadiness: ready, reluctance } = input;
  const eq = (first: unknown, second: string[]): boolean =>
    Array.isArray(first) && first.length === second.length &&
    first.every((item, i) => item === second[i]);
  return ready.grade === (unresolved.length ? "FAIL" : "PASS")
    && ready.status === (unresolved.length ? "NOT_READY_FOR_FULL_ANALYSIS"
      : "READY_FOR_FULL_ANALYSIS_INPUT_REVIEW")
    && ready.criteriaTotal === input.checks.length
    && ready.sourceSupported === sourceSupported
    && ready.unresolved === unresolved.length
    && eq(ready.unresolvedIds, unresolved)
    && str(ready.meaning)
    && reluctance.grade === (criticalBlocked.length ? "HIGH"
      : criticalPending.length ? "ELEVATED"
      : unresolved.length ? "MODERATE" : "LOW")
    && reluctance.status === (unresolved.length ? "CONCLUSIONS_WITHHELD"
      : "REVIEW_EVIDENCE_BEFORE_CONCLUSIONS")
    && eq(reluctance.criticalBlockedIds, criticalBlocked)
    && eq(reluctance.criticalReviewIds, criticalPending)
    && str(reluctance.meaning);
}

/**
 * Deny a mismatched or scored payload entirely rather than showing selective
 * fragments from an unverified or non-pilot response.
 */
export function validTrialSciencePilot(input: unknown): input is TrialSciencePilot {
  if (!object(input) || !object(input.pilot) || !object(input.dossier)
      || !object(input.publishedResults)) return false;
  const { pilot, dossier, publishedResults: data } = input;
  if (input.scientificReadiness !== undefined && !validScientificReadiness(input.scientificReadiness)) return false;
  if (input.sourceEvidenceAudit !== undefined && !validSourceEvidenceAudit(input.sourceEvidenceAudit)) return false;
  if (input.publishedSafetyReconciliation !== undefined && !validSafetyChronology(input.publishedSafetyReconciliation)) return false;
  if (input.publishedInterimDesign !== undefined && !validPublishedInterimDesign(input.publishedInterimDesign)) return false;
  if (input.europeanRegistryCrosscheck !== undefined &&
      !validEuProtocolCrosscheck(input.europeanRegistryCrosscheck)) return false;
  if (input.historicalRegulatoryTimeline !== undefined &&
      !validHistoricalRegulatoryTimeline(input.historicalRegulatoryTimeline)) return false;
  if (input.historicalRegulatoryTimeline !== undefined &&
      (input.publishedInterimDesign === undefined ||
       input.europeanRegistryCrosscheck === undefined ||
       input.scientificReadiness === undefined ||
       input.scientificReadiness.inputReadiness.grade !== "FAIL" ||
       input.scientificReadiness.reluctance.grade !== "HIGH" ||
       input.publishedInterimDesign.observedInterim.reportedPfsEvents !==
         input.historicalRegulatoryTimeline.interim.observedPfsEvents ||
       input.publishedInterimDesign.observedInterim.reportedDeaths !==
         input.historicalRegulatoryTimeline.interim.observedOsDeaths ||
       input.europeanRegistryCrosscheck.registry.firstRecordEnteredDate !==
         input.historicalRegulatoryTimeline.events[0].eventDate)) return false;
  if (input.europeanRegistryCrosscheck !== undefined &&
      (input.publishedInterimDesign === undefined ||
       input.scientificReadiness === undefined ||
       input.scientificReadiness.inputReadiness.grade !== "FAIL" ||
       input.scientificReadiness.reluctance.grade !== "HIGH" ||
       input.publishedInterimDesign.reportedDesign.secondInterim.plannedApproximatePfsEvents !==
         input.europeanRegistryCrosscheck.eventTiming.euPfsEventsTargetApprox ||
       input.publishedInterimDesign.observedInterim.reportedPfsEvents !==
         input.europeanRegistryCrosscheck.eventTiming.reportedPfsEventsObserved ||
       input.publishedInterimDesign.observedInterim.reportedDeaths !==
         input.europeanRegistryCrosscheck.eventTiming.reportedOsInterimDeathsObserved)) return false;
  if (input.publishedInterimDesign !== undefined && input.scientificReadiness !== undefined &&
      (input.scientificReadiness.inputReadiness.grade !== "FAIL" ||
       input.scientificReadiness.reluctance.grade !== "HIGH")) return false;
  if (input.publishedSafetyReconciliation !== undefined && input.sourceEvidenceAudit !== undefined &&
      input.publishedSafetyReconciliation.registryReconciliation.archivedGroupsObserved !==
      input.sourceEvidenceAudit.registrySafety.groupCount) return false;
  const scores = data.domain_scores;
  if (!object(scores)) return false;
  if (pilot.nct_id !== PILOT_NCT || dossier.nct_id !== PILOT_NCT
      || data.nct_id !== PILOT_NCT
      || dossier.exact_program_id !== "TRIAL|" + PILOT_NCT
      || pilot.trial_name !== "KEYNOTE-024"
      || pilot.phase !== "PHASE3" || !finite(pilot.enrollment)
      || pilot.enrollment !== 305 || data.randomized_population !== 305
      || !str(pilot.program) || !str(pilot.condition)
      || !exactDomains(pilot.domains, false) || !exactDomains(dossier.domains, true)
      || Object.keys(scores).length !== SCIENCE_DOMAINS.length
      || !SCIENCE_DOMAINS.every(domain => scores[domain] === null)
      || !str(dossier.source_sha256) || !/^[a-f0-9]{64}$/.test(dossier.source_sha256)
      || dossier.source_url !== "https://clinicaltrials.gov/study/" + PILOT_NCT
      || dossier.overall_score !== null || dossier.fda_approval_probability !== null
      || dossier.read_only !== true
      || data.overall_score !== null || data.fda_approval_probability !== null
      || data.read_only !== true || data.trading_actions_enabled !== false
      || input.scoringModified !== false || input.qualificationPresetsModified !== false
      || input.researchOnly !== true
      || input.assessmentStatus !== "source_reported_requires_independent_appraisal"
      || data.scientific_review_status !== input.assessmentStatus
      || !strings(data.unresolved_tasks)) return false;

  const snapshots = data.analysis_snapshots;
  if (!Array.isArray(snapshots) || snapshots.length !== 3) return false;
  const ids = new Set<string>();
  // Each analysis is tied to its known original PMID, not merely any URL
  // under PubMed. Do not permit swapping a correct trial ID with an
  // unrelated citation while retaining an apparently credible source.
  const expectedPmids: Record<string, string> = {
    keynote024_initial_2016: "27718847",
    keynote024_pros_2017: "29129441",
    keynote024_five_year_2021: "33872070",
  };
  const expected = new Set(Object.keys(expectedPmids));
  for (const snapshot of snapshots) {
    if (!object(snapshot) || snapshot.nct_id !== PILOT_NCT
        || !str(snapshot.analysis_id) || !expected.has(snapshot.analysis_id)
        || ids.has(snapshot.analysis_id)
        || snapshot.source_id !== expectedPmids[snapshot.analysis_id]
        || !str(snapshot.report_type) || !/^20[0-9]{2}-[0-9]{2}-[0-9]{2}$/.test(String(snapshot.publication_date))
        || (snapshot.data_cutoff_date !== undefined && !/^20[0-9]{2}-[0-9]{2}-[0-9]{2}$/.test(String(snapshot.data_cutoff_date)))
        || !str(snapshot.source_id) || !/^[1-9][0-9]{0,11}$/.test(snapshot.source_id)
        || snapshot.source_url !== "https://pubmed.ncbi.nlm.nih.gov/" + snapshot.source_id + "/"
        || !strings(snapshot.methodological_caveats)
        || snapshot.source_evidence_status !== "published_reported_not_independently_reanalyzed"
        || (snapshot.effects !== undefined && !object(snapshot.effects))
        || (snapshot.outcomes !== undefined && !object(snapshot.outcomes))
        || (snapshot.safety !== undefined && !object(snapshot.safety))
        || (snapshot.effective_crossover_percent_from_chemotherapy !== undefined &&
            !finite(snapshot.effective_crossover_percent_from_chemotherapy))) return false;
    ids.add(snapshot.analysis_id);
  }
  if (ids.size !== expected.size) return false;
  const sources = data.corroborating_sources;
  if (!Array.isArray(sources) || sources.length > 8) return false;
  return sources.every(source => object(source) && str(source.source_type)
    && str(source.source_url) && safePilotSource(source.source_url)
    && str(source.supported_observation) && str(source.scope_note));
}

export function pilotDomainStatus(value: string): string {
  const labels: Record<string, string> = {
    pending_review: "Not assessed",
    registry_metadata_available: "Registry metadata available",
    publications_identified_unadjudicated: "Publications identified · not independently assessed",
  };
  return labels[value] ?? "Not independently assessed";
}

export function pilotEffectSummary(result: TrialEffect | undefined): string {
  if (!result) return "Not reported in this analysis";
  if (finite(result.hazard_ratio)) {
    const interval = result.hazard_ratio_95pct_ci;
    const ci = Array.isArray(interval) && interval.length === 2
      && interval.every(finite) ? ` (95% CI ${interval[0]}–${interval[1]})` : "";
    return `HR ${result.hazard_ratio.toFixed(2)}${ci}`;
  }
  if (finite(result.between_group_difference)) {
    const interval = result.difference_95pct_ci;
    const ci = Array.isArray(interval) && interval.length === 2 && interval.every(finite)
      ? ` (95% CI ${interval[0]}–${interval[1]})` : "";
    return `Difference ${result.between_group_difference} points${ci}`;
  }
  if (finite(result.pembrolizumab) && finite(result.chemotherapy)) {
    const suffix = result.metric === "median_months" ? " months" :
      result.metric === "percent" ? "%" : " units";
    return `${result.pembrolizumab} vs ${result.chemotherapy}${suffix}`;
  }
  return "See cited publication";
}
