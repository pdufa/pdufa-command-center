"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path");
const root=path.resolve(__dirname,"..");
const snapshot=require("../data/raas-v2-candidate-source-readiness-site-snapshot.json");
const existing=require("../data/raas-fda-three-way-accuracy-site-snapshot.json");
const source=fs.readFileSync(path.join(root,"app/raas-worklist/page.tsx"),"utf8");
const metricSpecs=fs.readFileSync(path.join(root,"lib/raas-metric-specs.ts"),"utf8");

test("V2 source-readiness snapshot cannot pretend to be a calibrated model",()=>{
 assert.equal(snapshot.scope,"RAAS_V2_CANDIDATE_PROSPECTIVE_SOURCE_READINESS_SITE_SNAPSHOT");
 assert.equal(snapshot.candidateIteration,"V2_RESEARCH_CANDIDATE_STAGE_0");
 assert.equal(snapshot.activeFoundationIteration,"2026-11-02-foundation-v1");
 assert.equal(snapshot.status,"RESEARCH_CANDIDATE_NOT_A_CALIBRATED_PREDICTOR");
 assert.equal(snapshot.remainingLegacyFutureCaseSourceLeadsAtSnapshot,36);
 assert.equal(snapshot.verifiedOriginalGoalProspectiveThreeWayForecasts,0);
 assert.equal(snapshot.independentlyValidatedThreeWayFdaAccuracy,null);
 assert.equal(snapshot.approvedMetricCalibrations,0);
 assert.equal(snapshot.issuerDocumentedNearTermCycleSourceLeads,15);
 assert.equal(snapshot.knownRevisedGoalExcludedFromOriginalDeadlineQueue,4);
 assert.equal(snapshot.remainingUnexcludedLegacyDateResearchLeads,32);
 assert.equal(snapshot.legacyCasesStillUnreviewedByIssuerSources,21);
 assert.equal(snapshot.additionalIssuerDocumentedFormallyExtendedCases,3);
 assert.equal(snapshot.additionalOriginalGoalIssuerSourceLeads,4);
 assert.equal(snapshot.pivotalPhase2SourceLeadsNotStrictPhase3Eligible,2);
 assert.equal(snapshot.nov14IndependentPhase3RegistryCrossChecks,2);
 assert.equal(snapshot.nov14NumberedCurrentFdaApplicationCyclesCertified,0);
 assert.equal(snapshot.nov14FrozenThreeWayForecasts,0);
 assert.equal(snapshot.nightlyOfficialSecAtomFallback,
   "EDGAR_COMPANY_ATOM_AFTER_JSON_DENIAL_OFFICIAL_SOURCE_SEPARATE_ACCESS_STATUS");
 assert.equal(snapshot.nightlyOfficialIssuerNewsFallback,
   "CYTK_AND_SMMT_PUBLIC_ISSUER_NEWS_RESEARCH_LINKS_NOT_SEC_OR_FDA_VERIFICATION");
 assert.equal(snapshot.secEdgarRunnerStatus,
   "ACCESS_BLOCKED_HTTP_403_SOURCE_UNAVAILABLE_NOT_ZERO_FILINGS");
 assert.equal(snapshot.currentCYTKPendingMAPLESupplementNumber,
   "UNVERIFIED_NOT_PUBLICLY_ATTESTED");
 assert.equal(snapshot.currentSMMTOriginalHARMONIBLANumber,
   "UNVERIFIED_NOT_PUBLICLY_ATTESTED");
 assert.equal(snapshot.nightlySecNewIssuerFilingReviewWatch,
   "CYTK_SMMT_OFFICIAL_8K_10Q_10K_RESEARCH_LEADS_NOT_FDA_OUTCOMES");
 assert.equal(snapshot.secNewIssuerFilingWatchLastReviewedGoalDates.CYTK,"2026-08-06");
 assert.equal(snapshot.secNewIssuerFilingWatchLastReviewedGoalDates.SMMT,"2026-10-21");
 assert.equal(snapshot.nov14AdditionalDatedIssuerGoalContinuityCases,2);
 assert.equal(snapshot.nov14LocatedIssuerGoalSourcesOver30DaysOldAtSnapshot,1);
 assert.equal(snapshot.nov14SmmtLatestIssuerDeadlineReiterationDate,"2026-10-21");
 assert.equal(snapshot.nov14SmmtLatestSourceMainTrial,"EA2251_BILIARY_TRACT_NCT07765433_NOT_HARMONI");
 assert.equal(snapshot.nov14IssuerGoalContinuityIndependentlyRulesOutFurtherRevisions,0);
 assert.equal(snapshot.nightlyPublicFDAApplicationHistoryWatch,
   "RESEARCH_ONLY_MONITOR_SOURCE_STATUS_ARTIFACT_NOT_SITE_LIVE");
 assert.equal(snapshot.nov14KnownUnrelatedAlreadyApprovedFdaSupplementRemsControls,1);
 assert.equal(snapshot.nov14IssuerReportedOSRequirementPrimaryNonsignificantCases,1);
 assert.equal(snapshot.provenIndependentFirstGoalForecasts,0);
 assert.equal(existing.approvedRaasMetricCalibrations,0);
 assert.match(metricSpecs,/RAAS_SPEC_VERSION="2026-11-02-foundation-v1"/);
});

