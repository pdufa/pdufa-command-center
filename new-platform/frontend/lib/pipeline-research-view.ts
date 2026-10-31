/** Four Pipeline displays use the same exact-NCT research records.
 * Historical Phase 3 census entries are research pointers, not qualified programs.
 * No missing competitor, benefit or FDA date is converted to zero or a ranking.
 */
import type { ComparatorEvidence } from "./pipeline-benefit-assessments";
import { COMPETITIVE_ASSESSMENT_COLUMNS, verifiedCompetitiveFact, type CompetitiveAssessment, type ResearchEvidence } from "./competitive-assessment";
import { calculateTherapyCosts, type TherapyCostComparison } from "./post-phase3-population";
import { pipelineDayCounts, type TimelineDates } from "./pipeline-timeline";

export type PipelineResearchRow = {
 nctId:string; ticker:string; company:string; drug:string|null; indication:string|null;
 sourceUrl:string; censusStatus:string; capUsd:number; capAsOf:string;
 poolStatus:string; postPhase3Evidence:string; qualification:string; reasons:string[];
 timeline?:TimelineDates|null;
 commercialAssessment?:CompetitiveAssessment|null;
 /** Optional normalized, exact-program source-backed comparators; never inferred from a disease label. */
 competitorEvidence?:ComparatorEvidence[]|null;
 therapyCostComparison?:TherapyCostComparison|null;
};
type OriginalId=typeof COMPETITIVE_ASSESSMENT_COLUMNS[number]["id"];
export type ResearchFieldId = OriginalId | "daysSinceReadout" | "daysToPdufa"
 | "closestCompetitor" | "headToHead" | "magnitude" | "meaningfulBenefit"
 | "durability" | "seriousAes" | "responseRemission" | "timeToResponse"
 | "bestSubgroup" | "treatmentResistantBenefit" | "qualityOfLife" | "discontinuation"
 | "hospitalizationReduction" | "switchingPool" | "treatmentSequence"
 | "competitivePipelineThreat" | "exclusivity" | "valuePerOutcome" | "overallRank";
