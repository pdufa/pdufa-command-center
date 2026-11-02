/** A cross-source *protocol* check only. ClinicalTrials.gov registrations are
 * sponsor-entered plans, not independent clinical result validation. A result
 * matches its registered endpoint only when all exact NCT/program identifiers
 * and the Week 12/16 outcome text agree. Never upgrades the 38 survey fields.
 */
import type {BenefitRecord} from "./benefit-assessments";

export type Phase3RegistryEntry={
 nctId:string;ticker:string;drug:string;indication:string;trial:string;
 primaryEndpointId:string;primaryEndpointLabel:string;primaryWeek:number;
 randomized:boolean;placeboControlled:boolean;blinded:boolean;
 canonicalRegistry:string;registryMirror:string;registrySnapshotLastPosted:string;
 sourceNote:string;
};
export type Phase3RegistryConcordance={
 status:"PROTOCOL_ALIGNED"|"NOT_ESTABLISHED";
 trial:string;
 summary:string;
 primaryOutcome:string|null;
 design:string|null;
 registryUrl:string|null;
 registryMirrorUrl:string|null;
 snapshotDate:string|null;
 snapshotPredatesDisclosure:boolean|null;
 uncertainty:string;
};
const day=(s:string)=>/^\d{4}-\d{2}-\d{2}$/.test(s)&&!Number.isNaN(Date.parse(s))&&
 new Date(s+"T00:00:00Z").toISOString().slice(0,10)===s;
const normalize=(s:string)=>s.trim().toLowerCase();
const absent:Phase3RegistryConcordance={
 status:"NOT_ESTABLISHED",trial:"Unmatched",
 summary:"No verified cross-source protocol agreement for this exact trial.",
 primaryOutcome:null,design:null,registryUrl:null,registryMirrorUrl:null,
 snapshotDate:null,snapshotPredatesDisclosure:null,
 uncertainty:"No registry-protocol inference or clinical score is justified without a unique identity-matched record."
};
export function phase3RegistryConcordance(
 record:BenefitRecord|null,source:readonly Phase3RegistryEntry[]
):Phase3RegistryConcordance{
 if(!record)return {...absent};
 const matches=source.filter(entry=>entry.nctId===record.nctId);
 if(matches.length!==1)return {...absent};
 const e=matches[0];
 const facts=record.facts;
 const val=(key:string)=>facts[key]?.status==="VERIFIED"&&
 typeof facts[key].value==="string"?facts[key].value:"";
 const primary=e.primaryEndpointId==="UAS7_CHANGE"&&e.primaryWeek===12?
  val("clinicalBenefit").includes("Week 12 UAS7 LS mean change"):
  e.primaryEndpointId==="ACR50_RESPONSE"&&e.primaryWeek===16?
  /Week 16 ACR50 response/i.test(val("responseRemission")):"";
 const metadataOk=e.ticker===record.ticker&&normalize(e.drug)===normalize(record.drug)&&
  normalize(e.indication)===normalize(record.indication)&&
  e.randomized===true&&e.placeboControlled===true&&e.blinded===true&&
  e.primaryEndpointLabel.length>12&&day(e.registrySnapshotLastPosted)&&
  e.canonicalRegistry==="https://clinicaltrials.gov/study/"+record.nctId&&
  e.registryMirror==="https://ichgcp.net/clinical-trials-registry/"+record.nctId&&
  e.sourceNote.includes("Sponsor-supplied");
 if(!metadataOk||!primary)return {...absent};
 const datedFacts=Object.values(facts).filter(f=>f.status==="VERIFIED");
 const dates=datedFacts.map(f=>f.sourceDate).filter(day);
 const date=dates.length?dates.reduce((a,b)=>a<b?a:b):null;
 const predates=date?e.registrySnapshotLastPosted<date:null;
 return {
  status:"PROTOCOL_ALIGNED",trial:e.trial,
  summary:"The registry-listed primary outcome and timepoint agree with the separately documented issuer readout for this exact NCT.",
  primaryOutcome:e.primaryEndpointLabel+" · Week "+e.primaryWeek,
  design:"Phase 3 · randomized · blinded · placebo-controlled",
  registryUrl:e.canonicalRegistry,registryMirrorUrl:e.registryMirror,
  snapshotDate:e.registrySnapshotLastPosted,
  snapshotPredatesDisclosure:predates,
  uncertainty:predates===true?
   "The referenced registry snapshot predates the dated issuer findings. This establishes an accessible earlier protocol description, not an independently verified treatment effect, data audit, safety comparison or FDA forecast.":
   "The accessible registry snapshot is not demonstrated to predate the issuer readout. Historical prespecification requires version-history inspection. A matching endpoint is not independent efficacy, safety or FDA-outcome validation."
 };
}
