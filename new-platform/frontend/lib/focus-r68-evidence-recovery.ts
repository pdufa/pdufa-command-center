/** MAIN R68. Deterministic read-only SOURCE-RECOVERY worklist combining the
 * SHA-locked R60 original registry research, R64 PDF page index, R65 unsigned
 * reviewer worklist and R67 dated phase-first source. Missing a registry
 * field NEVER means a clinical trial failed, and source availability is not
 * an approval/CRL probability, phase validation or 800-method science grade.
 */
import {FOCUS_R60_ORIGINAL_TRIAL_REVIEW} from "./focus-r60-original-trial-research";
import {FOCUS_R64_METHOD_PAGE_VIEW} from "./focus-r64-original-method-page-view";
import {FOCUS_R65_REVIEW_GATES} from "./focus-r65-independent-review-gates";
import {FOCUS_R67_PHASE_SOURCE} from "./focus-r67-phase-source";

type Efficacy=NonNullable<typeof FOCUS_R60_ORIGINAL_TRIAL_REVIEW>;
type Methods=NonNullable<typeof FOCUS_R64_METHOD_PAGE_VIEW>;
type Review=NonNullable<typeof FOCUS_R65_REVIEW_GATES>;
type Phase=NonNullable<typeof FOCUS_R67_PHASE_SOURCE>;
export type SourceKind="PRIMARY"|"SAFETY"|"METHODS"|"ALL";

