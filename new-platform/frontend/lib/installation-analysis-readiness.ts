/** Source inventory checks for independent medical intelligence and FDA
 * document research. No rating engines or clinical-score feeds are imported.
 */
export type MedicalInventoryStatus={
 asOf:string;poolTrials:number;focusTrials:number;applications:number;
 metadataScreenedTrials:number;sourceExtractedTrials:number;fullyReviewedTrials:number;
 incompleteTrials:number;completedDecisions:number;sourceDocuments:number;
};
const count=(v:unknown):v is number=>Number.isSafeInteger(v)&&Number(v)>=0;
export function auditMedicalInventory(raw:unknown):MedicalInventoryStatus{
 if(!raw||typeof raw!=="object")throw Error("Independent medical inventory unavailable");
 const r=raw as {schemaVersion?:number;asOf?:string;generatedAt?:string;inventory?:Record<string,unknown>;applications?:unknown[]};
 const i=r.inventory;
 const keys=["poolTrials","focusTrials","applications","metadataScreenedTrials","sourceExtractedTrials","fullyReviewedTrials","incompleteTrials","completedDecisions","sourceDocuments"] as const;
 const asOf=r.asOf??r.generatedAt;
 if(r.schemaVersion!==1||!i||!asOf||!Number.isFinite(Date.parse(asOf))||keys.some(k=>!count(i[k]))||
  !Array.isArray(r.applications)||r.applications.length!==i.applications||
  Number(i.fullyReviewedTrials)>Number(i.sourceExtractedTrials)||Number(i.sourceExtractedTrials)>Number(i.metadataScreenedTrials)||
  Number(i.completedDecisions)>Number(i.applications))throw Error("Independent medical inventory does not reconcile");
 return {asOf,...Object.fromEntries(keys.map(k=>[k,i[k]]))} as MedicalInventoryStatus;
}
export type OutcomeSourceStatus={
 checkedAt:string;publishedLetters:number|null;approvedApplications:number|null;
 sourcePageReviewRows:number|null;independentlyVerifiedReviewCycles:number;
};
export function auditOutcomeSources(raw:unknown):OutcomeSourceStatus{
 if(!raw||typeof raw!=="object")throw Error("FDA source inventory unavailable");
 const r=raw as Record<string,unknown>;
 if(r.status!=="RESEARCH_ONLY"||r.modelValidated!==false||r.predictionAvailable!==false||r.probability!==null||
  r.denominatorComplete!==false||r.modelEligibleReviewCycles!==0||!count(r.independentlyVerifiedReviewCycles)||
  typeof r.checkedAt!=="string"||!Number.isFinite(Date.parse(r.checkedAt)))throw Error("FDA source inventory cannot certify predictions");
 for(const k of ["publishedLetters","approvedApplications","sourcePageReviewRows"])
  if(r[k]!=null&&!count(r[k]))throw Error("Invalid FDA source inventory count");
 return {
  checkedAt:r.checkedAt,publishedLetters:r.publishedLetters as number|null,
  approvedApplications:r.approvedApplications as number|null,sourcePageReviewRows:r.sourcePageReviewRows as number|null,
  independentlyVerifiedReviewCycles:r.independentlyVerifiedReviewCycles as number
 };
}