export type ResearchField = {id:ResearchFieldId;label:string;purpose:string;evidence:string};
const extra:ResearchField[]=[
 {id:"daysSinceReadout",label:"Days since Phase 3 data release",purpose:"Count calendar days since publicly announced Phase 3 results, not the registry completion date.",evidence:"Dated public pivotal readout announcement matched to exact NCT and therapy."},
 {id:"daysToPdufa",label:"Days to PDUFA",purpose:"Count calendar days until the documented FDA action date and mark the PDUFA-minus-three-day research cutoff.",evidence:"Source-verified FDA action date for the exact product and indication."},
 {id:"closestCompetitor",label:"Closest Competing Therapy",purpose:"Identify the most relevant existing or developing treatment for the same indication and line of therapy.",evidence:"Current FDA label, guideline, eligibility overlap and line of treatment."},
 {id:"headToHead",label:"Head-to-Head Evidence",purpose:"Determine whether a direct comparison shows superiority or noninferiority to the closest relevant therapy.",evidence:"Randomized comparator details, predefined estimand, endpoints, results and uncertainty."},
 {id:"magnitude",label:"Magnitude of Clinical Improvement",purpose:"Measure absolute and relative differences in patient-important outcomes against a valid comparator.",evidence:"Matched effect sizes, units, follow-up and confidence intervals."},
 {id:"meaningfulBenefit",label:"Clinically Meaningful Benefit",purpose:"Distinguish patient-important improvements from statistical significance alone.",evidence:"Disease-specific clinical relevance threshold and prespecified patient outcomes."},
 {id:"durability",label:"Durability of Treatment Effect",purpose:"Determine how long treatment response, remission or clinical benefit is maintained.",evidence:"Matched follow-up windows, sustained response curves and censoring."},
 {id:"seriousAes",label:"Serious Adverse Event Difference",purpose:"Compare serious adverse events and treatment-associated risks against relevant therapy.",evidence:"Exposure-adjusted comparable SAE rates, attribution and follow-up."},
 {id:"responseRemission",label:"Responder / Remission Advantage",purpose:"Compare the share of patients reaching clinically meaningful response or remission.",evidence:"Same responder definition, denominator and follow-up time."},
 {id:"timeToResponse",label:"Time to Treatment Response",purpose:"Measure how quickly patients experience meaningful improvement.",evidence:"Comparator-aligned onset endpoint, median time and uncertainty."},
 {id:"bestSubgroup",label:"Best-Responding Patient Subgroup",purpose:"Identify patient characteristics and biomarkers associated with supported incremental benefit.",evidence:"Predefined subgroup analyses, interaction tests and population size."},
 {id:"treatmentResistantBenefit",label:"Treatment-Resistant Patient Advantage",purpose:"Assess benefit for patients with prior failures or intolerance to available treatment.",evidence:"Refractory subgroup eligibility, comparator and confirmed benefit."},
 {id:"qualityOfLife",label:"Quality-of-Life Improvement",purpose:"Compare validated patient-reported outcomes, functioning and daily-life effects.",evidence:"Validated scales, clinically important difference and missing-data impact."},
 {id:"discontinuation",label:"Treatment Discontinuation Difference",purpose:"Compare stops due to adverse events, treatment burden or lack of effect.",evidence:"Similar follow-up and denominators with reason-coded discontinuations."},
 {id:"hospitalizationReduction",label:"Hospitalization / Complication Reduction",purpose:"Measure prevention of hospital admission, complications or disability.",evidence:"Patient-relevant outcomes, event rates and comparator-adjusted effect."},
 {id:"switchingPool",label:"Switching-Eligible Patient Pool",purpose:"Estimate how many patients on current treatments could appropriately switch.",evidence:"Indication overlap, contraindications, switching evidence and treated denominators."},
 {id:"treatmentSequence",label:"Place in Treatment Sequence",purpose:"Identify whether the therapy is suitable for first-line, later-line or post-failure treatment.",evidence:"Proposed indication, pivotal trial population and guideline sequencing."},
 {id:"competitivePipelineThreat",label:"Competitive Pipeline Threat",purpose:"Identify late-stage challengers for the same patient group and material upcoming events.",evidence:"Unique comparator programs, trial status, readout dates and labels."},
 {id:"exclusivity",label:"Commercial Exclusivity Advantage",purpose:"Evaluate relevant intellectual-property and regulatory exclusivity constraints.",evidence:"Dated FDA exclusivity records, patent claims, term and litigation caveats."},
 {id:"valuePerOutcome",label:"Value per Clinical Outcome",purpose:"Compare added medical benefit with the incremental cost of treatment.",evidence:"Comparable cost bases, outcome measures, time horizon and sensitivity analysis."},
 {id:"overallRank",label:"Overall Competitive Advantage Rank",purpose:"Rank only genuinely comparable therapies by verified patient benefit and competitive evidence.",evidence:"Same indication, line and populations, transparent weights, uncertainty and sufficient comparator coverage."},
];
const original=COMPETITIVE_ASSESSMENT_COLUMNS.map(x=>({...x} as ResearchField));
const fields:ResearchField[]=[...original,...extra];
const byId=new Map<ResearchFieldId,ResearchField>(fields.map(x=>[x.id,x]));
function section(title:string,ids:ResearchFieldId[]){return {title,fields:ids.map(id=>{const found=byId.get(id);if(!found)throw Error("Research column is missing: "+id);return found;})};}
export const PIPELINE_RESEARCH_SECTIONS=[
 section("1. Trial Identity & Timeline",["trialId","company","therapy","indication","daysSinceReadout","daysToPdufa"]),
 section("2. Patients & Existing Treatments",["eligibleUsPatients","standardOfCare","unmetNeed","closestCompetitor","competitorCount","bestSubgroup","treatmentResistantBenefit"]),
 section("3. Clinical Superiority",["clinicalBenefit","headToHead","magnitude","meaningfulBenefit","durability","responseRemission","timeToResponse","qualityOfLife","hospitalizationReduction"]),
 section("4. Safety & Treatment Practicality",["safetyAdvantage","seriousAes","discontinuation","convenience"]),
 section("5. Market Adoption & Economics",["costDifference","payerAccess","adoption","switchingPool","treatmentSequence","valuePerOutcome"]),
 section("6. Competition & Defensibility",["competitivePipelineThreat","exclusivity","competitiveStrategy"]),
 section("7. Evidence, Conclusion & Ranking",["evidence","verdict","overallRank"]),
] as const;
export const PIPELINE_RESEARCH_FIELDS=PIPELINE_RESEARCH_SECTIONS.flatMap(x=>x.fields);

