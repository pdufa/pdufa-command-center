/** Verified source inventory used only as research leads, never numerical scores.
 * Registry results are independent of issuer-evidenced TOP/BOTTOM assignment.
 * Protocol fields cannot be promoted to clinical outcomes, and p-values do not
 * become effect sizes or 0–100 scoring grades.
 */
import type {RaasStage} from "./raas-metric-specs";
export type RegistryPrimaryResult={
 title:string;timeFrame:string;unit:string;analysisCount:number;pValues:string[];
 groups?:{id:string;title:string}[];
 measurements?:{groupId?:string;value?:string;spread?:string;lowerLimit?:string;upperLimit?:string}[];
 comparisons?:{groupIds:string[];pValue:string;method:string;paramType:string;
   paramValue:string;ciPctValue:string;ciLowerLimit:string;ciUpperLimit:string}[];
};
export type RegistryTrialEvidence={
 nctId:string;ticker:string;sourceUrl:string;sourceHash:string;
 retrievedAt:string;registryLastUpdated:string|null;resultsFirstPosted:string|null;
 registryStatus:string;registeredPhases:string[];
 /** Optional to preserve compatibility with older primary registry source receipts. */
 registeredDesign?:{
  allocation:string;masking:string;interventionModel:string;studyType:string;
  enrollment:number|null;enrollmentType:string
 };
 registeredConditions:string[];registeredInterventions:string[];
 primaryDefinitions:{measure:string;timeFrame:string}[];
 postedResults:boolean;postedPrimaryOutcomeCount:number;postedOtherOutcomeCount:number;
 primaryResults:RegistryPrimaryResult[];seriousAdverseEventTermCount:number;
 seriousEventDetails?:{term:string;groups:{groupId:string;numAffected?:number|null;
  numAtRisk?:number|null;numEvents?:number|null}[]}[];
 evidenceState:"PROTOCOL_ONLY"|"POSTED_RESULTS_UNGRADED";
};
export type RegistryEvidenceIndex={
 schemaVersion:1;scope:"RAAS_REGISTRY_TRIAL_EVIDENCE_INDEX";source:string;
 sourceAsOf:string;summary:{
  researchNcts:number;registryRecords:number;postedRegistryResults:number;
  protocolOnly:number;approvedOverallRaasScores:0;
  trialsWithPrimaryComparisons?:number;trialsWithPrimaryGroupMeasurements?:number;
  trialsWithPrimaryConfidenceIntervals?:number;trialsWithSafetyRiskDenominators?:number
 };records:RegistryTrialEvidence[];
};
export type RegistryMetricLead={
 id:string;kind:string;sourceDate:string;sourceUrl:string;
 description:string;measurement:{label:string;value:number;unit:string}|null;metricIds:string[];
};
const exact=(a:string,b:string)=>a.trim().toLowerCase()===b.trim().toLowerCase();
const nct=/^NCT\d{8}$/;
const hash=/^[0-9a-f]{64}$/;
const sameTrial=(e:RegistryTrialEvidence,t:{nctId:string;ticker:string;drug?:string})=>{
 if(e.nctId!==t.nctId||!exact(e.ticker,t.ticker))return false;
 const drug=t.drug?.trim().toLowerCase();
 if(!drug)return true;
 // Early registry receipts omitted the intervention list. Exact NCT + ticker
 // still identify this TRIAL as a source lead, but NEVER establish a drug-level
 // causal result or authorize a numerical grade. New receipts preserve names.
 if(e.registeredInterventions.length===0)return true;
 // Do not attach a source to a different drug in a multi-asset issuer.
 const names=drug.split(/[|;]/).map(x=>x.replace(/\([^)]*\)/g,"").trim()).filter(Boolean);
 if(!names.length)return false;
 return e.registeredInterventions.some(name=>{
  const actual=name.toLowerCase();
  return names.some(x=>actual.includes(x)||x.includes(actual));
 });
};
export function parseRegistryEvidenceIndex(raw:unknown):RegistryEvidenceIndex{
 if(!raw||typeof raw!=="object")throw Error("RAAS_REGISTRY_INDEX_INVALID");
 const j=raw as RegistryEvidenceIndex;
 if(j.schemaVersion!==1||j.scope!=="RAAS_REGISTRY_TRIAL_EVIDENCE_INDEX"||
  !Array.isArray(j.records)||!j.summary||j.records.length!==j.summary.researchNcts||
  j.summary.researchNcts!==j.summary.registryRecords||
  j.summary.approvedOverallRaasScores!==0)
  throw Error("RAAS_REGISTRY_INDEX_INVALID");
 const ids=new Set<string>();let posted=0;
 for(const e of j.records){
  if(!nct.test(e.nctId)||ids.has(e.nctId)||!e.ticker?.trim()||
   e.sourceUrl!=="https://clinicaltrials.gov/study/"+e.nctId||
   !hash.test(e.sourceHash)||typeof e.postedResults!=="boolean"||
   !Array.isArray(e.primaryDefinitions)||!Array.isArray(e.primaryResults)||
   (e.seriousEventDetails!==undefined&&!Array.isArray(e.seriousEventDetails))||
   !Array.isArray(e.registeredInterventions)||!Array.isArray(e.registeredConditions)||
   (e.registeredDesign!==undefined&&(
    !e.registeredDesign||typeof e.registeredDesign!=="object"||
    !["allocation","masking","interventionModel","studyType","enrollmentType"].every(
      k=>typeof (e.registeredDesign as unknown as Record<string,unknown>)[k]==="string")||
    (e.registeredDesign.enrollment!==null&&
      (!Number.isInteger(e.registeredDesign.enrollment)||e.registeredDesign.enrollment<=0))
   ))||
   !Number.isInteger(e.postedPrimaryOutcomeCount)||
   !Number.isInteger(e.seriousAdverseEventTermCount)||
   e.seriousAdverseEventTermCount<0||e.postedPrimaryOutcomeCount<0||
   e.postedResults!==(e.evidenceState==="POSTED_RESULTS_UNGRADED")||
   (!e.postedResults&&(e.primaryResults.length>0||e.postedPrimaryOutcomeCount>0)))
   throw Error("RAAS_REGISTRY_INDEX_ROW_INVALID");
  for(const out of e.primaryResults){
   if((out.groups!==undefined&&(!Array.isArray(out.groups)||out.groups.length>14))||
      (out.measurements!==undefined&&(!Array.isArray(out.measurements)||out.measurements.length>24))||
      (out.comparisons!==undefined&&(!Array.isArray(out.comparisons)||out.comparisons.length>12)))
    throw Error("RAAS_REGISTRY_INDEX_RESULT_DETAILS_INVALID");
  }
  if(!e.postedResults&&((e.seriousEventDetails?.length||0)>0||
    e.primaryResults.some(x=>(x.measurements?.length||0)>0||(x.comparisons?.length||0)>0)))
   throw Error("RAAS_REGISTRY_INDEX_UNPUBLISHED_DETAILS");
  for(const event of e.seriousEventDetails||[]){
   if(!Array.isArray(event.groups)||event.groups.length>12)throw Error("RAAS_REGISTRY_INDEX_SAE_INVALID");
   for(const g of event.groups){
    if(["numAffected","numAtRisk","numEvents"].some(k=>{
     const n=g[k as "numAffected"|"numAtRisk"|"numEvents"];
     return n!==undefined&&n!==null&&(!Number.isInteger(n)||n<0||n>1000000);
    }))throw Error("RAAS_REGISTRY_INDEX_SAE_INVALID");
   }
  }
  ids.add(e.nctId);if(e.postedResults)posted++;
 }
 if(posted!==j.summary.postedRegistryResults||
  posted+j.summary.protocolOnly!==j.summary.researchNcts)
  throw Error("RAAS_REGISTRY_INDEX_COUNT_INVALID");
 const counts={
  trialsWithPrimaryComparisons:j.records.filter(r=>r.primaryResults.some(
   out=>out.comparisons?.some(a=>a.groupIds?.length>=2))).length,
  trialsWithPrimaryGroupMeasurements:j.records.filter(r=>r.primaryResults.some(
   out=>(out.measurements?.length||0)>0)).length,
  trialsWithPrimaryConfidenceIntervals:j.records.filter(r=>r.primaryResults.some(
   out=>out.comparisons?.some(a=>!!a.ciLowerLimit&&!!a.ciUpperLimit))).length,
  trialsWithSafetyRiskDenominators:j.records.filter(r=>r.seriousEventDetails?.some(
   ev=>ev.groups.some(g=>typeof g.numAffected==="number"&&
    typeof g.numAtRisk==="number"&&g.numAtRisk>0))).length
 };
 for(const key of Object.keys(counts) as (keyof typeof counts)[]){
  const n=j.summary[key];
  if(n!==undefined&&(!Number.isInteger(n)||n!==counts[key]))
   throw Error("RAAS_REGISTRY_INDEX_SOURCE_COVERAGE_MISMATCH");
 }
 return j;
}
let cached:Promise<RegistryEvidenceIndex|null>|null=null;
export function loadRegistryEvidenceIndex():Promise<RegistryEvidenceIndex|null>{
 if(!cached){
  cached=fetch("/raas-registry-evidence-index.json",{cache:"no-store"})
   .then(async r=>{
    if(!r.ok)throw Error("REGISTRY_EVIDENCE_SNAPSHOT_NOT_PUBLISHED");
    return parseRegistryEvidenceIndex(await r.json());
   }).catch(()=>{cached=null;return null;});
 }
 return cached;
}
export function registryTrialFor(
 index:RegistryEvidenceIndex|null,
 trial:{nctId:string;ticker:string;drug?:string}
):RegistryTrialEvidence|null{
 if(!index)return null;
 const found=index.records.find(x=>x.nctId===trial.nctId);
 return found&&sameTrial(found,trial)?found:null;
}
export function registryMetricLeads(
 e:RegistryTrialEvidence|null,stage:RaasStage,
 trial:{nctId:string;ticker:string;drug?:string}
):RegistryMetricLead[]{
 if(!e||!sameTrial(e,trial))return [];
 const leads:RegistryMetricLead[]=[];
 const base={sourceUrl:e.sourceUrl,measurement:null as null};
 const sourceDay=e.resultsFirstPosted||e.registryLastUpdated||e.retrievedAt.slice(0,10);
 const parseNumber=(raw:unknown):number|null=>{
  if(typeof raw!=="string"||!/^[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[-+]?\d+)?$/i.test(raw.trim()))return null;
  const n=Number(raw);return Number.isFinite(n)&&Math.abs(n)<=1e10?n:null;
 };
 const numeric=(label:string,value:number,unit:string)=>({label,value,unit});
 // A trial's registered design can inform the pre-readout DESIGN review,
 // but it cannot substantiate historical human efficacy or numerical scores.
 if(stage==="pre"&&e.primaryDefinitions.length){
  leads.push({...base,id:e.nctId+"-registered-design",kind:"REGISTERED_PHASE3_PROTOCOL",
   metricIds:["pre-1-2"],sourceDate:e.registryLastUpdated||e.retrievedAt.slice(0,10),
   description:"Registered Phase 3 primary endpoint: "+
    e.primaryDefinitions.slice(0,2).map(x=>x.measure+" ("+x.timeFrame+")").join("; ")+
    ". Protocol lead only; design power and prior results still need independent review."});
 }
 if(stage==="post"&&e.postedResults&&e.postedPrimaryOutcomeCount>0){
  leads.push({...base,id:e.nctId+"-posted-primary",kind:"POSTED_REGISTRY_RESULTS",
   metricIds:["post-1-1"],
   sourceDate:e.resultsFirstPosted||e.registryLastUpdated||e.retrievedAt.slice(0,10),
   description:"Registry reports "+e.postedPrimaryOutcomeCount+
    " primary outcome(s): "+
    e.primaryResults.slice(0,2).map(x=>x.title).join("; ")+
    ". Treatment effect, comparator, and clinical significance require review."});
  if(e.primaryResults.some(x=>x.analysisCount>0)){
   leads.push({...base,id:e.nctId+"-primary-statistics",kind:"POSTED_REGISTRY_STATISTICS",
    metricIds:["post-1-3"],
    sourceDate:e.resultsFirstPosted||e.registryLastUpdated||e.retrievedAt.slice(0,10),
    description:"Registry primary outcome includes statistical analyses; full confidence intervals, "+
     "multiplicity plan and missing-data sensitivity are not established by analysis presence."});
  }
 }
 // Quantitative source observations are NOT graded RAAS components. Never infer
 // the preferred outcome direction or significance across different indications.
 if(stage==="post"&&e.postedResults){
  for(const [oi,outcome] of e.primaryResults.slice(0,5).entries()){
   for(const [ai,analysis] of (outcome.comparisons||[]).slice(0,12).entries()){
    if(!Array.isArray(analysis.groupIds)||analysis.groupIds.length<2)continue;
    const effect=parseNumber(analysis.paramValue);
    const method=analysis.method||"unreported method";
    const pair=analysis.groupIds.join(" vs ");
    if(effect!==null){
     leads.push({metricIds:["post-1-1"],id:e.nctId+"-raw-primary-effect-"+oi+"-"+ai,
      kind:"POSTED_PRIMARY_CONTRAST_RAW_MEASUREMENT",sourceUrl:e.sourceUrl,
      sourceDate:sourceDay,
      description:outcome.title+" · groups "+pair+" · "+method+
       ". This is an unadjusted transcription of the reported analysis parameter, "+
       "not a direction-adjusted efficacy score or independent comparator benchmark.",
      measurement:numeric("Registry-reported "+(analysis.paramType||"analysis")+" contrast",
       effect,outcome.unit||"reported parameter units")});
    }
    const lower=parseNumber(analysis.ciLowerLimit),
      upper=parseNumber(analysis.ciUpperLimit);
    if(lower!==null&&upper!==null&&upper>=lower){
     leads.push({metricIds:["post-1-3"],id:e.nctId+"-raw-primary-ci-"+oi+"-"+ai,
      kind:"POSTED_PRIMARY_CI_WIDTH_RAW_MEASUREMENT",sourceUrl:e.sourceUrl,
      sourceDate:sourceDay,
      description:outcome.title+" · groups "+pair+" · confidence level "+
       (analysis.ciPctValue||"not reported")+"% · source interval ["+
       lower+", "+upper+"]. Width alone cannot establish statistical robustness "+
       "without prespecification, multiplicity and missing-data sensitivity review.",
      measurement:numeric("Published CI width",upper-lower,outcome.unit||"reported parameter units")});
    }
    const p=parseNumber(analysis.pValue);
    if(p!==null&&p>=0&&p<=1){
     leads.push({metricIds:["post-1-3"],id:e.nctId+"-raw-primary-p-"+oi+"-"+ai,
      kind:"POSTED_PRIMARY_P_VALUE_RAW_MEASUREMENT",sourceUrl:e.sourceUrl,
      sourceDate:sourceDay,
      description:outcome.title+" · groups "+pair+" · reported p-value; "+
       "does not prove clinical importance or multiplicity-adjusted significance.",
      measurement:numeric("Published p-value",p,"probability")});
    }
   }
  }
  // Rates are only matched to their own reported registry adverse-event group.
  // ClinicalTrials.gov EG IDs cannot be assumed to correspond to OG group IDs.
  for(const [ei,event] of (e.seriousEventDetails||[]).slice(0,8).entries()){
   for(const [gi,g] of event.groups.slice(0,6).entries()){
    const a=g.numAffected,n=g.numAtRisk;
    if(a===undefined||n===undefined||a===null||n===null||
      !Number.isInteger(a)||!Number.isInteger(n)||n<=0||a<0||a>n)continue;
    const pct=Math.round(10000*a/n)/100;
    leads.push({metricIds:["post-1-5"],id:e.nctId+"-raw-sae-rate-"+ei+"-"+gi,
     kind:"POSTED_SAE_AFFECTED_RATE_RAW_MEASUREMENT",sourceUrl:e.sourceUrl,
     sourceDate:sourceDay,
     description:"Serious adverse event "+event.term+" · event group "+
      g.groupId+" · "+a+"/"+n+" affected. Group identity, exposure duration, "+
      "causality, events per patient and comparative clinical importance require review.",
     measurement:numeric("Registry group serious-event affected rate",pct,"%")});
   }
  }
 }
 if(stage==="post"&&e.postedResults&&e.seriousAdverseEventTermCount>0){
  leads.push({...base,id:e.nctId+"-posted-safety",kind:"POSTED_REGISTRY_SAFETY",
   metricIds:["post-1-5"],sourceDate:e.resultsFirstPosted||e.registryLastUpdated||e.retrievedAt.slice(0,10),
   description:"Registry lists "+e.seriousAdverseEventTermCount+
    " serious-adverse-event term(s). Matched exposure and adverse-event rates "+
    "remain required; this is not a safety rating."});
 }
 return leads;
}
