/** MAIN R79: original documentary authenticity blockers, not a clinical grade. */
import raw from "../data/focus-r79-launch-htn-sap-lock-evidence-gates.json";
import {FOCUS_R78_LAUNCH_HTN_PUBLIC_CHRONOLOGY} from "./focus-r78-launch-htn-public-chronology";

const SOURCE_REQUIRMENTS=[
 ["CONTROLLED_ORIGINAL_SAP_BYTES","PUBLISHED_IMPRINT_ONLY"],
 ["FORMAL_SAP_FINALIZATION_RECORD","NOT_OBTAINED"],
 ["FINAL_DATABASE_LOCK_AUDIT","NOT_OBTAINED"],
 ["FIRST_UNBLINDED_ACCESS_AUDIT","NOT_OBTAINED"],
 ["SAP_AMENDMENT_CONTROLLED_CHAIN","NOT_OBTAINED"],
 ["CONFLICTED_ADDENDUM_YEAR_RECONCILIATION","UNRESOLVED_PRINTED_YEAR_CONFLICT"],
 ["TWO_TRUSTED_INDEPENDENT_ATTESTATIONS","NOT_OBTAINED"]
] as const;

export function buildR79AuthenticSapLockGates(input:unknown=raw){
 const prior=FOCUS_R78_LAUNCH_HTN_PUBLIC_CHRONOLOGY;
 if(!prior||prior.nct!=="NCT06153693"||
    prior.observation.originalActualDatabaseLockDate!==null||
    prior.observation.originalActualUnblindingDate!==null||
    prior.regulatory.officialOutcomeForecast!=="ABSTAIN"||
    !input||typeof input!=="object"||Array.isArray(input))return null;
 const d=input as typeof raw;
 if(d.schema!=="MAIN_R79_LAUNCH_HTN_AUTHENTIC_ORIGINAL_SAP_LOCK_EVIDENCE_GATE_RESEARCH_ONLY"||
    d.asOf!=="2026-11-09"||d.nct!=="NCT06153693"||d.ticker!=="MLYS"||
    d.trial!=="Launch-HTN"||d.cycleId!=="mlys-lorundrostat"||
    d.reviewStandards.length!==2||
    d.reviewStandards[0].kind!=="ICH_E9_5_1"||
    d.reviewStandards[0].url!=="https://www.hhs.gov/guidance/sites/default/files/hhs-guidance-documents/FDA/E9-Statistical-Principles-for-Clinical-Trials.pdf"||
    d.reviewStandards[1].kind!=="ICH_E6_R3_3_16_2"||
    d.reviewStandards[1].url!=="https://www.fda.gov/media/169090/download"||
    d.reviewStandards.some(x=>x.norm.length<75)||
    d.originalPublicSourceLead!=="https://jamanetwork.com/journals/jama/fullarticle/2835763"||
    d.observedPrintedMainSapDate!==prior.observation.mainSapPrintedSignatureImprint||
    d.observedPrintedWindowingAddendumDate!==prior.observation.windowingAddendumPrintedSignatureImprint||
    d.observedPublishedFirstToplineDate!==prior.observation.publicIssuerToplineSECDisclosureDate||
    d.sourceBytesSha256Authenticated!==0||d.originalDocumentCount!==7||
    d.machineGateAvailable!==true||d.productionApprovedTrustAnchors!==0||
    d.sourceRequirements.length!==7||
    d.requirementsIndependentlyVerified!==0||
    d.requiredBeforeProspectiveSapChronologyCertified!==7||
    d.authenticPlanFinalizedBeforeBlindBreak!==false||
    d.firstUnblindedAccessTimestampAuthenticated!==false||
    d.actualFinalDatabaseLockTimestampAuthenticated!==false||
    d.originalSourceAttestationsVerified!==false||
    d.qualifiedIndependentReviewersSigned!==0||
    d.validatedFDAApplicationForecasts!==0||
    d.scientificGrade!==null||d.FDAOutcome!=="ABSTAIN"||
    d.futureTiming!=="UNKNOWN"||d.sourceResearchOnly!==true||
    d.modelTrainingOrProductionWrites!==false||
    d.disclaimer.length<180)return null;
 for(let i=0;i<SOURCE_REQUIRMENTS.length;i++){
  const item=d.sourceRequirements[i],expect=SOURCE_REQUIRMENTS[i];
  if(item.id!==expect[0]||item.status!==expect[1]||
     item.independentReceipt!==null||item.label.length<40||
     item.evidence.length<90)return null;
 }
 return {...d,scientificReadiness:"BLOCKED_AUTHENTIC_PROSPECTIVE_SOURCE" as const,
   sourceProofsMissing:7 as const,clinicallyValidated:false as const,
   clinicalPredictionAllowed:false as const};
}
export const FOCUS_R79_LAUNCH_HTN_SAP_LOCK_GATES=buildR79AuthenticSapLockGates();
