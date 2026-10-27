import type {AssessmentDetail, AssessmentStage} from "./candidate-assessments";
import {candidateAssessmentToScienceReadiness, candidateAssessmentToOutcomeReadiness} from "./decision-assessment-adapter";
import {assessScienceOutcomeReadiness, type ResearchReadiness} from "./decision-research-readiness";
import {assessJoinedMainDecision, type MainEvidence} from "./decision-joined-main-gate";
import type {AnalogueTarget, HistoricalPdufaAnalogue} from "./decision-historical-analogues";
import type {HistoricalCoverageInput} from "./decision-historical-coverage";
import type {HistoricalSourceRecord} from "./decision-historical-source-chronology";
import type {HistoricalEvidenceRow} from "./decision-historical-evidence";
import {assessCalibrationCohortAtCutoff} from "./decision-calibration-cohort-gate";
import {evaluateChronologicalCalibration, type ChronologicalCalibrationPlan, type ChronologicalCalibrationRow} from "./decision-calibration-holdout";
import {auditOutcomeStatus, type OutcomeStatus} from "./science-outcome-gates";
import {researchReadiness} from "./research-readiness";
import {auditScienceInvestigation,type ScienceInvestigation,type ScienceInvestigationAudit} from "./decision-science-investigation";

export type DecisionIdentity = {exactKey:string; programId:string; trialId:string; ticker:string; stage:AssessmentStage};
/** A separate reviewed manifest is required. Candidate scores and aggregate archive counts
 * cannot populate these records or certify an OUTCOME model. */
export type ReviewedDecisionEvidence = {
  identity:DecisionIdentity;
  scienceDossier?:ScienceInvestigation|null;
  outcomeApplicationNumber?:string|null;
  mainCompanyCik?:string|null;
  science:ResearchReadiness|null; outcome:ResearchReadiness|null;
  target:AnalogueTarget; history:HistoricalPdufaAnalogue[]; coverage:HistoricalCoverageInput;
  chronology:Record<string, HistoricalSourceRecord[]>; main:MainEvidence|null;
  calibrationRows:HistoricalEvidenceRow[];
  holdout:{training:ChronologicalCalibrationRow[]; rows:ChronologicalCalibrationRow[]; plan:ChronologicalCalibrationPlan}|null;
};
export type DecisionWorkstream = {
  status:"NOT_READY"|"RESEARCH_REVIEW_REQUIRED";
  stages:{name:string; status:string; issues:string[]}[];
  historicalSource:OutcomeStatus|null;
  historicalMatches:number;
  sourceIssues:string[];
  issues:string[];
  modelValidated:false;
  probability:null;
  tradeAuthorized:false;
  scienceInvestigation:ScienceInvestigationAudit;
  prediction:{
    predictedOutcome:"INSUFFICIENT_EVIDENCE";
    approvalProbability:null;
    nonapprovalProbability:null;
    confidence:null;
    readyForReliablePrediction:false;
    reasons:string[];
  };
};

/** Compose every evidence gate without changing membership, restrictions, scores or FS/FA.
 * Even a complete manifest produces only a research review, never a validated prediction. */
