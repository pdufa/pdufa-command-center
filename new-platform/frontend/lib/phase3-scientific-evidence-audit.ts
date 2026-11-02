/** Trial-specific methodological verification checklist for source-linked Phase 3
 * SURVEY findings. These are disclosure checks, NOT clinical merit or a validated
 * FDA approval/CRL/extension probability.
 */
import type {BenefitRecord} from "./benefit-assessments";
export type ScientificEvidenceCheck={
 id:string;
 title:string;
 status:"DOCUMENTED"|"NOT_ESTABLISHED";
 detail:string;
};
export type ScientificEvidenceAudit={
 checks:ScientificEvidenceCheck[];
 documented:number;
 gaps:number;
};
const documented=(id:string,title:string,detail:string):ScientificEvidenceCheck=>({
 id,title,status:"DOCUMENTED",detail
});
const unknown=(id:string,title:string,detail:string):ScientificEvidenceCheck=>({
 id,title,status:"NOT_ESTABLISHED",detail
});
const fact=(record:BenefitRecord|null,id:string)=>
 record?.facts[id]?.status==="VERIFIED"?record.facts[id]:null;
export function phase3ScientificEvidenceAudit(record:BenefitRecord|null):ScientificEvidenceAudit{
 const source=record&&Object.values(record.facts).length>0&&
  Object.values(record.facts).every(f=>f.status==="VERIFIED");
 const primary=fact(record,"clinicalBenefit"),magnitude=fact(record,"magnitude");
 const comparator=!!primary&&!!magnitude&&
  /vs placebo|versus placebo/i.test(String(primary.value))&&
  /placebo-adjusted/i.test(String(magnitude.value));
 const later=fact(record,"durability");
 const safety=fact(record,"seriousAes")||fact(record,"discontinuation");
 const checks=[
  source?documented("issuer","Exact-trial issuer result documentation",
   "Source-linked reported observations are recorded for this NCT, drug, and indication. These are sponsor disclosures, not independently reviewed patient-level data."):
   unknown("issuer","Exact-trial issuer result documentation",
   "No source-matched issuer research record is available; results cannot be inferred from study status or ticker."),
  comparator?documented("comparator","Placebo-adjusted numerical efficacy comparison",
   "Sponsor disclosed a placebo comparison and treatment-effect magnitude; verify model assumptions, estimand, denominators, multiplicity, and confidence intervals independently."):
   unknown("comparator","Placebo-adjusted numerical efficacy comparison",
   "An exact-arm placebo-adjusted estimate is not documented in this research record. An active-arm response alone cannot establish comparative efficacy."),
  later&&/Week 24/i.test(String(later.value))?
   documented("later","Later observed response timepoint",
    "A Week 24 arm-level response rate is documented. Different timepoint proportions cannot demonstrate uninterrupted response in the same individuals."):
   unknown("later","Later observed response timepoint",
    "Longer-term comparative responses are not yet documented in this research feed. Do not assume durability from a Week 12 or Week 16 result."),
  safety?documented("safety","Numeric safety or discontinuation evidence",
   "A source-verified safety finding is recorded; still verify exposure, denominators, attribution, and follow-up before drawing comparisons."):
   unknown("safety","Numeric safety or discontinuation evidence",
    "The research feed contains no numerically documented, comparator-aligned serious adverse event or discontinuation input. A qualitative 'well tolerated' statement does not satisfy this check."),
  unknown("independent","Independent clinical data adjudication",
   "No independently reviewed complete clinical study report or patient-level analysis is authenticated by this sponsor-only research feed; absence here does not prove no external publication exists."),
  unknown("fda","Product- and indication-matched FDA decision evidence",
   "An issuer topline result is not a filed/accepted application, confirmed PDUFA action date, approval, CRL or extension.")
 ];
 return {checks,documented:checks.filter(x=>x.status==="DOCUMENTED").length,
  gaps:checks.filter(x=>x.status==="NOT_ESTABLISHED").length};
}
