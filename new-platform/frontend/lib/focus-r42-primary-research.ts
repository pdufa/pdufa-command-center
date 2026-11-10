/** R42 primary result field overlay. Source receipt is from exact GitHub Actions run.
 * 16 source-reported outcome tables are not independent scientific assessments.
 */
import pinned from "../data/focus-r42-primary-result-fields.json";
import {FOCUS_PRELIMINARY_R39} from "./focus-preliminary-application-research";
import {FOCUS_R40_SOURCE_STATUS} from "./focus-r40-source-readiness";
const RECEIPT_SHA="9ebfac62e6d99e105d63c107bc0aa9a52803293eba915ba4a43be3fba93f15cf";
const SRC_NCTS=new Set(FOCUS_R40_SOURCE_STATUS?.trialStatus
   .filter(t=>t.currentRegistryResultsSectionPresent).map(t=>t.nct)??[]);

export function buildFocusR42PrimarySourceView(data:unknown=pinned){
  if(!data||typeof data!=="object"||Array.isArray(data))return null;
  const v=data as typeof pinned;
  if(v.schema!=="MAIN_R42_PINNED_SOURCE_REPORTED_PRIMARY_FIELDS"||
     v.asOf!=="2026-11-09"||v.observedAtUtc!=="2026-11-09T16:49:39+00:00"||
     v.sourceReceiptSha256!==RECEIPT_SHA||
     v.sourceRunId!==42658620560||v.sourceArtifactId!==13693571338||
     v.sourceArtifactExpiresAt!=="2027-02-07T16:49:25Z"||
     v.counts?.trials!==29||v.counts.applications!==23||
     v.counts.primaryOutcomeTables!==16||v.counts.trialsWithPrimaryTables!==12||
     v.counts.trialsWithoutRegistryResultsSection!==17||
     v.counts.authorizedScientificGrades!==0||
     v.counts.validatedFdaForecasts!==0||v.counts.historicalBacktests!==0||
     v.clinicalMeaning!=="UNREVIEWED_REGISTRY_POSTED_PRIMARY_RESULT_FIELDS"||
     v.officialFutureFdaForecast!=="ABSTAIN"||v.accuracy!=="NOT_CALIBRATED"||
     v.sourcePublicationChronologyIndependentlyVerified!==false||
     v.clinicalReviewerSigned!==false||
     FOCUS_PRELIMINARY_R39.trials.length!==29||
     FOCUS_PRELIMINARY_R39.applications.length!==23||
     !FOCUS_R40_SOURCE_STATUS||SRC_NCTS.size!==12||
     !Array.isArray(v.trialPrimaryResults)||v.trialPrimaryResults.length!==12)
     return null;
  const sourceIds=new Set(FOCUS_PRELIMINARY_R39.trials.map(t=>t.nct));
  const present=new Set(v.trialPrimaryResults.map(t=>t.nct));
  if(present.size!==12||
     [...present].some(n=>!SRC_NCTS.has(n)||!sourceIds.has(n))||
     [...SRC_NCTS].some(n=>!present.has(n))||
     v.trialPrimaryResults.some(t=>!t.reportedPostedOn||
       !/^20\d{2}-\d{2}-\d{2}$/.test(t.reportedPostedOn)||
       !Array.isArray(t.endpoints)||t.endpoints.length<1||
       t.endpoints.some(e=>typeof e.title!=="string"||e.title.length<10||
          !Array.isArray(e.pValuesAsReported)||e.pValuesAsReported.some(p=>typeof p!=="string"))||
       t.endpoints.length>8)||
     v.trialPrimaryResults.reduce((sum,t)=>sum+t.endpoints.length,0)!==16)
     return null;
  const byNct=new Map(v.trialPrimaryResults.map(t=>[t.nct,t]));
  return {
    asOf:v.asOf,sourceArchiveUrl:v.sourceArtifactUrl,sha256:v.sourceReceiptSha256,
    counts:v.counts,
    trialRows:FOCUS_PRELIMINARY_R39.trials.map(t=>({
      nct:t.nct,ticker:t.ticker,
      applicationCycleIds:[...t.applicationCycleIds],
      sourceUrl:"https://clinicaltrials.gov/study/"+t.nct,
      primary:byNct.get(t.nct)??null,
      status:byNct.has(t.nct)?"POSTED_PRIMARY_OUTCOME_FIELDS":
        "NO_RESULTS_SECTION_IN_CURRENT_REGISTRY",
      reviewerGrade:null,
      FDAForecast:"ABSTAIN" as const
    })),
    sourceLimits:"Registry-reported p-values and arm tables have not been checked against a final locked SAP, multiplicity, safety/CONSORT, CMC or FDA reviewer decisions. No results section does not mean the study lacks published Phase 3 results.",
    independentlyReviewedMethods:0,
    validatedFDAForecasts:0,validatedHistoricalBacktests:0,
    fdaProbability:null,accuracy:"NOT_CALIBRATED" as const
  };
}
export const FOCUS_R42_PRIMARY_RESULTS=buildFocusR42PrimarySourceView();
