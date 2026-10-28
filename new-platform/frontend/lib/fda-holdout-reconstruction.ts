/** Dated research reconstruction; no independently validated forecast is accepted. */
export type HoldoutSource = {
  source_id: string; source_url: string; available_on: string | null;
  availability_basis: string; availability_source_url: string | null; source_role: string;
  classification: string; finding: string; science_question_ids: string[];
  independently_reviewed: false; eligible_for_frozen_prediction: false;
};
export type HoldoutQuestion = {
  question_id: string; question: string; layer: number; layer_name: string;
  source_ids: string[]; status: "NOT_CERTIFIED"; scientific_score: null;
};
type ScientificQuestion = {
  question_id: string; question: string; required_evidence: string; uncertainties: string[];
  scientific_rationale: string; historical_prediction_cutoff: null; research_cutoff: string;
  supporting_findings: string[]; contradictory_findings: string[]; missing_information: string[];
  confidence_grade: "NOT_ESTABLISHED"; independent_verification_status: "NOT_INDEPENDENTLY_ASSESSED";
  effect_on_proposed_fda_decision: "NO_CERTIFIED_EFFECT_ABSTAIN"; research_status: string;
  observations: {source_id: string; source_url: string; available_on: string}[];
  excluded_or_quarantined_sources: {source_id: string; source_url: string; reason: string}[];
};
type InvestigationDepth = {
  depth_level: number; level_id: string; title: string; objective: string; question_ids: string[];
  prerequisite_levels: number[]; blocking_prerequisite_levels: number[]; question_ids_without_source_leads: string[];
  requirements: string[]; completion_artifacts: string[]; source_lead_ids: string[]; completion_artifacts_status: "NOT_INDEPENDENTLY_ADJUDICATED";
  status: "INDEPENDENT_REVIEW_MISSING";
};
export type InvestigationFramework = {
  semantic_level_definitions_status: "DEFINED_RESEARCH_PROTOCOL_NOT_INDEPENDENTLY_VALIDATED";
  catalog_version: string; levels: InvestigationDepth[];
};
type ScientificIssueSource = {id: string; url: string; location: string; document_date: string | null;
  public_availability_verified: boolean; availability_source_url?: string; finding: string};
export type ScientificIssue = {
  issue_id: "RESILIENT-457-VS-456"; trial_id: "NCT05273749"; protocol_id: "TNX-CY-F307";
  randomized_population: {active: 231; placebo: 226; total: 457};
  reported_efficacy_population: {active: 231; placebo: 225; total: 456};
  reported_safety_population: {active: 231; placebo: 226; total: 457};
  sponsor_explanation: string; population_rule_observed: string; scientific_rationale: string;
  protocol_compliance_status: "NOT_ESTABLISHED"; confidence_grade: "NOT_ESTABLISHED";
  supporting_findings: string[]; contradictory_findings: string[]; missing_information: string[];
  uncertainty: string; effect_on_proposed_fda_decision: "ABSTAIN_NO_CERTIFIED_PROBABILITY_EFFECT";
  original_prediction_cutoff: null; research_cutoff: string; reviewed_content_on: string;
  sources: ScientificIssueSource[];
  postdecision_context: {source_url: string; application_index_url: string; source_role: "OUTCOME_ONLY";
    source_location: string; finding: string; application_index_observation: string;
    reported_efficacy_population: {active:231; placebo:225; total:456}; content_observed_on: string};
};
type TrialAnalysis = {analysis_role: "PRESPECIFIED_PRIMARY" | "SENSITIVITY_NOT_PRIMARY";
  method: string; endpoint: string; p_value: string; placebo_adjusted_ls_mean_difference: string;
  standard_error: string | null; source_id: string; source_reported_outcome?: "POSITIVE" | "FAILED"};
