/** MAIN R45 — pinned current registry text comparison, NOT an original locked SAP review. */
import pin from "../data/focus-r45-primary-text-concordance.json";
import {FOCUS_PRELIMINARY_R39} from "./focus-preliminary-application-research";
import {FOCUS_R42_PRIMARY_RESULTS} from "./focus-r42-primary-research";

const RECEIPT="5ca01f7ded8ba26939d520284ae1ecda908a155087af3e397f77c4a9fc0cc60e";
export function validateR45CurrentEndpointText(data:unknown=pin){
 if(!data||typeof data!=="object"||Array.isArray(data))return null;
 const v=data as typeof pin, c=v.counts;
 if(v.schema!=="MAIN_R45_PINNED_CURRENT_REGISTRY_PRIMARY_TEXT"||
   v.asOf!=="2026-11-09"||v.observedAtUtc!=="2026-11-09T17:35:22+00:00"||
   v.sourceRunId!==42666046282||v.sourceArtifactId!==13697545092||
   v.sourceReceiptSha256!==RECEIPT||
   v.sourceArtifactExpiresAt!=="2027-02-07T17:35:07Z"||
   c.trialNcts!==29||c.applicationGroups!==23||c.currentRegistryRecordsFetched!==29||
   c.withRegistryResults!==12||c.withoutRegistryResults!==17||
   c.currentRegisteredPrimaryTitles!==45||c.postedPrimaryTables!==16||
   c.exactCurrentTitleTimeframeMatches!==16||
   c.unmatchedPostedPrimaryTables!==0||c.titleOnlyTimeframeDifferences!==0||
   c.qualifiedClinicalReviews!==0||c.validatedFDAForecasts!==0||
   c.independentHistoricalBacktests!==0||
   v.originalPreReadoutRegistryVersionVerified!==false||
   v.lockedSapAndMultiplicityVerified!==false||
   v.independentClinicalReviewSigned!==false||v.scientificScoresWritten!==0||
   v.officialFdaPrediction!=="ABSTAIN"||v.reviewDelayPrediction!=="ABSTAIN"||
   v.numericProbability!==null||
   !FOCUS_R42_PRIMARY_RESULTS||FOCUS_PRELIMINARY_R39.trials.length!==29||
   FOCUS_PRELIMINARY_R39.applications.length!==23||
   !Array.isArray(v.rows)||v.rows.length!==29)return null;
 const byNct=new Map(FOCUS_PRELIMINARY_R39.trials.map(t=>[t.nct,t]));
 const posted=new Set(FOCUS_R42_PRIMARY_RESULTS.trialRows.filter(t=>t.primary).map(t=>t.nct));
 const seen=new Set<string>();
 let registeredTotal=0,postedTotal=0,exactTotal=0,resultCount=0;
 for(const r of v.rows){
   if(!Array.isArray(r)||r.length!==4||typeof r[0]!=="string"||
      !/^NCT\d{8}$/.test(r[0])||!byNct.has(r[0])||seen.has(r[0])||
      r.slice(1).some(n=>typeof n!=="number"||!Number.isSafeInteger(n)||n<0))return null;
   const [n,registered,withResult,exact]=r;
   if(Number(exact)>Number(withResult)||Number(withResult)>Number(registered)||
     (Number(withResult)>0)!==posted.has(String(n)))return null;
   seen.add(n);
   registeredTotal+=Number(registered);postedTotal+=Number(withResult);exactTotal+=Number(exact);
   resultCount+=Number(withResult)>0?1:0;
 }
 if(seen.size!==29||registeredTotal!==45||postedTotal!==16||exactTotal!==16||
    resultCount!==12)return null;
 const items=v.rows.map(r=>{
   const nct=String(r[0]),t=byNct.get(nct)!;
   return {nct,ticker:t.ticker,applicationCycleIds:[...t.applicationCycleIds],
     currentRegisteredPrimaryCount:Number(r[1]),postedPrimaryCount:Number(r[2]),
     exactCurrentTitleTimeframeMatchCount:Number(r[3]),
     registrySource:"https://clinicaltrials.gov/study/"+nct,
     originalPrespecificationVerified:false,clinicalGrade:null,FDAForecast:"ABSTAIN" as const};
 });
 return {...v,items};
}
export const FOCUS_R45_CURRENT_TEXT=validateR45CurrentEndpointText();
