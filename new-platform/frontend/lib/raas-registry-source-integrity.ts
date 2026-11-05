/** ClinicalTrials.gov source-integrity checks on the saved RAAS registry index.
 * Preserves raw reported contrasts/arm IDs. A flag indicates follow-up,
 * NOT a source error, efficacy conclusion, metric grade or FDA prediction.
 * Never infer pre/post readout stage from a registry posting.
 */
import type {RegistryTrialEvidence,RegistryEvidenceIndex} from "./raas-registry-evidence";

export type RegistrySourceIssueCode=
 "NONPOSITIVE_REPORTED_RATIO"|"CI_LOWER_ABOVE_UPPER"|
 "POINT_ESTIMATE_OUTSIDE_CI"|"COMPARISON_ARM_NOT_IDENTIFIED"|
 "SAE_AFFECTED_EXCEEDS_AT_RISK"|"UNREADABLE_REPORTED_CI";
export type RegistrySourceIssue={
 code:RegistrySourceIssueCode;path:string;reportedValue:string;
 explanation:string;sourceUrl:string;
};
export type RegistrySourceAudit={
 nctId:string;ticker:string;sourceHash:string;sourceAsOf:string;
 primaryComparisons:number;comparisonsWithNumericCI:number;
 armMeasurements:number;safetyGroupsWithDenominators:number;
 issues:RegistrySourceIssue[];
 /** Never a clinical score, statistical conclusion or independent review. */
 approvedRaasScore:null;calibratedFdaProbability:null;
};
const number=(s:unknown):number|null=>{
 if(typeof s!=="string"||!/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?$/i.test(s.trim()))return null;
 const n=Number(s);return Number.isFinite(n)?n:null;
};
const ratio=(x:string)=>/\b(?:odds ratio|hazard ratio|risk ratio|relative risk|rate ratio|incidence rate ratio|OR|HR|RR)\b/i.test(x);
const defined=(x:unknown)=>typeof x==="string"&&x.trim().length>0;

/** Validate only structural/interpretability facts directly in this exact source.
 * EG serious-event IDs and OG outcome IDs are DIFFERENT registry namespaces:
 * matching them by number would manufacture causal arm-level safety comparisons.
 */
