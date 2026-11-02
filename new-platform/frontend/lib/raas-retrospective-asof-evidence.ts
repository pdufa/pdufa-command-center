/** Historical BOTTOM evidence available before selected retrospective entry dates.
 * No observation is a RAAS grade, original trade signal or approved forecast.
 */
import type {RetrospectiveFeed} from "./raas-retrospective-intake";
export type AsOfEvidenceKind=
 "PLACEBO_ADJUSTED_CONTINUOUS"|"RANDOMIZED_RESPONSE"|
 "SINGLE_ARM_RESPONSE"|"CONDITIONAL_DURABILITY"|"CASH_BALANCE";
export type AsOfFact={
 id:string;kind:AsOfEvidenceKind;title:string;unit:string;
 sourcePublishedAt:string;sourceUrl:string;context:string;
 studyNctId?:string;measurementAsOf?:string;
 value?:number;activePercent?:number;comparatorPercent?:number;
};
export type AsOfFactRecord={caseId:string;facts:AsOfFact[]};
export type AsOfEvidenceFeed={
 schemaVersion:1;scope:"RAAS_RETROSPECTIVE_ASOF_EVIDENCE";
 sourceAsOf:string;note:string;records:AsOfFactRecord[];
};
export type AsOfFactMeasurement={
 label:string;value:number;unit:string;interpretation:string;
};
const date=(v:string):boolean=>/^\d{4}-\d{2}-\d{2}$/.test(v)&&
 Number.isFinite(Date.parse(v+"T00:00:00Z"))&&new Date(v+"T00:00:00Z").toISOString().slice(0,10)===v;
const url=(v:string):boolean=>/^https:\/\/[^\s/]+\/\S+/.test(v);
const num=(n:unknown):n is number=>typeof n==="number"&&Number.isFinite(n);
const pct=(n:unknown)=>num(n)&&n>=0&&n<=100;
const round=(v:number)=>Math.round(v*100)/100;
export function parseAsOfEvidence(input:unknown,cases:RetrospectiveFeed):AsOfEvidenceFeed{
 if(!input||typeof input!=="object")throw Error("RAAS_ASOF_INVALID");
 const feed=input as AsOfEvidenceFeed;
 if(feed.schemaVersion!==1||feed.scope!=="RAAS_RETROSPECTIVE_ASOF_EVIDENCE"||
 !date(feed.sourceAsOf)||!Array.isArray(feed.records)||feed.records.length>5000)
  throw Error("RAAS_ASOF_INVALID");
 const byId=new Map(cases.records.map(r=>[r.id,r]));
 const caseIds=new Set<string>();const factIds=new Set<string>();
 for(const row of feed.records){
  const c=byId.get(row.caseId);
  if(!c||caseIds.has(row.caseId)||!Array.isArray(row.facts)||!row.facts.length)
   throw Error("RAAS_ASOF_CASE_INVALID");
  caseIds.add(row.caseId);
  for(const f of row.facts){
   if(!f||!f.id?.trim()||factIds.has(f.id)||!f.title?.trim()||
    !f.unit?.trim()||!f.context?.trim()||!date(f.sourcePublishedAt)||
    f.sourcePublishedAt>c.entry.date||f.sourcePublishedAt>feed.sourceAsOf||
    !url(f.sourceUrl)||
    (f.measurementAsOf!==undefined&&(!date(f.measurementAsOf)||f.measurementAsOf>f.sourcePublishedAt))||
    (f.studyNctId!==undefined&&!c.nctIds.includes(f.studyNctId)))
     throw Error("RAAS_ASOF_FACT_INVALID");
   factIds.add(f.id);
   if(f.kind==="RANDOMIZED_RESPONSE"){
    if(!pct(f.activePercent)||!pct(f.comparatorPercent)||!f.studyNctId)
     throw Error("RAAS_ASOF_RANDOMIZED_INVALID");
   }else if(f.kind==="PLACEBO_ADJUSTED_CONTINUOUS"){
    if(!num(f.value)||!f.studyNctId)throw Error("RAAS_ASOF_CONTINUOUS_INVALID");
   }else if(f.kind==="SINGLE_ARM_RESPONSE"||f.kind==="CONDITIONAL_DURABILITY"){
    if(!pct(f.value)||!f.studyNctId||f.comparatorPercent!==undefined)
     throw Error("RAAS_ASOF_SINGLE_ARM_INVALID");
   }else if(f.kind==="CASH_BALANCE"){
    if(!num(f.value)||f.value<0||!f.measurementAsOf||f.studyNctId!==undefined)
     throw Error("RAAS_ASOF_CASH_INVALID");
   }else throw Error("RAAS_ASOF_KIND_INVALID");
  }
 }
 return feed;
}
export function factsForRetrospectiveCase(feed:AsOfEvidenceFeed,caseId:string):readonly AsOfFact[]{
 return feed.records.find(r=>r.caseId===caseId)?.facts??[];
}
export function measureAsOfFact(f:AsOfFact):AsOfFactMeasurement{
 if(f.kind==="RANDOMIZED_RESPONSE"){
  return {label:"Absolute active-minus-control response difference",
   value:round((f.activePercent??0)-(f.comparatorPercent??0)),unit:"percentage points",
   interpretation:"Descriptive between-arm result, not a RAAS score, causal proof of superiority over approved competitors or a return forecast."};
 }
 if(f.kind==="PLACEBO_ADJUSTED_CONTINUOUS"){
  return {label:"Issuer-reported placebo-adjusted clinical endpoint",
   value:f.value??0,unit:f.unit,
   interpretation:"One clinical endpoint with its original units. Disease-specific clinical importance and complete evidence require separate review."};
 }
 if(f.kind==="SINGLE_ARM_RESPONSE"){
  return {label:"Observed response rate without randomized comparator",
   value:f.value??0,unit:f.unit,
   interpretation:"No randomized comparator exists within this specific result; a placebo-adjusted response difference must NOT be inferred."};
 }
 if(f.kind==="CONDITIONAL_DURABILITY"){
  return {label:"Conditional duration-of-response estimate",
   value:f.value??0,unit:f.unit,
   interpretation:"Only for patients who had already achieved response; not the fraction of all treated patients with durable response."};
 }
 return {label:"Historical cash-related balance, not runway",
  value:f.value??0,unit:f.unit,
  interpretation:"A cash snapshot does not establish burn rate, runway, fully diluted enterprise value, financing risk or stock upside."};
}
