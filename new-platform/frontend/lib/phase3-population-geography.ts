import snapshot from "../data/phase3PopulationGeography20261106.json";

export const populationGeographyRecords=snapshot.records;
const byNct=new Map(populationGeographyRecords.map(r=>[r.nctId,r]));
export function populationGeographyRecord(nctId:string){return byNct.get(nctId);}
export function populationGeographyIntegrity(ncts:Set<string>){
 return byNct.size===populationGeographyRecords.length&&snapshot.censusTrials===ncts.size&&
  populationGeographyRecords.every(r=>ncts.has(r.nctId)&&r.sourceState==="FETCHED"&&
   r.sourceUrl===`https://clinicaltrials.gov/study/${r.nctId}`&&
   /^\d{4}-\d{2}-\d{2}$/.test(r.publicationDate)&&r.publicationDate<=snapshot.asOf.slice(0,10)&&
   /^[a-f0-9]{64}$/.test(r.batchSha256)&&r.criticalReviewStatus==="NOT_YET_REVIEWED"&&
   Number.isInteger(r.registeredLocationCount)&&r.registeredLocationCount>=0);
}
export function populationGeographyFact(nctId:string,question:number){
 const r=byNct.get(nctId);if(!r)return null;
 let evidence="";
 if(question===6&&(r.minimumAge||r.maximumAge||r.eligibilityCriteria)){
  evidence=`Registered eligibility, not observed participant demographics: ${r.conditions.join("; ")}. `+
   `Minimum age: ${r.minimumAge||"not specified"}; maximum age: ${r.maximumAge||"not specified"}; `+
   `sex eligibility: ${r.sex||"not specified"}; healthy volunteers: ${r.healthyVolunteers===null?"not specified":String(r.healthyVolunteers)}. `+
   (r.eligibilityCriteria?`Criteria excerpt: ${r.eligibilityCriteria.slice(0,750)}${r.eligibilityCriteria.length>750?" [excerpt; full criteria at source]":""}. `:"")+
   "Generalizability and eligibility adequacy have NOT been assessed.";
 }
 if(question===26&&r.registeredLocationCount>0){
  evidence=`Registry lists ${r.registeredLocationCount} location entries; `+
   `countries: ${r.countries.join("; ")||"not specified"}. `+
   "Registered locations are not confirmed recruiting sites, actual enrollment by country, or evidence of population representativeness. Scientific interpretation is pending.";
 }
 return evidence?{classification:"DOCUMENTED_SOURCE_FACT",evidence,sourceUrl:r.sourceUrl,
  publicationDate:r.publicationDate,assessmentNumber:question,nctId,
  evidenceScope:r.scope,criticalReviewStatus:r.criticalReviewStatus}:null;
}