export function auditRegistrySourceTrial(
 record:RegistryTrialEvidence,sourceAsOf:string
):RegistrySourceAudit{
 if(!/^NCT\d{8}$/.test(record.nctId)||record.sourceUrl!==
  "https://clinicaltrials.gov/study/"+record.nctId||
  !/^[0-9a-f]{64}$/.test(record.sourceHash))
  throw Error("RAAS_REGISTRY_AUDIT_SOURCE_IDENTITY_INVALID");
 const issues:RegistrySourceIssue[]=[];
 const report=(code:RegistrySourceIssueCode,path:string,reportedValue:string,explanation:string)=>
  issues.push({code,path,reportedValue,explanation,sourceUrl:record.sourceUrl});
 let primaryComparisons=0,comparisonsWithNumericCI=0,armMeasurements=0;
 for(const [oi,outcome] of record.primaryResults.entries()){
  armMeasurements+=(outcome.measurements||[]).length;
  const known=new Set((outcome.groups||[]).map(x=>x.id));
  for(const [ai,c] of (outcome.comparisons||[]).entries()){
   const prefix="primaryResults["+oi+"].comparisons["+ai+"]";
   if((c.groupIds||[]).length>=2)primaryComparisons++;
   if(known.size&&(c.groupIds||[]).some(g=>!known.has(g)))
    report("COMPARISON_ARM_NOT_IDENTIFIED",prefix+".groupIds",
     (c.groupIds||[]).join(", "),
     "An exact reported comparison arm ID is not present among this outcome's recorded OG group IDs. Verify the full original registry grouping.");
   const val=number(c.paramValue),lower=number(c.ciLowerLimit),upper=number(c.ciUpperLimit);
   if(defined(c.ciLowerLimit)||defined(c.ciUpperLimit)){
    if(lower===null||upper===null)
     report("UNREADABLE_REPORTED_CI",prefix+".ci",
      String(c.ciLowerLimit)+" .. "+String(c.ciUpperLimit),
      "One or both saved confidence limits cannot be parsed as numeric; recheck the original source instead of assuming an interval.");
    else if(lower>upper)
     report("CI_LOWER_ABOVE_UPPER",prefix+".ci",
      String(c.ciLowerLimit)+" .. "+String(c.ciUpperLimit),
      "The reported lower limit exceeds the upper limit; check whether the source uses another scale or an extraction field is reversed.");
    else{
     comparisonsWithNumericCI++;
     if(val!==null&&(val<lower||val>upper))
      report("POINT_ESTIMATE_OUTSIDE_CI",prefix+".paramValue",
       String(c.paramValue)+" vs ["+String(c.ciLowerLimit)+", "+String(c.ciUpperLimit)+"]",
       "The reported point value is outside its listed interval; verify whether a transformed scale or mismatched statistic was exported.");
    }
   }
   if(ratio(c.paramType)&&((val!==null&&val<=0)||
     (lower!==null&&lower<=0)||(upper!==null&&upper<=0)))
    report("NONPOSITIVE_REPORTED_RATIO",prefix+".paramType",
     String(c.paramType)+": "+String(c.paramValue)+
      " (CI "+String(c.ciLowerLimit)+" to "+String(c.ciUpperLimit)+")",
     "A value labeled as an odds/risk/hazard ratio or its confidence limit is nonpositive. It may be a transformed statistic or labeling mismatch; check the exact original registry analysis. Do not interpret this as a ratio or award efficacy points.");
  }
 }
 let safetyGroupsWithDenominators=0;
 for(const [ei,event] of (record.seriousEventDetails||[]).entries()){
  for(const [gi,g] of event.groups.entries()){
   if(typeof g.numAffected==="number"&&typeof g.numAtRisk==="number"&&
    g.numAtRisk>0){
    safetyGroupsWithDenominators++;
    if(g.numAffected>g.numAtRisk)
     report("SAE_AFFECTED_EXCEEDS_AT_RISK",
      "seriousEventDetails["+ei+"].groups["+gi+"]",
      String(g.numAffected)+"/"+String(g.numAtRisk),
      "Affected persons exceed the saved population at risk. Recheck the original source and never treat the raw value as an adverse-event rate.");
   }
  }
 }
 return {nctId:record.nctId,ticker:record.ticker,sourceHash:record.sourceHash,
  sourceAsOf,primaryComparisons,comparisonsWithNumericCI,
  armMeasurements,safetyGroupsWithDenominators,issues,
  approvedRaasScore:null,calibratedFdaProbability:null};
}
export function auditRegistrySourceIndex(
 index:RegistryEvidenceIndex
):{totalTrials:number;trialsWithComparisons:number;
 trialsWithNumericCI:number;trialsWithSaeDenominators:number;
 flaggedTrials:number;flaggedFindings:number;
 issuesByCode:Record<RegistrySourceIssueCode,number>;
 records:RegistrySourceAudit[]}{
 const records=index.records.map(r=>auditRegistrySourceTrial(r,index.sourceAsOf));
 const codes:RegistrySourceIssueCode[]=[
  "NONPOSITIVE_REPORTED_RATIO","CI_LOWER_ABOVE_UPPER",
  "POINT_ESTIMATE_OUTSIDE_CI","COMPARISON_ARM_NOT_IDENTIFIED",
  "SAE_AFFECTED_EXCEEDS_AT_RISK","UNREADABLE_REPORTED_CI"];
 const issuesByCode=Object.fromEntries(codes.map(code=>[
  code,records.reduce((sum,r)=>sum+r.issues.filter(i=>i.code===code).length,0)
 ])) as Record<RegistrySourceIssueCode,number>;
 return {totalTrials:records.length,
  trialsWithComparisons:records.filter(r=>r.primaryComparisons>0).length,
  trialsWithNumericCI:records.filter(r=>r.comparisonsWithNumericCI>0).length,
  trialsWithSaeDenominators:records.filter(r=>r.safetyGroupsWithDenominators>0).length,
  flaggedTrials:records.filter(r=>r.issues.length>0).length,
  flaggedFindings:records.reduce((n,r)=>n+r.issues.length,0),
  issuesByCode,records};
}
export function registryEvidenceReviewerPacket(
 record:RegistryTrialEvidence,sourceAsOf:string
){
 const audit=auditRegistrySourceTrial(record,sourceAsOf);
 return {
  schemaVersion:1,
  scope:"RAAS_EXACT_NCT_REGISTRY_REVIEW_SOURCE_PACKET_NO_GRADES",
  sourceAsOf,sourceHashOriginalRegistryReceipt:record.sourceHash,
  disclaimer:"Research-only source transcription. Does not verify clinical truth, readout stage, drug-specific effect, comparator ranking, current Pipeline, PDUFA eligibility, an approved RAAS score or FDA decision probability. OG outcome IDs and EG safety IDs must not be silently equated. Reopen the original dated ClinicalTrials.gov source and independently reconcile every reported contrast.",
  exactTrial:{nctId:record.nctId,ticker:record.ticker,
   sourceUrl:record.sourceUrl,registryStatus:record.registryStatus,
   phases:record.registeredPhases,
   conditions:record.registeredConditions,
   interventions:record.registeredInterventions,
   retrievedAt:record.retrievedAt,registryLastUpdated:record.registryLastUpdated,
   resultsFirstPosted:record.resultsFirstPosted},
  registeredPrimaryOutcomes:record.primaryDefinitions,
  sourceReportedResults:record.postedResults?record.primaryResults:[],
  sourceReportedSeriousEvents:record.postedResults?(record.seriousEventDetails||[]):[],
  audit,
  potentialReviewLinks:[
   {stage:"pre",metricId:"pre-1-2",if:"Registered protocol; does not prove trial power or Phase 3 efficacy."},
   {stage:"post",metricId:"post-1-1",if:"Only after exact independent readout verification and clinical relevance benchmark."},
   {stage:"post",metricId:"post-1-3",if:"Only after primary statistical methods and confidence interval corroboration."},
   {stage:"post",metricId:"post-1-5",if:"Only after seriousness, exposure, causality and separate adverse-event arm mapping."}
  ],
  independentReviewerSignoff:null,approvedRaasScore:null,calibratedFdaProbability:null
 };
}
