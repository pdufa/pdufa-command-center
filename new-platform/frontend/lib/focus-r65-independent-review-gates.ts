/** MAIN R65: read-only projection of the independently authenticated, original-
 * source clinical reviewer intake contract. This is NOT a reviewer submission
 * endpoint, an independent medical assessment, or an FDA forecast.
 */
import {FOCUS_R64_METHOD_PAGE_VIEW,EIGHT_SOURCE_DOMAINS} from
  "./focus-r64-original-method-page-view";

export const R65_DOMAIN_QUESTIONS = [
  ["Verify phase, indication, patient-relevant original endpoint, unit, threshold and follow-up",
   "Reconcile registry and protocol/SAP primary hierarchy to final reported results",
   "Check endpoint change chronology and outcome-adjudication blinding"],
  ["Verify original estimand, treatment policy and intercurrent-event handling",
   "Check randomized versus analyzed denominators, exclusions and analysis sets",
   "Identify deviations from the original locked estimand or analysis population"],
  ["Verify prospectively selected statistical model, effect scale and assumptions",
   "Independently examine uncertainty intervals, multiplicity-adjusted significance and model fit",
   "Record whether patient-level reanalysis is unavailable rather than infer correctness"],
  ["Verify original family-wise hypothesis structure, alpha budget and test ordering",
   "Reconcile every published p-value to the original locked testing hierarchy",
   "Disallow nominal p-values from being labeled multiplicity-adjusted without evidence"],
  ["Verify prespecified missing data treatment, protocol deviations and censoring",
   "Examine differential attrition and sensitivity to unobserved outcomes",
   "Do not convert missing evidence into a numerical failure score"],
  ["Verify prospective versus exploratory sensitivity analysis design",
   "Review robustness to alternative estimands and reasonable missingness assumptions",
   "Record contrary results and negative findings, not only positive corroboration"],
  ["Verify actual treatment exposure, treatment-emergent definitions and follow-up",
   "Review independent arm denominators, serious adverse events, deaths and imbalances",
   "Do not infer causal risks or aggregate incompatible arms without verification"],
  ["Obtain original, signed protocol and SAP versions and amendment chronology",
   "Independently verify first-public and pre-unblinding version timestamps",
   "Disclose post-hoc changes, source conflicts and unavailable original documents"],
] as const;

export const R65_REQUIRED_REVIEW_FIELDS=[
  "verifiedPhaseEventId","reviewerPrincipal","reviewerAuthorizedRole",
  "originalDocumentContentSha256","originalDocumentVersionAndDate",
  "firstPublicDateEvidence","unblindingOrReadoutDateEvidence",
  "examinationDateUtc","sourcePageLocation","favorableEvidence",
  "unfavorableEvidence","contradictoryEvidence","missingEvidence",
  "clinicalRationale","applicabilityJustification",
  "secondIndependentVerifier","reviewEventId"
] as const;

type Research=NonNullable<typeof FOCUS_R64_METHOD_PAGE_VIEW>;
export function buildR65ReviewGateDisplay(source:Research|null=FOCUS_R64_METHOD_PAGE_VIEW){
  if(!source||
     source.schema!=="MAIN_R64_VIEW_ONLY_ORIGINAL_R63_EIGHT_DOMAIN_PAGE_LEADS"||
     source.uniqueNctCount!==29||source.applicationGroups!==23||
     source.sourceReviewDimensions!==8||source.unscoredSourceReviewSlots!==232||
     source.originalCurrentAttachedDocuments!==23||
     source.sourcePageLeadCount!==466||
     source.clinicalMethodScores!==0||source.qualifiedReviewerSignoffs!==0||
     source.independentlyValidatedFdaForecasts!==0||
     source.measuredForecastAccuracy!==null||
     source.officialFutureFdaOutcome!=="ABSTAIN"||
     source.noProductionWritesOrModelTraining!==true||
     source.trials.length!==29||
     EIGHT_SOURCE_DOMAINS.length!==8||R65_DOMAIN_QUESTIONS.length!==8||
     R65_REQUIRED_REVIEW_FIELDS.length!==17)return null;
  const ids=new Set<string>();
  let exactRefs=0;
  const tasks=source.trials.map(t=>{
    if(ids.has(t.nct)||!/^NCT\d{8}$/.test(t.nct)||
       t.domains.length!==8||
       t.independentlyCompletedAssessmentLevel!==null||
       t.signedScientificGrades!==0||t.officialFdaOutcome!=="ABSTAIN"||
       t.accuracy!==null)return null;
    ids.add(t.nct);
    const byDomain=t.domains.map((d,i)=>{
      if(d.key!==EIGHT_SOURCE_DOMAINS[i].key||
         d.level!=="UNASSESSED_SOURCE_ONLY"||
         d.scientificScore!==null||d.qualifiedReviewerSigned!==false||
         d.originalSourceVersionBeforeUnblindingVerified!==false||
         !Array.isArray(d.references))return null;
      exactRefs+=d.references.length;
      return {
        id:t.nct+":"+d.key,domain:d.key,label:d.label,
        requiredQuestions:[...R65_DOMAIN_QUESTIONS[i]],
        sourcePageLeads:d.references.length,
        firstVerifyPhase:true,
        originalPreReadoutDocumentVersionVerified:false,
        evidenceFields:[...R65_REQUIRED_REVIEW_FIELDS],
        reviewerAttested:false as const,
        secondaryVerifierAttested:false as const,
        grade:null,
        clinicalDisposition:"PENDING_QUALIFIED_HUMAN_ADJUDICATION" as const,
        failureOrSuccess:"UNDETERMINED" as const,
      };
    });
    if(byDomain.some(x=>x===null))return null;
    return {
      nct:t.nct,ticker:t.ticker,
      applicationCycles:[...t.applicationCycles],
      reviewedPhaseVerified:false,
      sourceLeads:t.totalPageLeads,
      clinicalAssessmentLevel:"UNASSESSED_SOURCE_ONLY" as const,
      methodTasks:byDomain as NonNullable<typeof byDomain[number]>[],
      qualifiedSignedGrades:0,
    };
  });
  if(tasks.some(x=>x===null)||ids.size!==29||exactRefs!==466||
     tasks.reduce((n,t)=>n+(t?.methodTasks.length??0),0)!==232)return null;
  return {
    schema:"MAIN_R65_READ_ONLY_INDEPENDENT_REVIEW_GATE_DISPLAY" as const,
    originalReviewRun:42717833879,
    originalReviewArtifact:13717848415,
    originalSourceSha256:"1238d5a0ed120cd47d05dec12486e59e2bf8dbd6e7b73b989372955db622127a",
    sourceArchiveUrl:"https://github.com/pdufa/pdufa-command-center/actions/runs/42717833879/artifacts/13717848415",
    uniqueTrials:29,provisionalApplications:23,requiredMethodReviews:232,
    originalMachinePageLeads:466,
    records:tasks as NonNullable<typeof tasks[number]>[],
    signedPhaseReviews:0,signedScientificReviews:0,
    releasedMethodGrades:0,
    independentlyValidatedFdaForecasts:0,
    predictionAccuracy:null,officialFutureFdaOutcome:"ABSTAIN" as const,
    notAnEnabledReviewerSubmissionEndpoint:true,
    productionOrLedgerWrites:false,
  };
}
export const FOCUS_R65_REVIEW_GATES=buildR65ReviewGateDisplay();
