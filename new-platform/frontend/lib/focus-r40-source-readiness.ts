/** MAIN Rev40 source-access overlay; NOT historical/clinical/source-grade verification.
 * Exact GitHub Action source-retrieval receipt pinned by SHA-256. Do not overwrite
 * Rev39 clinical research leans, FDA ABSTAIN, reviewer grades or accuracy.
 */
import pinned from "../data/focus-r40-public-source-audit.json";
import {FOCUS_PRELIMINARY_R39} from "./focus-preliminary-application-research";

const RECEIPT_SHA="0601058cd65f62380c3f3242b408f95ca13408f21d2845e589e9e4f5faf7d32c";
const SHA=/^[a-f0-9]{64}$/;
type Audit=typeof pinned;
export function buildFocusR40SourceStatus(source:unknown=pinned){
  if(!source||typeof source!=="object"||Array.isArray(source))return null;
  const v=source as Audit, counts=v.counts, meta=v.source;
  if(v.schema!=="MAIN_FOCUS_R40_PUBLIC_SOURCE_METADATA_PIN_20261109"||
     v.snapshot!=="2026-11-09"||
     v.observedAtUtc!=="2026-11-09T16:24:54+00:00"||
     meta?.receiptSha256!==RECEIPT_SHA||!SHA.test(meta.artifactZipSha256)||
     meta.runId!==42654460905||meta.artifactId!==13691348436||
     meta.artifactExpiresAt!=="2027-02-07T16:24:36Z"||
     meta.sourceBytesStoredInRepository!==false||
     meta.metadataNotClinicalAdjudication!==true||
     counts?.registryRetrieved!==29||counts?.applicationGroups!==23||
     counts?.applicationGroupsWithPublicSource!==23||
     counts?.registryResultsSectionPresent!==12||
     counts?.registryResultsSectionNotPresent!==17||
     counts?.canonicalDistinctSourceUrls!==21||
     counts?.additionalOfficialSecUrls!==1||
     counts?.uniqueUrlsAttempted!==22||counts?.uniqueUrlsFetched!==21||
     counts?.originalSourcePublicationDatesAuthenticated!==0||
     counts?.qualifiedClinicalReviews!==0||
     counts?.independentlyValidatedFdaForecasts!==0||
     counts?.historicalBacktests!==0||
     v.sourceOnly!==true||v.modelAuthorized!==false||
     v.clinicalGradesWritten!==0||v.officialFdaForecast!=="ABSTAIN"||
     v.calibratedAccuracy!==null||
     !Array.isArray(v.ncts)||v.ncts.length!==29||
     !Array.isArray(v.registryResultsSectionPresent)||v.registryResultsSectionPresent.length!==12||
     !Array.isArray(v.applicationIds)||v.applicationIds.length!==23||
     !Array.isArray(v.registryPhaseTwoAndThree)||v.registryPhaseTwoAndThree.length!==1)
     return null;
  const trialSet=new Set(FOCUS_PRELIMINARY_R39.trials.map(t=>t.nct));
  const appSet=new Set(FOCUS_PRELIMINARY_R39.applications.map(a=>a.id));
  const pinnedTrials=new Set(v.ncts),pinnedApps=new Set(v.applicationIds);
  const withSection=new Set(v.registryResultsSectionPresent);
  const phaseMixed=new Set(v.registryPhaseTwoAndThree);
  if(trialSet.size!==29||appSet.size!==23||pinnedTrials.size!==29||pinnedApps.size!==23||
     withSection.size!==12||phaseMixed.size!==1||
     [...trialSet].some(n=>!pinnedTrials.has(n))||
     [...appSet].some(id=>!pinnedApps.has(id))||
     [...withSection].some(n=>!trialSet.has(n))||
     [...phaseMixed].some(n=>!trialSet.has(n))||
     !phaseMixed.has("NCT04871282")||
     v.canonicalUnavailable?.cycleId!=="achv-cytisinicline"||
     v.canonicalUnavailable.issuerHttpStatus!==301||
     v.canonicalUnavailable.alternativeFetched!==true||
     v.canonicalUnavailable.officialAlternative!=="https://www.sec.gov/Archives/edgar/data/949858/000119312526344624/achv-20260630.htm"||
     !SHA.test(v.canonicalUnavailable.alternateSha256))
     return null;
  if(FOCUS_PRELIMINARY_R39.summary.independentlyValidatedFDAForecasts!==0||
     FOCUS_PRELIMINARY_R39.summary.qualifiedIndependentClinicalReviews!==0||
     FOCUS_PRELIMINARY_R39.summary.verifiedHistoricalBacktests!==0)
     return null;
  const trialStatus=FOCUS_PRELIMINARY_R39.trials.map(t=>({
    nct:t.nct,
    registeredPhase:phaseMixed.has(t.nct)?"PHASE2 / PHASE3":"PHASE3",
    currentRegistryResultsSectionPresent:withSection.has(t.nct),
    registryFetchSucceeded:true,
    sourceOriginalPostingDateIndependentlyAuthenticated:false,
    independentlyGradedClinicalMethods:0,
  }));
  const groupStatus=FOCUS_PRELIMINARY_R39.applications.map(a=>({
    cycleId:a.id,
    retrievedPublicSource:true,
    sourceRoute:a.id==="achv-cytisinicline"?"OFFICIAL_SEC_FALLBACK":"CANONICAL_SOURCE_LINK",
    originalPublicationClockVerified:false,
    regulatorApplicationCycleVerified:false,
    qualifiedReviewerSignoff:false,
    fdaForecast:a.observedAction?"NOT_APPLICABLE_ALREADY_OBSERVED":"ABSTAIN"
  }));
  return {
    schema:v.schema,asOf:v.snapshot,observedAtUtc:v.observedAtUtc,
    sourceArtifactUrl:meta.artifactUrl,sourceReceiptSha256:meta.receiptSha256,
    sourceExpiresAt:meta.artifactExpiresAt,
    counts:counts,
    trialStatus,groupStatus,
    sourceInterpretation:v.sourceInterpretation,
    unreviewedRegistryResultsMissing:17,
    originalPublicationVersionsAuthenticated:0,
    qualifiedClinicalReviews:0,
    independentlyValidatedFdaForecasts:0,
    historicalRealBacktests:0,
    officialFutureFdaForecast:"ABSTAIN" as const,
    accuracy:"NOT_CALIBRATED" as const,
    reviewOrScoringWrites:false as const,
  };
}
export const FOCUS_R40_SOURCE_STATUS=buildFocusR40SourceStatus();
