import { programEligibility, type ProgramEligibilityEvidence } from "./pipeline-program-eligibility";
import { createHash } from "node:crypto";
import { PIPELINE_RESEARCH_FIELDS, researchFieldResult, workflowColumn, type PipelineResearchRow } from "./pipeline-research-view";
import { RANKED_BENEFIT_ASSESSMENTS, assessmentCoverage, validateComparatorInventory } from "./pipeline-benefit-assessments";
/** Both website and Sheets consume the authenticated scope-funnel dataset. */
export function canonicalResearchPage(page:{datasetVersion:string;rows:PipelineResearchRow[];total:number;offset:number;limit:number;nextOffset:number|null;overview:unknown},today:string){
 const records=page.rows.map(row=>{
  const identity={nctId:row.nctId,ticker:row.ticker,drug:row.drug,indication:row.indication};
  const fields=PIPELINE_RESEARCH_FIELDS.map(field=>({id:field.id,label:field.label,...researchFieldResult(row,field.id,today)}));
  const coverage=assessmentCoverage(row,today);
  const competitors=validateComparatorInventory(row,row.competitorEvidence||[]);
  const eligibility=programEligibility({nctId:row.nctId,ticker:row.ticker,drug:row.drug||"",indication:row.indication||"",sponsor:row.company},(row as PipelineResearchRow & {eligibilityEvidence?:ProgramEligibilityEvidence}).eligibilityEvidence,today);
  const recordId=createHash("sha256").update(JSON.stringify(identity)).digest("hex");
  return {recordId,recordVersion:page.datasetVersion,...identity,company:row.company,sourceUrl:row.sourceUrl,
   qualification:eligibility.status,researchWindow:eligibility.researchWindow,qualificationReasons:[...row.reasons,...eligibility.reasons],programId:null,
   classification:"HISTORICAL_RESEARCH_QUEUE",timeline:row.timeline||null,
   workflow:workflowColumn(row,today),fields,
   assessments:RANKED_BENEFIT_ASSESSMENTS.map((spec,i)=>({...coverage[i],objective:spec.objective,
    inputs:spec.fields.map(id=>({id,...researchFieldResult(row,id,today)}))})),
   competitors:competitors.accepted,competitorInventoryComplete:false,
   approvedCompetitors:competitors.accepted.length?competitors.approved:null,
   pipelineCompetitors:competitors.accepted.length?competitors.pipeline:null,
   comparativeRank:null,regulatoryPredictionIncluded:false};
 });
 return {schemaVersion:1,datasetVersion:page.datasetVersion,asOf:today,total:page.total,offset:page.offset,
  limit:page.limit,nextOffset:page.nextOffset,overview:page.overview,
  originalFieldCount:38,assessmentCount:20,verifiedEligiblePrograms:null,
  records};
}
