/** MAIN R61: render-only original R60 scientific source challenge.
 * All data are public trial-source research and R60 receipt-locked. No scoring,
 * FDA probability, trained model, clinical signoff, write API or live fallback.
 */
import snapshot from "../data/focus-r60-original-source-trial-detail.json";
import {FOCUS_PRELIMINARY_R39} from "./focus-preliminary-application-research";

const R60_ORIGINAL_RUN=42709199117;
const R60_ORIGINAL_ARTIFACT=13715890359;
const R60_OBSERVED_UTC="2026-11-09T22:09:29+00:00";
const R60_SOURCE_SHA={
  r46:"7e1681399ed242d0080d8517bbe62cfb931e88e1340295fdf9839affbc0d3f92",
  r55:"0e399209a26778f15e9b6fa1d7e626232d92f1a17ec042dbde6dc110a977729c",
  r59:"089370a0220173935fbec5e0b79d1c07c43685e82adb1650182db30fceb7c9f1"
} as const;
const HASH=/^[0-9a-f]{64}$/;
const NCT=/^NCT[0-9]{8}$/;
const SOURCE_ISSUES=new Set([
  "NO_CURRENT_POSTED_PRIMARY_TABLE_CHECK_OTHER_ORIGINALS",
  "NO_CURRENT_POSTED_SAFETY_ARM_TABLE_CHECK_OTHER_ORIGINALS",
  "POSTED_PRIMARY_WITHOUT_STATISTICAL_COMPARISON",
  "CURRENT_REGISTRATION_AND_POSTED_PRIMARY_TITLE_OR_TIME_DIFFER",
  "STATISTICAL_COMPARISON_WITHOUT_REPORTED_P_VALUE",
  "INCOMPLETE_POSTED_SAFETY_ARM_DENOMINATOR"
]);
type SummaryTuple=[string,Array<[string|null,string|null]>];
type SafetyTuple=[string,[number,number]];
type SourceTrial={
  n:string;h:string;p:number;q:number;a:number;
  e?:string[];m?:SummaryTuple[];s?:SafetyTuple[];
};
type Snapshot={
  rev:number;run:number;artifact:number;utc:string;
  sourceHashes:{r46:string;r55:string;r59:string};
  trials:SourceTrial[];
};
function integer(v:unknown){return typeof v==="number"&&Number.isSafeInteger(v)&&v>=0;}
function validPvalue(v:unknown){
  return v===null||(typeof v==="string"&&v.length<60&&
    /^(?:<\s*)?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)$/.test(v));
}
export function validateR60OriginalTrialResearch(input:unknown=snapshot){
  if(!input||typeof input!=="object"||Array.isArray(input))return null;
  const data=input as Snapshot;
  if(data.rev!==60||data.run!==R60_ORIGINAL_RUN||
    data.artifact!==R60_ORIGINAL_ARTIFACT||data.utc!==R60_OBSERVED_UTC||
    !data.sourceHashes||Object.keys(R60_SOURCE_SHA).some(key=>
      data.sourceHashes[key as keyof typeof R60_SOURCE_SHA]!==R60_SOURCE_SHA[key as keyof typeof R60_SOURCE_SHA])||
    !Array.isArray(data.trials)||data.trials.length!==29||
    FOCUS_PRELIMINARY_R39.trials.length!==29||
    FOCUS_PRELIMINARY_R39.applications.length!==23||
    FOCUS_PRELIMINARY_R39.summary.independentlyValidatedFDAForecasts!==0)return null;
  const original=FOCUS_PRELIMINARY_R39.trials;
  const byNct=new Map(original.map(x=>[x.nct,x]));
  const unique=new Set<string>();
  let tables=0,comparisons=0,withPrimary=0,withSafety=0;
  for(const item of data.trials){
    if(!item||typeof item!=="object"||!NCT.test(item.n)||unique.has(item.n)||
       !byNct.has(item.n)||typeof item.h!=="string"||!HASH.test(item.h)||
       !integer(item.p)||!integer(item.q)||!integer(item.a)||
       item.p>20||item.q>100||item.a>30||
       (item.m!==undefined&&!Array.isArray(item.m))||
       (item.s!==undefined&&!Array.isArray(item.s))||
       (item.e!==undefined&&!Array.isArray(item.e)))return null;
    unique.add(item.n);
    const methods=item.m??[];
    const safety=item.s??[];
    const exceptions=item.e??[];
    if(methods.length!==item.p||safety.length!==item.a||
       methods.reduce((sum,x)=>sum+(Array.isArray(x[1])?x[1].length:999),0)!==item.q||
       exceptions.length!==new Set(exceptions).size||
       exceptions.some(e=>!SOURCE_ISSUES.has(e)))return null;
    for(const m of methods){
      if(!Array.isArray(m)||m.length!==2||typeof m[0]!=="string"||
         m[0].length<3||m[0].length>600||!Array.isArray(m[1])||
         m[1].some(q=>!Array.isArray(q)||q.length!==2||
           !validPvalue(q[0])||(q[1]!==null&&typeof q[1]!=="string")))return null;
    }
    for(const arm of safety){
      if(!Array.isArray(arm)||arm.length!==2||
        typeof arm[0]!=="string"||arm[0].length>200||
        !Array.isArray(arm[1])||arm[1].length!==2||
        !integer(arm[1][0])||!integer(arm[1][1])||
        arm[1][0]>arm[1][1])return null;
    }
    if((item.p===0)!==exceptions.includes("NO_CURRENT_POSTED_PRIMARY_TABLE_CHECK_OTHER_ORIGINALS")||
       (item.a===0)!==exceptions.includes("NO_CURRENT_POSTED_SAFETY_ARM_TABLE_CHECK_OTHER_ORIGINALS")||
       methods.some(x=>x[1].length===0)!==
         exceptions.includes("POSTED_PRIMARY_WITHOUT_STATISTICAL_COMPARISON"))return null;
    tables+=item.p; comparisons+=item.q;
    if(item.p)withPrimary++;
    if(item.a)withSafety++;
  }
  if(unique.size!==29||[...byNct.keys()].some(n=>!unique.has(n))||
    tables!==16||comparisons!==20||withPrimary!==12||withSafety!==12)return null;
  const rows=data.trials.map(x=>{
    const base=byNct.get(x.n)!;
    return {
      nct:x.n,ticker:base.ticker,cycles:[...base.applicationCycleIds],
      originalRegistryUrl:"https://clinicaltrials.gov/study/"+x.n,
      originalRegistrySha256:x.h,
      primaryTables:x.p,reportedAnalyses:x.q,safetyArms:x.a,
      endpoints:x.m??[],seriousAeArmAffectedAtRisk:x.s??[],
      reviewExceptions:x.e??[],
      independentlyValidatedScientificReview:false,
      officialApprovalOrCrlForecast:"ABSTAIN" as const,
      officialReviewTimingForecast:"ABSTAIN" as const,
      fdaProbability:null
    };
  });
  return {
    schema:"MAIN_R61_VIEW_ONLY_OF_R60_ORIGINAL_REGISTRY_SOURCE",
    run:data.run,artifact:data.artifact,observedAtUtc:data.utc,
    sourceArchiveUrl:"https://github.com/pdufa/pdufa-command-center/actions/runs/"+data.run+"/artifacts/"+data.artifact,
    counts:{uniqueNcts:29,applicationGroups:23,postedPrimaryTables:16,
      reportedStatisticalComparisons:20,
      trialsWithCurrentPrimary:12,trialsWithCurrentSafetyArms:12,
      sourceReportedSeriousAeTermRows:244,sourceReportedOtherAeTermRows:202,
      independentlyValidatedFdaForecasts:0},
    originalInputSha256:{...R60_SOURCE_SHA},
    trials:rows,
    originalSourceRetrievalDoesNotValidateOriginalSAPOrClinicallyAdjudicateData:true,
    allOfficialFDAForecasts:"ABSTAIN" as const,
    predictionAccuracy:null
  };
}
export const FOCUS_R60_ORIGINAL_TRIAL_REVIEW=validateR60OriginalTrialResearch();
