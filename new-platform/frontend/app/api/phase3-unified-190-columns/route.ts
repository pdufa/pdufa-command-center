import ledger from "../../../public/phase3-unified-classifications-2026-11-05.json";
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
 "Passing Evidence Date","Passing Evidence Type","Results Publication Group",
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

const escaped=(input:unknown):string=>{
 let s=input===null||input===undefined?"":String(input);
 s=s.replace(/[\r\n]+/g," ");
 if(/^[=+\-@]/.test(s))s="'"+s;
 return '"'+s.replace(/"/g,'""')+'"';
};
const writeRow=(cells:unknown[])=>cells.map(escaped).join(",");

export async function GET(){
 if(HEADERS.length!==190||ledger.total!==762||ledger.rows.length!==762||
    new Set(ledger.rows.map(r=>r.nctId)).size!==762){
  return Response.json({error:"Phase 3 190-column ledger integrity check failed"},{status:503});
 }
 const rows=[writeRow(HEADERS)];
 let passedCount=0;
 for(const r of ledger.rows){
  const observedPass=r.classificationVerified&&
   r.readoutOutcome==="PRIMARY_ENDPOINT_MET"&&Boolean(r.readoutEvidenceUrl);
  if(observedPass)passedCount++;
  const passing=observedPass?"PASS_DOCUMENTED_PRIMARY_ENDPOINT":"UNDETERMINED";
  const passRationale=observedPass?
   "Dated exact-NCT issuer evidence says primary endpoint met; this is not FDA approval":
   r.classificationCode==="P3_TERMINATED"?"Trial terminated; primary-endpoint FAIL not established by this record":
   r.classificationCode==="P3_WITHDRAWN"?"Trial withdrawn; primary-endpoint FAIL not established by this record":
   r.classificationCode.startsWith("P3_POST_DATA")?
    "Public results located, but primary-endpoint PASS/FAIL not adjudicated":
    "No independently adjudicated primary-endpoint PASS/FAIL in the saved ledger";
  const slots=phase3QuestionSlots(r.nctId);
  const predictions=slots.filter(q=>Boolean(q.answer)).length;
  const observations=slots.filter(q=>!q.answer&&Boolean(q.observation)).length;
  const base=[
   r.nctId,r.ticker,r.company,r.classification,r.classificationCode,
   r.registryStatus,r.rosterStatus,r.registryAsOf,r.readoutEvidenceType,
   r.readoutSourceDate,r.readoutOutcome,r.drug,r.indication,r.registeredInterventions,
   r.fdaApplicationStatus,r.fdaReviewType,r.pdufaGoalDate,r.readoutEvidenceUrl,
   r.registrySourceUrl,r.classificationEvidence
  ];
  const extra=[
   passing,passRationale,observedPass?r.readoutEvidenceUrl:"",
   observedPass?r.readoutSourceDate:"",observedPass?r.readoutEvidenceType:"NOT_VERIFIED",
   r.classificationCode,r.classificationVerified,
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
   if(q.number===1&&observedPass)return ["OBSERVED_PRIMARY_ENDPOINT_MET","","",
    "Issuer-reported primary endpoint met; this is an observed readout, not a forecast",
    r.readoutEvidenceUrl];
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
  const values=[...base,...extra,...questions];
  if(values.length!==190){
   return Response.json({error:"Question-field alignment failed"},{status:503});
  }
  rows.push(writeRow(values));
 }
 if(rows.length!==763||passedCount!==1){
  return Response.json({error:"Trial/pass reconciliation failed"},{status:503});
 }
 return new Response("\uFEFF"+rows.join("\r\n")+"\r\n",{
  status:200,headers:{
   "Content-Type":"text/csv; charset=utf-8",
   "Content-Disposition":'attachment; filename="Phase3-762-Trials-190-Columns-2026-11-05.csv"',
   "Cache-Control":"no-store"
  }
 });
}
