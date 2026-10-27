import {auditHistoricalEvidence,type HistoricalEvidenceRow} from "./decision-historical-evidence";
import {summarizeHistoricalCalibration,type CalibrationSummary} from "./decision-calibration";
/** Only audited point-in-time rows may enter calibration. Metadata is not independent proof. */
export type AuditedCalibration={status:"NOT_READY"|"RESEARCH_ONLY";issues:string[];calibration:CalibrationSummary|null};
export function calibrateAuditedHistory(rows:HistoricalEvidenceRow[],minimum=30):AuditedCalibration{
 const audit=auditHistoricalEvidence(rows,minimum);
 if(audit.status!=="READY_FOR_INDEPENDENT_REVIEW")return {status:"NOT_READY",issues:audit.issues,calibration:null};
 const predictions=rows.map(r=>({programId:r.programId,predictedAt:r.predictedAt,decisionAt:r.decisionAt,approvalProbability:r.probability,approved:r.approved,cohort:"audited-historical"}));
 const calibration=summarizeHistoricalCalibration(predictions,minimum);
 if(calibration.status!=="RESEARCH_ONLY")return {status:"NOT_READY",issues:calibration.issues,calibration:null};
 return {status:"RESEARCH_ONLY",issues:["Review flags and URLs are self-declared; independently verify underlying records before using estimates"],calibration};
}
