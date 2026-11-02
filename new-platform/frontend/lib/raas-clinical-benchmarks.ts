/** Endpoint-specific medical interpretation references.
 * Critical distinction: a within-patient MID is not a between-arm
 * clinically meaningful treatment difference, nor a trade-return threshold.
 */
export type ClinicalBenchmark={
 id:string;condition:string;endpoint:string;unit:string;
 min:number;max:number;interpretation:"WITHIN_PATIENT_CHANGE";
 sourceUrl:string;citation:string;sourceYear:number;
 description:string;notApplicableTo:string;
};
export const RAAS_CLINICAL_BENCHMARKS:readonly ClinicalBenchmark[]=[
 {
  id:"uas7-within-patient-mid-2015",
  condition:"Chronic spontaneous / idiopathic urticaria",endpoint:"UAS7",unit:"UAS7 points",
  min:9.5,max:10.5,interpretation:"WITHIN_PATIENT_CHANGE",
  sourceUrl:"https://pubmed.ncbi.nlm.nih.gov/26314821/",
  citation:"Mathias et al., The minimal important difference for measures of urticaria disease activity: updated findings, 2015; PMID 26314821",
  sourceYear:2015,
  description:"Estimated minimal important within-patient difference in UAS7 from combined anchor- and distribution-based methods across three randomized studies.",
  notApplicableTo:"Do not treat this MID as the required placebo-adjusted between-group treatment effect, as a UAS7 standardized effect size, or as a numerical stock appreciation grade."
 }
];
export function contextualClinicalBenchmark(drug:string,indication:string,unit:string):ClinicalBenchmark|null{
 if(!drug.trim()||!/(?:chronic spontaneous urticaria|chronic idiopathic urticaria)/i.test(indication)||
    unit!=="UAS7 points")return null;
 return RAAS_CLINICAL_BENCHMARKS[0];
}
