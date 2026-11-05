/** Browser-safe schema and structural preflight for unsigned RAAS worksheets.
 * NEVER an authenticated reviewer sign-off, medical evaluation, score,
 * source-quality assessment, or FDA prediction.
 */
import type {TrialMetricReviewDossier} from "./raas-trial-metric-review-dossier";
export const REVIEW_WORKSHEET_HEADERS=[
 "nctId","ticker","registrySourceHash","registrySnapshotAsOf","stage",
 "metricId","metricName","category","metricWeightPercent",
 "requiredEvidence","criticalRisk","registeredRegistrySource",
 "registrySourceLeads","registryNumericLeads","provisionalResearchFinding",
 "provisionalResearchBandNotApproved","provisionalSourceUrl","provisionalBenchmarkUrl",
 "reviewerStatus","reviewerProposedBandNotApproved","reviewerPrimarySourceUrl",
 "reviewerSourceDate","reviewerBenchmarkSourceUrl","reviewerBenchmarkContext",
 "reviewerObservedFinding","reviewerUncertaintyReview","reviewerCriticalRiskReview",
 "reviewerMethodNotes","externalIndependentAuthenticationRequired"
] as const;
export const EDITABLE_REVIEW_COLUMNS=new Set<number>([18,19,20,21,22,23,24,25,26,27]);
export type WorksheetIssue={metricId:string;code:string;description:string};
export type WorksheetMetricPreflight={
 metricId:string;stage:"pre"|"post";status:string;issues:WorksheetIssue[];
 evidenceFieldsComplete:boolean;readyForExternalReview:boolean;
};
export type WorksheetPreflight={
 scope:"RAAS_LOCAL_WORKSHEET_STRUCTURAL_PREFLIGHT_NOT_CERTIFICATION";
 nctId:string;ticker:string;registrySourceHash:string;registrySnapshotAsOf:string;
 expectedMetricRows:60;receivedMetricRows:number;
 schemaValid:boolean;blockedRows:number;readyForExternalReview:number;
 completedEvidenceFields:number;independentlyAuthenticatedMetrics:0;
 approvedRaasScores:0;calibratedFdaPredictions:0;
 issues:WorksheetIssue[];metrics:WorksheetMetricPreflight[];
};
function escapedSheetText(str:string):string{
 return /^\s*[=+@-]/.test(str)?"'"+str:str;
}
function safeCell(value:unknown):string{
 return '"'+escapedSheetText(String(value??"")).replaceAll('"','""')+'"';
}
export function expectedReviewerRows(dossier:TrialMetricReviewDossier):string[][]{
 const rows=(["pre","post"] as const).flatMap(stage=>
  dossier.perStage[stage].categories.flatMap(category=>
   category.metrics.map(metric=>[
    dossier.trial.nctId,dossier.trial.ticker,dossier.trial.sourceHash,
    dossier.registrySnapshotAsOf,stage,metric.metricId,metric.name,
    category.name,String(metric.metricWeightPercent),metric.requiredEvidence,
    metric.criticalRisk,dossier.trial.sourceUrl,
    String(metric.registryLeadCount),String(metric.registryRawNumericCount),
    metric.provisionalReview?.finding??"",
    String(metric.provisionalReview?.researchBand??""),
    metric.provisionalReview?.sourceUrl??"",
    metric.provisionalReview?.benchmarkSourceUrl??"",
    "NOT_STARTED","","","","","","","","","",
    "EXTERNAL_AUTHENTICATION_REQUIRED"
   ])));
 if(rows.length!==60||rows.some(r=>r.length!==REVIEW_WORKSHEET_HEADERS.length))
  throw Error("RAAS_REVIEW_WORKSHEET_COLUMN_PARITY");
 return rows;
}
export function serializeReviewerWorksheet(dossier:TrialMetricReviewDossier):string{
 return "\uFEFF"+REVIEW_WORKSHEET_HEADERS.join(",")+"\r\n"+
  expectedReviewerRows(dossier).map(row=>row.map(safeCell).join(",")).join("\r\n")+"\r\n";
}
/** Strict, bounded RFC-4180 quoted-value support, including embedded newlines. */
export function parseReviewerWorksheetCsv(csv:string):string[][]{
 if(typeof csv!=="string"||csv.length>2_000_000||csv.length===0)
  throw Error("RAAS_WORKSHEET_FILE_EMPTY_OR_OVERSIZE");
 const source=csv.charCodeAt(0)===0xfeff?csv.slice(1):csv;
 const rows:string[][]=[];let row:string[]=[],value="",quoted=false,closed=false,started=false;
 const cell=()=>{row.push(value);value="";closed=false;started=false;};
 const end=()=>{cell();rows.push(row);row=[];if(rows.length>61)
  throw Error("RAAS_WORKSHEET_TOO_MANY_ROWS");};
 for(let i=0;i<source.length;i++){
  const ch=source[i];
  if(quoted){
   if(ch==='"'){
    if(source[i+1]==='"'){value+='"';i++;}else{quoted=false;closed=true;}
   }else value+=ch;
  }else if(ch===","){cell();}
  else if(ch==="\n"||ch==="\r"){
   if(ch==="\r"&&source[i+1]==="\n")i++;
   end();
  }else if(ch==='"'&&!started&&!closed){quoted=true;started=true;}
  else{
   if(closed||ch==='"')throw Error("RAAS_WORKSHEET_MALFORMED_CSV_QUOTING");
   value+=ch;started=true;
  }
  if(value.length>20_000)throw Error("RAAS_WORKSHEET_CELL_TOO_LONG");
 }
 if(quoted)throw Error("RAAS_WORKSHEET_UNCLOSED_CSV_QUOTE");
 if(value!==""||started||row.length)end();
 return rows;
}
const dates=(s:string)=>/^\d{4}-\d{2}-\d{2}$/.test(s)&&
 !Number.isNaN(Date.parse(s+"T00:00:00Z"))&&
 new Date(s+"T00:00:00Z").toISOString().slice(0,10)===s;
