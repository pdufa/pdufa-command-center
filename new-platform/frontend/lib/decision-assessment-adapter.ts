import type {AssessmentDetail} from "./candidate-assessments";
import type {ResearchReadiness} from "./decision-research-readiness";
/** Existing 7-category candidate scores are not the independent 20-level SCIENCE review. */
export function candidateAssessmentToScienceReadiness(detail:AssessmentDetail|null):ResearchReadiness|null{
 if(!detail)return null;
 const id=typeof detail.programId==="string"?detail.programId:"";
 const trialId=typeof detail.nctId==="string"?detail.nctId:"";
 const asOf=typeof detail.asOf==="string"?detail.asOf:"";
 return {programId:id,trialId,asOf,status:"PARTIAL",sourceStatus:"UNVERIFIED",reviewedLevels:0,requiredLevels:20,criticalFindingsResolved:false};
}
/** No independent OUTCOME records are present in the candidate-assessment schema. */
export function candidateAssessmentToOutcomeReadiness(_detail:AssessmentDetail|null):null{return null;}
