/** MAIN R44 — source-reported arm-specific registry safety, not a risk model. */
import pinned from "../data/focus-r44-original-registry-safety.json";
import {FOCUS_R42_PRIMARY_RESULTS} from "./focus-r42-primary-research";
import {FOCUS_PRELIMINARY_R39} from "./focus-preliminary-application-research";

const SHA="7cf71efffaf9cc46446e75cd4a8be60c13783b5121e8d0d4650582b3d71340ab";
const NCT=/^NCT\d{8}$/;
export function validateFocusR44Safety(data:unknown=pinned){
 if(!data||typeof data!=="object"||Array.isArray(data))return null;
 const x=data as typeof pinned;
 if(x.schema!=="MAIN_R44_PINNED_ORIGINAL_REGISTRY_SAFETY_PUBLICATION"||
    x.asOf!=="2026-11-09"||x.observedAtUtc!=="2026-11-09T17:21:54+00:00"||
    x.sourceRunId!==42663832735||x.sourceArtifactId!==13695013486||
    x.originalResearchReceiptSha256!==SHA||
    x.sourceArtifactExpiresAt!=="2027-02-07T17:21:36Z"||
    x.counts.trials!==29||x.counts.applicationCycles!==23||
    x.counts.registryFetched!==29||x.counts.registryResultSections!==12||
    x.counts.registryAdverseEventsModules!==12||
    x.counts.withoutCurrentRegistryResults!==17||
    x.counts.seriousEventTermRows!==244||x.counts.otherEventTermRows!==202||
    x.counts.eventGroupRows!==28||
    x.counts.independentlySignedClinicalGrades!==0||
    x.counts.validatedApplicationFdaForecasts!==0||
    x.counts.realHistoricalBacktests!==0||
    x.sourceResearchOnly!==true||
    x.sourcePublicationChronologyIndependentlyVerified!==false||
    x.clinicalSafetyAdjudicated!==false||
    x.numericalApprovalProbability!==null||x.calibratedFdaAccuracy!==null||
    x.officialFutureFdaForecast!=="ABSTAIN"||
    x.officialFutureReviewDelayForecast!=="ABSTAIN"||
    !FOCUS_R42_PRIMARY_RESULTS||
    FOCUS_PRELIMINARY_R39.trials.length!==29||
    FOCUS_PRELIMINARY_R39.applications.length!==23||
    !Array.isArray(x.posted)||x.posted.length!==12)return null;
 const originalPosted=new Set(FOCUS_R42_PRIMARY_RESULTS.trialRows.filter(r=>r.primary).map(r=>r.nct));
 const trialMap=new Map(FOCUS_PRELIMINARY_R39.trials.map(r=>[r.nct,r]));
 if(x.posted.some(r=>!NCT.test(r.nct)||!originalPosted.has(r.nct)||
     !trialMap.has(r.nct)||!Array.isArray(r.groups)||r.groups.length<1||
     r.groups.length>20||r.groups.some(g=>!Array.isArray(g)||g.length!==7||
       typeof g[0]!=="string"||g[0].length<1||
       g.slice(1).some(v=>typeof v!=="number"||!Number.isSafeInteger(v)||v<0)||
       Number(g[1])>Number(g[2])||Number(g[3])>Number(g[4])||Number(g[5])>Number(g[6]))||
     !Number.isInteger(r.seriousEventTerms)||r.seriousEventTerms<0||
     !Number.isInteger(r.otherEventTerms)||r.otherEventTerms<0))return null;
 if(new Set(x.posted.map(r=>r.nct)).size!==12||
    x.posted.some(r=>r.groups.length===0)||
    x.posted.reduce((n,r)=>n+r.seriousEventTerms,0)!==244||
    x.posted.reduce((n,r)=>n+r.otherEventTerms,0)!==202||
    x.posted.reduce((n,r)=>n+r.groups.length,0)!==28)return null;
 return {...x,items:x.posted.map(r=>({...r,ticker:trialMap.get(r.nct)!.ticker,
      applicationCycleIds:trialMap.get(r.nct)!.applicationCycleIds})),
      absent:FOCUS_PRELIMINARY_R39.trials.filter(r=>!originalPosted.has(r.nct)).map(r=>({nct:r.nct,ticker:r.ticker}))};
}
export const FOCUS_R44_SAFETY=validateFocusR44Safety();