export type TnxpTrialComparison = {
  event_key: "TNXP|2025-08-15"; application_id: "NDA219428"; research_cutoff: string;
  original_prediction_cutoff: null; assembled_on: string;
  sources: {source_id: string; source_url: string; document_date: string | null;
    public_availability_verified: false; provenance_note: string}[];
  trials: {trial_id: string; name: string; registry_id: string | null; primary_analysis: TrialAnalysis;
    sensitivity_analyses: TrialAnalysis[];
    populations: {randomized_total: number | null; randomized_active: number | null; randomized_placebo: number | null;
      efficacy_total: number | null; efficacy_active: number | null; efficacy_placebo: number | null;
      safety_total: number | null; safety_active: number | null; safety_placebo: number | null; status: string};
    design: {sites: number | null; duration_weeks: number | null};
    safety: {ae_related_discontinuation_percent: {active: string; placebo: string; source_id: string};
      source_reported_events: {finding: string; source_id: string; independently_adjudicated: false}[];
      causality_status: "NOT_INDEPENDENTLY_ADJUDICATED"};
    unresolved_requirements: string[];
  }[];
  comparison_limits: string[]; required_resolution_artifacts: string[];
  comparison_summary: {predicted_decision: "ABSTAIN"; resilient_exclusion_compliance_status: "NOT_ESTABLISHED"};
};
type ScientificDossier = {
  layers: {layer: number; layer_name: string; questions: ScientificQuestion[];
    questions_with_research_observations: number; independently_completed_assessments: 0}[];
  summary: {independently_completed_assessments: 0; independently_completed_depth_levels: 0};
  depth_framework: InvestigationFramework;
  extended_investigation_framework: InvestigationFramework;
  scientific_issues: ScientificIssue[];
  tnxp_trial_comparison: TnxpTrialComparison | null;
};
export type DecisionContract = {
  predicted_decision: "ABSTAIN"; target_classes: ["PASS", "CRL", "EXTENSION"];
  class_definitions: {PASS: string; CRL: string; EXTENSION: string};
  probabilities: {PASS: null; CRL: null; EXTENSION: null};
  science_readiness_grade: "NOT_READY"; prediction_confidence_grade: "NOT_ESTABLISHED";
  reluctance_grade: "INSUFFICIENT_VERIFIED_EVIDENCE"; evidence_completeness: "INCOMPLETE_NOT_QUANTIFIED";
  source_verification_status: "NOT_INDEPENDENTLY_AUTHENTICATED";
  historical_validation_status: "NOT_INDEPENDENTLY_VALIDATED"; last_updated: string;
};
export type HoldoutCase = {
  event_key: string; application_id: string; indication: string; program_family: string;
  legacy_goal_date: string; action_date: string; reconstruction_cutoff: string;
  original_prediction_cutoff: null; legacy_goal_differs_from_action: boolean;
  source_classification: HoldoutSource[]; predecision_research_candidate_count: number;
  frozen_prediction_source_count: 0; independently_certified_assessments: 0;
  science_worklist: HoldoutQuestion[]; depth_worklist: {depth_level: number; status: "NOT_CERTIFIED"}[];
  supporting_factors: string[]; opposing_factors: string[]; missing_documents: string[]; blockers: string[];
  related_precedents: {name: string; comparison: string; status: string; source_url?: string; eligible_for_training: false}[];
  eligible_for_validation: false; model_eligible: false;
  outcome: Abstention; main: Abstention; decision_contract: DecisionContract; scientific_dossier: ScientificDossier;
  action_document: {status: string; source_url: string; source_bytes_retained: false; original_publication_date: null};
};
type Abstention = {status: "INSUFFICIENT_EVIDENCE"; pass_probability: null; fail_probability: null; prediction_confidence: null; model_validated: false; trading_authorized: false};
export type HoldoutReconstruction = {
  schemaVersion: "fda-holdout-reconstruction-view-v1"; researchOnly: true; asOf: string;
  historyRecords: number; caseReports: HoldoutCase[]; validatedCases: 0; tradingAuthorized: false;
};
const PRIORITIES: Record<string, string> = {
  "NVAX|2025-04-01": "BLA125817", "UNCY|2025-06-28": "NDA218607", "TNXP|2025-08-15": "NDA219428",
  "BCRX|2025-12-12": "NDA219776", "CORT|2025-12-30": "NDA219398", "VNDA|2025-12-30": "NDA220152",
};
const OFFICIAL_HOSTS = new Set(["sec.gov", "www.sec.gov", "fda.gov", "www.fda.gov", "accessdata.fda.gov", "www.accessdata.fda.gov", "download.open.fda.gov"]);
function check(condition: unknown): asserts condition {
  if (!condition) throw new Error("Historical reconstruction is incomplete or inconsistent; counts withheld");
}
function record(value: unknown): Record<string, unknown> {
  check(!!value && typeof value === "object" && !Array.isArray(value));
  return value as Record<string, unknown>;
}
function text(value: unknown): value is string { return typeof value === "string" && value.trim().length > 0; }
function strings(value: unknown): value is string[] { return Array.isArray(value) && value.every(text); }
function day(value: unknown): number {
  check(typeof value === "string" && /^\d{4}-\d{2}-\d{2}$/.test(value));
  const n = Date.parse(value + "T00:00:00Z");
  check(Number.isFinite(n) && new Date(n).toISOString().slice(0, 10) === value);
  return n;
}
export function holdoutSourceUrl(value: unknown): string | undefined {
  if (typeof value !== "string" || /\s/.test(value)) return undefined;
  try {
    const u = new URL(value);
    return u.protocol === "https:" && !u.username && !u.password && !u.port && !u.hash
      && value.match(/^https:\/\/([^/]+)/)?.[1] === u.host && OFFICIAL_HOSTS.has(u.hostname) && u.pathname !== "/" ? value : undefined;
  } catch { return undefined; }
}
function abstains(value: unknown) {
  const r = record(value);
  check(r.status === "INSUFFICIENT_EVIDENCE" && r.pass_probability === null && r.fail_probability === null
    && r.prediction_confidence === null && r.model_validated === false && r.trading_authorized === false);
}

