/** FDA three-way scoring methods for a *research* cohort. Never FDA
 * probabilities, investor recommendations or independently certified model accuracy.
 * A complete-looking JSON record is not an authenticated freeze or FDA action.
 */
import {buildThreeWayFDAFreezePreflightPlan}
 from "./raas-fda-three-way-freeze-preflight";
import {currentRaasFdaForecastFreezeReceiptAudit}
 from "./raas-fda-forecast-freeze-receipt-audit";
import {currentRaasFdaOriginalGoalOutcomeAudit}
 from "./raas-fda-original-goal-outcome-audit";
import saved from "../data/raas-fda-three-way-scorecard-pairs.json";

const LABELS=["PASS","CRL","EXTENSION"] as const;
export type ThreeWayFdaLabel=typeof LABELS[number];
export type ThreeWayFdaProbabilities=Record<ThreeWayFdaLabel,number>;
export type ThreeWayFdaResearchPair={
 caseKey:string;issuer:string;sourceFingerprint:string;
 exactFdaApplicationNumber:string;exactReviewCycleId:string;
 originalFirstGoalDate:string;forecastFrozenAt:string;
 probabilities:ThreeWayFdaProbabilities;
 actualOriginalGoalDisposition:ThreeWayFdaLabel;
 actionEffectiveDate:string;outcomeEvidencePublishedDate:string;
};
export type ThreeWayFdaResearchInput={
 sourceAsOf:string;
 cohortCaseKeys:string[];
 unpairedCaseKeys:string[];
 trainingIssuerKeys:string[];
 declaredCohortComplete:boolean;
 holdoutProtocolPrecommitted:boolean;
 pairs:ThreeWayFdaResearchPair[];
};
type ScoreReadiness="NO_VERIFIED_PAIRS"|"INSUFFICIENT_RESEARCH_VALIDATION"|
 "RESEARCH_DIAGNOSTIC_ONLY_INDEPENDENT_AUDIT_REQUIRED";
export type ThreeWayFdaResearchScorecard={
 scope:"RAAS_FDA_THREE_WAY_RESEARCH_SCORECARD_NOT_CERTIFIED";
 status:ScoreReadiness;researchRosterCases:number;unpairedCases:number;
 researchPairedCases:number;trainingIssuers:number;holdoutIssuers:number;
 forecastCoveragePct:number;
 perOutcomeCounts:Record<ThreeWayFdaLabel,number>;
 researchStatistics:null|{
  topClassAccuracyPct:number;alwaysPassBaselineAccuracyPct:number;
  balancedAccuracyPct:number;
  multiclassBrier:number;multiclassLogLoss:number;
  expectedCalibrationErrorPct:number;
  confusionMatrix:Record<ThreeWayFdaLabel,Record<ThreeWayFdaLabel,number>>;
  perClassRecallPct:Record<ThreeWayFdaLabel,number>;
  accuracyWilson95Pct:[number,number];
 };
 readinessGates:{id:string;passed:boolean;achieved:number;required:number;description:string}[];
 independentValidatedAccuracyPct:null;
 independentValidatedCalibration:null;
 approvedPredictionModel:false;
 automatedTradingSignals:0;
 warning:string;
};
const uniq=(xs:string[])=>new Set(xs).size===xs.length;
const text=(x:unknown,min=1,max=200):x is string=>
 typeof x==="string"&&x.trim().length>=min&&x.length<=max&&
 !/[\u0000-\u001f\u007f]/.test(x);
const day=(x:unknown):x is string=>typeof x==="string"&&
 /^\d{4}-\d{2}-\d{2}$/.test(x)&&
 Number.isFinite(Date.parse(x+"T00:00:00Z"))&&
 new Date(x+"T00:00:00Z").toISOString().slice(0,10)===x;
const instant=(v:unknown):v is string=>typeof v==="string"&&
 /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?(?:Z|[+-]\d{2}:\d{2})$/.test(v)&&
 Number.isFinite(Date.parse(v));
const finiteProb=(v:unknown):v is number=>typeof v==="number"&&
 Number.isFinite(v)&&v>=0&&v<=1;
const round=(n:number,p=4)=>Number(n.toFixed(p));
const emptyCount=()=>({PASS:0,CRL:0,EXTENSION:0});
const emptyMatrix=()=>({
 PASS:emptyCount(),CRL:emptyCount(),EXTENSION:emptyCount()
});
/** Only research diagnostics; never assert independent provenance from
 * self-reported cohort flags, witness strings or SHA hashes.
 */
