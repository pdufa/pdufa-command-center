import {assessDecisionWithHistory,type DecisionHistoricalGate} from "./decision-historical-gate";
import {auditHistoricalOutcomeCoverage,type HistoricalCoverageInput} from "./decision-historical-coverage";
import type {ResearchReadiness} from "./decision-research-readiness";
import type {AnalogueTarget,HistoricalPdufaAnalogue} from "./decision-historical-analogues";
/** A review-only composite gate: complete historical denominator required alongside matched analogues. */
export type CompleteHistoricalDecisionGate=DecisionHistoricalGate&{historicalCoveragePct:number|null};
export function assessDecisionWithCompleteHistory(science:ResearchReadiness|null,outcome:ResearchReadiness|null,target:AnalogueTarget,history:HistoricalPdufaAnalogue[],coverage:HistoricalCoverageInput,now=new Date()):CompleteHistoricalDecisionGate{
 const base=assessDecisionWithHistory(science,outcome,target,history,now);
 const audit=auditHistoricalOutcomeCoverage(coverage);
 const issues=[...base.issues,...audit.issues];
 if(coverage.asOf!==target.asOf)issues.push("Historical denominator and target cutoffs differ");
 return {status:issues.length?"NOT_READY":"EVIDENCE_READY_FOR_REVIEW",issues,historicalMatches:base.historicalMatches,historicalCoveragePct:audit.coveragePct};
}
