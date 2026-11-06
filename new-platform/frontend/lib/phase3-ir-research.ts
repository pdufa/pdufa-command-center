import evidence from "../data/phase3CompanyWebsiteEvidence20261105.json";
import queue from "../data/phase3InvestorRelationsResearchQueue20261106.json";
import {populationGeographyFact,populationGeographyRecord} from "./phase3-population-geography";

export const irAssessmentRecords=evidence.assessmentRecords;
const bySlot=new Map(irAssessmentRecords.map(r=>[`${r.nctId}:${r.assessmentNumber}`,r]));
export function irAssessment(nctId:string,number:number){return bySlot.get(`${nctId}:${number}`);}
export const isVerifiedIrFact=(status:string)=>[
 "DOCUMENTED_SOURCE_FACT","DOCUMENTED_PRIMARY_ENDPOINT_MET",
 "DOCUMENTED_PRIMARY_ENDPOINT_NOT_MET","DOCUMENTED_NON_BINARY_ENDPOINT"
].includes(status);
export const isObservedStatus=(status:string)=>[
 "OBSERVED_PRIMARY_ENDPOINT_MET","OBSERVED_PRIMARY_ENDPOINT_NOT_MET",
 "DOCUMENTED_PRIMARY_ENDPOINT_MET","DOCUMENTED_PRIMARY_ENDPOINT_NOT_MET",
 "DOCUMENTED_NON_BINARY_ENDPOINT","DOCUMENTED_PUBLIC_READOUT"
].includes(status);
export const isSourceFactStatus=(status:string)=>status==="SOURCE_FACT_ONLY"||status==="DOCUMENTED_SOURCE_FACT";
export const requiresResearchStatus=(status:string)=>["UNSCORED","NOT_YET_REVIEWED","REQUIRES_INTERPRETATION"].includes(status);

export function irResearchIntegrity(ncts:Set<string>){
 const allowed=new Set(["DOCUMENTED_SOURCE_FACT","DOCUMENTED_PRIMARY_ENDPOINT_MET","DOCUMENTED_PRIMARY_ENDPOINT_NOT_MET",
  "DOCUMENTED_NON_BINARY_ENDPOINT","NOT_PUBLICLY_DISCLOSED","NOT_YET_REVIEWED","REQUIRES_INTERPRETATION"]);
 return bySlot.size===irAssessmentRecords.length&&irAssessmentRecords.every(r=>
  ncts.has(r.nctId)&&Number.isInteger(r.assessmentNumber)&&r.assessmentNumber>=1&&r.assessmentNumber<=30&&
  allowed.has(r.classification)&&r.evidence&&/^https:\/\//.test(r.sourceUrl)&&
  (/^\d{4}-\d{2}-\d{2}$/.test(r.publicationDate)||
   ("publicationDatePrecision" in r&&r.publicationDatePrecision==="MONTH"&&/^\d{4}-\d{2}$/.test(r.publicationDate))))&&
  new Set(queue.companies.flatMap(c=>c.trials.map(t=>t.nctId))).size===ncts.size&&
  queue.companies.flatMap(c=>c.trials).length===ncts.size&&
  queue.companies.every(c=>c.trials.every(t=>ncts.has(t.nctId)));
}

export function investorRelationsCoverage(){
 return queue.companies.map(c=>({...c,
  matchedTrials:c.trials.filter(t=>t.identityMatched).length,
  trialsRequiringInvestigation:c.trials.filter(t=>t.assessmentReviewStatus!=="COMPLETE").length,
  registeredPopulationTrials:c.trials.filter(t=>populationGeographyFact(t.nctId,6)).length,
  registeredGeographyTrials:c.trials.filter(t=>populationGeographyFact(t.nctId,26)).length,
  registryIdentityMatchedTrials:c.trials.filter(t=>populationGeographyRecord(t.nctId)).length,
  questionEvidenceRecords:irAssessmentRecords.filter(r=>c.trials.some(t=>t.nctId===r.nctId)).length
 }));
}
