import ledger from "../../../public/phase3-unified-classifications-2026-11-05.json";
import endpointAdjudications from "../../../data/phase3EndpointAdjudications20261105.json";
import {UNIVERSAL_PHASE3_QUESTIONS} from "../../../lib/phase3-universal-questions";
import {phase3QuestionSlots} from "../../../lib/phase3-top-questions";

export const dynamic = "force-dynamic";

/** One Phase 3 trial per exact NCT; predictions never count as observed PASS/FAIL. */
const baseHeaders = [
 "NCT","Ticker","Company","Trial Classification","Classification Code",
 "Current Registry Status","Original Roster Status","Registry Snapshot Date",
 "Readout Evidence Type","Public Readout Evidence Date","Readout Outcome","Drug",
 "Indication","Registered Interventions","FDA Application Status","FDA Review Type",
 "PDUFA Goal Date","Readout Source URL","Registry Source URL","Classification Basis"
];
const extendedHeaders = [
 "Passing Classification","Passing Classification Rationale","Passing Evidence URL",
 "Passing Evidence Reviewed At","Passing Evidence Type","Results Publication Group",
 "Readout Evidence Verified","Registry State Group","Registry Source As Of",
 "Market Cap Source Status","In Dated $300M–$10B Screen","FDA Application Verified",
 "PDUFA Date Verified","Predictions Completed","Documented Source Facts",
 "Questions Not Scored","Question Model","Research Source Coverage",
 "Unified Ledger As Of","Interpretation Note"
];
const questionHeaders = UNIVERSAL_PHASE3_QUESTIONS.flatMap((q,i)=>{
 const p="Q"+String(i+1).padStart(2,"0")+" "+q.heading+" — ";
 return [p+"Evidence status",p+"Predicted outcome",p+"Score 0–100 (subjective)",
  p+"Evidence / missing information",p+"Source URL(s)"];
});
const HEADERS=[...baseHeaders,...extendedHeaders,...questionHeaders];
const endpointByNct=new Map(endpointAdjudications.records.map(x=>[x.nctId,x] as const));

