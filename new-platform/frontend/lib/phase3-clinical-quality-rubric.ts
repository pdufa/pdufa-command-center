/** MAIN Phase III pilot: method-specific *clinical quality rubric framework*.
 * A 0–5 grade is not assigned from public aggregates alone: each item needs
 * source-versioned independent review and a signed authoritative ledger event.
 * This module reports completion of specific verification steps and the
 * predeclared 0–5 interpretive anchors. It never writes or signs a grade.
 */
import type {QuantitativeResearchReport} from "./acacia-quantitative-science";

export type CheckState="DOCUMENTED_PUBLIC"|"INDEPENDENTLY_UNVERIFIED"|"UNRESOLVED";
export type EvidenceCheck={id:string;label:string;state:CheckState;sourceUrl:string|null;why:string};
export type RatingBand={grade:0|1|2|3|4|5;meaning:string};
export type ClinicalMethodRubric={
  assessmentId:"5.1"|"5.3";methodIndex:12|19;methodName:string;rubricVersion:"MAIN_PHASE3_METHOD_GRADE_RUBRIC_V1";
  requirements:EvidenceCheck[];
  gradeBands:RatingBand[];
  documentedPublicChecks:number;requirementsTotal:6;
  eligibility:"NOT_ELIGIBLE_REQUIRES_INDEPENDENT_REVIEW";
  numericGrade:null;confidenceRating:null;officialGrade:null;reviewerSignature:null;
  sourceSnapshotAsOf:string;fdaPrediction:"ABSTAIN";limitations:string[];
};
export type RubricCoverage={
  schema:"MAIN_PHASE3_METHOD_RUBRIC_READINESS_V1";nct:"NCT06081894";
  methods:[ClinicalMethodRubric,ClinicalMethodRubric];
  candidateMethodPositionsWithResearch:5;
  sourceMappedPositions:18;unmappedMethodPositions:782;
  clinicalMethodGradesWritten:0;fdaPrediction:"ABSTAIN";
};
const PUBLICATION="https://pubmed.ncbi.nlm.nih.gov/42663312/";
const SECONDARY="https://pmc.ncbi.nlm.nih.gov/articles/PMC13674601/";
const SEC="https://www.sec.gov/Archives/edgar/data/1061983/000119312526447408/cytk-20260930.htm";
const bands={
  efficacy:[
    "Independently reviewed original analyses invalidate the prespecified primary result.",
    "Confirmed material statistical flaw undermines the pivotal estimate.",
    "Reviewed conflicting methods or estimands materially weaken the result.",
    "Primary estimate survives required reviews but significant limitations remain.",
    "Prespecified primary and sensitivity estimates agree; clinically relevant magnitude independently supported.",
    "Robust prespecified estimates and external/independent evidence corroborate exceptional consistency."
  ],
  safety:[
    "Reproduced original event accounting is materially invalid and cannot support a safety evaluation.",
    "Confirmed severe source-accounting errors or material unresolved clinical coding defects.",
    "Independent review reconciles some data but confirms material residual discrepancies.",
    "Event counts and populations are reconciled with transparent remaining limitations.",
    "Complete original event datasets, exposure, causality and temporal analyses are independently reproducible.",
    "Original, independent and external safety evidence are consistent across populations and sensitivity checks."
  ]
};
const gradeBands=(a:readonly string[]):RatingBand[]=>a.map((meaning,i)=>({
  grade:i as RatingBand["grade"],meaning
}));
function check(id:string,label:string,state:CheckState,sourceUrl:string|null,why:string):EvidenceCheck{
  return {id,label,state,sourceUrl,why};
}
function makeRubric(
  assessmentId:"5.1"|"5.3",methodIndex:12|19,methodName:string,
  requirements:EvidenceCheck[],anchorText:string[],asOf:string,limitations:string[]
):ClinicalMethodRubric|null{
  if(requirements.length!==6||new Set(requirements.map(x=>x.id)).size!==6||
    anchorText.length!==6||requirements.some(x=>
      x.state==="DOCUMENTED_PUBLIC"?!x.sourceUrl||!x.sourceUrl.startsWith("https://"):
      x.sourceUrl!==null))return null;
  return {
    assessmentId,methodIndex,methodName,rubricVersion:"MAIN_PHASE3_METHOD_GRADE_RUBRIC_V1",
    requirements,gradeBands:gradeBands(anchorText),
    documentedPublicChecks:requirements.filter(c=>c.state==="DOCUMENTED_PUBLIC").length,
    requirementsTotal:6,eligibility:"NOT_ELIGIBLE_REQUIRES_INDEPENDENT_REVIEW",
    numericGrade:null,confidenceRating:null,officialGrade:null,reviewerSignature:null,
    sourceSnapshotAsOf:asOf,fdaPrediction:"ABSTAIN",limitations
  };
}
export function evaluateClinicalRubricReadiness(
 report:QuantitativeResearchReport|null,
 ctx:{nct:string;phaseReported:string;phaseIndependentReviewerVerified:boolean;
   scientificFramework:{positions:number;mappedCandidateMethodLeads:number;methodPositionsUnexamined:number;
     independentlyGradedMethodPositions:number;currentPhaseReviewSignoffs:number};
   finalDecision:{approval:string;crl:string;reviewDelay:string;certainty:string;calibratedAccuracy:null}}
):RubricCoverage|null{
 if(!report||report.schema!=="MAIN_ACACIA_QUANTITATIVE_RESEARCH_V1"||
   report.nct!=="NCT06081894"||report.fdaPrediction!=="ABSTAIN"||
   report.officialMethodGrade!==null||report.provisionalClinicalGrade!==null||
   report.independentClinicalReview!==false||report.lockedSapVerified!==false||
   report.clinicalImportanceVerified!==false||
   report.seriousHeartFailureReconciliation!=="UNRESOLVED_11_1_VS_12_3"||
   report.endpoints.length!==2||report.safety.length!==2||
   report.positivePublishedEndpointSignals!==2||
   report.treatedArmExcessInDescriptiveSafety!==2||
   report.endpoints.some(x=>x.sourceUrl!==PUBLICATION)||
   report.safety.some(x=>x.sourceUrl!==PUBLICATION)||
   ctx?.nct!=="NCT06081894"||ctx.phaseReported!=="PHASE3"||
   ctx.phaseIndependentReviewerVerified!==false||
   ctx.scientificFramework?.positions!==800||
   ctx.scientificFramework?.mappedCandidateMethodLeads!==18||
   ctx.scientificFramework?.methodPositionsUnexamined!==782||
   ctx.scientificFramework?.independentlyGradedMethodPositions!==0||
   ctx.scientificFramework?.currentPhaseReviewSignoffs!==0||
   ctx.finalDecision?.approval!=="ABSTAIN"||ctx.finalDecision?.crl!=="ABSTAIN"||
   ctx.finalDecision?.reviewDelay!=="ABSTAIN"||
   ctx.finalDecision?.certainty!=="NOT_VALIDATED"||
   ctx.finalDecision?.calibratedAccuracy!==null)return null;

 const efficacy=makeRubric("5.1",12,"Multi-method adjudication — primary efficacy",[
   check("PRIMARY_PUBLISHED","Published co-primary estimates, reported P-values and 95% intervals",
    "DOCUMENTED_PUBLIC",PUBLICATION,"Both published directional primary estimates available, not original analysis datasets"),
   check("PRESPECIFIED_SAP","Locked SAP and prespecified estimands/multiplicity hierarchy",
    "INDEPENDENTLY_UNVERIFIED",null,"Final dated locked statistical analysis plan not authenticated"),
   check("FULL_SENSITIVITY","Original missing-data, intercurrent-event and model sensitivity results",
    "INDEPENDENTLY_UNVERIFIED",null,"Original CSR/primary sensitivity appendix not independently audited"),
   check("CLINICAL_IMPORTANCE","Independently assessed clinically meaningful effect thresholds",
    "INDEPENDENTLY_UNVERIFIED",null,"Statistical direction does not establish importance to patients"),
   check("ALTERNATIVE_ESTIMANDS","Cross-check alternate analysis sets and effect estimates",
    "INDEPENDENTLY_UNVERIFIED",null,"Aggregate results do not disclose complete alternate analyses"),
   check("INDEPENDENT_REANALYSIS","Qualified independent reconstruction and phase signoff",
    "INDEPENDENTLY_UNVERIFIED",null,"Neither authorized reviewer nor independent reanalysis is recorded"),
 ],bands.efficacy,report.asOf,[
   "Statistical primary signal is not a full multi-method adjudication.",
   "Numerical grade requires clinical-importance, SAP, sensitivity and independent review gates."
 ]);
 const safety=makeRubric("5.3",19,"Reproducibility audit — safety events",[
   check("ORIGINAL_ARM_NUMERATORS","Published serious-event and LVEF numerators and randomized denominators",
    "DOCUMENTED_PUBLIC",PUBLICATION,"Unadjusted arithmetic can be replicated from the reported aggregates"),
   check("HF_SAE_DEFINITIONS","Serious heart-failure event counts and analysis windows reconciled",
    "UNRESOLVED",null,"Secondary study 11/1 versus later sponsor 12/3; not equivalent populations until proved"),
   check("INTERRUPTION_DENOMINATOR","Source-specific interruption denominator and reported percentages",
    "UNRESOLVED",null,"Secondary interruption 14 (2.7%) and 1 (0.8%) not reconstructed from randomized arms"),
   check("EXPOSURE_ADJUSTMENT","Time at risk, exposure durations, repeat events and censoring",
    "INDEPENDENTLY_UNVERIFIED",null,"Arm-level percentages are not exposure-adjusted causal estimates"),
   check("SAFETY_CAUSALITY","Independent AE coding, causality, severity and reversibility adjudication",
    "INDEPENDENTLY_UNVERIFIED",null,"Original line listings and causality assessment not fully reviewed"),
   check("INDEPENDENT_SAFETY_REPLAY","Qualified reproduction of full analysis and original record versions",
    "INDEPENDENTLY_UNVERIFIED",null,"Independent source-data reconstruction and authorization absent")
 ],bands.safety,report.asOf,[
   "The source discrepancy cannot be interpreted as a safety signal trend or a resolved coding error.",
   "Numerical grade requires fully reconciled safety populations and independent review."
 ]);
 if(!efficacy||!safety||efficacy.documentedPublicChecks!==1||safety.documentedPublicChecks!==1)return null;
 return {schema:"MAIN_PHASE3_METHOD_RUBRIC_READINESS_V1",nct:"NCT06081894",
   methods:[efficacy,safety],candidateMethodPositionsWithResearch:5,
   sourceMappedPositions:18,unmappedMethodPositions:782,
   clinicalMethodGradesWritten:0,fdaPrediction:"ABSTAIN"};
}