function auditDecisionContract(value: unknown, caseReport: Record<string, unknown>, asOf: number) {
  const contract = record(value), probabilities = record(contract.probabilities), definitions = record(contract.class_definitions);
  check(contract.schema_version === "fda-three-outcome-research-contract-v1" && contract.research_only === true
    && Array.isArray(contract.target_classes) && contract.target_classes.join(",") === "PASS,CRL,EXTENSION"
    && text(definitions.PASS) && text(definitions.CRL) && text(definitions.EXTENSION)
    && contract.target_definition_status === "PRESPECIFIED_REVIEW_HORIZON_REQUIRED"
    && contract.extension_is_binary_nonapproval === false && contract.predicted_decision === "ABSTAIN"
    && contract.abstention_reason === "INSUFFICIENT_INDEPENDENTLY_VERIFIED_EVIDENCE_AND_MODEL_VALIDATION"
    && probabilities.PASS === null && probabilities.CRL === null && probabilities.EXTENSION === null
    && contract.science_readiness_grade === "NOT_READY" && contract.prediction_confidence_grade === "NOT_ESTABLISHED"
    && contract.reluctance_grade === "INSUFFICIENT_VERIFIED_EVIDENCE" && contract.evidence_completeness === "INCOMPLETE_NOT_QUANTIFIED"
    && contract.source_verification_status === "NOT_INDEPENDENTLY_AUTHENTICATED"
    && contract.historical_validation_status === "NOT_INDEPENDENTLY_VALIDATED"
    && contract.uncertainty_range === null && contract.model_version === null && contract.prediction_version === null
    && contract.eligible_for_validated_accuracy === false && contract.trading_authorized === false
    && day(contract.last_updated) <= asOf && strings(contract.blockers) && contract.blockers.length > 0
    && strings(caseReport.blockers) && caseReport.blockers.every(reason => (contract.blockers as string[]).includes(reason)));
}

