/**
 * The 23 FDA application-specific subspecialty research dossiers.
 * Every entry is PARTIAL_SOURCED_RESEARCH, never physician reviewed or
 * a final prediction. A study may legitimately contribute to more than one
 * separate application but data are not automatically transferred to a
 * different indication, dose or formulation.
 */
import {APPLICATION_CYCLES} from "./medical-intelligence-applications";
import {SPECIALIST_CASES,type SpecialistCase} from "./medical-intelligence-specialist-casebook";
import {EXPANDED_SPECIALIST_CASES} from "./medical-intelligence-specialist-expanded";
import {SPECIALIST_WAVE_ONE} from "./medical-intelligence-specialist-wave-one";
import {SPECIALIST_WAVE_TWO} from "./medical-intelligence-specialist-wave-two";
export const ALL_SPECIALIST_CASES:readonly SpecialistCase[]=[
 ...SPECIALIST_CASES,
 ...EXPANDED_SPECIALIST_CASES,
 ...SPECIALIST_WAVE_ONE,
 ...SPECIALIST_WAVE_TWO
];
export function getFullSpecialistCase(cycleId:string):SpecialistCase|null{
 return ALL_SPECIALIST_CASES.find(c=>c.cycleId===cycleId)||null;
}
export type SpecialistDepthCoverage={
 cycleId:string;
 clinicalDimensions:number;
 sourceLinkedDimensions:number;
 clinicalStatus:"PARTIAL_SOURCED_RESEARCH"|"NOT_YET_RESEARCHED";
 completedClinicalAdjudication:false;
 completedPhysicianSignoff:false;
};
export function getSpecialistDepthCoverage():SpecialistDepthCoverage[]{
 return APPLICATION_CYCLES.map(a=>{
  const c=getFullSpecialistCase(a.id);
  return {
   cycleId:a.id,
   clinicalDimensions:c?.dimensions.length??0,
   sourceLinkedDimensions:c?.dimensions.filter(d=>typeof d.sourceUrl==="string"&&/^https:\/\//.test(d.sourceUrl)).length??0,
   clinicalStatus:c?"PARTIAL_SOURCED_RESEARCH":"NOT_YET_RESEARCHED",
   completedClinicalAdjudication:false,
   completedPhysicianSignoff:false
  };
 });
}
