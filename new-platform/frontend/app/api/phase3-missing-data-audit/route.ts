import ledger from "../../../public/phase3-unified-classifications-2026-11-05.json";
import adjudications from "../../../data/phase3EndpointAdjudications20261105.json";
import preData from "../../../data/phase3PreDataBatch20261105.json";
import officialResearch from "../../../data/phase3PreDataOfficialResearch.json";
import {UNIVERSAL_PHASE3_QUESTIONS} from "../../../lib/phase3-universal-questions";
import {phase3QuestionSlots} from "../../../lib/phase3-top-questions";

export const dynamic="force-dynamic";

const endpointByNct=new Map(adjudications.records.map(x=>[x.nctId,x] as const));
const preDataByNct=new Map(preData.trials.map(x=>[x.nctId,x] as const));
const officialByNct=new Set(officialResearch.records.map(x=>x.nctId));
type QuestionAudit={number:number;heading:string;predictions:number;observed:number;sourceFacts:number;unscored:number};
type TrialAudit={
 nctId:string;ticker:string;classificationCode:string;registryStatus:string;
 missingDrug:boolean;unknownRegistryStatus:boolean;hasDetailedOfficialResearch:boolean;
 hasStoredProtocol:boolean;hasEndpointAdjudication:boolean;
 unverifiedFDAApplication:boolean;unverifiedPDUFADate:boolean;outsideDatedMarketCapScreen:boolean;
 predicted:number;observed:number;sourceFacts:number;unscored:number;questionStatuses:string[];
};
function statusFor(
 q:ReturnType<typeof phase3QuestionSlots>[number],
 r:(typeof ledger.rows)[number],
 e:(typeof adjudications.records)[number]|undefined
){
 if(q.answer)return "PREDICTED_PRE_READOUT";
 if(q.number===1&&e?.endpointOutcome==="PRIMARY_ENDPOINT_MET")return "OBSERVED_PRIMARY_ENDPOINT_MET";
 if(q.number===1&&e?.endpointOutcome==="PRIMARY_ENDPOINT_NOT_MET")return "OBSERVED_PRIMARY_ENDPOINT_NOT_MET";
 if(q.number===1&&e?.endpointOutcome==="NO_BINARY_PASS_FAIL")return "DOCUMENTED_NON_BINARY_ENDPOINT";
 if(q.number===29&&e)return "DOCUMENTED_PUBLIC_READOUT";
 if(q.observation)return "SOURCE_FACT_ONLY";
 if(q.number===25&&r.registrySourceUrl)return "SOURCE_FACT_ONLY";
 if(q.number===27&&/\bplacebo\b/i.test(r.registeredInterventions||""))return "SOURCE_FACT_ONLY";
 return "UNSCORED";
}
const counts=(statuses:string[])=>({
 predicted:statuses.filter(x=>x==="PREDICTED_PRE_READOUT").length,
 observed:statuses.filter(x=>x.startsWith("OBSERVED_")||x.startsWith("DOCUMENTED_")).length,
 sourceFacts:statuses.filter(x=>x==="SOURCE_FACT_ONLY").length,
 unscored:statuses.filter(x=>x==="UNSCORED").length
});
const escapeCsv=(v:unknown)=>{
 let s=v===null||v===undefined?"":String(v).replace(/[\r\n]+/g," ");
 if(/^[=+@-]/.test(s))s="'"+s;
 return '"'+s.replace(/"/g,'""')+'"';
};
const csv=(v:unknown[])=>v.map(escapeCsv).join(",");
export async function GET(request:Request){
 if(ledger.total!==762||ledger.rows.length!==762||
    new Set(ledger.rows.map(r=>r.nctId)).size!==762||
    UNIVERSAL_PHASE3_QUESTIONS.length!==30||
    preData.trials.length!==253||
    officialResearch.records.length!==253||
    adjudications.records.length!==19){
   return Response.json({error:"The research snapshot failed a count/identity check"},{status:503});
 }
 const perQuestion:QuestionAudit[]=UNIVERSAL_PHASE3_QUESTIONS.map((q,i)=>({
  number:i+1,heading:q.heading,predictions:0,observed:0,sourceFacts:0,unscored:0
 }));
 const rows:TrialAudit[]=[];
 for(const r of ledger.rows){
  const evidence=endpointByNct.get(r.nctId),p=preDataByNct.get(r.nctId);
  const slots=phase3QuestionSlots(r.nctId);
  const statuses=slots.map(q=>statusFor(q,r,evidence));
  if(statuses.length!==30)return Response.json({error:"Question count mismatch"},{status:503});
  const c=counts(statuses);
  for(let i=0;i<30;i++){
   const q=perQuestion[i],st=statuses[i];
   if(st==="PREDICTED_PRE_READOUT")q.predictions++;
   else if(st==="SOURCE_FACT_ONLY")q.sourceFacts++;
   else if(st==="UNSCORED")q.unscored++;
   else q.observed++;
  }
  rows.push({
   nctId:r.nctId,ticker:r.ticker,classificationCode:r.classificationCode,
   registryStatus:r.registryStatus,missingDrug:!r.drug,
   unknownRegistryStatus:!r.registryStatus||r.registryStatus==="UNKNOWN",
   hasDetailedOfficialResearch:officialByNct.has(r.nctId),
   hasStoredProtocol:Boolean(p?.protocol),
   hasEndpointAdjudication:Boolean(evidence),
   unverifiedFDAApplication:r.fdaApplicationStatus==="NOT_VERIFIED",
   unverifiedPDUFADate:!r.pdufaGoalDate,
   outsideDatedMarketCapScreen:!r.inDatedMarketCapScreen,
   ...c,questionStatuses:statuses
  });
 }
 const total=rows.length*30;
 const assessment={
  totalSlots:total,
  predicted:rows.reduce((a,r)=>a+r.predicted,0),
  observed:rows.reduce((a,r)=>a+r.observed,0),
  sourceFacts:rows.reduce((a,r)=>a+r.sourceFacts,0),
  unscored:rows.reduce((a,r)=>a+r.unscored,0),
  trialsWithNumericalPredictions:rows.filter(r=>r.predicted>0).length,
  trialsWithOutcomeAdjudication:rows.filter(r=>r.hasEndpointAdjudication).length
 };
 const fields={
  missingDrugField:rows.filter(r=>r.missingDrug).length,
  unknownRegistryStatus:rows.filter(r=>r.unknownRegistryStatus).length,
  detailedOfficialResearch:rows.filter(r=>r.hasDetailedOfficialResearch).length,
  missingDetailedOfficialResearch:rows.filter(r=>!r.hasDetailedOfficialResearch).length,
  storedProtocol:rows.filter(r=>r.hasStoredProtocol).length,
  missingStoredProtocol:rows.filter(r=>!r.hasStoredProtocol).length,
  unverifiedFDAApplication:rows.filter(r=>r.unverifiedFDAApplication).length,
  unverifiedPDUFADate:rows.filter(r=>r.unverifiedPDUFADate).length,
  missingAdjudicatedEndpoint:rows.filter(r=>!r.hasEndpointAdjudication).length,
  outsideDatedMarketCapScreen:rows.filter(r=>r.outsideDatedMarketCapScreen).length
 };
 if(assessment.totalSlots!==22860||
    assessment.predicted+assessment.observed+assessment.sourceFacts+assessment.unscored!==total||
    assessment.trialsWithNumericalPredictions!==4||
    assessment.trialsWithOutcomeAdjudication!==19||
    fields.unknownRegistryStatus!==3||
    fields.missingDrugField!==753){
  return Response.json({error:"Missingness audit reconciliation failed"},{status:503});
 }
 const report={
  asOf:ledger.asOf,officialResearchAsOf:officialResearch.asOf,
  scope:"Saved research evidence and numerical assessments; NOT a live recrawl of 762 trial registries",
  trials:rows.length,questionsPerTrial:30,columnsInAssessmentExport:190,
  assessment,fields,perQuestion,
  endpointOutcomes:adjudications.counts,
  exceptions:{
   unknownRegistryNcts:rows.filter(r=>r.unknownRegistryStatus).map(r=>r.nctId),
   outsideMarketCapScreenNcts:rows.filter(r=>r.outsideDatedMarketCapScreen).map(r=>r.nctId)
  },
  notes:[
   "Unscored means no verified source fact or defensible numerical prediction is stored for that question; it does not prove evidence is absent publicly.",
   "Source-fact columns document available registry facts, not favorable clinical or FDA predictions.",
   "All 762 trials have registered intervention text; a missing separately named drug field is not evidence that the drug is unknown.",
   "Not every historical or pre-readout Phase 3 trial has an FDA application or PDUFA date."
  ]
 };
 const u=new URL(request.url);
 if(u.searchParams.get("format")==="csv"){
  const base=[
   "NCT","Ticker","Classification","Registry status","Separate drug field missing",
   "Registry status unknown","Detailed official registry saved","Protocol summary saved",
   "Primary endpoint reviewed","FDA application not verified","PDUFA date not verified",
   "Outside dated market cap screen","Numerically predicted questions",
   "Observed endpoint/readout facts","Documented source facts","Unscored questions"
  ];
  const headers=[...base,...UNIVERSAL_PHASE3_QUESTIONS.map((_,i)=>"Q"+String(i+1).padStart(2,"0")+" status")];
  const lines=[csv(headers),...rows.map(r=>csv([
   r.nctId,r.ticker,r.classificationCode,r.registryStatus,r.missingDrug,
   r.unknownRegistryStatus,r.hasDetailedOfficialResearch,r.hasStoredProtocol,
   r.hasEndpointAdjudication,r.unverifiedFDAApplication,r.unverifiedPDUFADate,
   r.outsideDatedMarketCapScreen,r.predicted,r.observed,r.sourceFacts,r.unscored,
   ...r.questionStatuses
  ]))];
  if(lines.length!==763||headers.length!==46)
   return Response.json({error:"CSV row/column count mismatch"},{status:503});
  return new Response("\uFEFF"+lines.join("\r\n")+"\r\n",{
   status:200,headers:{
    "Content-Type":"text/csv; charset=utf-8",
    "Content-Disposition":'attachment; filename="Phase3-762-Trials-Missing-Data-Audit.csv"',
    "Cache-Control":"no-store"
   }
  });
 }
 return Response.json(report,{headers:{"Cache-Control":"no-store"}});
}