export function scientificIssueSourceUrl(value: unknown): string | undefined {
  if (typeof value !== "string" || /\s/.test(value)) return undefined;
  try {
    const url = new URL(value);
    return url.protocol === "https:" && !url.username && !url.password && !url.port && !url.hash
      && value.match(/^https:\/\/([^/]+)/)?.[1] === url.host
      && ["www.tonixpharma.com", "cdn.clinicaltrials.gov", "doi.org", "www.sec.gov"].includes(url.hostname)
      && url.pathname !== "/" ? value : undefined;
  } catch { return undefined; }
}
function auditScientificIssues(value: unknown, caseReport: Record<string, unknown>, asOf: number) {
  check(Array.isArray(value));
  if (caseReport.event_key !== "TNXP|2025-08-15") { check(value.length === 0); return; }
  check(value.length === 1);
  const issue = record(value[0]);
  check(issue.schema_version === "tnxp-resilient-population-audit-v1" && issue.issue_id === "RESILIENT-457-VS-456"
    && issue.event_key === caseReport.event_key && issue.application_id === caseReport.application_id
    && issue.trial_id === "NCT05273749" && issue.protocol_id === "TNX-CY-F307"
    && issue.research_cutoff === caseReport.reconstruction_cutoff && issue.original_prediction_cutoff === null
    && day(issue.reviewed_content_on) <= asOf && issue.protocol_compliance_status === "NOT_ESTABLISHED"
    && issue.arithmetic_reconciliation_status === "SPONSOR_EXPLANATION_RECORDED_NOT_INDEPENDENTLY_ADJUDICATED"
    && issue.independently_adjudicated === false && issue.source_bytes_retained === false
    && issue.original_document_sha256 === null && issue.eligible_for_predecision_features === false
    && issue.eligible_for_validated_accuracy === false && issue.trading_authorized === false
    && issue.confidence_grade === "NOT_ESTABLISHED" && issue.approval_probability === null
    && issue.effect_on_proposed_fda_decision === "ABSTAIN_NO_CERTIFIED_PROBABILITY_EFFECT");
  for (const [field, expected] of [["randomized_population", [231, 226, 457]], ["reported_efficacy_population", [231, 225, 456]],
    ["reported_safety_population", [231, 226, 457]]] as const) {
    const population = record(issue[field]);
    check(population.active === expected[0] && population.placebo === expected[1] && population.total === expected[2]);
  }
  for (const field of ["sponsor_explanation", "population_rule_observed", "scientific_rationale", "uncertainty"]) check(text(issue[field]));
  for (const field of ["supporting_findings", "contradictory_findings", "missing_information", "required_resolution_artifacts"]) {
    check(strings(issue[field]) && (issue[field] as string[]).length > 0);
  }
  const context = record(issue.postdecision_context), labelPopulation = record(context.reported_efficacy_population);
  check(context.source_url === "https://www.accessdata.fda.gov/drugsatfda_docs/label/2025/219428s000lbl.pdf"
    && context.application_index_url === "https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm?ApplNo=219428&event=overview.process"
    && context.source_role === "OUTCOME_ONLY" && text(context.source_location) && text(context.finding)
    && text(context.application_index_observation) && labelPopulation.active === 231 && labelPopulation.placebo === 225
    && labelPopulation.total === 456 && context.public_availability_verified === false
    && context.source_bytes_retained === false && context.original_document_sha256 === null
    && context.protocol_exclusion_authority_established === false && context.eligible_for_predecision_features === false
    && day(context.content_observed_on) <= asOf);
  const sourceIds = new Set<string>();
  check(Array.isArray(issue.sources) && issue.sources.length === 5);
  for (const rawSource of issue.sources) {
    const source = record(rawSource);
    check(text(source.id) && !sourceIds.has(source.id) && scientificIssueSourceUrl(source.url)
      && text(source.location) && text(source.finding));
    sourceIds.add(source.id);
    check(source.availability_source_url === undefined || holdoutSourceUrl(source.availability_source_url));
    if (source.document_date !== null) day(source.document_date);
    if (source.public_availability_verified === true) {
      check(source.id === "SEC-JULY9-SUPPLEMENT" && source.document_date === "2025-07-09"
        && source.url === "https://www.sec.gov/Archives/edgar/data/1430306/000199937125008877/ex99-02.htm"
        && source.availability_source_url === "https://www.sec.gov/Archives/edgar/data/1430306/000199937125008877/0001999371-25-008877-index.htm");
    } else check(source.public_availability_verified === false);
  }
  check(["ACR-2024-SPONSOR-POSTER", "RESILIENT-SAP-FINAL-V1", "RESILIENT-PROTOCOL-AMENDMENT-2", "RESILIENT-PUBLISHED-PAPER", "SEC-JULY9-SUPPLEMENT"].every(id => sourceIds.has(id)));
}

