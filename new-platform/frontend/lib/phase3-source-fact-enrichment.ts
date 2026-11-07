import peerEvidence from "../data/phase3PeerReviewedClinicalEvidence20261106.json";
import {activeOfficialRegistryRecord} from "./phase3-active-official-registry";

/**
 * Exact-trial public outcomes and explicit registry ABSENCE statements are
 * documentary answers only. They must never be interpreted as 0%/100%
 * drug success probabilities, safety assessments, grades or future forecasts.
 */
export const PHASE3_PEER_FACT_COUNT=peerEvidence.facts.length;
const bySlot=new Map(peerEvidence.facts.map(r=>[r.nctId+"#"+r.question,r] as const));
export function phase3PeerReviewedFact(nctId:string,question:number){
 return bySlot.get(nctId+"#"+question)??null;
}
export function phase3PeerEvidenceIntegrity(activeIds:ReadonlySet<string>):boolean{
 return peerEvidence.schemaVersion===1&&peerEvidence.asOf==="2026-11-06"&&
  peerEvidence.facts.length===18&&bySlot.size===18&&
  peerEvidence.facts.every(f=>activeIds.has(f.nctId)&&
   [20,21,23,24,28].includes(f.question)&&f.status==="SOURCE_FACT_ONLY"&&
   f.clinicalRating===null&&f.raasScore===null&&
   f.sourceDate<="2026-11-06"&&/^\d{4}-\d{2}-\d{2}$/.test(f.sourceDate)&&
   f.sourceUrl.startsWith("https://")&&f.evidence.length>60);
}
type RegistryBinaryFact={status:"SOURCE_FACT_ONLY";evidence:string;sourceUrl:string};
export function phase3RegistryBinaryFact(nctId:string,question:number):RegistryBinaryFact|null{
 if(question!==11&&question!==27)return null;
 const r=activeOfficialRegistryRecord(nctId);
 if(!r||r.sourceState!=="FETCHED"||!r.interventionNames||
  !r.registryUrl.endsWith(nctId))return null;
 if(question===11&&!r.comparators){
  return {status:"SOURCE_FACT_ONLY",sourceUrl:r.registryUrl,
   evidence:"Checked official ClinicalTrials.gov registry snapshot lists the interventions "+
    "but no arm explicitly tagged PLACEBO_COMPARATOR, ACTIVE_COMPARATOR, "+
    "SHAM_COMPARATOR or NO_INTERVENTION in the arm-type field. "+
    "This is a documented coding/label absence, NOT proof that there is no control, "+
    "no comparison, inadequate trial design, or a negative efficacy outcome."};
 }
 if(question===27&&!/\bplacebo\b/i.test(r.interventionNames)){
  return {status:"SOURCE_FACT_ONLY",sourceUrl:r.registryUrl,
   evidence:"The checked official intervention-name list does not contain the explicit word "+
    "'placebo'. Other branded or active control names and disguised arms may exist; "+
    "this is only the answer to whether 'placebo' is explicitly named, not a "+
    "prediction about efficacy or double-blind design."};
 }
 return null;
}
