/** R62 read-only application-level source coverage from the verified R61/R60
 * exact-NCT trial source. This is a research checklist, NOT an FDA forecast,
 * approval lean, clinical method grade or independent regulatory decision.
 */
import {FOCUS_R60_ORIGINAL_TRIAL_REVIEW} from "./focus-r60-original-trial-research";
import {FOCUS_PRELIMINARY_R39} from "./focus-preliminary-application-research";

type SourceReview = NonNullable<typeof FOCUS_R60_ORIGINAL_TRIAL_REVIEW>;
type OriginalApplications = typeof FOCUS_PRELIMINARY_R39.applications;
type App = OriginalApplications[number];

export function buildR62ApplicationSourceReview(
  source:SourceReview|null=FOCUS_R60_ORIGINAL_TRIAL_REVIEW,
  originals:OriginalApplications=FOCUS_PRELIMINARY_R39.applications
){
  if(!source||source.schema!=="MAIN_R61_VIEW_ONLY_OF_R60_ORIGINAL_REGISTRY_SOURCE"||
     source.counts.uniqueNcts!==29||source.counts.applicationGroups!==23||
     source.counts.postedPrimaryTables!==16||
     source.counts.reportedStatisticalComparisons!==20||
     source.counts.independentlyValidatedFdaForecasts!==0||
     source.predictionAccuracy!==null||source.allOfficialFDAForecasts!=="ABSTAIN"||
     source.trials.length!==29||originals.length!==23||
     FOCUS_PRELIMINARY_R39.summary.qualifiedIndependentClinicalReviews!==0||
     FOCUS_PRELIMINARY_R39.summary.independentlyValidatedFDAForecasts!==0)return null;

  const byNct=new Map(source.trials.map(t=>[t.nct,t]));
  const groups=new Set<string>();
  const seen=new Map(source.trials.map(t=>[t.nct,0]));
  if(byNct.size!==29)return null;
  const rows=[];
  for(const a of originals){
    if(groups.has(a.id)||!a.ncts.length||new Set(a.ncts).size!==a.ncts.length||
       a.qualifiedReviewerSignoff!==false||
       a.numericalFDAProbability!==null||a.calibratedAccuracy!==null||
       a.exactFdaDecisionCycleIndependentlyCertified!==false)return null;
    groups.add(a.id);
    const linked=[];
    for(const nct of a.ncts){
      const trial=byNct.get(nct);
      if(!trial||!trial.cycles.includes(a.id)||
         trial.independentlyValidatedScientificReview!==false||
         trial.officialApprovalOrCrlForecast!=="ABSTAIN"||
         trial.officialReviewTimingForecast!=="ABSTAIN"||
         trial.fdaProbability!==null)return null;
      seen.set(nct,(seen.get(nct)??0)+1);
      linked.push({
        nct:trial.nct,
        registryUrl:trial.originalRegistryUrl,
        currentPrimaryTables:trial.primaryTables,
        sourceReportedComparisons:trial.reportedAnalyses,
        currentSafetyArms:trial.safetyArms,
        evidenceExceptions:[...trial.reviewExceptions],
        currentRegistryPrimaryAvailable:trial.primaryTables>0,
        scientificReviewValidated:false as const
      });
    }
    rows.push({
      id:a.id,ticker:a.ticker,drug:a.drug,indication:a.indication,
      sponsorReportedStageUnverified:a.originalStage,
      linkedNctCount:linked.length,
      linkedTrials:linked,
      currentPrimaryTrialCount:linked.filter(t=>t.currentRegistryPrimaryAvailable).length,
      currentSafetyTrialCount:linked.filter(t=>t.currentSafetyArms>0).length,
      sourceReportedStatisticalComparisons:linked.reduce((n,t)=>n+t.sourceReportedComparisons,0),
      originalSourceExceptionCount:linked.reduce((n,t)=>n+t.evidenceExceptions.length,0),
      reviewNextSteps:[
        "Independently verify each Phase 3 trial and source chronology",
        "Reconcile original pre-unblinding protocol/SAP, primary endpoint and multiplicity",
        "Adjudicate safety exposures, benefit-risk, and application-specific FDA/CMC evidence",
        "Validate and calibrate historical predictions separately before release"
      ],
      observedAlreadyFromPreliminarySnapshot:a.originalStage==="APPROVED_ALREADY",
      officialFutureFdaOutcome:"ABSTAIN" as const,
      officialFutureTiming:"ABSTAIN" as const,
      calibratedProbability:null,
      signedScientificReview:false as const
    });
  }
  if([...seen.entries()].some(([n,count])=>
      count===0||count!==byNct.get(n)?.cycles.length)||
     [...source.trials].some(t=>t.cycles.length===0||
       t.cycles.some(id=>!groups.has(id)))||
     rows.length!==23||
     rows.some(a=>a.linkedTrials.some(t=>
       byNct.get(t.nct)?.cycles.filter(id=>id===a.id).length!==1)))return null;
  return {
    schema:"MAIN_R62_23_APPLICATION_RESEARCH_COVERAGE_ONLY" as const,
    originalR60Run:source.run,
    originalR60Artifact:source.artifact,
    sourceArchiveUrl:source.sourceArchiveUrl,
    uniqueTrials:29,
    provisionalApplicationGroups:23,
    rows,
    qualifiedClinicalReviews:0,
    independentlyValidatedFdaForecasts:0,
    historicalMeasuredAccuracy:null,
    allFutureApprovalCrlAndTimingForecasts:"ABSTAIN" as const,
    evidenceCoverageNotOutcomeProbability:true,
    noProductionOrClinicalWrites:true
  };
}
export const FOCUS_R62_APPLICATION_SOURCE_REVIEW=buildR62ApplicationSourceReview();