function auditTnxpComparison(value: unknown, caseReport: Record<string, unknown>, asOf: number) {
  if (caseReport.event_key !== "TNXP|2025-08-15") { check(value === null); return; }
  const comparison = record(value);
  check(comparison.schema_version === "tnxp-three-trial-comparison-v1" && comparison.event_key === caseReport.event_key
    && comparison.application_id === caseReport.application_id && comparison.research_cutoff === caseReport.reconstruction_cutoff
    && comparison.original_prediction_cutoff === null && day(comparison.assembled_on) <= asOf
    && comparison.research_only === true && comparison.independently_completed_assessments === 0
    && comparison.independently_completed_levels === 0 && comparison.eligible_for_predecision_features === false
    && comparison.eligible_for_validated_accuracy === false && comparison.trading_authorized === false
    && comparison.interpretation_scope === "DESCRIPTIVE_WITHIN_PROGRAM_RESEARCH_NOT_FORECAST_OR_META_ANALYSIS");
  for (const field of ["comparison_limits", "required_resolution_artifacts"]) check(strings(comparison[field]) && (comparison[field] as string[]).length > 0);
  const expectedSources: Record<string, [string, string | null]> = {
    "TNXP-RALLY-RELIEF-20220321": ["https://www.sec.gov/Archives/edgar/data/1430306/000138713122003807/ex99-01.htm", "2022-03-21"],
    "TNXP-RESILIENT-EFFECT-20240610": ["https://www.sec.gov/Archives/edgar/data/1430306/000183988224018368/ex99-02.htm", "2024-06-10"],
    "TNXP-RESILIENT-DISPOSITION-2024": ["https://www.sec.gov/Archives/edgar/data/1430306/000183988224043326/ex99-03.htm", null],
  };
  check(Array.isArray(comparison.sources) && comparison.sources.length === 3);
  const sourceIds = new Set<string>();
  for (const rawSource of comparison.sources) {
    const source = record(rawSource);
    check(text(source.source_id) && !sourceIds.has(source.source_id) && Object.hasOwn(expectedSources, source.source_id));
    const [url, documentDate] = expectedSources[source.source_id];
    check(source.source_url === url && holdoutSourceUrl(source.source_url) && source.document_date === documentDate
      && source.public_availability_verified === false && source.original_document_sha256 === null
      && source.source_bytes_retained === false && source.independently_reviewed === false && text(source.provenance_note));
    if (documentDate !== null) check(day(documentDate) <= day(comparison.research_cutoff));
    sourceIds.add(source.source_id);
  }
  check(Array.isArray(comparison.trials) && comparison.trials.length === 3);
  const profiles = [
    {id:"F304", name:"RELIEF", registry:null, primary:["0.010","-0.4","0.16","POSITIVE"], sensitivity:["0.004","-0.5",null],
      populations:[null,null,null,null,null,null,null,null,null], sites:null, duration:null, ae:["8.5","3.5"], populationStatus:"NOT_ESTABLISHED_FROM_CURRENT_COMPARISON_SOURCES"},
    {id:"F306", name:"RALLY", registry:null, primary:["0.115","-0.2","0.16","FAILED"], sensitivity:["0.014","-0.4","0.16"],
      populations:[514,null,null,null,null,null,null,null,null], sites:36, duration:14, ae:["15.2","6.2"], populationStatus:"SOURCE_REPORTED_PARTIAL_POPULATION_DEFINITION"},
    {id:"F307", name:"RESILIENT", registry:"NCT05273749", primary:["0.00005","-0.65","0.16","POSITIVE"], sensitivity:null,
      populations:[457,231,226,456,231,225,457,231,226], sites:33, duration:14, ae:["6.1","3.5"], populationStatus:"SOURCE_REPORTED_EXCLUSION_COMPLIANCE_NOT_ESTABLISHED"},
  ];
  comparison.trials.forEach((rawTrial, index) => {
    const trial = record(rawTrial), profile = profiles[index];
    const analysisSource = profile.id === "F307" ? "TNXP-RESILIENT-EFFECT-20240610" : "TNXP-RALLY-RELIEF-20220321";
    const populationSource = profile.id === "F304" ? null : profile.id === "F307" ? "TNXP-RESILIENT-DISPOSITION-2024" : analysisSource;
    check(trial.trial_id === profile.id && trial.name === profile.name && trial.registry_id === profile.registry
      && trial.independently_reviewed === false && trial.eligible_for_frozen_prediction === false
      && trial.assessment_status === "SOURCE_REPORTED_NOT_INDEPENDENTLY_ADJUDICATED");
    const primary = record(trial.primary_analysis);
    check(primary.analysis_role === "PRESPECIFIED_PRIMARY" && primary.method === "MMRM_WITH_MULTIPLE_IMPUTATION"
      && primary.endpoint === "pain numeric rating score" && primary.source_id === analysisSource
      && primary.p_value === profile.primary[0] && primary.placebo_adjusted_ls_mean_difference === profile.primary[1]
      && primary.standard_error === profile.primary[2] && primary.source_reported_outcome === profile.primary[3]);
    check(Array.isArray(trial.sensitivity_analyses) && trial.sensitivity_analyses.length === (profile.sensitivity ? 1 : 0));
    if (profile.sensitivity) {
      const sensitivity = record(trial.sensitivity_analyses[0]);
      check(sensitivity.analysis_role === "SENSITIVITY_NOT_PRIMARY" && sensitivity.method === "MMRM_WITHOUT_MULTIPLE_IMPUTATION"
        && sensitivity.endpoint === "pain numeric rating score" && sensitivity.source_id === analysisSource
        && sensitivity.p_value === profile.sensitivity[0] && sensitivity.placebo_adjusted_ls_mean_difference === profile.sensitivity[1]
        && sensitivity.standard_error === profile.sensitivity[2] && sensitivity.source_reported_outcome === undefined);
    }
    const populations = record(trial.populations);
    ["randomized_total","randomized_active","randomized_placebo","efficacy_total","efficacy_active","efficacy_placebo","safety_total","safety_active","safety_placebo"]
      .forEach((field, i) => check(populations[field] === profile.populations[i]));
    check(populations.source_id === populationSource && populations.status === profile.populationStatus);
    const design = record(trial.design), safety = record(trial.safety), ae = record(safety.ae_related_discontinuation_percent);
    check(design.sites === profile.sites && design.duration_weeks === profile.duration && design.source_id === populationSource
      && safety.causality_status === "NOT_INDEPENDENTLY_ADJUDICATED" && ae.active === profile.ae[0] && ae.placebo === profile.ae[1]
      && ae.source_id === (profile.id === "F307" ? populationSource : analysisSource));
    check(Array.isArray(safety.source_reported_events));
    for (const rawEvent of safety.source_reported_events) {
      const event = record(rawEvent);
      check(text(event.finding) && event.source_id === ae.source_id && event.independently_adjudicated === false);
    }
    check(strings(trial.unresolved_requirements) && trial.unresolved_requirements.length > 0);
  });
  const summary = record(comparison.comparison_summary), probabilities = record(summary.probabilities);
  check(summary.primary_replication_status === "MIXED_SOURCE_REPORTED_NOT_INDEPENDENTLY_ADJUDICATED"
    && Array.isArray(summary.source_reported_positive_primary_trials) && summary.source_reported_positive_primary_trials.join(",") === "F304,F307"
    && Array.isArray(summary.source_reported_failed_primary_trials) && summary.source_reported_failed_primary_trials.join(",") === "F306"
    && summary.rally_sensitivity_does_not_replace_primary === true && summary.within_program_comparison_is_independent_fda_cohort === false
    && summary.cross_trial_causal_explanation_established === false && summary.resilient_exclusion_compliance_status === "NOT_ESTABLISHED"
    && summary.pooled_p_value === null && summary.pooled_effect === null && summary.confidence_interval === null
    && summary.prediction_accuracy === null && summary.predicted_decision === "ABSTAIN" && summary.confidence_grade === "NOT_ESTABLISHED"
    && probabilities.PASS === null && probabilities.CRL === null && probabilities.EXTENSION === null
    && summary.independently_completed_assessments === 0 && summary.independently_completed_levels === 0
    && summary.source_count === 3 && summary.trial_count === 3);
}

