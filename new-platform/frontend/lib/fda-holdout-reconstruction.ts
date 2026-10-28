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
type ScientificQuestion = {question_id: string; question: string; required_evidence: string; uncertainties: string[]};
type InvestigationDepth = {
  depth_level: number; level_id: string; title: string; objective: string; question_ids: string[];
  prerequisite_levels: number[]; blocking_prerequisite_levels: number[]; question_ids_without_source_leads: string[];
  requirements: string[]; completion_artifacts: string[]; source_lead_ids: string[]; completion_artifacts_status: "NOT_INDEPENDENTLY_ADJUDICATED";
  status: "INDEPENDENT_REVIEW_MISSING";
};
type ScientificDossier = {
  layers: {layer: number; layer_name: string; questions: ScientificQuestion[]}[];
  depth_framework: {
    semantic_level_definitions_status: "DEFINED_RESEARCH_PROTOCOL_NOT_INDEPENDENTLY_VALIDATED";
    catalog_version: string; levels: InvestigationDepth[];
  };
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
  outcome: Abstention; main: Abstention; scientific_dossier: ScientificDossier;
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
    const framework = record(dossier.depth_framework);
    check(framework.semantic_level_definitions_status === "DEFINED_RESEARCH_PROTOCOL_NOT_INDEPENDENTLY_VALIDATED"
      && framework.catalog_version === "science-investigation-depth-catalog-v1"
      && framework.predictive_value_validated === false
      && Array.isArray(framework.independently_reviewed_levels) && framework.independently_reviewed_levels.length === 0
      && Array.isArray(framework.levels) && framework.levels.length === 20);
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
    check(Array.isArray(dossier.layers) && dossier.layers.length === 8);
    dossier.layers.forEach((rawLayer, layerIndex) => {
      const layer = record(rawLayer);
      check(layer.layer === layerIndex + 1 && text(layer.layer_name)
        && Array.isArray(layer.questions) && layer.questions.length === 5);
      layer.questions.forEach((rawQuestion, questionIndex) => {
        const q = record(rawQuestion), worklist = record((c.science_worklist as unknown[])[layerIndex * 5 + questionIndex]);
        check(q.question_id === worklist.question_id && q.question === worklist.question && layer.layer_name === worklist.layer_name
          && text(q.required_evidence) && strings(q.uncertainties) && q.uncertainties.length > 0
          && q.assessment_status === "NOT_INDEPENDENTLY_ASSESSED" && q.scientific_conclusion === null);
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