export type FieldResult={value:string;state:"RECORD"|"VERIFIED"|"MODELED"|"MISSING";why:string;sourceUrl:string|null;sourceDate:string|null;method:string|null;confidence:string|null};
const missing=(why:string):FieldResult=>({value:"Not assessed",state:"MISSING",why,sourceUrl:null,sourceDate:null,method:null,confidence:null});
function factResult(value:ResearchEvidence,unit=""):FieldResult {
 const txt=typeof value.value==="number"?value.value.toLocaleString("en-US")+unit:String(value.value);
 return {value:txt,state:value.status==="VERIFIED"?"VERIFIED":"MODELED",why:value.reason,sourceUrl:value.sourceUrl,sourceDate:value.sourceDate,method:value.method,confidence:value.confidence};
}
const identity=(row:PipelineResearchRow)=>({nctId:row.nctId,ticker:row.ticker,indication:row.indication});
function fact(row:PipelineResearchRow,id:string):ResearchEvidence|null{
 return verifiedCompetitiveFact(row.commercialAssessment,identity(row),id);
}
export function researchFieldResult(row:PipelineResearchRow,id:ResearchFieldId,today:string):FieldResult{
 if(id==="trialId")return {value:row.nctId,state:"RECORD",why:"Exact source NCT; pivotal status and commercial rights remain under review.",sourceUrl:row.sourceUrl,sourceDate:null,method:"Exact NCT plus ticker match to pinned census",confidence:null};
 if(id==="company"||id==="therapy"||id==="indication"){
  const value=id==="company"?row.company+" ("+row.ticker+")":id==="therapy"?row.drug:row.indication;
  return value?{value,state:"RECORD",why:"Recorded in reconciled POOL; sponsor, product and proposed indication require independent confirmation.",sourceUrl:row.sourceUrl,sourceDate:null,method:"Exact NCT / ticker source reconciliation",confidence:null}:missing("Not identified in the exact-matched research source.");
 }
 if(id==="daysSinceReadout"||id==="daysToPdufa"){
  const timeline=row.timeline||{phase3DataRelease:null,pdufaTarget:null};
  const counts=pipelineDayCounts(timeline,today);
  const source=id==="daysSinceReadout"?timeline.phase3DataRelease:timeline.pdufaTarget;
  const count=id==="daysSinceReadout"?counts.daysSincePhase3Release:counts.daysToPdufa;
  return source&&count!==null?{value:count+" days",state:"VERIFIED",why:id==="daysToPdufa"
    ?(counts.cutoffReached?"Reached PDUFA − 3 research cutoff":"Research window ends 3 calendar days before PDUFA")
    :"Calendar days since verified public Phase 3 data release, not study completion.",
   sourceUrl:source.sourceUrl,sourceDate:source.date,method:"Pacific calendar-date difference",confidence:"HIGH"}:
   missing(id==="daysSinceReadout"?"No verified public pivotal Phase 3 data-release date, or the release is in the future.":"No source-verified exact-program FDA PDUFA target date.");
 }
 if(id==="competitorCount"){
  const approved=fact(row,"approvedCompetitors"),late=fact(row,"lateStageCompetitors");
  if(approved&&late){
   return {value:(Number(approved.value)+Number(late.value)).toLocaleString("en-US")+" competitors",state:approved.status==="MODELED"||late.status==="MODELED"?"MODELED":"VERIFIED",
    why:"Approved "+approved.value+"; late-stage "+late.value+". Products must be deduplicated and indication-matched.",
    sourceUrl:approved.sourceUrl,sourceDate:approved.sourceDate,method:"Approved: "+approved.method+"; late-stage: "+late.method,confidence:approved.confidence===late.confidence?approved.confidence:"MIXED"};
  }
  return missing("Complete indication-matched inventory requires both approved and late-stage comparator counts. Missing does not equal zero.");
 }
 if(id==="costDifference"){
  const c=calculateTherapyCosts(row.therapyCostComparison);
  if(c.costDifferenceUsd!==null){
   const a=row.therapyCostComparison?.current,b=row.therapyCostComparison?.proposed;
   return {value:c.costDifferenceUsd.toLocaleString("en-US",{style:"currency",currency:"USD",maximumFractionDigits:0}),
    state:a?.evidenceStatus==="MODELED"||b?.evidenceStatus==="MODELED"?"MODELED":"VERIFIED",
    why:"Proposed first-12-month treatment cost minus current standard-of-care cost; negative indicates lower proposed cost. This is not patient copay.",
    sourceUrl:b?.sourceUrl||null,sourceDate:b?.sourceDate||null,method:"Both regimens include drug, administration and monitoring costs and share a comparable price basis.",confidence:null};
  }
  return missing("Comparable dated current and proposed first-year cost evidence is unavailable.");
 }
 if(id==="competitiveStrategy")return missing("Default review priorities exist, but the actual proposed drug has not earned a verified indication-specific strategy rank.");
 if(id==="evidence"){
  const verified=PIPELINE_RESEARCH_FIELDS.filter(x=>!["evidence","verdict","overallRank"].includes(x.id)&&
    researchFieldResultDirect(row,x.id,today).state==="VERIFIED").length;
  return {value:verified+" verified of "+(PIPELINE_RESEARCH_FIELDS.length-3)+" fields",state:"RECORD",
   why:"Evidence coverage only, not clinical success, eligibility, FDA approval probability or competitive rank.",
   sourceUrl:row.sourceUrl,sourceDate:null,method:"Count of individually source-verified research fields",confidence:null};
 }
 const supported=fact(row,id);
 if(supported)return factResult(supported,id==="adoption"?"% of eligible U.S. patients (12 mo)":"");
 return missing(id==="verdict"?"ABSTAIN: clinical and commercial evidence does not yet support a defensible peer comparison.":
  id==="overallRank"?"No comparable, sufficiently sourced peer group or independently checked competitive rank.":"No independently sourced, exact-program evidence is attached for this metric.");
}
function researchFieldResultDirect(row:PipelineResearchRow,id:ResearchFieldId,today:string):FieldResult {
 if(id==="evidence")return missing("Evidence index does not count itself.");
 return researchFieldResult(row,id,today);
}
export function verifiedMetricCount(row:PipelineResearchRow,today:string):number {
 return PIPELINE_RESEARCH_FIELDS.filter(x=>!["evidence","verdict","overallRank"].includes(x.id) && researchFieldResultDirect(row,x.id,today).state==="VERIFIED").length;
}
export const WORKFLOW_COLUMNS=[
 {id:"readout",label:"Verify Phase 3 readout"},
 {id:"pdufa",label:"Verify PDUFA date"},
 {id:"research",label:"Research competitive evidence"},
 {id:"approaching",label:"Within 90 days of PDUFA"},
 {id:"cutoff",label:"PDUFA − 3 reached"},
] as const;
export type WorkflowColumn=typeof WORKFLOW_COLUMNS[number]["id"];
export function workflowColumn(row:PipelineResearchRow,today:string):WorkflowColumn{
 const dates=row.timeline||{phase3DataRelease:null,pdufaTarget:null};
 if(!dates.phase3DataRelease)return "readout";
 if(!dates.pdufaTarget)return "pdufa";
 const days=pipelineDayCounts(dates,today).daysToPdufa;
 if(days!==null&&days<=3)return "cutoff";
 if(days!==null&&days<=90)return "approaching";
 return "research";
}
export function comparableIndication(row:PipelineResearchRow):string|null {
 return row.indication?.trim().toLocaleLowerCase("en-US")||null;
}