function auditInvestigationFramework(value: unknown, candidates: Record<string, unknown>[], levelCount: number, catalogVersion: string) {
  const framework = record(value);
    check(framework.semantic_level_definitions_status === "DEFINED_RESEARCH_PROTOCOL_NOT_INDEPENDENTLY_VALIDATED"
      && framework.catalog_version === catalogVersion
      && framework.predictive_value_validated === false
      && Array.isArray(framework.independently_reviewed_levels) && framework.independently_reviewed_levels.length === 0
      && Array.isArray(framework.levels) && framework.levels.length === levelCount);
    const completionPolicy = record(framework.completion_policy);
    check(completionPolicy.source_leads_complete_levels === false && completionPolicy.automatic_completion_enabled === false
      && completionPolicy.fixed_800_review_requirement === false && completionPolicy.independent_evidence_and_interpretation_required === true
      && completionPolicy.missing_evidence_is_unknown === true);
    const depthIds = new Set<string>();
    framework.levels.forEach((rawDepth, index) => {
      const depth = record(rawDepth);
      check(depth.depth_level === index + 1 && depth.level_id === "D" + String(index + 1).padStart(2, "0") && !depthIds.has(depth.level_id as string)
        && text(depth.title) && text(depth.objective) && depth.status === "INDEPENDENT_REVIEW_MISSING"
        && strings(depth.question_ids) && depth.question_ids.length > 0
        && new Set(depth.question_ids).size === depth.question_ids.length
        && depth.question_ids.every(id => /^S(?:0[1-9]|[12][0-9]|3[0-9]|40)$/.test(id)));
      depthIds.add(depth.level_id as string);
      for (const field of ["requirements", "completion_artifacts"]) {
        check(strings(depth[field]) && (depth[field] as string[]).length > 0);
      }
      check(depth.independently_completed === false && depth.ready_for_independent_certification === false
        && depth.completion_artifacts_status === "NOT_INDEPENDENTLY_ADJUDICATED"
        && Array.isArray(depth.independently_reviewed_question_ids) && depth.independently_reviewed_question_ids.length === 0
        && Array.isArray(depth.prerequisite_levels) && new Set(depth.prerequisite_levels).size === depth.prerequisite_levels.length
        && depth.prerequisite_levels.every(level => Number.isInteger(level) && level >= 1 && level < index + 1)
        && Array.isArray(depth.blocking_prerequisite_levels)
        && depth.blocking_prerequisite_levels.length === depth.prerequisite_levels.length
        && new Set(depth.blocking_prerequisite_levels).size === depth.prerequisite_levels.length
        && depth.prerequisite_levels.every(level => (depth.blocking_prerequisite_levels as unknown[]).includes(level)));
      check(strings(depth.source_lead_ids) && new Set(depth.source_lead_ids).size === depth.source_lead_ids.length);
      const expectedSources = candidates.filter(source =>
        (source.science_question_ids as string[]).some(id => (depth.question_ids as string[]).includes(id))
      ).map(source => source.source_id);
      check(depth.source_lead_ids.length === expectedSources.length
        && expectedSources.every(id => (depth.source_lead_ids as string[]).includes(id as string)));
      const questionsWithLeads = (depth.question_ids as string[]).filter(id => candidates.some(source =>
        (source.science_question_ids as string[]).includes(id)));
      const questionsWithoutLeads = (depth.question_ids as string[]).filter(id => !questionsWithLeads.includes(id));
      for (const [field, expected] of [["question_ids_with_source_leads", questionsWithLeads],
        ["question_ids_without_source_leads", questionsWithoutLeads]] as const) {
        check(strings(depth[field]) && (depth[field] as string[]).length === expected.length
          && new Set(depth[field] as string[]).size === expected.length
          && expected.every(id => (depth[field] as string[]).includes(id)));
      }
    });
}

