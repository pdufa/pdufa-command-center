/** Historical KEYNOTE-024 FDA action timeline. Read-only; NEVER a forecast. */

export type HistoricalPdufaEvent = {
  eventDate: string;
  key: string;
  category: string;
  title: string;
  sourceUrl: string;
  sourceLocator: string;
  sourceTemporalStatus: string;
  sourcePublicationOrEntryDate: string;
  caveat: string;
  originalDmcMinutesVerified: false;
  originalSignedSapVerified: false;
};

export type HistoricalRegulatoryTimeline = {
  nctId: "NCT02142738";
  schemaVersion: "historical-keynote024-dmc-pdufa-timeline-v1";
  status: "historical_source_timeline_not_outcome_forecast";
  application: {
    biologicsLicense: "125514/S-12";
    indication: "first_line_PDL1_TPS_ge_50_metastatic_NSCLC";
    targetAnnouncedDate: "2016-09-07";
    targetPdufaDate: "2016-12-24";
    actualFdaActionDate: "2016-10-24";
    actualAction: "approved_first_line_pembrolizumab";
    firstLineSupportedBy: "NCT02142738";
    sameDaySecondLineConversionDifferentTrial: "KEYNOTE-010";
    neverTreatTargetAsObservedDecision: true;
    actualActionKnownOnlyInHindsight: true;
    observationalHistoryNotForecast: true;
  };
  eventCount: 10;
  events: HistoricalPdufaEvent[];
  interim: {
    dataCutoff: "2016-05-09";
    independentCommitteeReviewDatesReportedByJournal: ["2016-06-08","2016-06-14"];
    firstPublicStoppingRecommendationDisclosure: "2016-06-16";
    dmcMinutesAndSignedRecommendationReviewed: false;
    dmcExactRecommendationDecisionDateProven: false;
    prospectiveStoppingBoundaryRecalculated: false;
    observedPfsEvents: 189;
    observedOsDeaths: 108;
    journalRetrospectiveReportingSource: string;
    sponsorContemporaneousReleaseSource: string;
    pfsTargetWasApproximate: true;
    fdaReviewDossierComplete: false;
  };
  conclusions: {
    publicStoppingChronologyCorroborated: true;
    regulatoryTargetAndActualActionIdentified: true;
    independentDmcMinutesReviewed: false;
    originalProtocolSapAuthenticated: false;
    originalSignedAlphaSpendingReconstructed: false;
    fullIndependentScientificAdjudicationDone: false;
    inputReadinessGradeChanged: false;
    reluctanceGradeChanged: false;
    retrospectiveDataNotProspectivePrediction: true;
  };
  scientificScore: null;
  fdaApprovalProbability: null;
  readOnly: true;
  tradingActionsEnabled: false;
  fsFaModified: false;
};

const NEJM = "https://www.nejm.org/doi/abs/10.1056/NEJMoa1606774";
const EU = "https://www.clinicaltrialsregister.eu/ctr-search/trial/2014-000323-25/NL";
const ASCO = "https://ascopubs.org/doi/10.1200/jco.2015.33.15_suppl.tps8103";
const MERCK_DMC = "https://www.merck.com/news/mercks-keytruda-pembrolizumab-demonstrates-superior-progression-free-and-overall-survival-compared-to-chemotherapy-as-first-line-treatment-in-patients-with-advanced-non-small-cel/";
const MERCK_REVIEW = "https://www.merck.com/news/fda-accepts-supplemental-biologics-license-application-assigns-priority-review-and-grants-breakthrough-therapy-designation-to-mercks-keytruda-pembrolizumab-for-first-line-treatment-o/";
const NCI_APPROVAL = "https://www.cancer.gov/news-events/cancer-currents-blog/2016/fda-atezolizumab-pembrolizumab-lung";

const EXPECTED = [
  ["2014-06-19", "european_registry_first_entry", "Trial registration", EU,
   "registry_source_version_unverified", "2014-06-19"],
  ["2015-05-20", "early_public_study_design", "Prospective study description", ASCO,
   "contemporaneous_public_study_description", "2015-05-20"],
  ["2016-05-09", "original_interim_data_cutoff", "Data cutoff", NEJM,
   "event_reported_retrospectively", "2016-10-08"],
  ["2016-06-08", "dmc_review_first", "DMC review", NEJM,
   "event_reported_retrospectively", "2016-10-08"],
  ["2016-06-14", "dmc_review_second", "DMC review", NEJM,
   "event_reported_retrospectively", "2016-10-08"],
  ["2016-06-16", "sponsor_public_stopping_notice", "Public disclosure", MERCK_DMC,
   "contemporaneous_sponsor_news", "2016-06-16"],
  ["2016-09-07", "first_line_priority_review_notice", "Regulatory review", MERCK_REVIEW,
   "contemporaneous_sponsor_regulatory_notice", "2016-09-07"],
  ["2016-10-08", "original_results_online", "Published results", NEJM,
   "original_journal_publication", "2016-10-08"],
  ["2016-10-24", "fda_first_line_approval", "FDA decision", NCI_APPROVAL,
   "federal_historical_confirmation", "2016-11-17"],
  ["2016-12-24", "announced_pdufa_goal", "Superseded target", MERCK_REVIEW,
   "historical_target_not_decision", "2016-09-07"],
] as const;