export function assessDecisionWorkstream(identity:DecisionIdentity, detail:AssessmentDetail|null,
  historicalSource:unknown=null, mainSource:unknown=null,
  reviewed:ReviewedDecisionEvidence|null=null, now=new Date()):DecisionWorkstream {
  const identityIssues:string[]=[];
  if (!identity.exactKey || !/^PDUFA-\d{6,}$/.test(identity.programId)
      || !/^NCT\d{8}$/.test(identity.trialId) || !/^[A-Z][A-Z0-9.-]{0,9}$/.test(identity.ticker)
      || !["PIPELINE", "GEM_JR", "GEM"].includes(identity.stage)) identityIssues.push("Exact program, trial, ticker and stage identity required");
  const matchedDetail=detail && detail.id===identity.exactKey && detail.programId===identity.programId
    && detail.nctId===identity.trialId ? detail : null;
  if(detail && !matchedDetail) identityIssues.push("Candidate assessment identity differs from the selected trial");
  if(reviewed && (Object.keys(identity).some(k=>reviewed.identity[k as keyof DecisionIdentity]!==identity[k as keyof DecisionIdentity])
      || reviewed.target.programId!==identity.programId
      || [reviewed.science,reviewed.outcome].some(r=>r && (r.programId!==identity.programId || r.trialId!==identity.trialId))
      || reviewed.main && (reviewed.main.programId!==identity.programId || reviewed.main.ticker!==identity.ticker))) {
    identityIssues.push("Reviewed evidence differs from the selected program, trial or ticker");
  }
  // Do not evaluate or display another trial's manifest, even as individual ready stages.
  const evidence=identityIssues.length?null:reviewed;
  const investigation=auditScienceInvestigation(evidence?.scienceDossier??null,identity,evidence?.target.asOf??matchedDetail?.asOf??"");
  const science=investigation.readiness ?? candidateAssessmentToScienceReadiness(matchedDetail);
  const outcome=evidence?.outcome ?? candidateAssessmentToOutcomeReadiness(matchedDetail);
  const readiness=assessScienceOutcomeReadiness(science,outcome,now);
  const scienceIssues=[...readiness.issues.filter(s=>s.startsWith("SCIENCE")),...investigation.issues];
  if(evidence?.science&&investigation.readiness&&["programId","trialId","asOf","reviewedLevels","requiredLevels","status","sourceStatus","criticalFindingsResolved"].some(k=>evidence.science![k as keyof ResearchReadiness]!==investigation.readiness![k as keyof ResearchReadiness]))
    scienceIssues.push("SCIENCE: summary disagrees with source-cited investigation");
  if(evidence?.scienceDossier&&(!evidence.scienceDossier.fdaApplication||evidence.scienceDossier.indication.trim().toLowerCase()!==evidence.target.indication.trim().toLowerCase()))
    scienceIssues.push("SCIENCE: FDA application or indication identity has not been reconciled");
  const outcomeIssues=readiness.issues.filter(s=>s.startsWith("OUTCOME"));
  if(evidence&&(!evidence.scienceDossier?.fdaApplication||evidence.outcomeApplicationNumber!==evidence.scienceDossier.fdaApplication))
    outcomeIssues.push("OUTCOME: declared FDA application identity differs from the scientific dossier or is missing");
  const sourceIssues:string[]=[];
  let source:OutcomeStatus|null=null;
  if(historicalSource!=null) {
    try { source=auditOutcomeStatus(historicalSource); }
    catch { sourceIssues.push("Historical FDA source response could not be verified; counts withheld"); }
  } else sourceIssues.push("Historical FDA source audit unavailable");
  // The existing MAIN endpoint is a separate source connection, not the historical market audit.
  let mainConnected=false;
  if(mainSource!=null && identity.stage!=="PIPELINE") {
    try { researchReadiness(mainSource,identity.programId,identity.exactKey,identity.stage); mainConnected=true; }
    catch { sourceIssues.push("MAIN source identity, stage or research boundary could not be verified"); }
  }
  const joined=evidence ? assessJoinedMainDecision(science,outcome,evidence.target,evidence.history,
    evidence.coverage,evidence.chronology,evidence.main,now) : null;
  const historyIssues=joined ? joined.issues.filter(s=>!readiness.issues.includes(s) && !s.startsWith("MAIN:"))
    : ["Reviewed close analogues, source chronology and complete historical denominator are not connected"];
  const mainIssues=joined?.mainIssues ?? ["Independently audited MAIN evidence is not connected"];
  if(evidence&&(!evidence.scienceDossier?.companyCik||evidence.mainCompanyCik!==evidence.scienceDossier.companyCik))
    mainIssues.push("MAIN: declared company CIK differs from the scientific dossier or is missing");
  const calibration=evidence ? assessCalibrationCohortAtCutoff(evidence.calibrationRows,evidence.target.asOf) : null;
  const holdout=evidence?.holdout ? evaluateChronologicalCalibration(evidence.holdout.training,evidence.holdout.rows,evidence.holdout.plan) : null;
  const calibrationIssues=[...(calibration?.issues ?? ["Independent point-in-time historical calibration is not connected"]),
    ...(holdout?.issues ?? ["A frozen chronological holdout is not connected"])];
  if(evidence?.holdout && !(Date.parse(evidence.holdout.plan.evaluatedAt)<=Date.parse(evidence.target.asOf)))
    calibrationIssues.push("Holdout evaluation is unavailable at the target cutoff");
  if(holdout?.holdout && holdout.holdout.improvementVsTrainingBaseline<=0)
    calibrationIssues.push("No holdout improvement over the frozen training baseline");
  const issues=[...identityIssues,...readiness.issues,...scienceIssues,...outcomeIssues,...historyIssues,...mainIssues,...calibrationIssues];
  const ready=identityIssues.length===0 && joined?.status==="EVIDENCE_READY_FOR_REVIEW"
    && calibration?.status==="RESEARCH_ONLY" && holdout?.status==="RESEARCH_ONLY" && calibrationIssues.length===0
    &&scienceIssues.length===0&&outcomeIssues.length===0&&mainIssues.length===0;
  return {
    status:ready?"RESEARCH_REVIEW_REQUIRED":"NOT_READY",
    stages:[
      ...(identityIssues.length?[{name:"Identity",status:"NOT_READY",issues:identityIssues}]:[]),
      {name:"SCIENCE",status:scienceIssues.length?"NOT_READY":"EVIDENCE_READY_FOR_REVIEW",issues:scienceIssues},
      {name:"Historical FDA",status:historyIssues.length?"NOT_READY":"EVIDENCE_READY_FOR_REVIEW",issues:historyIssues},
      {name:"OUTCOME",status:outcomeIssues.length?"NOT_READY":"EVIDENCE_READY_FOR_REVIEW",issues:outcomeIssues},
      {name:"MAIN",status:mainIssues.length?(mainConnected?"SOURCE_CONNECTED_REVIEW_INCOMPLETE":"NOT_READY"):"EVIDENCE_READY_FOR_REVIEW",issues:mainIssues},
      {name:"Calibration",status:calibrationIssues.length?"NOT_READY":"RESEARCH_ONLY",issues:calibrationIssues},
    ],
    historicalSource:source,historicalMatches:identityIssues.length?0:joined?.historicalMatches ?? 0,
    sourceIssues,issues:[...new Set(issues)],modelValidated:false,probability:null,tradeAuthorized:false,scienceInvestigation:investigation,
    // Research prerequisite completion and fixture metrics cannot activate a
    // predictive model. Abstention is distinct from the historical FDA label.
    prediction:{predictedOutcome:"INSUFFICIENT_EVIDENCE",approvalProbability:null,
      nonapprovalProbability:null,confidence:null,readyForReliablePrediction:false,
      reasons:[...new Set(["Independent model validation for reliable FDA predictions is unavailable",...issues])]},
  };
}
