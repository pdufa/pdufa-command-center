/** Export RAAS RESEARCH metric requirements strictly from the two
 * source-classified TOP and BOTTOM Phase 3 spreadsheets, never from the
 * unscreened 11k+ POOL, 762 registry-preparation queue, or an unverified
 * readout-stage row. Does not create or approve numerical full RAAS scores.
 */
import type {ReadoutRow} from "./phase3-public-readout";
import {RAAS_METRIC_CATALOG,type RaasStage} from "./raas-metric-specs";
import {RAAS_PROVISIONAL_RUBRICS} from "./raas-provisional-rubric-engine";
import {fullReviewedTrialCandidate} from "./raas-reviewed-full-score";

const headers=[
 "nctId","ticker","phase3Spreadsheet","readoutEvidenceKind",
 "drug","indication","issuerEvidenceDate","issuerEvidenceUrl",
 "metricId","category","metricName","categoryWeightPct",
 "metricEvidenceStatus","existingProvisionalScoreOrBlank","reviewDate",
 "reviewSourceDate","reviewSourceUrl","independentBenchmarkSourceUrl",
 "requiredEvidence","benchmarkRequirement","criticalRisk",
 "nextReviewAction","fullValidatedRaasScore","fdaPassCrlExtensionProbability"
] as const;
const date=(x:string)=>/^\d{4}-\d{2}-\d{2}$/.test(x)&&
 !Number.isNaN(Date.parse(x+"T00:00:00Z"))&&
 new Date(x+"T00:00:00Z").toISOString().slice(0,10)===x;
const cell=(x:string|number|null|undefined)=>{
 const raw=x==null?"":String(x);
 const safe=/^[=+@\-\t\r]/.test(raw)?"'"+raw:raw;
 return /[",\r\n]/.test(safe)?'"'+safe.replace(/"/g,'""')+'"':safe;
};
const line=(xs:readonly (string|number|null|undefined)[])=>
 xs.map(cell).join(",");

export function buildTopBottomRaasMetricWorklist(
 stage:RaasStage,classifiedRows:readonly ReadoutRow[]
):{
 csv:string;summary:{
  sheet:"TOP"|"BOTTOM";classifiedTrials:number;metricRequirementRows:number;
  existingProvisionalGrades:number;reviewMissingRows:number;
  approvedOverallRaasScores:0;calibratedFdaForecasts:0;
 }
}{
 if(stage!=="pre"&&stage!=="post")throw Error("RAAS_ONLY_TOP_BOTTOM_SHEETS");
 if(!Array.isArray(classifiedRows)||classifiedRows.length>2000)
  throw Error("RAAS_STAGE_SHEET_SOURCE_SIZE_INVALID");
 const expected=stage==="pre"?"PRE_AS_OF_CHECK":"POST_PUBLIC_READOUT";
 const group=RAAS_METRIC_CATALOG[stage];
 if(group.length!==6||group.some(c=>c.metrics.length!==5)||
  group.flatMap(c=>c.metrics).length!==30)
  throw Error("RAAS_STAGE_SHEET_METRIC_CATALOG_INVALID");
 const rubricMap=new Map(RAAS_PROVISIONAL_RUBRICS.filter(x=>x.stage===stage)
  .map(x=>[x.metricId,x]));
 if(rubricMap.size!==30)
  throw Error("RAAS_STAGE_SHEET_RUBRIC_INCOMPLETE");
 const seen=new Set<string>(),csv=[headers.join(",")];
 let grades=0;
 for(const row of [...classifiedRows].sort((a,b)=>a.nctId.localeCompare(b.nctId))){
  const e=row?.evidence;
  if(!e||e.kind!==expected||e.nctId!==row.nctId||
   e.ticker!==row.ticker||!/^NCT\d{8}$/.test(row.nctId)||
   !row.ticker?.trim()||seen.has(row.nctId)||
   !date(e.evidenceDate)||!e.evidenceUrl?.startsWith("https://")||
   !e.drug?.trim()||!e.indication?.trim()||
   row.sourceUrl!=="https://clinicaltrials.gov/study/"+row.nctId)
   throw Error("RAAS_STAGE_SHEET_UNVERIFIED_OR_MISMATCHED_ROW");
  seen.add(row.nctId);
  // Exact trial, ticker, therapy, indication, stage. No ticker-only joins.
  const reviewed=fullReviewedTrialCandidate({
   nctId:row.nctId,ticker:row.ticker,drug:e.drug,indication:e.indication
  },stage,false);
  const known=new Map(reviewed.grades.map(x=>[x.metricId,x]));
  if(known.size!==reviewed.reviewedCount)
   throw Error("RAAS_STAGE_SHEET_REVIEW_NOT_UNIQUE");
  for(const category of group){
   for(const m of category.metrics){
    const rubric=rubricMap.get(m.id);
    if(!rubric||rubric.approvedForComposite!==false)
     throw Error("RAAS_STAGE_SHEET_RUBRIC_NOT_RESEARCH_ONLY");
    const review=known.get(m.id);
    if(review)grades++;
    csv.push(line([
     row.nctId,row.ticker,stage==="pre"?"TOP":"BOTTOM",e.kind,
     e.drug,e.indication,e.evidenceDate,e.evidenceUrl,
     m.id,category.name,m.name,category.weight,
     review?review.reviewClass==="INDEPENDENT_REVIEW"?
      "PROVISIONAL_INDEPENDENT_REVIEW_NOT_VALIDATED":
      "PROVISIONAL_AI_SOURCE_CROSSCHECK_NOT_VALIDATED":
      "MISSING_DOCUMENTED_METRIC_REVIEW",
     review?.score??null,review?.assessedAt??null,
     review?.sourceDate??null,review?.sourceUrl??null,
     review?.benchmarkSourceUrl??null,
     m.requiredEvidence,rubric.benchmarkRequirement,m.criticalRisk,
     review?
      "Verify source, uncertainty and independent review; do not imply model accuracy":
      "Collect exact-therapy primary evidence and independent metric benchmark before grading",
     null,null
    ]));
   }
  }
 }
 if(csv.length!==classifiedRows.length*30+1)
  throw Error("RAAS_STAGE_SHEET_METRIC_OUTPUT_MISMATCH");
 return {
  csv:csv.join("\r\n")+"\r\n",
  summary:{
   sheet:stage==="pre"?"TOP":"BOTTOM",
   classifiedTrials:classifiedRows.length,
   metricRequirementRows:classifiedRows.length*30,
   existingProvisionalGrades:grades,
   reviewMissingRows:classifiedRows.length*30-grades,
   approvedOverallRaasScores:0,calibratedFdaForecasts:0
  }
 };
}