export function auditHoldoutReconstruction(value: unknown): HoldoutReconstruction {
  const r = record(value);
  check(r.schemaVersion === "fda-holdout-reconstruction-view-v1" && r.researchOnly === true
    && r.tradingAuthorized === false && r.validatedCases === 0
    && Number.isSafeInteger(r.historyRecords) && (r.historyRecords as number) >= 6);
  const asOf = day(r.asOf);
  check(Array.isArray(r.caseReports) && r.caseReports.length === 6);
  const seen = new Set<string>();
  for (const raw of r.caseReports) {
    const c = record(raw);
    check(typeof c.event_key === "string" && c.application_id === PRIORITIES[c.event_key] && !seen.has(c.event_key));
    seen.add(c.event_key);
    check(text(c.indication) && text(c.program_family));
    const goal = day(c.legacy_goal_date), action = day(c.action_date), cutoff = day(c.reconstruction_cutoff);
    check(c.event_key.split("|")[1] === c.legacy_goal_date && action <= asOf
      && cutoff === Math.min(goal, action) - 86400000 && c.legacy_goal_differs_from_action === (goal !== action));
    check(c.original_prediction_cutoff === null && c.frozen_prediction_source_count === 0
      && c.independently_certified_assessments === 0 && c.eligible_for_validation === false && c.model_eligible === false);
    abstains(c.outcome); abstains(c.main);
    auditDecisionContract(c.decision_contract, c, asOf);
    const actionDocument = record(c.action_document);
    check(text(actionDocument.status) && holdoutSourceUrl(actionDocument.source_url)
      && actionDocument.source_bytes_retained === false && actionDocument.original_publication_date === null);
    for (const field of ["supporting_factors", "opposing_factors", "missing_documents", "blockers"]) check(strings(c[field]));
    check((c.blockers as string[]).length > 0 && (c.missing_documents as string[]).length > 0);
    check(Array.isArray(c.source_classification));
    const sources = new Map<string, Record<string, unknown>>();
    for (const rawSource of c.source_classification) {
      const s = record(rawSource);
      check(text(s.source_id) && !sources.has(s.source_id) && holdoutSourceUrl(s.source_url) && text(s.finding)
        && strings(s.science_question_ids) && s.science_question_ids.every(id => /^S(?:0[1-9]|[12][0-9]|3[0-9]|40)$/.test(id))
        && s.independently_reviewed === false && s.eligible_for_frozen_prediction === false);
      check(s.availability_source_url === null || holdoutSourceUrl(s.availability_source_url));
      check(["SEC_FILING_INDEX", "PRINTED_DATE_ONLY", "UNKNOWN"].includes(s.availability_basis as string));
      check(s.source_role === "PREDECISION_RESEARCH" || s.source_role === "OUTCOME_ONLY");
      const available = s.available_on === null ? null : day(s.available_on);
      if (s.source_role === "OUTCOME_ONLY") check(s.classification === "EXCLUDED_OUTCOME_ONLY");
      else if (available === null || s.availability_basis === "UNKNOWN") check(s.classification === "QUARANTINED_UNKNOWN_AVAILABILITY");
      else if (available > asOf) check(s.classification === "EXCLUDED_AFTER_AUDIT_SNAPSHOT");
      else if (available > cutoff) check(s.classification === "EXCLUDED_AFTER_RECONSTRUCTION_CUTOFF");
      else if (s.availability_basis === "PRINTED_DATE_ONLY") check(s.classification === "QUARANTINED_PRINTED_DATE_ONLY");
      else {
        check(s.classification === "PREDECISION_RESEARCH_CANDIDATE" && s.availability_basis === "SEC_FILING_INDEX");
        const source = new URL(s.source_url as string), index = new URL(s.availability_source_url as string);
        const directory = source.pathname.slice(0, source.pathname.lastIndexOf("/") + 1);
        const accession = directory.split("/").filter(Boolean).at(-1) || "";
        check(["sec.gov", "www.sec.gov"].includes(source.hostname) && index.hostname === source.hostname
          && /^\d{18}$/.test(accession) && index.pathname.startsWith(directory)
          && index.pathname.slice(directory.length).replace(/-index\.html?$/, "").replaceAll("-", "") === accession
          && /-index\.html?$/.test(index.pathname) && !index.search);
      }
      sources.set(s.source_id, s);
    }
    const candidates = [...sources.values()].filter(s => s.classification === "PREDECISION_RESEARCH_CANDIDATE");
    check(c.predecision_research_candidate_count === candidates.length);
    check(Array.isArray(c.science_worklist) && c.science_worklist.length === 40);
    c.science_worklist.forEach((rawQuestion, i) => {
      const q = record(rawQuestion), id = "S" + String(i + 1).padStart(2, "0");
      check(q.question_id === id && q.layer === 1 + Math.floor(i / 5) && text(q.layer_name) && text(q.question)
        && q.status === "NOT_CERTIFIED" && q.scientific_score === null && strings(q.source_ids));
      const expected = candidates.filter(s => (s.science_question_ids as string[]).includes(id)).map(s => s.source_id);
      check(q.source_ids.length === expected.length && new Set(q.source_ids).size === expected.length
        && expected.every(sourceId => (q.source_ids as string[]).includes(sourceId as string)));
    });
    check(Array.isArray(c.depth_worklist) && c.depth_worklist.length === 20);
    c.depth_worklist.forEach((rawDepth, i) => {
      const d = record(rawDepth); check(d.depth_level === i + 1 && d.status === "NOT_CERTIFIED");
    });
    const dossier = record(c.scientific_dossier), summary = record(dossier.summary);
    check(dossier.schema_version === "fda-science-research-dossier-v1" && dossier.research_only === true
      && dossier.event_key === c.event_key && dossier.application_id === c.application_id
      && dossier.reconstruction_cutoff === c.reconstruction_cutoff && dossier.original_prediction_cutoff === null
      && dossier.trading_authorized === false);
    check(summary.required_assessments === 40 && summary.required_layers === 8 && summary.required_depth_levels === 20
      && summary.independently_completed_assessments === 0 && summary.independently_completed_depth_levels === 0
      && summary.eligible_frozen_features === 0 && summary.scientific_score === null
      && summary.approval_probability === null && summary.independent_scientific_conclusion === null);
    auditInvestigationFramework(dossier.depth_framework, candidates, 20, "science-investigation-depth-catalog-v1");
    auditInvestigationFramework(dossier.extended_investigation_framework, candidates, 50, "science-investigation-50-level-extension-v1");
    const extended = record(dossier.extended_investigation_framework), base = record(dossier.depth_framework);
    check(extended.base_catalog_version === "science-investigation-depth-catalog-v1"
      && extended.independently_completed_level_count === 0 && extended.legacy_backend_review_boundary_changed === false
      && JSON.stringify((extended.levels as unknown[]).slice(0, 20)) === JSON.stringify(base.levels));
    auditScientificIssues(dossier.scientific_issues, c, asOf);
    auditTnxpComparison(dossier.tnxp_trial_comparison, c, asOf);
    check(Array.isArray(dossier.layers) && dossier.layers.length === 8);
    dossier.layers.forEach((rawLayer, layerIndex) => {
      const layer = record(rawLayer);
      check(layer.layer === layerIndex + 1 && text(layer.layer_name)
        && Array.isArray(layer.questions) && layer.questions.length === 5);
      layer.questions.forEach((rawQuestion, questionIndex) => {
        const q = record(rawQuestion), worklist = record((c.science_worklist as unknown[])[layerIndex * 5 + questionIndex]);
        check(q.question_id === worklist.question_id && q.question === worklist.question && layer.layer_name === worklist.layer_name
          && text(q.required_evidence) && strings(q.uncertainties) && q.uncertainties.length > 0
          && q.assessment_status === "NOT_INDEPENDENTLY_ASSESSED" && q.scientific_conclusion === null
          && text(q.scientific_rationale) && q.historical_prediction_cutoff === null
          && q.research_cutoff === c.reconstruction_cutoff && q.confidence_grade === "NOT_ESTABLISHED"
          && q.independent_verification_status === "NOT_INDEPENDENTLY_ASSESSED"
          && q.effect_on_proposed_fda_decision === "NO_CERTIFIED_EFFECT_ABSTAIN"
          && Array.isArray(q.supporting_findings) && q.supporting_findings.length === 0
          && Array.isArray(q.contradictory_findings) && q.contradictory_findings.length === 0
          && strings(q.missing_information) && q.missing_information.length > 0);
      });
    });
    check(Array.isArray(c.related_precedents));
    for (const rawPrecedent of c.related_precedents) {
      const p = record(rawPrecedent);
      check(text(p.name) && text(p.comparison) && text(p.status) && p.eligible_for_training === false
        && (p.source_url === undefined || holdoutSourceUrl(p.source_url)));
    }
  }
  check(seen.size === 6 && Object.keys(PRIORITIES).every(key => seen.has(key)));
  return value as HoldoutReconstruction;
}
