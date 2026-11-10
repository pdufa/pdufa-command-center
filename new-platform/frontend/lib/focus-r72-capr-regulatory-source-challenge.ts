/** R72 CAPR original FDA-versus-sponsor source challenge. Research only.
 * The July advisory package predates the August major amendment and cannot be
 * presented as a final FDA ruling on the later narrowed proposed indication.
 */
import rawData from "../data/focus-r72-capr-regulatory-source-challenge.json";
import {FOCUS_R71_PIVOTAL_EVIDENCE_INTAKE} from "./focus-r71-pivotal-evidence-intake";

const FDA="https://www.fda.gov/media/193839/download";
const SEC="https://www.sec.gov/Archives/edgar/data/1133869/000110465926100071/capr-20260824x8k.htm";
const ISSUER="https://www.globenewswire.com/news-release/2026/11/09/3398455/0/en/capricor-s-hope-3-phase-3-cardiac-results-for-deramiocel-win-american-heart-association-outstanding-research-award-in-pediatric-cardiology.html";
const PRIMARY=[
 ["FDA_SAP11_PRESPECIFIED","0.66","-0.45 to 1.77","0.24","Absolute PUL 2.0 total-score points"],
 ["FDA_SAP30_NO_IMPUTATION","2.53","-1.48 to 6.53","0.21","Percentage-point PUL 2.0 change"],
 ["APPLICANT_MODIFIED_CSR","4.55","0.47 to 8.63","0.029","Percentage-point PUL 2.0 change"]
] as const;
const SECONDARY=[
 ["FDA_SAP11_LVEF","0.97","Absolute LVEF percentage-point change"],
 ["FDA_SAP30_LVEF","0.09","Rank-based outcome; not comparable to absolute change"],
 ["APPLICANT_CSR_LVEF","0.041","Rank-based outcome; different model from original"]
] as const;
const DATES=["2022-07-19","2025-06-18","2025-09-26","2025-11-24","2025-11-25","2026-07-29","2026-08-24","2026-11-09"] as const;

export function buildR72CaprSourceChallenge(input:unknown=rawData){
 const upstream=FOCUS_R71_PIVOTAL_EVIDENCE_INTAKE;
 if(!upstream||upstream.focusNcts!==29||upstream.applicationCycles!==23||
    upstream.scientificallyValidatedFutureFDAForecasts!==0||
    upstream.fiveRecords.find(t=>t.nct==="NCT05126758")?.futureFDAOutcome!=="ABSTAIN"||
    !input||typeof input!=="object"||Array.isArray(input))return null;
 const r=input as typeof rawData;
 if(Object.keys(r).sort().join("|")!==[
   "asOf","bla","clinicalGrade","cycleId","evidenceChronology","fdaGoal",
   "futureApprovalOrCrlForecast","futureTimingForecast","independentClinicalReviewSigned",
   "nct","originalFDAFirstPublicAvailabilityAuthenticated","originalFDAReportDate",
   "originalFDAReportSource","pdufaTarget","primaryAnalysisComparisons",
   "priorityResearchGates","refinedIndication","regulatoryAsOf","researchLimitations",
   "schema","secondaryAnalysisComparisons","ticker"].filter(x=>x!=="fdaGoal").sort().join("|") ||
    r.schema!=="MAIN_R72_CAPR_HOPE3_FDA_SPONSOR_ORIGINAL_SOURCE_CONFLICT_RESEARCH"||
    r.asOf!=="2026-11-09"||r.nct!=="NCT05126758"||r.ticker!=="CAPR"||
    r.cycleId!=="capr-deramiocel"||r.bla!=="125842/0"||
    r.regulatoryAsOf!=="SPONSOR_REPORTS_PENDING_FDA_REVIEW"||
    r.originalFDAReportDate!=="2026-07-29"||
    r.originalFDAFirstPublicAvailabilityAuthenticated!==false||
    r.originalFDAReportSource!==FDA||
    r.futureApprovalOrCrlForecast!=="ABSTAIN"||r.futureTimingForecast!=="UNKNOWN"||
    r.clinicalGrade!==null||r.independentClinicalReviewSigned!==false||
    !r.refinedIndication.includes("upper-limb")||
    r.pdufaTarget.date!=="2026-11-22"||
    r.pdufaTarget.previousDate!=="2026-08-22"||
    r.pdufaTarget.status!=="FORMAL_MAJOR_AMENDMENT_EXTENSION_ALREADY_REPORTED"||
    r.pdufaTarget.sourceDate!=="2026-08-24"||r.pdufaTarget.source!==SEC)return null;
 if(r.primaryAnalysisComparisons.length!==3||r.secondaryAnalysisComparisons.length!==3||
    r.evidenceChronology.length!==8||r.priorityResearchGates.length!==6)return null;
 for(let i=0;i<3;i++){
  const p=r.primaryAnalysisComparisons[i],e=PRIMARY[i],s=r.secondaryAnalysisComparisons[i],t=SECONDARY[i];
  if(p.id!==e[0]||p.difference!==e[1]||p.ci!==e[2]||
     p.p!==e[3]||p.endpointScale!==e[4]||
     p.sourcePdfPrintedPage!==40||p.analysis.length<20||
     p.interpretation.length<40||s.id!==t[0]||s.p!==t[1]||
     s.endpointScale!==t[2]||s.sourcePdfPrintedPage!==42)return null;
 }
 for(let i=0;i<DATES.length;i++){
  const c=r.evidenceChronology[i];
  if(c.date!==DATES[i]||
     c.source!==(i<6?FDA:i===6?SEC:ISSUER)||
     c.event.length<35)return null;
 }
 if(r.priorityResearchGates.some(t=>typeof t!=="string"||t.length<40)||
    Object.values(r.researchLimitations).some((v,i)=>i===6?v!==true:v!==false)||
    Object.keys(r.researchLimitations).length!==7)return null;
 return {...r,
   sourceClassification:"ORIGINAL_FDA_AND_ISSUER_MATERIALS_INTERPRETATION_ONLY" as const,
   historicalPredictionSafe:false as const,
   canAwardScienceGrade:false as const,
   canProduceNumericalFDAProbability:false as const
 };
}
export const FOCUS_R72_CAPR_REGULATORY_SOURCE_CHALLENGE=buildR72CaprSourceChallenge();
