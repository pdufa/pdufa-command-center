/** An indication-scoped source-evidence worklist, never an automatic clinical verdict.
 * Uses exact-NCT registry fields; source presence is not scientific verification.
 * No model score, FDA probability, trial promotion or reassessment is inferred.
 */
import type {PoolRegistryDetail,PoolDetailField} from "./pool-registry-details";
export type IndicationReviewItem={
 key:string;label:string;researchQuestion:string;
 state:"SOURCE_OBSERVED_REVIEW_REQUIRED"|"RESEARCH_REQUIRED"|"NOT_SCORED"|"NOT_CONNECTED";
 evidence:string|null;sourceUrl:string|null;
};
export type IndicationReviewTrial={nct:string;indicationText:string;stage:string;focus:boolean};
const observed=(detail:PoolRegistryDetail|null,key:PoolDetailField)=>
 detail?.fields[key]?.trim()||null;
const source=(detail:PoolRegistryDetail|null,value:string|null)=>value?detail?.sourceUrl||null:null;
export function buildIndicationReview(trial:IndicationReviewTrial,detail:PoolRegistryDetail|null):IndicationReviewItem[]{
 const field=(key:string,label:string,question:string,from:PoolDetailField):IndicationReviewItem=>{
  const evidence=observed(detail,from);
  return {key,label,researchQuestion:question,
   state:evidence?"SOURCE_OBSERVED_REVIEW_REQUIRED":"RESEARCH_REQUIRED",
   evidence,sourceUrl:source(detail,evidence)};
 };
 const eligible=field("patient-subgroups","Disease severity, biomarkers and clinical subgroup",
  "Verify exact disease severity, testing methods, mutations and previous-treatment lines from protocol and applicable publications; eligibility text alone is not adjudication.",
  "eligibility");
 const indication:IndicationReviewItem={
  key:"indication-identity",label:"Exact drug–indication identity",
  researchQuestion:"Verify proposed treatment indication and enrolled clinical population; never apply one indication's conclusions to another.",
  state:"RESEARCH_REQUIRED",evidence:trial.indicationText||null,sourceUrl:null
 };
 return [
  indication,
  eligible,
  field("patient-population","Patient eligibility and addressable population",
   "Separate trial enrollment from epidemiologic prevalence, clinically eligible patients and commercial market size.",
   "enrollment"),
  field("mechanism","Mechanism and biological rationale",
   "Find manufacturer or published primary mechanism, target engagement and subtype-relevant support; registration is not proof.",
   "documentsPublications"),
  field("existing-therapies","Standard of care and trial comparators",
   "Identify up-to-date guideline therapy, comparator appropriateness, lines of therapy and alternatives. Registered arms are not the entire standard of care.",
   "treatmentArms"),
  {key:"competitive-trials",label:"Competing clinical treatments",
   researchQuestion:"Perform an independently sourced same-indication competitor search by population, biomarker and phase.",
   state:"RESEARCH_REQUIRED",evidence:null,sourceUrl:null},
  field("efficacy","Efficacy, endpoint validity and clinical meaning",
   "Interpret registered and posted outcomes by verified trial phase and comparator, including effect size, uncertainty and relevance; no result equals success automatically.",
   "reportedResults"),
  field("safety","Safety, durability and subgroup risks",
   "Evaluate serious events, exposure, withdrawals, duration and specialty-specific harms. Registry counts need denominator and review.",
   "safetyResults"),
  {key:"regulatory",label:"Indication-specific FDA regulatory requirements",
   researchQuestion:"Verify exact drug–indication application, FDA pathway, labeling, manufacturing and required endpoints; do not infer an application from trial phase.",
   state:"RESEARCH_REQUIRED",evidence:null,sourceUrl:null},
  {key:"score-confidence",label:"Scientific score, certainty and 20-level FOCUS readiness",
   researchQuestion:"Release scores only from a calibrated, independently reviewed phase-appropriate evidence package. FOCUS list membership alone is not certification.",
   state:"NOT_SCORED",evidence:null,sourceUrl:null},
  {key:"history",label:"Assessment history and event-triggered reassessment",
   researchQuestion:"Persist immutable timestamped source versions, reviewed changes and outcome-neutral prediction history; this read-only screen does not save a longitudinal dossier.",
   state:"NOT_CONNECTED",evidence:null,sourceUrl:null}
 ];
}
export function indicationReviewSummary(items:readonly IndicationReviewItem[]){
 return {sourceObservations:items.filter(x=>x.state==="SOURCE_OBSERVED_REVIEW_REQUIRED").length,
  researchGaps:items.filter(x=>x.state==="RESEARCH_REQUIRED").length,
  scored:0,clinicallyAdjudicated:0};
}