const obj = (x: unknown): x is Record<string, unknown> =>
  x !== null && typeof x === "object" && !Array.isArray(x);
const nonempty = (x: unknown): x is string =>
  typeof x === "string" && x.trim().length > 0 && x.length <= 800;
const numbers = (x: unknown, values: readonly (number|string)[]) =>
  Array.isArray(x) && x.length === values.length &&
  values.every((v, i) => x[i] === v);

export function validHistoricalRegulatoryTimeline(input: unknown):
  input is HistoricalRegulatoryTimeline {
  if (!obj(input) || input.nctId !== "NCT02142738"
      || input.schemaVersion !== "historical-keynote024-dmc-pdufa-timeline-v1"
      || input.status !== "historical_source_timeline_not_outcome_forecast"
      || !obj(input.application) || !obj(input.interim)
      || !obj(input.conclusions)
      || input.scientificScore !== null || input.fdaApprovalProbability !== null
      || input.readOnly !== true || input.tradingActionsEnabled !== false
      || input.fsFaModified !== false || input.eventCount !== EXPECTED.length
      || !Array.isArray(input.events) || input.events.length !== EXPECTED.length) return false;

  for (let i = 0; i < EXPECTED.length; i++) {
    const event = input.events[i];
    const [date, key, category, url, temporalStatus, sourceDate] = EXPECTED[i];
    if (!obj(event) || event.eventDate !== date || event.key !== key
        || event.category !== category || event.sourceUrl !== url
        || event.sourceTemporalStatus !== temporalStatus
        || event.sourcePublicationOrEntryDate !== sourceDate
        || !nonempty(event.title) || !nonempty(event.sourceLocator)
        || !nonempty(event.caveat)
        || event.originalDmcMinutesVerified !== false
        || event.originalSignedSapVerified !== false) return false;
  }

  const app = input.application;
  if (app.biologicsLicense !== "125514/S-12"
      || app.indication !== "first_line_PDL1_TPS_ge_50_metastatic_NSCLC"
      || app.targetAnnouncedDate !== "2016-09-07"
      || app.targetPdufaDate !== "2016-12-24"
      || app.actualFdaActionDate !== "2016-10-24"
      || app.actualAction !== "approved_first_line_pembrolizumab"
      || app.firstLineSupportedBy !== "NCT02142738"
      || app.sameDaySecondLineConversionDifferentTrial !== "KEYNOTE-010"
      || app.neverTreatTargetAsObservedDecision !== true
      || app.actualActionKnownOnlyInHindsight !== true
      || app.observationalHistoryNotForecast !== true) return false;

  const d = input.interim;
  if (d.dataCutoff !== "2016-05-09"
      || !numbers(d.independentCommitteeReviewDatesReportedByJournal,
                  ["2016-06-08", "2016-06-14"])
      || d.firstPublicStoppingRecommendationDisclosure !== "2016-06-16"
      || d.dmcMinutesAndSignedRecommendationReviewed !== false
      || d.dmcExactRecommendationDecisionDateProven !== false
      || d.prospectiveStoppingBoundaryRecalculated !== false
      || d.observedPfsEvents !== 189 || d.observedOsDeaths !== 108
      || d.journalRetrospectiveReportingSource !== NEJM
      || d.sponsorContemporaneousReleaseSource !== MERCK_DMC
      || d.pfsTargetWasApproximate !== true || d.fdaReviewDossierComplete !== false) return false;

  const c = input.conclusions;
  return c.publicStoppingChronologyCorroborated === true
    && c.regulatoryTargetAndActualActionIdentified === true
    && c.independentDmcMinutesReviewed === false
    && c.originalProtocolSapAuthenticated === false
    && c.originalSignedAlphaSpendingReconstructed === false
    && c.fullIndependentScientificAdjudicationDone === false
    && c.inputReadinessGradeChanged === false
    && c.reluctanceGradeChanged === false
    && c.retrospectiveDataNotProspectivePrediction === true;
}
