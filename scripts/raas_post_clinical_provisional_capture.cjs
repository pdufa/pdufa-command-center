#!/usr/bin/env node
/** Append only source-confirmed BOTTOM exploratory UAS7 / complete response
 * signal grades, never composite RAAS scores or retroactive predictions.
 */
"use strict";

// Permanent retirement: no historical artifact writer may execute as a command.
if (require.main === module) { process.stderr.write("RAAS_PERMANENTLY_RETIRED: this archived command cannot run or modify historical records.\n"); process.exit(78); }

const fs=require("node:fs"),path=require("node:path"),crypto=require("node:crypto");
const root=path.resolve(__dirname,"../new-platform/frontend");
const hash=x=>crypto.createHash("sha256").update(JSON.stringify(x)).digest("hex");
const norm=s=>String(s||"").trim().toLowerCase();
const RULE="uas7-placebo-contrast-descriptive-2026-11-04-v1";
const SOURCE="https://ir.celldex.com/node/16781/ixbrl-viewer";
const bands=(v,[a,b,c])=>v<=0?0:v<a?25:v<b?50:v<c?75:100;
function derivePostCandidates(pilot,readout){
 if(pilot.scope!=="HISTORICAL_PHASE3_RAAS_PILOT_OBSERVATIONS"||
  !Array.isArray(pilot.records)||readout.schemaVersion!==1||
  !Array.isArray(readout.entries))throw Error("RAAS_POST_PILOT_SOURCE_INVALID");
 const validReadouts=new Map(readout.entries.filter(e=>
  e.kind==="POST_PUBLIC_READOUT"&&e.ticker==="CLDX"&&e.drug==="barzolvolimab"&&
  e.indication==="chronic spontaneous urticaria"&&
  e.primaryEndpointP?.display==="p < 0.00001").map(e=>[e.nctId,e]));
 const candidates=[];
 for(const row of pilot.records){
  const readout=validReadouts.get(row.nctId);
  if(!readout||row.stage!=="post"||row.ticker!=="CLDX"||
   row.drug!=="barzolvolimab"||row.indication!=="chronic spontaneous urticaria"||
   !/^NCT\d{8}$/.test(row.nctId)||readout.evidenceDate>pilot.sourceAsOf)continue;
  for(const o of row.observations){
   if(o.sourceUrl!==SOURCE||o.assessmentDate<readout.evidenceDate||
    o.assessmentDate>pilot.sourceAsOf||!o.title.includes("Week 12")||
    !o.title.includes("150 mg Q4W")||o.measurementDate>o.assessmentDate)continue;
   let metricId,delta,score,inputs,explanation;
   if(o.kind==="active_control_mean_change"&&o.unit==="UAS7 points"&&
    o.metricIds.includes("post-1-1")&&
    Number.isFinite(o.activeChange)&&Number.isFinite(o.controlChange)&&
    o.activeChange>=-42&&o.activeChange<=0&&o.controlChange>=-42&&o.controlChange<=0){
    delta=Math.round((o.controlChange-o.activeChange)*100)/100;
    metricId="post-1-1";score=bands(delta,[2,5,10]);
    inputs="Placebo-adjusted LS mean UAS7 change "+delta+" points, 150 mg Q4W, Week 12";
    explanation="Exploratory contrast bands: nonpositive=0; positive <2=25; 2–<5=50; 5–<10=75; >=10=100. Not a validated clinical minimum important between-group difference.";
   }else if(o.kind==="active_control_response"&&
    o.metricIds.includes("post-1-2")&&
    o.title.includes("complete response")&&
    [o.activePercent,o.controlPercent].every(x=>Number.isFinite(x)&&x>=0&&x<=100)){
    delta=Math.round((o.activePercent-o.controlPercent)*100)/100;
    metricId="post-1-2";score=bands(delta,[10,20,30]);
    inputs="Placebo-adjusted UAS7=0 complete-response difference "+delta+" percentage points, 150 mg Q4W, Week 12";
    explanation="Exploratory response contrast bands: nonpositive=0; positive <10pp=25; 10–<20pp=50; 20–<30pp=75; >=30pp=100. No comparison with active alternatives.";
   }else continue;
   candidates.push({...row,metricId,score,observationId:o.id,
    inputs,explanation,sourceUrl:o.sourceUrl,sourceDate:o.assessmentDate,
    label:metricId==="post-1-1"?"Placebo-adjusted UAS7 effect (research only)":
     "Placebo-adjusted complete response (research only)"});
  }
 }
 const keys=new Set();
 for(const c of candidates){
  const k=[c.nctId,c.ticker,c.drug,c.indication,c.stage,c.metricId].join("|");
  if(keys.has(k))throw Error("RAAS_POST_PILOT_DUPLICATE_METRIC");keys.add(k);
 }
 return candidates.sort((a,b)=>a.nctId.localeCompare(b.nctId)||a.metricId.localeCompare(b.metricId));
}
function appendPostMetricEvents(ledger,candidates,recordedAt,asOf){
 if(ledger.schemaVersion!==1||ledger.scope!=="RAAS_TRIAL_SCORE_HISTORY"||
  !Array.isArray(ledger.records)||new Date(recordedAt).toISOString()!==recordedAt||
  asOf>recordedAt.slice(0,10))throw Error("RAAS_POST_HISTORY_INVALID");
 let added=0;
 const records=[...ledger.records];
 for(const c of candidates){
  const fingerprint=hash([c.nctId,norm(c.ticker),norm(c.drug),norm(c.indication),
   "post",c.metricId,c.score,c.inputs,c.sourceUrl,c.sourceDate,c.observationId,RULE]);
  const before=records.filter(e=>e.nctId===c.nctId&&e.stage==="post"&&
   norm(e.drug)===norm(c.drug)&&norm(e.indication)===norm(c.indication)&&
   e.kind==="METRIC_SCORE_UPDATED"&&e.metricIds.includes(c.metricId)).at(-1);
  if(before?.evidenceFingerprint===fingerprint)continue;
  if(records.some(e=>e.recordedAt>recordedAt))throw Error("RAAS_POST_BACKDATING");
  const grade={metricId:c.metricId,score:c.score,ruleId:RULE,
   observationId:c.observationId,sourceUrl:c.sourceUrl,sourceDate:c.sourceDate,
   label:c.label,inputs:c.inputs,explanation:c.explanation+
    " Company-announced outcomes, not independent clinical adjudication."};
  records.push({
   eventId:hash([c.nctId,c.metricId,recordedAt,fingerprint]),
   nctId:c.nctId,ticker:c.ticker,drug:c.drug,indication:c.indication,
   stage:"post",recordedAt,sourceAsOf:asOf,kind:"METRIC_SCORE_UPDATED",
   summary:"Research-only "+c.metricId+" descriptive clinical contrast "+c.score+
    "/100. Clinical efficacy/return probabilities and overall RAAS remain unscored.",
   scoreKind:"UNSCORED",score:null,scoreVersion:null,
   metricCoverage:1,metricIds:[c.metricId],sourceUrls:[c.sourceUrl],
   evidenceFingerprint:fingerprint,metricGrades:[grade]
  });added++;
 }
 records.sort((a,b)=>a.recordedAt.localeCompare(b.recordedAt)||a.eventId.localeCompare(b.eventId));
 return {ledger:{...ledger,records},added};
}
function main(){
 const load=p=>JSON.parse(fs.readFileSync(path.join(root,p),"utf8"));
 const pilot=load("data/raas-pilot-observations.json");
 const readout=load("public/phase3-public-readout-evidence-2026-11-01.json");
 const ledger=load("data/raas-trial-score-history.json");
 const candidates=derivePostCandidates(pilot,readout);
 const res=appendPostMetricEvents(ledger,candidates,new Date().toISOString(),pilot.sourceAsOf);
 if(res.added)fs.writeFileSync(path.join(root,"data/raas-trial-score-history.json"),
  JSON.stringify(res.ledger,null,2)+"\n");
 process.stdout.write("Research-only BOTTOM: "+candidates.length+" narrow source-backed component grades, "+
  res.added+" new history events; 0 approved overall RAAS scores.\n");
}
if(require.main===module)main();
module.exports={derivePostCandidates,appendPostMetricEvents,bands,RULE};
