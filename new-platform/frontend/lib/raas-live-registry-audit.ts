/** Read-only, exact-NCT current primary-source RAAS evidence inventory.
 * Registry outcome data are not necessarily an FDA filing, public issuer readout,
 * statistically valid comparison, or independently validated RAAS metric.
 */
import type {RegistryBenefitResearch,RegistryOutcome} from "./registry-benefit-research";
export type RaasLiveRegistryAudit={
 nctId:string;sourceUrl:string;retrievedAt:string;sourceUpdated:string|null;
 status:"REGISTRY_POSTED_UNGRADED"|"REGISTRY_PROTOCOL_ONLY";
 phase3Registered:boolean;resultsPosted:boolean;
 primaryOutcomes:number;primaryMeasurements:number;primaryWithAnalysis:number;
 secondaryOutcomes:number;secondaryMeasurements:number;
 seriousAdverseEventTerms:number;seriousAdverseEventArms:number;
 preliminaryMetricLeads:string[];
 sourceNotValidated:true;
 limitations:string[];
};
const dateOk=(s:string):boolean=>Number.isFinite(Date.parse(s))&&s.length<=40;
const countedMeasurements=(items:RegistryOutcome[])=>items.reduce(
 (sum,o)=>sum+o.measurements.length,0);
export function auditLiveRegistryForRaas(packet:RegistryBenefitResearch,expectedNct:string,
 stage:"pre"|"post"):RaasLiveRegistryAudit{
 if(!/^NCT\d{8}$/.test(expectedNct)||!packet||packet.nctId!==expectedNct||
  packet.sourceUrl!=="https://clinicaltrials.gov/study/"+expectedNct||
  !dateOk(packet.retrievedAt)||!Array.isArray(packet.primary)||
  !Array.isArray(packet.secondary)||!Array.isArray(packet.seriousAdverseEvents)||
  !Array.isArray(packet.registeredPhases)||
  packet.comparisonVerified!==false||packet.fdaDecisionVerified!==false||
  packet.benefitRank!==null||
  (packet.resultsPosted!==true&&packet.resultsPosted!==false))
  throw Error("RAAS_LIVE_REGISTRY_SOURCE_INVALID");
 const primary=packet.resultsPosted?packet.primary:[];
 const secondary=packet.resultsPosted?packet.secondary:[];
 const serious=packet.resultsPosted?packet.seriousAdverseEvents:[];
 const primaryMeasurements=countedMeasurements(primary);
 const secondaryMeasurements=countedMeasurements(secondary);
 const seriousAdverseEventArms=serious.reduce((sum,e)=>sum+e.groups.filter(g=>
  Number.isSafeInteger(g.affected)&&Number.isSafeInteger(g.atRisk)&&
  g.affected>=0&&g.atRisk>0&&g.affected<=g.atRisk).length,0);
 const leads:string[]=[];
 // *Candidates* to evaluate, not accepted 0–100 RAAS grades.
 if(stage==="post"&&primaryMeasurements>0)leads.push("post-1-1");
 if(stage==="post"&&secondaryMeasurements>0)leads.push("post-1-2");
 if(stage==="post"&&seriousAdverseEventArms>0)leads.push("post-1-5");
 return {
  nctId:expectedNct,sourceUrl:packet.sourceUrl,retrievedAt:packet.retrievedAt,
  sourceUpdated:packet.sourceUpdated,status:packet.resultsPosted?
   "REGISTRY_POSTED_UNGRADED":"REGISTRY_PROTOCOL_ONLY",
  phase3Registered:packet.registeredPhases.some(x=>x.toUpperCase().includes("PHASE3")),
  resultsPosted:packet.resultsPosted,
  primaryOutcomes:primary.length,primaryMeasurements,
  primaryWithAnalysis:primary.filter(x=>x.analysisReported).length,
  secondaryOutcomes:secondary.length,secondaryMeasurements,
  seriousAdverseEventTerms:serious.length,seriousAdverseEventArms,
  preliminaryMetricLeads:leads,sourceNotValidated:true,
  limitations:[
   "This is a live exact-NCT registry lookup, not a validated issuer market-cap or PDUFA filter.",
   "Registry groups and reported outcomes are not automatically comparable, causal or statistically persuasive.",
   stage==="pre"&&packet.resultsPosted?
    "Registry shows results posted for a trial currently in the TOP source-classification spreadsheet. Recheck the classification; do not retroactively change source-checked readout dates.":
    "A registry result does not prove the timing of an issuer's public Phase 3 readout.",
   "No FDA action, expected stock return, composite RAAS rating or risk-adjusted prediction is calculated."
  ]
 };
}