const escaped=(input:unknown):string=>{
 let s=input===null||input===undefined?"":String(input);
 s=s.replace(/[\r\n]+/g," ");
 if(/^[=+\-@]/.test(s))s="'"+s;
 return '"'+s.replace(/"/g,'""')+'"';
};
const writeRow=(cells:unknown[])=>cells.map(escaped).join(",");

export async function GET(){
 if(HEADERS.length!==190||ledger.total!==762||ledger.rows.length!==762||
    new Set(ledger.rows.map(r=>r.nctId)).size!==762||
    endpointByNct.size!==20||endpointAdjudications.records.length!==20||
    endpointAdjudications.records.some(x=>!ledger.rows.some(r=>r.nctId===x.nctId))){
  return Response.json({error:"Phase 3 190-column ledger integrity check failed"},{status:503});
 }
 const rows=[writeRow(HEADERS)];
 let passedCount=0,failedCount=0;
 for(const r of ledger.rows){
  const endpoint=endpointByNct.get(r.nctId);
  const outcome=endpoint?.endpointOutcome||r.readoutOutcome;
  const endpointEvidenceUrl=endpoint?.evidenceUrl||r.readoutEvidenceUrl||"";
  const observedPass=outcome==="PRIMARY_ENDPOINT_MET"&&
   Boolean(endpointEvidenceUrl)&&(Boolean(endpoint)||r.classificationVerified);
  const observedFail=outcome==="PRIMARY_ENDPOINT_NOT_MET"&&
   Boolean(endpointEvidenceUrl)&&Boolean(endpoint);
  const noBinary=outcome==="NO_BINARY_PASS_FAIL";
  if(observedPass)passedCount++;
  if(observedFail)failedCount++;
  const passing=observedPass?"PASS_DOCUMENTED_PRIMARY_ENDPOINT":
   observedFail?"FAIL_DOCUMENTED_PRIMARY_ENDPOINT":
   noBinary?"NON_BINARY_ENDPOINT":"UNDETERMINED";
  const passRationale=endpoint?.rationale||
   (r.classificationCode==="P3_TERMINATED"?"Trial terminated; an efficacy FAIL is not established by trial status":
    r.classificationCode==="P3_WITHDRAWN"?"Trial withdrawn; an efficacy FAIL is not established by trial status":
    "No source-qualified Phase 3 primary-endpoint determination available in the saved evidence");
  const slots=phase3QuestionSlots(r.nctId);
  const predictions=slots.filter(q=>Boolean(q.answer)).length;
  const observations=slots.filter(q=>!q.answer&&Boolean(q.observation)).length;
  const base=[
   r.nctId,r.ticker,r.company,r.classification,r.classificationCode,
   r.registryStatus,r.rosterStatus,r.registryAsOf,r.readoutEvidenceType,
   r.readoutSourceDate,outcome,r.drug,r.indication,r.registeredInterventions,
   r.fdaApplicationStatus,r.fdaReviewType,r.pdufaGoalDate,endpointEvidenceUrl,
   r.registrySourceUrl,r.classificationEvidence
  ];
  const extra=[
   passing,passRationale,endpoint?endpointEvidenceUrl:observedPass?endpointEvidenceUrl:"",
   endpoint?.reviewedAt||r.readoutSourceDate||"",
   endpoint?.evidenceType||r.readoutEvidenceType||"NOT_VERIFIED",
   r.classificationCode,Boolean(endpoint)||r.classificationVerified,
   r.registryStatus,r.registryAsOf,r.marketCapSourceStatus,r.inDatedMarketCapScreen,
   r.fdaApplicationStatus!=="NOT_VERIFIED",Boolean(r.pdufaGoalDate),
   predictions,observations,30-predictions-observations,
   "UNIVERSAL_PHASE3_30_QUESTION_EVIDENCE_AWARE_V1",
   predictions?"REVIEWED_PRE_READOUT_PREDICTIONS":
    observations?"PARTIAL_REGISTRY_SOURCE_FACTS":"NO_REVIEWED_QUESTION_EVIDENCE",
   ledger.asOf,"Research classifications are not final clinical or FDA verdicts"
  ];
  const questions=slots.flatMap(q=>{
   if(q.answer)return ["PREDICTED_PRE_READOUT",q.answer.prediction,
    q.answer.score,q.answer.summary+" | "+q.answer.reason,
    q.answer.sources.map(s=>s.url).join(" | ")];
   if(q.number===1&&(observedPass||observedFail))return [observedPass?"OBSERVED_PRIMARY_ENDPOINT_MET":"OBSERVED_PRIMARY_ENDPOINT_NOT_MET","","",
    passRationale+"; observed result, not a prospective prediction",endpointEvidenceUrl];
   if(q.number===1&&noBinary)return ["DOCUMENTED_NON_BINARY_ENDPOINT","","",
    passRationale,endpointEvidenceUrl];
   if(q.number===29&&endpoint)return ["DOCUMENTED_PUBLIC_READOUT","","",
    "Public Phase 3 readout or results exist. "+passRationale,endpointEvidenceUrl];
   if(q.observation)return ["SOURCE_FACT_ONLY","","",
    q.observation.description,q.observation.sourceUrl];
   if(q.number===25&&r.registrySourceUrl)return ["SOURCE_FACT_ONLY","","",
    "Dated registry recruitment status: "+r.registryStatus+" (as of "+r.registryAsOf+")",
    r.registrySourceUrl];
   if(q.number===27&&/\bplacebo\b/i.test(r.registeredInterventions||""))
    return ["SOURCE_FACT_ONLY","","",
     "Placebo appears in the registered intervention list; comparator adequacy not assessed",
     r.registrySourceUrl];
   return ["UNSCORED","","",q.missingEvidence,""];
  });
  const statuses=Array.from({length:30},(_,i)=>questions[i*5]);
  const countedPredictions=statuses.filter(x=>x==="PREDICTED_PRE_READOUT").length;
  const countedEvidence=statuses.filter(x=>x!=="PREDICTED_PRE_READOUT"&&x!=="UNSCORED").length;
  extra[13]=countedPredictions;
  extra[14]=countedEvidence;
  extra[15]=30-countedPredictions-countedEvidence;
  extra[17]=endpoint?"PUBLIC_ENDPOINT_EVIDENCE_REVIEWED":
   countedPredictions?"REVIEWED_PRE_READOUT_PREDICTIONS":
   countedEvidence?"PARTIAL_REGISTRY_SOURCE_FACTS":"NO_REVIEWED_QUESTION_EVIDENCE";
  const values=[...base,...extra,...questions];
  if(values.length!==190){
   return Response.json({error:"Question-field alignment failed"},{status:503});
  }
  rows.push(writeRow(values));
 }
 if(rows.length!==763||passedCount!==endpointAdjudications.counts.PRIMARY_ENDPOINT_MET||
    failedCount!==endpointAdjudications.counts.PRIMARY_ENDPOINT_NOT_MET){
  return Response.json({error:"Trial/pass reconciliation failed"},{status:503});
 }
 return new Response("\uFEFF"+rows.join("\r\n")+"\r\n",{
  status:200,headers:{
   "Content-Type":"text/csv; charset=utf-8",
   "Content-Disposition":'attachment; filename="Phase3-762-Trials-190-Columns-2026-11-05-adjudicated.csv"',
   "Cache-Control":"no-store"
  }
 });
}
