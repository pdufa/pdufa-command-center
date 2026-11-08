/**
 * ClinicalTrials.gov API v2 posted-results parser. Extract source-reported values
 * without interpreting significance, guessing arm relationships or inventing data.
 */
export type RegisteredAnalysis={
  comparisons:string[];
  reportedPValue:string|null;
  method:string|null;
  parameter:string|null;
  estimate:string|null;
  confidenceInterval:string|null;
  note:string|null;
};
export type RegisteredOutcome={
  type:string; title:string; timeFrame:string|null; unit:string|null;
  groups:Record<string,string>;
  analyses:RegisteredAnalysis[];
};
export type RegisteredAdverseEventGroup={
  id:string; title:string;
  seriousAffected:number|null;seriousAtRisk:number|null;
  otherAffected:number|null;otherAtRisk:number|null;
  deathAffected:number|null;deathAtRisk:number|null;
};
export type RegistryResultReport={
  nct:string;resultsPosted:boolean;
  outcomes:RegisteredOutcome[];
  events:RegisteredAdverseEventGroup[];
  seriousEventTerms:number;
  nonSeriousEventTerms:number;
  limitations:string[];
};
const record=(x:unknown):Record<string,unknown>=>x&&typeof x==="object"&&!Array.isArray(x)?x as Record<string,unknown>:{};
const field=(o:unknown,k:string)=>record(o)[k];
const array=(x:unknown):unknown[]=>Array.isArray(x)?x:[];
const string=(x:unknown):string=>typeof x==="string"?x:"";
const present=(x:unknown):string|null=>{
  if(typeof x==="string")return x.trim()||null;
  if(typeof x==="number"&&Number.isFinite(x))return String(x);
  return null;
};
const count=(x:unknown):number|null=>typeof x==="number"&&Number.isSafeInteger(x)&&x>=0?x:null;
export function parseRegistryResults(study:unknown,expectedNct:string):RegistryResultReport{
 if(!/^NCT\d{8}$/.test(expectedNct))throw Error("Invalid NCT");
 if(field(field(study,"protocolSection"),"identificationModule")===undefined)throw Error("Not a ClinicalTrials.gov study");
 const nct=string(field(field(field(study,"protocolSection"),"identificationModule"),"nctId"));
 if(nct!==expectedNct)throw Error("Registry NCT mismatch");
 const results=record(field(study,"resultsSection"));
 const om=record(field(results,"outcomeMeasuresModule"));
 const ae=record(field(results,"adverseEventsModule"));
 const outcomes=array(field(om,"outcomeMeasures")).map(item=>{
   const o=record(item);
   const groups:Record<string,string>={};
   for(const g of array(field(o,"groups"))){
     const id=string(field(g,"id")),title=string(field(g,"title"));
     if(id)groups[id]=title||id;
   }
   const analyses=array(field(o,"analyses")).map(item=>{
      const a=record(item);
      const selected=array(field(a,"groupIds")).map(id=>groups[string(id)]||string(id)).filter(Boolean);
      const ciLower=present(field(a,"ciLowerLimit")),ciUpper=present(field(a,"ciUpperLimit"));
      const pct=present(field(a,"ciPctValue")),sides=present(field(a,"ciNumSides"));
      const ci=ciLower!==null||ciUpper!==null?[
        pct?pct+"% CI":(sides?sides+"-sided CI":"CI"),
        ciLower!==null?ciLower:"not reported","to",ciUpper!==null?ciUpper:"not reported"
      ].join(" "):null;
      return {
        comparisons:selected,
        reportedPValue:present(field(a,"pValue")),
        method:present(field(a,"statisticalMethod")),
        parameter:present(field(a,"paramType")),
        estimate:present(field(a,"paramValue")),
        confidenceInterval:ci,
        note:present(field(a,"pValueComment"))||present(field(a,"otherAnalysisDescription"))||present(field(a,"statisticalComment"))
      };
   });
   return {
     type:string(field(o,"type"))||"UNSPECIFIED",
     title:string(field(o,"title"))||"Unnamed outcome",
     timeFrame:present(field(o,"timeFrame")),
     unit:present(field(o,"unitOfMeasure")),
     groups,analyses
   };
 });
 const events=array(field(ae,"eventGroups")).map(g=>({
  id:string(field(g,"id")),title:string(field(g,"title"))||"Unlabeled arm",
  seriousAffected:count(field(g,"seriousNumAffected")),
  seriousAtRisk:count(field(g,"seriousNumAtRisk")),
  otherAffected:count(field(g,"otherNumAffected")),
  otherAtRisk:count(field(g,"otherNumAtRisk")),
  deathAffected:count(field(g,"deathsNumAffected"))??count(field(g,"allCauseMortalityNumAffected")),
  deathAtRisk:count(field(g,"deathsNumAtRisk"))??count(field(g,"allCauseMortalityNumAtRisk"))
 }));
 const limitations=[
   "Registry values reflect posted sponsor results, not an independent FDA review.",
   "A p-value is shown only when explicitly posted for that outcome comparison; missing does not mean nonsignificant.",
   "Statistical multiplicity, prespecification, missing-data models and changes to endpoints require underlying protocol/SAP verification.",
   "Adverse-event totals are group-specific and can include overlapping periods; no pooled rates or direct arm comparisons are calculated automatically."
 ];
 return {nct,resultsPosted:Object.keys(results).length>0,outcomes,events,
  seriousEventTerms:array(field(ae,"seriousEvents")).length,
  nonSeriousEventTerms:array(field(ae,"otherEvents")).length,
  limitations};
}