export function scoreThreeWayFdaResearchCohort(
 input:ThreeWayFdaResearchInput
):ThreeWayFdaResearchScorecard{
 if(!input||!day(input.sourceAsOf)||
  !Array.isArray(input.cohortCaseKeys)||!Array.isArray(input.unpairedCaseKeys)||
  !Array.isArray(input.trainingIssuerKeys)||!Array.isArray(input.pairs)||
  typeof input.declaredCohortComplete!=="boolean"||
  typeof input.holdoutProtocolPrecommitted!=="boolean"||
  input.cohortCaseKeys.length>10000||input.pairs.length>10000||
  input.cohortCaseKeys.some(k=>!text(k,3,160))||
  input.unpairedCaseKeys.some(k=>!text(k,3,160))||
  input.trainingIssuerKeys.some(k=>!text(k,2,100))||
  !uniq(input.cohortCaseKeys)||!uniq(input.unpairedCaseKeys)||
  !uniq(input.trainingIssuerKeys))
  throw Error("RAAS_FDA_SCORECARD_COHORT_INPUT_INVALID");
 const allKeys=new Set(input.cohortCaseKeys);
 const observed=new Set<string>();
 const issuers=new Set<string>();
 const outcomeCounts=emptyCount();
 for(const pair of input.pairs){
  if(!pair||!text(pair.caseKey,3,160)||!allKeys.has(pair.caseKey)||
   observed.has(pair.caseKey)||!text(pair.issuer,2,100)||
   !text(pair.sourceFingerprint,64,64)||
   !/^[a-f0-9]{64}$/.test(pair.sourceFingerprint)||
   !text(pair.exactFdaApplicationNumber,5,120)||
   !text(pair.exactReviewCycleId,5,120)||
   !day(pair.originalFirstGoalDate)||!instant(pair.forecastFrozenAt)||
   !day(pair.actionEffectiveDate)||!day(pair.outcomeEvidencePublishedDate)||
   !LABELS.includes(pair.actualOriginalGoalDisposition)||
   !pair.probabilities||
   Object.keys(pair.probabilities).sort().join("|")!=="CRL|EXTENSION|PASS"||
   !LABELS.every(k=>finiteProb(pair.probabilities[k]))||
   Math.abs(LABELS.reduce((s,k)=>s+pair.probabilities[k],0)-1)>1e-9)
   throw Error("RAAS_FDA_SCORECARD_PAIR_INVALID");
  const forecast=Date.parse(pair.forecastFrozenAt);
  const originalGoal=Date.parse(pair.originalFirstGoalDate+"T00:00:00Z");
  const action=Date.parse(pair.actionEffectiveDate+"T00:00:00Z");
  if(forecast>=originalGoal||forecast>=action||
    pair.actionEffectiveDate>pair.originalFirstGoalDate||
    pair.actionEffectiveDate>pair.outcomeEvidencePublishedDate||
    pair.outcomeEvidencePublishedDate>input.sourceAsOf||
    forecast>Date.parse(input.sourceAsOf+"T23:59:59.999Z"))
   throw Error("RAAS_FDA_SCORECARD_TEMPORAL_LOOKAHEAD_OR_GOAL_MISMATCH");
  observed.add(pair.caseKey);
  issuers.add(pair.issuer.toUpperCase());
  outcomeCounts[pair.actualOriginalGoalDisposition]++;
 }
 const combined=new Set([...observed,...input.unpairedCaseKeys]);
 if(combined.size!==allKeys.size||
  [...combined].some(key=>!allKeys.has(key))||
  [...input.unpairedCaseKeys].some(key=>observed.has(key))||
  input.pairs.length+input.unpairedCaseKeys.length!==allKeys.size)
  throw Error("RAAS_FDA_SCORECARD_COHORT_DENOMINATOR_MISMATCH");
 const train=new Set(input.trainingIssuerKeys.map(s=>s.toUpperCase()));
 const disjoint=[...issuers].every(issuer=>!train.has(issuer));
 const minimum=30;
 const enoughClasses=LABELS.every(k=>outcomeCounts[k]>=10);
 const gates=[
  {id:"predeclared-cohort",passed:input.declaredCohortComplete,
   achieved:input.declaredCohortComplete?1:0,required:1,
   description:"Prespecified complete eligible cohort, including abstentions and unresolved outcomes; outside independent audit required"},
  {id:"forecast-outcome-pairs",passed:input.pairs.length>=minimum,
   achieved:input.pairs.length,required:minimum,
   description:"At least 30 actual original-goal forecast/outcome pairs"},
  {id:"issuer-disjoint-training",passed:train.size>=minimum&&disjoint,
   achieved:disjoint?train.size:0,required:minimum,
   description:"30 or more training issuers with no overlap in the test cohort"},
  {id:"issuer-diverse-holdout",passed:issuers.size>=minimum,
   achieved:issuers.size,required:minimum,
   description:"30 or more independently distinct test issuers"},
  {id:"all-three-classes",passed:enoughClasses,
   achieved:Math.min(...LABELS.map(k=>outcomeCounts[k])),required:10,
   description:"At least 10 observed original-goal outcomes in each of PASS, CRL and EXTENSION"},
  {id:"prespecified-test-protocol",passed:input.holdoutProtocolPrecommitted,
   achieved:input.holdoutProtocolPrecommitted?1:0,required:1,
   description:"Reviewable precommitted, chronology-safe walk-forward holdout"},
 ];
 const ready=gates.every(g=>g.passed);
 let statistics:ThreeWayFdaResearchScorecard["researchStatistics"]=null;
 if(ready){
  const n=input.pairs.length;
  const cm=emptyMatrix();
  const confidences:Array<{confidence:number;correct:number}>=[];
  let correct=0,brier=0,logLoss=0;
  for(const p of input.pairs){
   // Deterministic order for ties, never use actual outcome as the tie breaker.
   const predicted=LABELS.reduce((a,b)=>
    p.probabilities[b]>p.probabilities[a]?b:a,LABELS[0]);
   const match=predicted===p.actualOriginalGoalDisposition?1:0;
   correct+=match;cm[p.actualOriginalGoalDisposition][predicted]++;
   const confidence=p.probabilities[predicted];
   confidences.push({confidence,correct:match});
   brier+=LABELS.reduce((s,k)=>s+
    (p.probabilities[k]-(k===p.actualOriginalGoalDisposition?1:0))**2,0);
   logLoss-=Math.log(Math.max(p.probabilities[p.actualOriginalGoalDisposition],1e-15));
  }
  let ece=0;
  for(let bucket=0;bucket<10;bucket++){
   const points=confidences.filter(p=>Math.min(9,Math.floor(10*p.confidence))===bucket);
   if(!points.length)continue;
   const acc=points.reduce((s,p)=>s+p.correct,0)/points.length;
   const conf=points.reduce((s,p)=>s+p.confidence,0)/points.length;
   ece+=points.length/n*Math.abs(acc-conf);
  }
  const perClass=emptyCount();
  for(const k of LABELS)perClass[k]=round(100*cm[k][k]/outcomeCounts[k],2);
  const phat=correct/n,z=1.95996398454,denom=1+z*z/n;
  const center=(phat+z*z/(2*n))/denom;
  const half=z*Math.sqrt((phat*(1-phat)+z*z/(4*n))/n)/denom;
  statistics={
   topClassAccuracyPct:round(100*phat,2),
   alwaysPassBaselineAccuracyPct:round(100*outcomeCounts.PASS/n,2),
   balancedAccuracyPct:round(LABELS.reduce((s,k)=>s+perClass[k],0)/3,2),
   multiclassBrier:round(brier/n),
   multiclassLogLoss:round(logLoss/n),
   expectedCalibrationErrorPct:round(100*ece,2),
   confusionMatrix:cm,perClassRecallPct:perClass,
   accuracyWilson95Pct:[round(100*(center-half),2),round(100*(center+half),2)]
  };
 }
 return {
  scope:"RAAS_FDA_THREE_WAY_RESEARCH_SCORECARD_NOT_CERTIFIED",
  status:ready?"RESEARCH_DIAGNOSTIC_ONLY_INDEPENDENT_AUDIT_REQUIRED":
   input.pairs.length===0?"NO_VERIFIED_PAIRS":
   "INSUFFICIENT_RESEARCH_VALIDATION",
  researchRosterCases:allKeys.size,unpairedCases:input.unpairedCaseKeys.length,
  researchPairedCases:input.pairs.length,trainingIssuers:train.size,
  holdoutIssuers:issuers.size,
  forecastCoveragePct:allKeys.size?round(100*input.pairs.length/allKeys.size,2):0,
  perOutcomeCounts:outcomeCounts,researchStatistics:statistics,
  readinessGates:gates,independentValidatedAccuracyPct:null,
  independentValidatedCalibration:null,approvedPredictionModel:false,
  automatedTradingSignals:0,
  warning:"No score, model or trading approval. Any research statistics are NOT independently validated: external freeze authentication, cycle/outcome adjudication, eligibility and walk-forward cohort audit must happen outside self-reported JSON. Empty or incomplete data gives null accuracy, never 0% accuracy."
 };
}
export function currentRaasFdaThreeWayResearchScorecard():ThreeWayFdaResearchScorecard{
 if(saved.schemaVersion!==1||
  saved.scope!=="RAAS_FDA_THREE_WAY_RESEARCH_SCORECARD_PAIRS_UNVERIFIED"||
  !Array.isArray(saved.records)||saved.records.length!==0)
  throw Error("RAAS_FDA_SCORECARD_PRODUCTION_PAIRS_REQUIRE_INDEPENDENT_AUDIT");
 const plan=buildThreeWayFDAFreezePreflightPlan();
 const receipt=currentRaasFdaForecastFreezeReceiptAudit();
 const outcome=currentRaasFdaOriginalGoalOutcomeAudit();
 if(receipt.independentlyAuthenticatedForecasts!==0||
  outcome.independentlyAdjudicatedOriginalGoalLabels!==0||
  outcome.qualifiedForecastOutcomePairs!==0)
  throw Error("RAAS_FDA_SCORECARD_AUDIT_UNEXPECTED_VERIFIED_SOURCE");
 const cohort=plan.records.filter(x=>x.eligibility!=="PHASE2_EXCLUDED");
 return scoreThreeWayFdaResearchCohort({
  sourceAsOf:plan.snapshotAsOf,
  cohortCaseKeys:cohort.map(x=>x.caseKey),
  unpairedCaseKeys:cohort.map(x=>x.caseKey),
  pairs:[],trainingIssuerKeys:[],
  declaredCohortComplete:false,holdoutProtocolPrecommitted:false
 });
}
