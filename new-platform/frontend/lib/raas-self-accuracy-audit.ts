/** Evidence-gated self-audit of RAAS reliability, not a prediction or an accuracy grade.
 * A source-readiness check and a legacy binary benchmark cannot certify
 * an issuer-disjoint RAAS stock-return score or a three-way FDA forecast.
 */
import type {RaasReadinessReport} from "./raas-readiness-scan";
import type {RaasInstallationStatus} from "./raas-installation-gates";

export type FDAAccuracyEvidence={
 readonly scope:string;readonly classes:readonly string[];
 readonly legacyRetrospectiveCases:number;readonly legacyCorrect:number;
 readonly legacyRetrospectiveAccuracyPct:number;
 readonly alwaysApproveCorrect:number;readonly alwaysApproveRetrospectiveAccuracyPct:number;
 readonly historicalExtensions:number;
 readonly predecisionThreeWayIndependentlyVerifiedForecasts:number;
 readonly certifiedFDAThreeWayPredictionAccuracyPct:number|null;
 readonly approvedThreeWayFDAOutcomeModel:boolean;
 readonly approvedRaasMetricCalibrations:number;
 readonly completeEligibleCohortIndependentlyVerified:boolean;
 readonly independentOutcomeAdjudicationComplete:boolean;
};
export type AccuracyProofGate={
 readonly id:string;readonly name:string;readonly achieved:number;
 readonly required:number;readonly unit:string;readonly passed:boolean;
 readonly explanation:string;
};
export type RaasSelfAccuracyAudit={
 readonly scope:"RAAS_SURVEY_ACCURACY_SELF_AUDIT";
 readonly status:"NOT_MEASURABLE"|"EVIDENCE_UNDER_REVIEW";
 readonly numericAccuracyRating:null;
 readonly independentReturnAccuracyPct:null;
 readonly independentFDAThreeWayAccuracyPct:null;
 readonly raasGatesPassed:number;readonly raasGatesRequired:5;
 readonly raasGates:readonly AccuracyProofGate[];
 readonly fdaProspectiveGate:AccuracyProofGate;
 readonly retrospectiveBaselineDifferencePctPoints:number;
 readonly retrospectiveDifferenceInCorrectCalls:number;
 readonly warning:string;
};
function count(x:number):boolean{return Number.isSafeInteger(x)&&x>=0;}
function proofGate(id:string,name:string,achieved:number,required:number,unit:string,
 explanation:string,independentlyVerified=true):AccuracyProofGate{
 if(!count(achieved)||!count(required)||required===0)
  throw Error("RAAS_SELF_AUDIT_GATE_INPUT_INVALID:"+id);
 return {id,name,achieved,required,unit,
  passed:independentlyVerified&&achieved>=required,explanation};
}
export function auditRaasSurveyAccuracy(
 report:RaasReadinessReport,installation:RaasInstallationStatus,
 fda:FDAAccuracyEvidence
):RaasSelfAccuracyAudit{
 const s=report.summary;
 const topGate=installation.gates.find(g=>g.id==="top-calibration");
 const bottomGate=installation.gates.find(g=>g.id==="bottom-calibration");
 if(!topGate||!bottomGate)throw Error("RAAS_SELF_AUDIT_MISSING_CALIBRATION_GATES");
 if(report.scope!=="RAAS_EXECUTED_READINESS_AUDIT" ||
    report.finalScoring!=="NOT_VALIDATED" ||
    report.metrics.length!==60 ||
    report.categories.length!==12 ||
    s.metricsInspected!==60 ||
    s.preMetricsInspected!==30 || s.postMetricsInspected!==30 ||
    new Set(report.metrics.map(m=>m.stage+"|"+m.id)).size!==60 ||
    report.metrics.filter(m=>m.approvedCalibration).length!==s.approvedMetricCalibrations ||
    report.metrics.filter(m=>m.historicalReviewEligible).length!==s.reviewEligibleMetrics ||
    installation.totalGates!==6 ||
    installation.sourceYears.length!==2 ||
    installation.eligibleSourceYears!==installation.sourceYears.filter(y=>y.verified).length ||
    installation.gates.find(g=>g.id==="historical-trades")?.achieved!==s.historicalAcceptedCases ||
    topGate.achieved+bottomGate.achieved!==s.approvedMetricCalibrations)
  throw Error("RAAS_SELF_AUDIT_SOURCE_INCONSISTENT");
 if(fda.scope!=="RAAS_FDA_THREE_WAY_DECISION_ACCURACY_SITE_SNAPSHOT" ||
    !Array.isArray(fda.classes) || fda.classes.join("|")!=="PASS|CRL|EXTENSION" ||
    ![fda.legacyRetrospectiveCases,fda.legacyCorrect,fda.alwaysApproveCorrect,
      fda.historicalExtensions,fda.predecisionThreeWayIndependentlyVerifiedForecasts,
      fda.approvedRaasMetricCalibrations].every(count) ||
    fda.legacyRetrospectiveCases===0 ||
    fda.legacyCorrect>fda.legacyRetrospectiveCases ||
    fda.alwaysApproveCorrect>fda.legacyRetrospectiveCases ||
    Math.abs(100*fda.legacyCorrect/fda.legacyRetrospectiveCases-
      fda.legacyRetrospectiveAccuracyPct)>0.02 ||
    Math.abs(100*fda.alwaysApproveCorrect/fda.legacyRetrospectiveCases-
      fda.alwaysApproveRetrospectiveAccuracyPct)>0.02 ||
    fda.approvedRaasMetricCalibrations!==s.approvedMetricCalibrations)
  throw Error("RAAS_SELF_AUDIT_FDA_SNAPSHOT_INCONSISTENT");
 const raasGates=[
  proofGate("metric-catalog","60 stage-specific metric definitions",s.metricsInspected,60,"definitions",
   "Design specification only. Completing it does not measure accuracy."),
  proofGate("historical-census","Independent full 2024 and 2025 event censuses",
   installation.eligibleSourceYears,2,"audited years",
   "Original dates and complete eligible denominators must be verified."),
  proofGate("return-cases","Accepted historical event-window return cases",
   s.historicalAcceptedCases,60,"accepted cases",
   "Returns must be point-in-time, corporate-action adjusted and independent."),
  proofGate("issuer-disjoint-holdout","Metrics passing issuer-disjoint walk-forward holdouts",
   s.reviewEligibleMetrics,60,"eligible metrics",
   "Training and later test issuers must not overlap."),
  proofGate("approved-calibrations","Metrics with approved historical scoring calibration",
   s.approvedMetricCalibrations,60,"approved metrics",
   "A raw source link or missing metric cannot be assigned a numerical grade.")
 ] as const;
 const fdaProspectiveGate=proofGate(
  "fda-three-way","Independently verified prospective PASS / CRL / EXTENSION forecasts",
  fda.predecisionThreeWayIndependentlyVerifiedForecasts,30,"frozen forecasts",
  "Separate FDA target; class counts, immutable predecision receipts, official outcome labels, calibration and independent adjudication are also required.",
  // A site snapshot contains no independent per-class recall or receipt proof.
  // It can never alone certify this downstream validation gate.
  false
 );
 const raasGatesPassed=raasGates.filter(g=>g.passed).length;
 return {
  scope:"RAAS_SURVEY_ACCURACY_SELF_AUDIT",
  status:s.historicalAcceptedCases===0&&s.approvedMetricCalibrations===0&&
    fda.predecisionThreeWayIndependentlyVerifiedForecasts===0
    ?"NOT_MEASURABLE":"EVIDENCE_UNDER_REVIEW",
  numericAccuracyRating:null,independentReturnAccuracyPct:null,
  independentFDAThreeWayAccuracyPct:null,
  raasGatesPassed,raasGatesRequired:5,raasGates,fdaProspectiveGate,
  retrospectiveBaselineDifferencePctPoints:Math.round(
   (fda.legacyCorrect-fda.alwaysApproveCorrect)*10000/fda.legacyRetrospectiveCases)/100,
  retrospectiveDifferenceInCorrectCalls:fda.legacyCorrect-fda.alwaysApproveCorrect,
  warning:"This is a proof-completeness assessment, not an empirical accuracy grade. The selected legacy binary retrospective benchmark cannot validate PASS / CRL / EXTENSION or RAAS stock-return predictions."
 };
}
