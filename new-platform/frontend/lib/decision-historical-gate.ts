import {assessScienceOutcomeReadiness,type ResearchReadiness} from "./decision-research-readiness";
import {compareHistoricalPdufa,type AnalogueTarget,type HistoricalPdufaAnalogue} from "./decision-historical-analogues";
/** Research-only gate. Historical comparison is required and never overrides SCIENCE or OUTCOME deficiencies. */
export type DecisionHistoricalGate={status:"NOT_READY"|"EVIDENCE_READY_FOR_REVIEW";issues:string[];historicalMatches:number};
export function assessDecisionWithHistory(science:ResearchReadiness|null,outcome:ResearchReadiness|null,target:AnalogueTarget,history:HistoricalPdufaAnalogue[],now=new Date()):DecisionHistoricalGate{
 const readiness=assessScienceOutcomeReadiness(science,outcome,now);
 const analogues=compareHistoricalPdufa(target,history);
 const issues=[...readiness.issues,...analogues.issues];
 if(science&&science.programId!==target.programId)issues.push("SCIENCE/target program mismatch");
 if(outcome&&outcome.programId!==target.programId)issues.push("OUTCOME/target program mismatch");
 if(science&&science.asOf!==target.asOf)issues.push("SCIENCE/target cutoff mismatch");
 if(outcome&&outcome.asOf!==target.asOf)issues.push("OUTCOME/target cutoff mismatch");
 if(Date.parse(target.asOf)>now.getTime()+300000)issues.push("Historical cutoff cannot be in future");
 return {status:issues.length?"NOT_READY":"EVIDENCE_READY_FOR_REVIEW",issues,historicalMatches:analogues.matched.length};
}