export function buildR68EvidenceRecovery(
  efficacy:Efficacy|null=FOCUS_R60_ORIGINAL_TRIAL_REVIEW,
  methods:Methods|null=FOCUS_R64_METHOD_PAGE_VIEW,
  review:Review|null=FOCUS_R65_REVIEW_GATES,
  phase:Phase|null=FOCUS_R67_PHASE_SOURCE
){
  if(!efficacy||!methods||!review||!phase||
    efficacy.counts.uniqueNcts!==29||efficacy.counts.applicationGroups!==23||
    efficacy.counts.trialsWithCurrentPrimary!==12||
    efficacy.counts.trialsWithCurrentSafetyArms!==12||
    efficacy.counts.independentlyValidatedFdaForecasts!==0||
    efficacy.allOfficialFDAForecasts!=="ABSTAIN"||efficacy.predictionAccuracy!==null||
    methods.uniqueNctCount!==29||methods.applicationGroups!==23||
    methods.trialsWithCurrentPageLeads!==12||
    methods.trialsWithoutCurrentPageLeads!==17||
    methods.sourceReviewDimensions!==8||methods.unscoredSourceReviewSlots!==232||
    methods.sourcePageLeadCount!==466||
    methods.clinicalMethodScores!==0||methods.qualifiedReviewerSignoffs!==0||
    methods.independentlyValidatedFdaForecasts!==0||
    methods.officialFutureFdaOutcome!=="ABSTAIN"||
    review.uniqueTrials!==29||review.provisionalApplications!==23||
    review.requiredMethodReviews!==232||review.originalMachinePageLeads!==466||
    review.signedPhaseReviews!==0||review.signedScientificReviews!==0||
    review.releasedMethodGrades!==0||
    review.independentlyValidatedFdaForecasts!==0||
    review.officialFutureFdaOutcome!=="ABSTAIN"||review.predictionAccuracy!==null||
    review.notAnEnabledReviewerSubmissionEndpoint!==true||
    phase.ncts!==29||phase.applications!==23||
    phase.verifiedPhaseReviews!==0||phase.signedScienceReviews!==0||
    phase.independentlyValidatedFDAForecasts!==0||
    phase.futureFDAOutcome!=="ABSTAIN"||
    phase.measuredForecastAccuracy!==null||
    phase.sourceLabelsAreNotClinicalAdjudication!==true||
    phase.productionOrClinicalWrites!==false
  )return null;
  const trials=efficacy.trials;
  const methodsBy=new Map(methods.trials.map(x=>[x.nct,x]));
  const phaseBy=new Map(phase.records.map(x=>[x.nct,x]));
  const reviewBy=new Map(review.records.map(x=>[x.nct,x]));
  if(trials.length!==29||methodsBy.size!==29||
     phaseBy.size!==29||reviewBy.size!==29||
     new Set(trials.map(x=>x.nct)).size!==29)return null;

  const rows=[];
  let posted=0,safety=0,pdf=0;
  let missingPrimary=0,missingSafety=0,missingPdf=0;
  for(const x of trials){
    const m=methodsBy.get(x.nct),p=phaseBy.get(x.nct),h=reviewBy.get(x.nct);
    if(!m||!p||!h||x.ticker!==m.ticker||x.ticker!==p.ticker||
       x.ticker!==h.ticker||
       JSON.stringify(x.cycles)!==JSON.stringify(m.applicationCycles)||
       JSON.stringify(x.cycles)!==JSON.stringify(p.applicationCycles)||
       JSON.stringify(x.cycles)!==JSON.stringify(h.applicationCycles)||
       x.primaryTables<0||x.safetyArms<0||x.reportedAnalyses<0||
       x.originalRegistrySha256!==p.currentOriginalSourceSha256||
       x.officialApprovalOrCrlForecast!=="ABSTAIN"||
       x.independentlyValidatedScientificReview!==false||
       p.independentlyVerifiedTrialPhase!==false||
       p.predictedFDAOutcome!=="ABSTAIN"||
       m.independentlyCompletedAssessmentLevel!==null||
       m.signedScientificGrades!==0||
       m.officialFdaOutcome!=="ABSTAIN"||
       h.qualifiedSignedGrades!==0||h.reviewedPhaseVerified!==false||
       h.clinicalAssessmentLevel!=="UNASSESSED_SOURCE_ONLY"||
       h.methodTasks.length!==8||
       m.domains.length!==8
    )return null;

    const primaryAvailable=x.primaryTables>0;
    const safetyAvailable=x.safetyArms>0;
    const sourcePdfFound=m.sourcePdfDocumentsWithPageLeads>0;
    if(primaryAvailable)posted++;else missingPrimary++;
    if(safetyAvailable)safety++;else missingSafety++;
    if(sourcePdfFound)pdf++;else missingPdf++;
    if(x.reviewExceptions.some(f=>typeof f!=="string"||f.length>150)||
       m.totalPageLeads!==h.sourceLeads||
       m.sourcePdfDocumentsWithPageLeads<0||
       m.sourcePdfDocumentsWithPageLeads>4||
       (m.sourcePdfDocumentsWithPageLeads===0)!==(m.totalPageLeads===0))return null;
    const blockers=[
      {key:"PHASE",label:"Independent source-phase adjudication",
        detail:"Confirm study design, stage and indication from original source and authorized reviewer",
        sourceOnly:true},
      {key:"SAP",label:"Pre-unblinding protocol/SAP chronology",
        detail:"Verify dated, signed original versions, amendments and locked endpoint hierarchy",
        sourceOnly:true},
      {key:"PRIMARY",label:primaryAvailable?
        "Adjudicate currently posted primary endpoint results":
        "Recover original primary endpoint results",
        detail:primaryAvailable?
          "Reconcile posted results, effect, estimand, multiplicity and contradictory evidence with original signed SAP":
          "No primary table in this retained current registry copy; search original sponsor, journal, CSR and regulator records",
        sourceOnly:true},
      {key:"SAFETY",label:safetyAvailable?
        "Independently assess posted safety arm data":
        "Recover original safety exposure and adverse-event tables",
        detail:safetyAvailable?
          "Verify treatment exposure, denominators, comparative risk and causal limitations":
          "No safety arm table in this retained registry copy; retrieve and check sponsor/CSR/regulator sources",
        sourceOnly:true},
      {key:"METHODS",label:sourcePdfFound?
        "Review current protocol/SAP PDF page leads":
        "Recover original protocol and statistical-analysis-plan PDFs",
        detail:sourcePdfFound?
          "The machine-indexed pages are review leads, not verified historical prospective prespecification":
          "No current PDF page lead in this archive; original documents may exist at other locations",
        sourceOnly:true},
    ] as const;
    const designFlags=[
      ...(p.sourcePhase==="Combined Phase 2/3"?
        ["Combined Phase 2/3 label: verify pivotal design suitability"]:[]),
      ...(p.allocation==="NA"?
        ["Registry allocation N/A: do not infer randomization"]:[]),
      ...x.reviewExceptions.map(s=>s.replaceAll("_"," ").toLowerCase())
    ];
    rows.push({
      nct:x.nct,ticker:x.ticker,applicationCycles:[...x.cycles],
      sourceRegistryUrl:x.originalRegistryUrl,
      originalSourceUpdatedDate:p.sourceUpdatedDate,
      originalRegistrySHA256:x.originalRegistrySha256,
      registryReportedPhase:p.sourcePhase,registryReportedStatus:p.sourceStatus,
      currentPostedPrimaryTables:x.primaryTables,
      currentReportedStatisticalComparisons:x.reportedAnalyses,
      currentSafetyArms:x.safetyArms,
      currentPdfFilesWithMachinePageLeads:m.sourcePdfDocumentsWithPageLeads,
      machinePageLeads:m.totalPageLeads,
      sourcePrimaryTableAvailable:primaryAvailable,
      sourceSafetyArmsAvailable:safetyAvailable,
      sourcePdfPageLeadsAvailable:sourcePdfFound,
      missingInRetainedRegistryCopyCount:Number(!primaryAvailable)+
        Number(!safetyAvailable)+Number(!sourcePdfFound),
      designAndOriginalSourceExceptions:designFlags,
      sourceRecoveryTasks:blockers,
      originalMethodPageUrl:"/predictions/assessment?nct="+x.nct+
        "#original-methods-r64",
      assessmentUrl:"/predictions/assessment?nct="+x.nct,
      scientificAssessmentLevel:"UNASSESSED_SOURCE_ONLY" as const,
      qualifiedReviewerSigned:false as const,
      clinicalScienceScore:null,
      officialFutureFdaOutcome:"ABSTAIN" as const,
      historicalMeasuredAccuracy:null,
    });
  }
  if(rows.length!==29||posted!==12||safety!==12||pdf!==12||
     missingPrimary!==17||missingSafety!==17||missingPdf!==17||
     rows.reduce((sum,x)=>sum+x.machinePageLeads,0)!==466||
     rows.some(x=>x.applicationCycles.length===0||
      x.missingInRetainedRegistryCopyCount<0||
      x.missingInRetainedRegistryCopyCount>3))return null;

  // Sorting is ONLY by how many source categories need recovery;
  // it is NEVER by predicted benefit, trial success, grade or FDA outcome.
  const sorted=[...rows].sort((a,b)=>
    b.missingInRetainedRegistryCopyCount-a.missingInRetainedRegistryCopyCount||
    a.ticker.localeCompare(b.ticker)||a.nct.localeCompare(b.nct));
  return {
    schema:"MAIN_R68_ORIGINAL_SOURCE_RECOVERY_WORKLIST_ONLY" as const,
    originalSources:{
      r60:efficacy.sourceArchiveUrl,r63:methods.archiveUrl,
      r65:review.sourceArchiveUrl,r66:phase.archiveUrl
    },
    uniqueTrials:29,provisionalApplicationCycles:23,
    postedPrimaryTrials:12,currentSafetyArmTrials:12,
    trialsWithCurrentPdfPageLeads:12,
    trialsWithoutCurrentPostedPrimary:17,
    trialsWithoutCurrentSafetyArmTables:17,
    trialsWithoutCurrentPdfPageLeads:17,
    scientificDomainSourcePositions:232,
    originalMachinePageLeads:466,
    rows:sorted,
    independentPhaseReviews:0,
    independentClinicalGrades:0,
    qualifiedReviewerSignoffs:0,
    validatedFDAForecasts:0,
    historicalPredictionAccuracy:null,
    allFutureFdaOutcomes:"ABSTAIN" as const,
    sourceMissingDoesNotMeanTrialFailure:true,
    sourceRecoveryIsNotAClinicalRanking:true,
    noWritesToHistoricalOutcomesOrProduction:true,
  };
}
export const FOCUS_R68_EVIDENCE_RECOVERY=buildR68EvidenceRecovery();