const validUrl=(s:string)=>s.length<=1500&&
 /^https:\/\/[^\s/@?#]+\.[^\s/@?#]+\/\S+$/.test(s);
const substantive=(s:string)=>s.trim().length>=12&&s.length<=5000;
const allowedStatus=new Set(["NOT_STARTED","IN_PROGRESS","BLOCKED","READY_FOR_EXTERNAL_REVIEW"]);
const allowedGrades=new Set(["","0","25","50","75","100"]);
function addIssue(issues:WorksheetIssue[],metricId:string,code:string,description:string){
 issues.push({metricId,code,description});
}
export function auditReviewerWorksheetCsv(
 csv:string,dossier:TrialMetricReviewDossier
):WorksheetPreflight{
 const rows=parseReviewerWorksheetCsv(csv);
 const expected=expectedReviewerRows(dossier),issues:WorksheetIssue[]=[];
 const headings=[...REVIEW_WORKSHEET_HEADERS];
 if(!rows.length||rows[0].length!==headings.length||
  !headings.every((h,i)=>rows[0][i]===h))
  throw Error("RAAS_WORKSHEET_WRONG_SCHEMA_DOWNLOAD_LATEST");
 const received=rows.slice(1);
 if(received.length!==60)
  addIssue(issues,"ALL","MISSING_OR_EXTRA_METRIC_ROWS",
   "Expected exactly 60 distinct TOP/BOTTOM RAAS rows.");
 const expectedById=new Map(expected.map(r=>[r[5],r]));
 const receivedIds=new Set<string>();
 const detail:WorksheetMetricPreflight[]=[];
 for(const [offset,row] of received.entries()){
  const rawId=row[5]??"ROW-"+(offset+2);
  const metricId=rawId.slice(0,70);
  const problems:WorksheetIssue[]=[];
  if(row.length!==headings.length){
   addIssue(problems,metricId,"WRONG_COLUMN_COUNT",
    "CSV row does not contain the exact worksheet column count.");
  }
  const canonical=expectedById.get(rawId);
  if(!canonical){
   addIssue(problems,metricId,"UNKNOWN_METRIC",
    "The worksheet contains a metric outside this trial's RAAS catalog.");
  }
  if(receivedIds.has(rawId))
   addIssue(problems,metricId,"DUPLICATE_METRIC","Metric appears more than once.");
  receivedIds.add(rawId);
  if(canonical&&row.length===headings.length){
   for(let i=0;i<headings.length;i++){
    if(!EDITABLE_REVIEW_COLUMNS.has(i)&&row[i]!==escapedSheetText(canonical[i])){
     addIssue(problems,metricId,"SOURCE_OR_CATALOG_MODIFIED",
      "Protected value changed: "+headings[i]+". Redownload the exact trial worksheet.");
    }
   }
  }
  const status=row[18]??"";
  if(!allowedStatus.has(status))
   addIssue(problems,metricId,"INVALID_REVIEW_STATUS",
    "Status must be NOT_STARTED, IN_PROGRESS, BLOCKED, or READY_FOR_EXTERNAL_REVIEW.");
  if(!allowedGrades.has(row[19]??""))
   addIssue(problems,metricId,"INVALID_PROPOSED_BAND",
    "Unapproved reviewer band must be blank, 0, 25, 50, 75, or 100.");
  if((row[20]??"")!==""&&!validUrl(row[20]))
   addIssue(problems,metricId,"INVALID_PRIMARY_URL","Use a full HTTPS primary source URL.");
  if((row[22]??"")!==""&&!validUrl(row[22]))
   addIssue(problems,metricId,"INVALID_BENCHMARK_URL","Use a full HTTPS independent benchmark URL.");
  if((row[21]??"")!==""&&!dates(row[21]))
   addIssue(problems,metricId,"INVALID_SOURCE_DATE","Source date must be an actual YYYY-MM-DD date.");
  const complete=allowedGrades.has(row[19]??"")&&(row[19]??"")!==""&&
   validUrl(row[20]??"")&&validUrl(row[22]??"")&&
   row[20]!==row[22]&&dates(row[21]??"")&&
   [23,24,25,26,27].every(i=>substantive(row[i]??""));
  if(status==="READY_FOR_EXTERNAL_REVIEW"&&!complete){
   addIssue(problems,metricId,"REVIEW_FIELDS_INCOMPLETE",
    "A ready-for-external-review row needs one proposed band, distinct primary and benchmark URLs, real source date, and substantive findings, uncertainty, critical risk, benchmark context, and method.");
  }
  if((row[20]??"")!==""&&row[20]===row[22])
   addIssue(problems,metricId,"SELF_BENCHMARK",
    "The primary source and independent benchmark cannot be identical.");
  if(["READY_FOR_EXTERNAL_REVIEW"].includes(status)&&dossier.ambiguousProgramReviews)
   addIssue(problems,metricId,"UNRESOLVED_PROGRAM_IDENTITY",
    "Multiple drug/indication programs share this NCT; independently reconcile the exact program.");
  if(["READY_FOR_EXTERNAL_REVIEW"].includes(status)&&
    dossier.trial.stage==="unverified")
   addIssue(problems,metricId,"READOUT_STAGE_UNVERIFIED",
    "Separate dated evidence of public readout is required before treating TOP/BOTTOM as verified.");
  if(["READY_FOR_EXTERNAL_REVIEW"].includes(status)&&
    dossier.trial.stage!=="unverified"&&row[4]!==dossier.trial.stage)
   addIssue(problems,metricId,"STAGE_NOT_SUPPORTED_BY_SNAPSHOT",
    "Selected stage does not match the dated stage lead in the saved snapshot.");
  issues.push(...problems);
  detail.push({metricId,stage:row[4]==="post"?"post":"pre",status,
   issues:problems,evidenceFieldsComplete:complete,
   readyForExternalReview:status==="READY_FOR_EXTERNAL_REVIEW"&&problems.length===0});
 }
 for(const canonical of expected){
  if(!receivedIds.has(canonical[5]))
   addIssue(issues,canonical[5],"MISSING_METRIC","The expected metric is missing from the file.");
 }
 const schemaValid=issues.every(i=>i.code!=="MISSING_OR_EXTRA_METRIC_ROWS"&&
  i.code!=="MISSING_METRIC"&&i.code!=="DUPLICATE_METRIC"&&
  i.code!=="WRONG_COLUMN_COUNT"&&i.code!=="UNKNOWN_METRIC"&&
  i.code!=="SOURCE_OR_CATALOG_MODIFIED");
 return {
  scope:"RAAS_LOCAL_WORKSHEET_STRUCTURAL_PREFLIGHT_NOT_CERTIFICATION",
  nctId:dossier.trial.nctId,ticker:dossier.trial.ticker,
  registrySourceHash:dossier.trial.sourceHash,
  registrySnapshotAsOf:dossier.registrySnapshotAsOf,
  expectedMetricRows:60,receivedMetricRows:received.length,schemaValid,
  blockedRows:detail.filter(x=>x.issues.length>0).length,
  readyForExternalReview:detail.filter(x=>x.readyForExternalReview).length,
  completedEvidenceFields:detail.filter(x=>x.evidenceFieldsComplete).length,
  independentlyAuthenticatedMetrics:0,approvedRaasScores:0,
  calibratedFdaPredictions:0,issues,metrics:detail
 };
}
