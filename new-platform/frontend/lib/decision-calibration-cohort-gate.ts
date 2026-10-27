import {calibrateAuditedHistory} from "./decision-audited-calibration";
import type {HistoricalEvidenceRow} from "./decision-historical-evidence";

/** A historical cohort may be reviewed only when every decision predates the target cutoff.
 * Self-declared source verification is not independent validation or trading authorization. */
export function assessCalibrationCohortAtCutoff(rows:HistoricalEvidenceRow[],cutoff:string,minimum=30){
 const audit=calibrateAuditedHistory(rows,minimum);
 const issues=[...audit.issues];
 const time=Date.parse(cutoff);
 if(!Number.isFinite(time))issues.push("Invalid target cutoff");
 for(const row of rows){
  const decided=Date.parse(row.decisionAt);
  if(!Number.isFinite(decided)||!Number.isFinite(time)||decided>=time){
   issues.push("Historical outcome unavailable at target cutoff: "+row.programId);
  }
 }
 if(audit.status!=="RESEARCH_ONLY"||!audit.calibration)issues.push("Historical calibration unavailable");
 else if((audit.calibration.improvementVsBaseline??0)<=0)
  issues.push("No improvement over historical cohort baseline");
 return {status:issues.length?"NOT_READY" as const:"RESEARCH_ONLY" as const,
  issues,calibration:audit.calibration,tradeAuthorized:false as const};
}
