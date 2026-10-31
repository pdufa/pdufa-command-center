/** Exact stated purposes for the post-Phase-3 PIPELINE commercial review.
 * Each trial is an NCT study, NOT necessarily a distinct commercial program.
 * A dossier is never accepted on ticker-only or disease-only matching.
 * Commercial reasoning and FDA decision prediction remain separate.
 */
export const COMPETITIVE_ASSESSMENT_COLUMNS = [
  { id: "trialId", label: "Trial ID (NCT)", purpose: "Identify the exact clinical trial and link to its original evidence.", evidence: "Exact ClinicalTrials.gov NCT record." },
  { id: "company", label: "Company / Ticker", purpose: "Identify the publicly traded company and verify its relationship to the therapy.", evidence: "Sponsor, licensing rights and dated company listing." },
  { id: "therapy", label: "Proposed Therapy", purpose: "Identify the drug, biologic, or treatment being evaluated.", evidence: "Trial intervention matched to the sponsor's exact investigational product." },
  { id: "indication", label: "Indication", purpose: "Define precisely which patients and medical condition the therapy targets.", evidence: "Trial inclusion/exclusion and proposed or approved indication wording." },
  { id: "eligibleUsPatients", label: "Eligible U.S. Patients", purpose: "Estimate the number of patients who could actually qualify for treatment, not merely total disease prevalence.", evidence: "Dated U.S. epidemiology, diagnosis rates, label-eligible subsets and exclusions." },
  { id: "standardOfCare", label: "Current Standard of Care", purpose: "Identify the treatments patients currently receive and the appropriate comparison.", evidence: "Contemporary clinical guidelines, current FDA labels and treatment share." },
  { id: "competitorCount", label: "Number of Competitors", purpose: "Count competing approved treatments and late-stage therapies separately, using the same indication and patient population.", evidence: "Deduplicated drug-indication comparison, approved FDA labels and current Phase 3 pipeline; exclude same-drug duplicate trials." },
  { id: "clinicalBenefit", label: "Clinical Patient Benefit", purpose: "Explain exactly what improves for patients compared with existing treatment, and by how much.", evidence: "Matched endpoints, effect size, comparator, follow-up and uncertainty, not a p-value alone." },
  { id: "safetyAdvantage", label: "Safety Advantage", purpose: "Compare adverse effects, serious risks, and treatment discontinuation.", evidence: "Comparable safety populations, follow-up and clinically relevant adverse events." },
  { id: "unmetNeed", label: "Unmet Medical Need", purpose: "Determine how many patients remain inadequately treated by existing options.", evidence: "Residual symptom burden, treatment failure and eligible untreated or refractory population." },
  { id: "convenience", label: "Treatment Convenience", purpose: "Compare dosing frequency, route, treatment burden, and monitoring.", evidence: "Current vs proposed regimen, route, frequency, monitoring and persistence." },
  { id: "costDifference", label: "Treatment Cost Advantage", purpose: "Compare equivalent first-year treatment costs and explain the difference.", evidence: "Dated comparable price basis and 12-month drug plus monitoring/administration regimen costs." },
  { id: "payerAccess", label: "Insurance / Access", purpose: "Determine whether coverage, reimbursement, and prescribing restrictions may limit adoption.", evidence: "Payer policy, formulary, prior authorization, patient copays and access date." },
  { id: "adoption", label: "Projected Adoption", purpose: "Estimate the proportion of eligible patients who could receive the new therapy over time.", evidence: "12/24/36-month adoption assumptions, eligible denominator, switching, new starts, coverage and confidence." },
  { id: "competitiveStrategy", label: "Competitive Strategies", purpose: "Rank the therapy’s evidence-supported competitive advantages from strongest to weakest.", evidence: "Rank each comparator-specific advantage with sources, magnitude and counterarguments; generic priorities are unscored." },
  { id: "evidence", label: "Evidence and Reasoning", purpose: "State the exact supporting facts, source links, assumptions, counterarguments, and confidence level.", evidence: "Primary sources, dates, denominators, methodology, conflicts and independent review." },
  { id: "verdict", label: "Competitive Conclusion", purpose: "Explain whether the therapy has a meaningful commercial advantage, why, and what evidence could change that conclusion.", evidence: "Synthesized clinical, adoption, pricing and competitive comparison; do not equate commercial prospects with FDA approval." },
] as const;

export type CompetitiveColumnId = typeof COMPETITIVE_ASSESSMENT_COLUMNS[number]["id"];
export type ResearchEvidence = {
  value: string | number | null;
  status: "VERIFIED" | "MODELED";
  sourceUrl: string;
  sourceDate: string;
  method: string;
  reason: string;
  confidence: "HIGH" | "MODERATE" | "LOW";
};
export type CompetitiveAssessment = {
  nctId: string;
  ticker: string;
  indication: string;
  fields: Partial<Record<Exclude<CompetitiveColumnId, "trialId" | "company" | "therapy" | "indication" | "competitorCount" | "costDifference" | "competitiveStrategy" | "evidence"> | "approvedCompetitors" | "lateStageCompetitors", ResearchEvidence>>;
};
const numericFields = new Set(["eligibleUsPatients", "approvedCompetitors", "lateStageCompetitors", "adoption"]);
const fullDay = (v: string) => {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(v)) return false;
  const d=new Date(v+"T00:00:00Z");
  return Number.isFinite(d.getTime()) && d.toISOString().slice(0,10)===v && d.getTime()<=Date.now();
};

/** Missing or invalid source details fail closed. Zero verified competitors IS a valid count. */
export function verifiedCompetitiveFact(
  dossier: CompetitiveAssessment | null | undefined,
  row: {nctId:string; ticker:string; indication:string|null},
  key: keyof CompetitiveAssessment["fields"],
): ResearchEvidence | null {
  if (!dossier || dossier.nctId!==row.nctId || dossier.ticker!==row.ticker
      || !row.indication || dossier.indication!==row.indication) return null;
  const item=dossier.fields?.[key];
  if (!item || !["VERIFIED","MODELED"].includes(item.status)
      || !/^https:\/\/[^\s]+$/.test(item.sourceUrl) || !fullDay(item.sourceDate)
      || !item.method?.trim() || !item.reason?.trim()
      || !["HIGH","MODERATE","LOW"].includes(item.confidence)
      || item.method.length>2000 || item.reason.length>2000) return null;
  if(numericFields.has(key)){
    if(typeof item.value!=="number" || !Number.isFinite(item.value) || item.value<0)return null;
    if(key==="adoption"&&item.value>100)return null;
    if(key!=="adoption"&&!Number.isSafeInteger(item.value))return null;
  }else if(typeof item.value!=="string" || !item.value.trim() || item.value.length>500)return null;
  return item;
}
