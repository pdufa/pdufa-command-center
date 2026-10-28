const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const ts = require("typescript");

require.extensions[".ts"] = (mod, filename) =>
  mod._compile(ts.transpileModule(fs.readFileSync(filename, "utf8"), {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2022,
      esModuleInterop: true,
    },
  }).outputText, filename);

const { validHistoricalRegulatoryTimeline } =
  require("../lib/trial-science-regulatory-timeline.ts");
const NEJM="https://www.nejm.org/doi/abs/10.1056/NEJMoa1606774";
const EU="https://www.clinicaltrialsregister.eu/ctr-search/trial/2014-000323-25/NL";
const ASCO="https://ascopubs.org/doi/10.1200/jco.2015.33.15_suppl.tps8103";
const DMC="https://www.merck.com/news/mercks-keytruda-pembrolizumab-demonstrates-superior-progression-free-and-overall-survival-compared-to-chemotherapy-as-first-line-treatment-in-patients-with-advanced-non-small-cel/";
const REVIEW="https://www.merck.com/news/fda-accepts-supplemental-biologics-license-application-assigns-priority-review-and-grants-breakthrough-therapy-designation-to-mercks-keytruda-pembrolizumab-for-first-line-treatment-o/";
const NCI="https://www.cancer.gov/news-events/cancer-currents-blog/2016/fda-atezolizumab-pembrolizumab-lung";
const plan=[
  ["2014-06-19","european_registry_first_entry","Trial registration",EU,
   "registry_source_version_unverified","2014-06-19"],
  ["2015-05-20","early_public_study_design","Prospective study description",ASCO,
   "contemporaneous_public_study_description","2015-05-20"],
  ["2016-05-09","original_interim_data_cutoff","Data cutoff",NEJM,
   "event_reported_retrospectively","2016-10-08"],
  ["2016-06-08","dmc_review_first","DMC review",NEJM,
   "event_reported_retrospectively","2016-10-08"],
  ["2016-06-14","dmc_review_second","DMC review",NEJM,
   "event_reported_retrospectively","2016-10-08"],
  ["2016-06-16","sponsor_public_stopping_notice","Public disclosure",DMC,
   "contemporaneous_sponsor_news","2016-06-16"],
  ["2016-09-07","first_line_priority_review_notice","Regulatory review",REVIEW,
   "contemporaneous_sponsor_regulatory_notice","2016-09-07"],
  ["2016-10-08","original_results_online","Published results",NEJM,
   "original_journal_publication","2016-10-08"],
  ["2016-10-24","fda_first_line_approval","FDA decision",NCI,
   "federal_historical_confirmation","2016-11-17"],
  ["2016-12-24","announced_pdufa_goal","Superseded target",REVIEW,
   "historical_target_not_decision","2016-09-07"],
];

function fixture() {
  return {
    nctId:"NCT02142738",
    schemaVersion:"historical-keynote024-dmc-pdufa-timeline-v1",
    status:"historical_source_timeline_not_outcome_forecast",
    application:{
      biologicsLicense:"125514/S-12",
      indication:"first_line_PDL1_TPS_ge_50_metastatic_NSCLC",
      targetAnnouncedDate:"2016-09-07",
      targetPdufaDate:"2016-12-24",
      actualFdaActionDate:"2016-10-24",
      actualAction:"approved_first_line_pembrolizumab",
      firstLineSupportedBy:"NCT02142738",
      sameDaySecondLineConversionDifferentTrial:"KEYNOTE-010",
      neverTreatTargetAsObservedDecision:true,
      actualActionKnownOnlyInHindsight:true,
      observationalHistoryNotForecast:true,
    },
    eventCount:10,
    events:plan.map(([eventDate,key,category,sourceUrl,sourceTemporalStatus,
                      sourcePublicationOrEntryDate])=>({
      eventDate,key,category,sourceUrl,sourceTemporalStatus,
      sourcePublicationOrEntryDate,title:key,
      sourceLocator:"Original source date and document subsection",
      caveat:"Exact signature or review minutes not independently read",
      originalDmcMinutesVerified:false,
      originalSignedSapVerified:false,
    })),
    interim:{
      dataCutoff:"2016-05-09",
      independentCommitteeReviewDatesReportedByJournal:["2016-06-08","2016-06-14"],
      firstPublicStoppingRecommendationDisclosure:"2016-06-16",
      dmcMinutesAndSignedRecommendationReviewed:false,
      dmcExactRecommendationDecisionDateProven:false,
      prospectiveStoppingBoundaryRecalculated:false,
      observedPfsEvents:189,observedOsDeaths:108,
      journalRetrospectiveReportingSource:NEJM,
      sponsorContemporaneousReleaseSource:DMC,
      pfsTargetWasApproximate:true,fdaReviewDossierComplete:false,
    },
    conclusions:{
      publicStoppingChronologyCorroborated:true,
      regulatoryTargetAndActualActionIdentified:true,
      independentDmcMinutesReviewed:false,
      originalProtocolSapAuthenticated:false,
      originalSignedAlphaSpendingReconstructed:false,
      fullIndependentScientificAdjudicationDone:false,
      inputReadinessGradeChanged:false,
      reluctanceGradeChanged:false,
      retrospectiveDataNotProspectivePrediction:true,
    },
    scientificScore:null,fdaApprovalProbability:null,
    readOnly:true,tradingActionsEnabled:false,fsFaModified:false,
  };
}

