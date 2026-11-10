/** R91: check the archived exact original public source structured readbacks
 * before presenting source-data counts or using them for scientific handoff.
 * No efficacy, clinical significance, safety or FDA outcome grades can be
 * concluded from posted aggregate results without qualified review.
 */
import source from "../data/focus-r91-posted-original-results-readbacks-20261110.json";
import {R91_POSTED_RESULTS_ROSTER} from "./focus-r91-posted-results-reconciliation";

export function buildR91SourceAuditReadiness(input:typeof source=source){
 const roster=R91_POSTED_RESULTS_ROSTER;
 if(!roster||roster.exactTrials!==29||roster.provisionalCycles!==23||
    roster.withPostedResultsAtSnapshot!==12||
    roster.withoutPostedResultsAtSnapshot!==17||
    roster.qualifiedScienceSignoffs!==0||
    roster.originalSignedSAPsVerified!==0||
    roster.validatedFDAPredictions!==0||
    input.schema!=="MAIN_R91_12_CURRENT_ORIGINAL_REGISTRY_PRIMARY_OUTCOME_AND_SAFETY_SOURCED_READBACKS_NOT_GRADED"||
    input.observedOnUtc!=="2026-11-10"||
    input.timePrecision!=="DAY_ONLY"||
    input.census.exactFocusTrials!==29||
    input.census.provisionalFDAApplicationCycles!==23||
    input.census.exactPostedResultsRecordsRead!==12||
    input.census.recordsWithoutPostedOriginalRegistryResultsAtPriorSnapshot!==17||
    input.census.originalReportedPrimaryOutcomeEntries!==16||
    input.census.originalSeriousAdverseEventTerms!==244||
    input.census.sourceSafetyArmGroups!==28||
    input.census.sourceReportedPValueEntries!==20||
    input.census.sourceReportedPrimaryDenominatorGroupValues!==34||
    input.originalCanonicalFOCUSRosterChanged!==false||
    input.qualifiedClinicalReviewsSigned!==0||
    input.originalSignedProspectiveSAPsAuthenticated!==0||
    input.statisticalEffectRecalculationsByModel!==0||
    input.completedSafetyAdjudications!==0||
    input.calibratedFDAForecasts!==0||
    input.FDAOutcome!=="ABSTAIN"||
    input.rows.length!==12)return null;
 const expected=new Map(roster.rows.filter(r=>r.resultsPostedInDatedRegistrySnapshot)
  .map(r=>[r.nct,r]));
 if(expected.size!==12)return null;
 const seen=new Set<string>(),listed=[];
 let primary=0,sae=0,arm=0,pvals=0,denoms=0;
 for(const x of input.rows){
  const r=expected.get(x.nct);
  if(!r||seen.has(x.nct)||x.ticker!==r.ticker||
     x.sourceApiUrl!=="https://clinicaltrials.gov/api/v2/studies/"+x.nct+"?format=json"||
     !/^[a-f0-9]{64}$/u.test(x.officialPublicRawSourceSha256)||
     !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/u.test(x.retrievedAtUtc)||
     x.exactSourceResponseCharacters<1000||
     x.status!=="ORIGINAL_PUBLIC_AGGREGATE_RESULTS_POSTED_NOT_ADJUDICATED"||
     x.sourceChangedSinceLastCensus!==false||
     x.qualifiedScientificAssessmentPerformed!==false||
     x.originalProspectiveSignedSAPAuthenticated!==false||
     x.independentStatisticalModelVerified!==false||
     x.independentSafetyDenominatorsReconciled!==false||
     x.clinicalGrade!==null||x.FDAOutcome!=="ABSTAIN"||
     x.originalReportedPrimaryOutcomes.length!==x.observedPrimaryOutcomeCount||
     x.recordedSeriousAdverseEventTermCount!==x.seriousAdverseEventTerms.length||
     x.observedPrimaryOutcomeCount<=0||
     x.observedOutcomeMeasureCount<x.observedPrimaryOutcomeCount||
     x.originalReportedSafetyArmDenominators.length<=0)return null;
  seen.add(x.nct);
  primary+=x.observedPrimaryOutcomeCount;
  sae+=x.recordedSeriousAdverseEventTermCount;
  arm+=x.originalReportedSafetyArmDenominators.length;
  const originalPrimaryTitles=[];
  for(const o of x.originalReportedPrimaryOutcomes){
   if(!o.title||!Array.isArray(o.groups)||!Array.isArray(o.denominators)||
      !Array.isArray(o.measurements)||!Array.isArray(o.reportedAnalyses))
    return null;
   originalPrimaryTitles.push(o.title);
   pvals+=o.reportedAnalyses.filter(a=>a.pValue!==null).length;
   for(const d of o.denominators){
    if(!Array.isArray(d.counts))return null;
    denoms+=d.counts.length;
   }
  }
  listed.push({
   nct:x.nct,ticker:x.ticker,
   originalResultNctUrl:r.originalRegistryUrl+"?tab=results",
   rawOriginalSourceSHA256:x.officialPublicRawSourceSha256,
   sourceReadAtUtc:x.retrievedAtUtc,
   primaryOutcomeCount:x.observedPrimaryOutcomeCount,
   allSourceOutcomeCount:x.observedOutcomeMeasureCount,
   seriousAdverseEventTerms:x.recordedSeriousAdverseEventTermCount,
   safetyArmGroups:x.originalReportedSafetyArmDenominators.length,
   originallyPostedPrimaryTitles:originalPrimaryTitles,
   sourceOnly:true as const,
   signedQualifiedReview:false as const,
   FDAForecast:"ABSTAIN" as const
  });
 }
 if(seen.size!==12||[...expected.keys()].some(id=>!seen.has(id))||
    primary!==16||sae!==244||arm!==28||pvals!==20||denoms!==34)return null;
 listed.sort((a,b)=>a.ticker.localeCompare(b.ticker)||a.nct.localeCompare(b.nct));
 return {
  schema:"MAIN_R91_FROZEN_12_CASE_SCIENCE_SOURCE_READINESS_NO_JUDGMENT" as const,
  observedDateUtc:input.observedOnUtc,
  originalResultsSourceNcts:12 as const,
  unpostedOriginalResultsNcts:17 as const,
  reportedPrimaryOutcomeEntries:16 as const,
  seriousAdverseTermEntries:244 as const,
  safetyArmGroupEntries:28 as const,
  sourcePValueEntries:20 as const,
  primarySourceDenominatorGroupEntries:34 as const,
  qualifiedIndependentScientificSignoffs:0 as const,
  finalProspectivelySignedSAPsIndependentlyAuthenticated:0 as const,
  validatedFDAForecasts:0 as const,
  rows:listed
 };
}
export const R91_DATED_SOURCE_AUDIT=buildR91SourceAuditReadiness();