test("Mobile site distinguishes V1 active foundation and V2 source candidate and provides nightly evidence link",()=>{
 assert.match(source,/function V2CandidateReadiness\(\)/);
 assert.match(source,/<V2CandidateReadiness\/>/);
 assert.match(source,/id="raas-v2-source-readiness"/);
 assert.match(source,/data-raas-v2-status="RESEARCH_CANDIDATE_NOT_CALIBRATED"/);
 assert.match(source,/Foundation V1 remains installed/);
 assert.match(source,/No V2 FDA accuracy percentage can yet be reported/);
 assert.match(source,/x\.remainingLegacyFutureCaseSourceLeadsAtSnapshot/);
 assert.match(source,/x\.approvedMetricCalibrations/);
 assert.match(source,/x\.nightlySourceReadinessAuditUrl/);
 assert.match(source,/href="#raas-v2-source-readiness"/);
 assert.match(source,/x\.knownRevisedGoalExcludedFromOriginalDeadlineQueue/);
 assert.match(source,/x\.legacyCasesStillUnreviewedByIssuerSources/);
 assert.match(source,/The remaining \{x\.remainingUnexcludedLegacyDateResearchLeads\} are not independently certified original-goal forecasts/);
});

test("Mobile nightly official FDA lookup is explicitly separate from a scored forecast",()=>{
 assert.match(source,/raas-v2-daily-openfda-application-watch/);
 assert.match(source,/S-001 is a February REMS-only action/);
 assert.match(source,/the pending MAPLE-HCM efficacy supplement/);
 assert.ok(source.includes("<strong>not</strong>"));
 assert.match(source,/SMMT ivonescimab ingredient search/);
 assert.match(source,/may reveal a BLA candidate/);
 assert.match(source,/FDA Purple Book/);
 assert.match(snapshot.nightlyPublicFDAApplicationHistoryWatchScope,/SMMT ivonescimab public ingredient search/);
 assert.match(source,/Live results are in the/);
 assert.match(source,/not this dated website snapshot/);
});

