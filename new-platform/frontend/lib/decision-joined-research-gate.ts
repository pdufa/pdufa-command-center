import {assessDecisionWithCompleteHistory,type CompleteHistoricalDecisionGate} from "./decision-complete-history-gate";
import {auditHistoricalSourceChronology,type HistoricalSourceRecord} from "./decision-historical-source-chronology";
import type {ResearchReadiness} from "./decision-research-readiness";
import {compareHistoricalPdufa,type AnalogueTarget,type HistoricalPdufaAnalogue} from "./decision-historical-analogues";
import type {HistoricalCoverageInput} from "./decision-historical-coverage";

/** Joined research gate. Each matched historical analogue must have independently reviewed,
 * cutoff-safe source chronology. No score or trading authorization is produced. */
export type JoinedDecisionResearchGate=CompleteHistoricalDecisionGate&{
 chronologyReviewed:number;
 chronologyRequired:number;
};
export function assessJoinedDecisionResearch(
 science:ResearchReadiness|null,
 outcome:ResearchReadiness|null,
 target:AnalogueTarget,
 history:HistoricalPdufaAnalogue[],
 coverage:HistoricalCoverageInput,
 chronology:Record<string,HistoricalSourceRecord[]>,
 now=new Date()
):JoinedDecisionResearchGate{
 const base=assessDecisionWithCompleteHistory(science,outcome,target,history,coverage,now);
 const issues=[...base.issues];
 let chronologyReviewed=0;
 const matched=compareHistoricalPdufa(target,history).matched;
 const chronologyRequired=matched.length;
 for(const row of matched){
  const id=row.programId;
  const sources=chronology[id];
  if(!sources?.length){issues.push(`Missing historical source chronology: ${id}`);continue;}
  const audits=sources.map(source=>{
   const audit=auditHistoricalSourceChronology(source);
   if(source.decisionAt!==row.decisionAt)audit.issues.push("Source decision timestamp differs from analogue");
   if(source.sourceUrl!==row.sourceUrl)audit.issues.push("Source URL differs from analogue");
   return audit;
  });
  if(audits.some(a=>a.issues.length)){
   for(const audit of audits)for(const issue of audit.issues)issues.push(`${id}: ${issue}`);
  }else if(sources.some(s=>s.predictionCutoff!==target.asOf)){
   issues.push(`${id}: Source cutoff differs from target cutoff`);
  }else chronologyReviewed++;
 }
 return {...base,status:issues.length?"NOT_READY":"EVIDENCE_READY_FOR_REVIEW",issues,
  chronologyReviewed,chronologyRequired};
}