test("chronology keeps late PDUFA target separate from October FDA decision",()=>{
  const x=fixture();
  assert.equal(validHistoricalRegulatoryTimeline(x),true);
  assert.equal(x.eventCount,10);
  assert.equal(x.events[3].eventDate,"2016-06-08");
  assert.equal(x.events[4].eventDate,"2016-06-14");
  assert.equal(x.events[5].sourcePublicationOrEntryDate,"2016-06-16");
  assert.equal(x.events[4].sourcePublicationOrEntryDate,"2016-10-08");
  assert.equal(x.application.actualFdaActionDate,"2016-10-24");
  assert.equal(x.application.targetPdufaDate,"2016-12-24");
  assert.equal(x.events[9].sourceTemporalStatus,"historical_target_not_decision");
  assert.equal(x.conclusions.retrospectiveDataNotProspectivePrediction,true);
});

test("reject fake DMC decision dates, invented PDUFA/approval dates, and scores",()=>{
  const changes=[
    x=>{x.nctId="NCT87654321";},
    x=>{x.application.targetPdufaDate="2016-10-24";},
    x=>{x.application.actualFdaActionDate="2016-12-24";},
    x=>{x.application.sameDaySecondLineConversionDifferentTrial="KEYNOTE-024";},
    x=>{x.application.actualActionKnownOnlyInHindsight=false;},
    x=>{x.events[3].eventDate="2016-06-09";},
    x=>{x.events[4].originalDmcMinutesVerified=true;},
    x=>{x.events[4].sourcePublicationOrEntryDate="2016-06-14";},
    x=>{x.events[5].sourceUrl="https://attacker.invalid";},
    x=>{x.events[8].sourceTemporalStatus="contemporaneous_fda_approval";},
    x=>{x.events[9].category="FDA decision";},
    x=>{x.events[9].sourceTemporalStatus="real_action";},
    x=>{x.interim.dmcExactRecommendationDecisionDateProven=true;},
    x=>{x.interim.independentCommitteeReviewDatesReportedByJournal=["2016-06-15"];},
    x=>{x.interim.prospectiveStoppingBoundaryRecalculated=true;},
    x=>{x.conclusions.originalProtocolSapAuthenticated=true;},
    x=>{x.conclusions.independentDmcMinutesReviewed=true;},
    x=>{x.conclusions.inputReadinessGradeChanged=true;},
    x=>{x.conclusions.reluctanceGradeChanged=true;},
    x=>{x.scientificScore=99;},
    x=>{x.fdaApprovalProbability=.99;},
    x=>{x.tradingActionsEnabled=true;},
    x=>{x.fsFaModified=true;},
  ];
  for(const mutate of changes){
    const x=fixture();mutate(x);
    assert.equal(validHistoricalRegulatoryTimeline(x),false,String(mutate));
  }
});

test("source-linked timeline is accessible and keeps both scientific grades",()=>{
  const ui=fs.readFileSync(path.join(__dirname,"../app/TrialSciencePilot.tsx"),"utf8");
  const stylesheet=fs.readFileSync(path.join(__dirname,"../app/TrialSciencePilot.module.css"),"utf8");
  const guards=fs.readFileSync(path.join(__dirname,"../lib/trial-science-pilot.ts"),"utf8");
  assert.match(ui,/One trial · interim evidence to FDA action and PDUFA goal/);
  assert.match(ui,/Open ten dated milestones and their primary evidence/);
  assert.match(ui,/pilot\.historicalRegulatoryTimeline\.events\.map/);
  assert.match(ui,/original signed/);
  assert.match(ui,/actualFdaActionDate/);
  assert.match(ui,/targetPdufaDate/);
  assert.match(ui,/Input Readiness remains FAIL; Reluctance remains HIGH/);
  assert.match(stylesheet,/historyTimeline/);
  assert.match(guards,/validHistoricalRegulatoryTimeline/);
  assert.doesNotMatch(ui,/placeOrder\(|runTrade\(/);
});
