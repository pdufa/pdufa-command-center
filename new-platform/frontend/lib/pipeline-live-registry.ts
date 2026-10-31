/** ClinicalTrials.gov current registry fact inspection.
 * This is NOT pivotal Phase 3 confirmation, issuer market-cap verification,
 * FDA PDUFA confirmation, competitive analysis or a trade signal.
 */
export type RegistryReview={
 nctId:string;
 title:string|null;
 registryStatus:string|null;
 phases:string[];
 phase3Registered:boolean;
 completedRegistered:boolean;
 registryAssessment:"PHASE3_COMPLETED_REGISTRY_ONLY"|"PHASE3_OTHER_STATUS"|"PHASE3_NOT_ESTABLISHED";
 leadSponsor:string|null;
 conditions:string[];
 interventions:string[];
 primaryCompletionDate:string|null;
 lastUpdatePosted:string|null;
 enrollment:number|null;
 resultsPosted:boolean;
 sourceUrl:string;
 verifiedAt:string;
 qualification:"NEEDS_REVIEW";
 remainingChecks:string[];
};
const text=(value:unknown,max=400):string|null=>
 typeof value==="string"&&!!value.trim()?value.trim().slice(0,max):null;
const strings=(value:unknown,max=15):string[]=>
 Array.isArray(value)?[...new Set(value.map(x=>text(x,130)).filter((x):x is string=>!!x))].slice(0,max):[];
const record=(value:unknown):Record<string,unknown>=>value!==null&&typeof value==="object"&&!Array.isArray(value)?value as Record<string,unknown>:{};
function date(value:unknown):string|null{
 const s=text(value,10);
 if(!s||!/^\d{4}(-\d{2})?(-\d{2})?$/.test(s))return null;
 const iso=/^\d{4}-\d{2}-\d{2}$/.test(s);
 if(iso&&new Date(s+"T00:00:00Z").toISOString().slice(0,10)!==s)return null;
 return s;
}
export function normalizeRegistryStudy(raw:unknown,expectedNctId:string,asOf:string):RegistryReview{
 if(!/^NCT\d{8}$/.test(expectedNctId))throw Error("Invalid pinned NCT ID");
 const study=record(raw),protocol=record(study.protocolSection);
 const id=record(protocol.identificationModule);
 if(id.nctId!==expectedNctId)throw Error("Registry study identifier mismatch");
 const status=record(protocol.statusModule),design=record(protocol.designModule);
 const sponsor=record(protocol.sponsorCollaboratorsModule);
 const conditions=record(protocol.conditionsModule),interventions=record(protocol.armsInterventionsModule);
 const phases=strings(design.phases),phase3Registered=phases.includes("PHASE3");
 const registryStatus=text(status.overallStatus,50),completedRegistered=registryStatus==="COMPLETED";
 const registryAssessment:RegistryReview["registryAssessment"]=!phase3Registered?"PHASE3_NOT_ESTABLISHED":
   completedRegistered?"PHASE3_COMPLETED_REGISTRY_ONLY":"PHASE3_OTHER_STATUS";
 const names=Array.isArray(interventions.interventions)?interventions.interventions.map(x=>record(x).name):[];
 const count=record(design.enrollmentInfo).count;
 if(!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$/.test(asOf) || Number.isNaN(Date.parse(asOf)))
   throw Error("Invalid registry retrieval timestamp");
 return {
  nctId:expectedNctId,title:text(id.briefTitle,500),registryStatus,phases,
  phase3Registered,completedRegistered,registryAssessment,
  leadSponsor:text(record(sponsor.leadSponsor).name),
  conditions:strings(conditions.conditions,15),interventions:strings(names,20),
  primaryCompletionDate:date(record(status.primaryCompletionDateStruct).date),
  lastUpdatePosted:date(record(status.lastUpdatePostDateStruct).date),
  enrollment:Number.isSafeInteger(count)&&Number(count)>=0?Number(count):null,
  resultsPosted:study.hasResults===true || (!!study.resultsSection&&Object.keys(record(study.resultsSection)).length>0),
  sourceUrl:"https://clinicaltrials.gov/study/"+expectedNctId,
  verifiedAt:asOf,qualification:"NEEDS_REVIEW",
  remainingChecks:[
   "Verify public pivotal Phase 3 results and the exact therapy–indication program; registry COMPLETED is not evidence of pivotal efficacy.",
   "Verify current U.S. listing and market cap $300M–$10B; dated census price is not current.",
   "Verify commercial rights and exact treatment line / patient subgroup.",
   "Verify original FDA action date separately and apply PDUFA minus-three-day cutoff when relevant."
  ]
 };
}