test("Nov14 mobile issuer-goal panel distinguishes actual January sNDA filing from Feb public release",()=>{
 assert.match(source,/import nov14IssuerGoalContinuity from/);
 assert.match(source,/raas-v2-nov14-issuer-goal-continuity/);
 assert.match(source,/nov14IssuerGoalContinuity\.records\.map/);
 assert.match(source,/January is the actual filing month/);
 assert.match(source,/February 24 was the public announcement/);
 assert.match(source,/CYTK\x27s August source is over 30 days old/);
 assert.match(source,/not a live FDA deadline guarantee/);
 const d=require("../data/raas-v2-nov14-issuer-goal-continuity.json");
 assert.equal(d.latestDatedIssuerGoalContinuityCases,2);
 assert.equal(d.independentlyVerifiedNoSubsequentGoalRevisionsCount,0);
 assert.equal(d.prospectivelyFrozenThreeWayForecastCount,0);
 assert.equal(d.approvedRAASMetricCalibrationCount,0);
 assert.deepEqual(d.records.map(r=>r.ticker),["CYTK","SMMT"]);
 assert.ok(d.records.every(r=>r.reportedGoalDate==="2026-11-14" &&
   r.originalNov14GoalStillListedByIssuerAtSourceDate===true &&
   r.absenceOfLaterGoalChangeIndependentlyEstablished===false &&
   r.fullDatedFDAActionCycleIndependentlyEstablished===false));
});

test("Latest SMMT issuer HARMONi goal is an Oct 21 EA2251 background item, not trial conflation",()=>{
 const evidence=require("../data/raas-v2-nov14-issuer-goal-continuity.json");
 const by=Object.fromEntries(evidence.records.map(x=>[x.ticker,x]));
 assert.equal(by.SMMT.issuerPublicSourceDate,"2026-10-21");
 assert.equal(by.SMMT.sourceMainSubject,"EA2251_BILIARY_TRACT_CANCER_NOT_HARMONI");
 assert.equal(by.SMMT.sourceMainSubjectClinicalTrialId,"NCT07765433");
 assert.equal(by.SMMT.pendingBlaPivotalTrialId,"NCT06396065");
 assert.equal(by.SMMT.sourceMainSubjectIsPendingHarmoniBlaStudy,false);
 assert.equal(by.SMMT.harmoniNov14PdufaGoalExplicitlyRepeatedInBackground,true);
 assert.equal(by.SMMT.absenceOfLaterGoalChangeIndependentlyEstablished,false);
 assert.match(source,/EA2251 \(NCT07765433\), biliary tract cancer/);
 assert.match(source,/not<\/strong> HARMONi \(NCT06396065\)/);
 assert.match(source,/November 14 date is repeated only in the HARMONi background/);
 assert.match(source,/while SMMT's October 21 issuer background paragraph is more recent/);
});

test("SEC recent issuer filings can only initiate manual source review",()=>{
 assert.match(source,/raas-v2-sec-recent-issuer-filings/);
 assert.match(source,/data\.sec\.gov\/submissions\/CIK0001061983/);
 assert.match(source,/data\.sec\.gov\/submissions\/CIK0001599298/);
 assert.match(source,/A new SEC filing is only a document to inspect/);
 assert.match(source,/SEC HTTP 403/);
 assert.match(source,/not an automatically refreshed filing list/);
});

test("Issuer official news fallback does not mislabel SEC denial as restored",()=>{
 assert.match(source,/raas-v2-official-issuer-news-fallback/);
 assert.match(source,/ir\.cytokinetics\.com\/press-releases/);
 assert.match(source,/smmttx\.com\/investor-information/);
 assert.match(source,/SEC source unavailable/);
 assert.match(source,/not a complete SEC filing feed/);
 assert.match(source,/both remain unverified/);
});

test("Official SEC Atom recovery source is separate from denied JSON and only unreviewed filing leads",()=>{
 assert.match(source,/New: Official SEC Atom alternate feed/);
 assert.match(source,/browse-edgar\?action=getcompany&amp;CIK=0001061983/);
 assert.match(source,/browse-edgar\?action=getcompany&amp;CIK=0001599298/);
 assert.match(source,/Only CIK-matched 8-K, 10-Q and 10-K filing links/);
 assert.match(source,/An Atom error is also marked/);
 assert.match(source,/not zero filings/);
});
