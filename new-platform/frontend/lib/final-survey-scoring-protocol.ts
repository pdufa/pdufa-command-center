/** Scoring method preregistration for the original 20 SURVEY assessments.
 * Research evidence can satisfy a method-review gate, never confer an
 * uncalibrated medical, commercial, stock or FDA probability score.
 * Dates, methods and source URLs are validated by parseBenefitFeed upstream.
 */
import {BENEFIT_GROUPS,type BenefitRecord} from "./benefit-assessments";

export type SurveyScoringGate=
 "NO_EXACT_RECORD"|"PUBLIC_RESULTS_UNCONFIRMED"|"MISSING_VERIFIED_INPUTS"|
 "LOW_CONFIDENCE_INPUTS"|"METHOD_VALIDATION_REQUIRED";
export type SurveyScoringProtocol={
 number:number;
 evidenceBasis:string;
 comparisonRequired:string;
 outcomeCriterion:string;
 requiresPublicReadout:boolean;
};
export type SurveyScoringAssessment={
 number:number;name:string;required:number;
 verified:number|null;modeled:number|null;missing:number|null;
 lowConfidence:number|null;
 gate:SurveyScoringGate;
 missingInputs:readonly string[];
 sourceLinks:readonly {label:string;url:string;date:string;confidence:string}[];
 protocol:SurveyScoringProtocol;
 numericalScore:null;
};
const RULES:readonly Omit<SurveyScoringProtocol,"number">[]=[
 {evidenceBasis:"Documented indication-specific eligible population, stratified by treatment line and biomarker.",
  comparisonRequired:"Use a defined eligible-patient denominator; do not extrapolate from general prevalence.",
  outcomeCriterion:"Quantify addressable patients with geography, exclusions and source-date sensitivity.",requiresPublicReadout:false},
 {evidenceBasis:"Patient-important unmet burden and documented shortcomings of current standard treatment.",
  comparisonRequired:"Use treatment-line matched standard of care and disease-specific outcomes.",
  outcomeCriterion:"Measure residual burden and affected subgroups, not an unsourced unmet-need adjective.",requiresPublicReadout:false},
 {evidenceBasis:"Prespecified pivotal endpoints, effect magnitude, precision, durability and clinical relevance.",
  comparisonRequired:"Compare the primary estimand and valid control with aligned follow-up and confidence intervals.",
  outcomeCriterion:"Evaluate absolute effect, uncertainty, multiplicity, patient relevance and prespecification.",requiresPublicReadout:true},
 {evidenceBasis:"Documented survival endpoint, follow-up maturity, censoring and hazard/absolute effect if applicable.",
  comparisonRequired:"Use aligned risk sets and population; no survival inference from a non-survival endpoint.",
  outcomeCriterion:"Assess survival effect, confidence interval and competing risks; N/A is not failure.",requiresPublicReadout:true},
 {evidenceBasis:"Validated patient-reported outcome instrument, minimal important difference and missing data.",
  comparisonRequired:"Align instrument, patient mix, reporting time and missingness across groups.",
  outcomeCriterion:"Score only prespecified clinically important quality-of-life changes.",requiresPublicReadout:true},
 {evidenceBasis:"Documented approved or pipeline alternatives for the same disease, population and treatment line.",
  comparisonRequired:"A directional superiority claim needs direct comparative effect estimates; indirect estimates require validated adjustment.",
  outcomeCriterion:"Distinguish comparability, uncertainty and clinical relevance; a competitor count is not advantage.",requiresPublicReadout:false},
 {evidenceBasis:"Route, treatment frequency, monitoring, care setting and sequence for actual eligible patients.",
  comparisonRequired:"Use a comparator matched to indication, eligible patient population, and treatment line.",
  outcomeCriterion:"Describe treatment burden and adherence consequences separately from clinical efficacy.",requiresPublicReadout:false},
 {evidenceBasis:"Exposure-aligned serious adverse events, discontinuations, attribution and follow-up.",
  comparisonRequired:"Use comparable denominators and exposure; avoid ranking safety from raw percentages alone.",
  outcomeCriterion:"Consider severity, incidence, confidence intervals and benefit-risk tradeoffs.",requiresPublicReadout:true},
 {evidenceBasis:"Documented hospitalizations, complications, treatment costs and patient outcome measurement.",
  comparisonRequired:"Use matched costs, payer perspective, time horizon and patient-outcome denominators.",
  outcomeCriterion:"Calculate incremental cost per relevant outcome with explicit uncertainty.",requiresPublicReadout:true},
 {evidenceBasis:"Dated payer policy, coverage criteria, utilization management and approval assumptions.",
  comparisonRequired:"Distinguish authorized reimbursement from prospective post-approval estimates.",
  outcomeCriterion:"Estimate access by payer population and restrictions, not presumed reimbursement.",requiresPublicReadout:false},
 {evidenceBasis:"Documented or explicitly labeled modeled net treatment price, duration and geography.",
  comparisonRequired:"Normalize comparator prices by payer, dosing, discounts and treatment duration.",
  outcomeCriterion:"Provide uncertainty ranges and explain unverified commercial price assumptions.",requiresPublicReadout:false},
 {evidenceBasis:"Eligible starts, current treatments, switching conditions and modeled adoption assumptions.",
  comparisonRequired:"Anchor uptake to the verified addressable population and realistic treatment alternatives.",
  outcomeCriterion:"Produce low/base/high adoption scenarios, not a single unsupported market-share number.",requiresPublicReadout:false},
 {evidenceBasis:"Jurisdiction-specific population, diagnostic rates and local indication scope.",
  comparisonRequired:"Keep foreign regulatory and reimbursement status separate from US indications.",
  outcomeCriterion:"Size addressable non-US populations with overlapping groups removed.",requiresPublicReadout:false},
 {evidenceBasis:"Distinct trial programs, target indications and pathway-specific requirements.",
  comparisonRequired:"Do not treat adjacent indications as FDA-approved or equivalent to primary pivotal trials.",
  outcomeCriterion:"Evaluate incremental opportunities only for source-linked programs.",requiresPublicReadout:false},
 {evidenceBasis:"Eligible treated population, uptake, net price, therapy duration and territorial rights.",
  comparisonRequired:"Source every low/base/high commercial driver and exclude overlap or double-counting.",
  outcomeCriterion:"Calculate scenario peak annual revenue, not clinical benefit or FDA probability.",requiresPublicReadout:false},
 {evidenceBasis:"Modeled treatment starts, persistence, launch ramp, competition and price over time.",
  comparisonRequired:"Reconcile yearly patient cohorts, churn and payer-adjusted economics.",
  outcomeCriterion:"Compute sensitivity-bounded annual revenue paths, not an unsupported growth rate.",requiresPublicReadout:false},
 {evidenceBasis:"Dated patent claims, FDA exclusivity records, challenges and expiry timing.",
  comparisonRequired:"Separate patent assertions from verified enforceable market protection.",
  outcomeCriterion:"Express exclusivity-duration scenarios with litigation and market-entry uncertainty.",requiresPublicReadout:false},
 {evidenceBasis:"Actual commercial rights, partners, royalties, milestones and source agreements.",
  comparisonRequired:"Separate potential deals from signed contracts and contingent milestones.",
  outcomeCriterion:"Value only attributable contractual economics with stated discount assumptions.",requiresPublicReadout:false},
 {evidenceBasis:"Product-level risk-adjusted cash flows, enterprise valuation, dilution and pipeline context.",
  comparisonRequired:"Separate clinical/regulatory likelihood from financing and share-price assumptions.",
  outcomeCriterion:"Require calibrated probability inputs and disclosed valuation sensitivities before numeric upside.",requiresPublicReadout:false},
 {evidenceBasis:"Bear/base/bull enterprise outcomes, cash runway, financing, liquidity and share count.",
  comparisonRequired:"Model scenario-specific dilution, risk and market response separately from clinical efficacy.",
  outcomeCriterion:"Present range and downside distribution only after model calibration, not trade advice.",requiresPublicReadout:false}
];
export const SURVEY_SCORING_PROTOCOLS:readonly SurveyScoringProtocol[]=RULES.map((x,i)=>({...x,number:i+1}));

