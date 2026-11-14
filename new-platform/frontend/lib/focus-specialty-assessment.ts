/**
 * Read-only research intake for the canonical FOCUS exact-NCT roster.
 *
 * IMPORTANT: Mappings, dated source pointers and partial specialist-style notes
 * are not completed clinical adjudications, current FDA status checks, or
 * validated predictions. This queue is a reproducible, owner-only worklist
 * for phase-first, evidence-backed scientific assessment without outside approval.
 */
import focus from "../data/p3PostDataActive.json";
import {APPLICATION_CYCLES} from "./medical-intelligence-applications";
import {getSpecialtyProfile,getSpecialtyTasks} from "./medical-intelligence-specialty";
import {getFullSpecialistCase} from "./medical-intelligence-specialist-all";
import {FOCUS_FINAL_TRIAL_AUDIT} from "./focus-final-gate-checks";

export type SpecialtyCycleIntake={
  cycleId:string;drug:string;indication:string;applicationType:string;
  recordedStage:string;recordedGoal:string|null;sourceDate:string;sourceUrl:string;
  specialty:string|null;researchQuestions:number;
  partialCaseDimensions:number;sourceLinkedDimensions:number;
  specialistSignoff:false;clinicalAdjudicationComplete:false;
  externalReviewerRequired:false;ownerReviewStatus:"OWNER_NOT_REVIEWED";
};
export type TrialAssessmentIntake={
  ticker:string;nct:string;company:string;rosterAsOf:string;
  registryUrl:string;reportedRegulatorySource:string|null;
  recordedPdufaDate:string|null;
  reportedFilingStatus:string|null;
  phaseVerified:false;scientificAssessment:"INSUFFICIENT_VERIFIED_EVIDENCE";
  prediction:"ABSTAIN";certainty:"NOT_VALIDATED";
  independentlyVerifiedGates:0;
  externalReviewerRequired:false;ownerReviewStatus:"OWNER_NOT_REVIEWED";
  reviewRequiredGates:number;missingEvidenceGates:number;
  applications:SpecialtyCycleIntake[];
};
export function buildFocusSpecialtyAssessmentQueue():TrialAssessmentIntake[]{
  const audit=new Map(FOCUS_FINAL_TRIAL_AUDIT.rows.map(row=>[row.nct,row]));
  const seen=new Set<string>();
  return focus.records.map(row=>{
    if(!/^NCT\d{8}$/.test(row.nct)||seen.has(row.nct))
      throw new Error("FOCUS_SPECIALTY_INVALID_OR_DUPLICATE_NCT");
    seen.add(row.nct);
    const check=audit.get(row.nct);
    if(!check||check.ticker!==row.ticker)throw new Error("FOCUS_SPECIALTY_AUDIT_MISMATCH");
    const applications=APPLICATION_CYCLES.filter(cycle=>
      cycle.ticker===row.ticker&&cycle.ncts.includes(row.nct)
    ).map(cycle=>{
      const profile=getSpecialtyProfile(cycle.id);
      const partial=getFullSpecialistCase(cycle.id);
      const dimensions=partial?.dimensions??[];
      return {
        cycleId:cycle.id,drug:cycle.drug,indication:cycle.indication,
        applicationType:cycle.applicationType,recordedStage:cycle.stage,
        recordedGoal:cycle.reportedGoal,sourceDate:cycle.sourceDate,
        sourceUrl:cycle.sourceUrl,specialty:profile?.specialty??null,
        researchQuestions:getSpecialtyTasks(cycle.id).length,
        partialCaseDimensions:dimensions.length,
        sourceLinkedDimensions:dimensions.filter(x=>typeof x.sourceUrl==="string"&&/^https:\/\//.test(x.sourceUrl)).length,
        specialistSignoff:false as const,clinicalAdjudicationComplete:false as const,
        externalReviewerRequired:false as const,ownerReviewStatus:"OWNER_NOT_REVIEWED" as const
      };
    });
    return {
      ticker:row.ticker,nct:row.nct,company:row.company,
      rosterAsOf:focus.asOf,
      registryUrl:"https://clinicaltrials.gov/study/"+row.nct,
      reportedRegulatorySource:row.regulatoryUrl??null,
      recordedPdufaDate:row.recordedPdufaDate,
      reportedFilingStatus:row.fdaStatus??null,
      phaseVerified:false,
      scientificAssessment:"INSUFFICIENT_VERIFIED_EVIDENCE" as const,
      prediction:"ABSTAIN" as const,certainty:"NOT_VALIDATED" as const,
      independentlyVerifiedGates:0 as const,
      externalReviewerRequired:false as const,
      ownerReviewStatus:"OWNER_NOT_REVIEWED" as const,
      reviewRequiredGates:check.review,missingEvidenceGates:check.missing,
      applications
    };
  });
}
export const FOCUS_SPECIALTY_ASSESSMENT_QUEUE=buildFocusSpecialtyAssessmentQueue();
export const FOCUS_SPECIALTY_SUMMARY={
  rosterAsOf:focus.asOf,
  ncts:FOCUS_SPECIALTY_ASSESSMENT_QUEUE.length,
  tickers:new Set(FOCUS_SPECIALTY_ASSESSMENT_QUEUE.map(r=>r.ticker)).size,
  mappedApplicationCycles:APPLICATION_CYCLES.length,
  mappedNcts:FOCUS_SPECIALTY_ASSESSMENT_QUEUE.filter(r=>r.applications.length>0).length,
  partialClinicalDimensions:FOCUS_SPECIALTY_ASSESSMENT_QUEUE.flatMap(r=>r.applications)
    .filter((r,i,all)=>all.findIndex(other=>other.cycleId===r.cycleId)===i)
    .reduce((n,r)=>n+r.partialCaseDimensions,0),
  independentlyAdjudicatedTrials:0,
  ownerReviewedTrials:0,
  externalReviewerRequirements:0,
  validatedForecasts:0
} as const;