/** An input can be source-recorded without independently adjudicating efficacy.
 * This queue only clears evidence and quality blockers. A numeric score remains
 * null until externally validated scoring functions and calibration are added.
 */
export function surveyScoringAssessments(
 record:BenefitRecord|null,publicReadoutDocumented:boolean
):SurveyScoringAssessment[]{
 return BENEFIT_GROUPS.map(group=>{
  const protocol=SURVEY_SCORING_PROTOCOLS[group.number-1];
  const facts=record?.facts||{};
  const verified=group.fields.filter(f=>facts[f.id]?.status==="VERIFIED");
  const modeled=group.fields.filter(f=>facts[f.id]?.status==="MODELED");
  const lowConfidence=verified.filter(f=>facts[f.id]?.confidence==="LOW");
  const missingInputs=record?group.fields.filter(f=>facts[f.id]?.status!=="VERIFIED")
    .map(f=>f.label):[];
  const sourceLinks=verified.map(f=>({
    label:f.label,url:facts[f.id].sourceUrl,date:facts[f.id].sourceDate,
    confidence:facts[f.id].confidence
  }));
  const gate:SurveyScoringGate=!record?"NO_EXACT_RECORD":
   protocol.requiresPublicReadout&&!publicReadoutDocumented?"PUBLIC_RESULTS_UNCONFIRMED":
   verified.length!==group.fields.length?"MISSING_VERIFIED_INPUTS":
   lowConfidence.length>0?"LOW_CONFIDENCE_INPUTS":"METHOD_VALIDATION_REQUIRED";
  return {
   number:group.number,name:group.name,required:group.fields.length,
   verified:record?verified.length:null,modeled:record?modeled.length:null,
   missing:record?group.fields.length-verified.length-modeled.length:null,
   lowConfidence:record?lowConfidence.length:null,gate,missingInputs,
   sourceLinks,protocol,numericalScore:null
  };
 });
}
export const surveyScoringGateLabel=(gate:SurveyScoringGate):string=>({
 NO_EXACT_RECORD:"Exact source record required",
 PUBLIC_RESULTS_UNCONFIRMED:"Public results not documented as checked",
 MISSING_VERIFIED_INPUTS:"Research inputs missing",
 LOW_CONFIDENCE_INPUTS:"Low-confidence evidence review",
 METHOD_VALIDATION_REQUIRED:"Method calibration required"
})[gate];
