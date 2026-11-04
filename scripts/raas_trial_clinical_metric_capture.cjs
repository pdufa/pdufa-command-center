#!/usr/bin/env node
/** Append genuine, time-stamped narrow BOTTOM placebo-contrast pilot grades.
 * Experimental endpoint-specific proxies, NOT validated treatment efficacy,
 * FDA success, future returns, or a completed 30-metric RAAS score.
 */
"use strict";
const fs=require("node:fs"),path=require("node:path"),crypto=require("node:crypto");
const root=path.resolve(__dirname,"..");
const data=path.join(root,"new-platform/frontend/data");
const ruleId="csu-placebo-contrast-heuristic-2026-11-04-v1";
const sha=v=>crypto.createHash("sha256").update(JSON.stringify(v)).digest("hex");
const norm=s=>String(s||"").trim().toLowerCase().replace(/\s+/g," ");
const secure=s=>typeof s==="string"&&/^https:\/\/[^\s/]+\/\S+/.test(s);
const date=s=>typeof s==="string"&&/^\d{4}-\d{2}-\d{2}$/.test(s)&&
 !Number.isNaN(Date.parse(s+"T00:00:00Z"))&&new Date(s+"T00:00:00Z").toISOString().slice(0,10)===s;
const band=(x,t)=>x<=0?0:x<t[0]?25:x<t[1]?50:x<t[2]?75:100;
const fmt=x=>Number(x.toFixed(2));
function deriveClinicalCandidates(pilot,readout){
 if(pilot.scope!=="HISTORICAL_PHASE3_RAAS_PILOT_OBSERVATIONS"||
  !date(pilot.sourceAsOf)||!Array.isArray(pilot.records)||!Array.isArray(readout.entries))
  throw Error("RAAS_CLINICAL_SOURCE_INVALID");
 const matched=new Map();
 for(const e of readout.entries){
  if(e.kind!=="POST_PUBLIC_READOUT")continue;
  const k=[e.nctId,norm(e.ticker),norm(e.drug),norm(e.indication)].join("|");
  if(matched.has(k))throw Error("RAAS_CLINICAL_DUPLICATE_READOUT");
  matched.set(k,e);
 }
 const out=[];
 for(const row of pilot.records){
  if(row.stage!=="post"||!/^NCT\d{8}$/.test(row.nctId)||
     !/chronic (spontaneous|idiopathic) urticaria/i.test(row.indication))continue;
  const key=[row.nctId,norm(row.ticker),norm(row.drug),norm(row.indication)].join("|");
  if(!matched.has(key))continue; // no unsigned BOTTOM classification
  const grades=[];
  for(const o of row.observations){
   if(!secure(o.sourceUrl)||!date(o.assessmentDate)||
      !date(o.measurementDate)||o.assessmentDate>pilot.sourceAsOf||
      o.measurementDate>o.assessmentDate)continue;
   let score=null,metricId=null,label="",inputs="",explanation="";
   if(o.kind==="active_control_mean_change"&&o.unit==="UAS7 points"&&
      o.metricIds.includes("post-1-1")&&
      Number.isFinite(o.activeChange)&&Number.isFinite(o.controlChange)&&
      o.activeChange>=-42&&o.activeChange<=0&&o.controlChange>=-42&&o.controlChange<=0){
    const delta=fmt(o.controlChange-o.activeChange);
    if(delta < -42||delta>42)continue;
    metricId="post-1-1";score=band(delta,[3,6,9]);
    label="Placebo-adjusted UAS7 endpoint magnitude proxy (research only)";
    inputs="Active "+o.activeChange+", placebo "+o.controlChange+
     "; placebo-adjusted improvement "+delta+" UAS7 points";
    explanation="Uncalibrated UAS7 between-arm difference bins: <=0 -> 0, >0 to <3 -> 25, "+
     "3 to <6 -> 50, 6 to <9 -> 75, >=9 -> 100. NOT a full clinical or efficacy grade.";
   }else if(o.kind==="active_control_response"&&
      /complete response\s*\(UAS7\s*=\s*0\)/i.test(o.title)&&
      o.metricIds.includes("post-1-2")&&
      Number.isFinite(o.activePercent)&&Number.isFinite(o.controlPercent)&&
      o.activePercent>=0&&o.activePercent<=100&&o.controlPercent>=0&&o.controlPercent<=100){
    const delta=fmt(o.activePercent-o.controlPercent);
    if(delta < -100||delta>100)continue;
    metricId="post-1-2";score=band(delta,[10,20,30]);
    label="Placebo-adjusted complete-response percentage-point proxy (research only)";
    inputs="Active "+o.activePercent+"%, placebo "+o.controlPercent+
     "%; complete-response difference "+delta+" percentage points";
    explanation="Uncalibrated complete-response contrast bins: <=0 -> 0, >0 to <10 pp -> 25, "+
     "10 to <20 pp -> 50, 20 to <30 pp -> 75, >=30 pp -> 100. NOT a full clinical grade.";
   }
   if(metricId!==null){
    if(grades.some(g=>g.metricId===metricId))throw Error("RAAS_CLINICAL_DUPLICATE_METRIC:"+key);
    grades.push({metricId,score,ruleId,observationId:o.id,sourceUrl:o.sourceUrl,
     sourceDate:o.assessmentDate,label,inputs,explanation});
   }
  }
  if(grades.length){
   grades.sort((a,b)=>a.metricId.localeCompare(b.metricId));
   out.push({nctId:row.nctId,ticker:row.ticker,drug:row.drug,
    indication:row.indication,stage:"post",grades});
  }
 }
 return out.sort((a,b)=>a.nctId.localeCompare(b.nctId));
}
function appendClinicalEvents(ledger,candidates,recordedAt,sourceAsOf){
 if(ledger.schemaVersion!==1||ledger.scope!=="RAAS_TRIAL_SCORE_HISTORY"||
    !Array.isArray(ledger.records)||!date(sourceAsOf)||
    !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(recordedAt)||
    new Date(recordedAt).toISOString()!==recordedAt||
    sourceAsOf>recordedAt.slice(0,10))throw Error("RAAS_CLINICAL_LEDGER_INVALID");
 if(ledger.records.some(e=>e.recordedAt>recordedAt))throw Error("RAAS_CLINICAL_BACKDATING");
 const updated={...ledger,records:[...ledger.records]};let added=0;
 for(const item of candidates){
  if(item.stage!=="post"||!/^NCT\d{8}$/.test(item.nctId)||
     !item.ticker||!item.drug||!item.indication||
     !Array.isArray(item.grades)||!item.grades.length||item.grades.length>2||
     item.grades.some(g=>!["post-1-1","post-1-2"].includes(g.metricId)||
       ![0,25,50,75,100].includes(g.score)||g.ruleId!==ruleId||
       !secure(g.sourceUrl)||!date(g.sourceDate)||g.sourceDate>sourceAsOf||
       !g.label||!g.inputs||!g.explanation||!g.observationId))
   throw Error("RAAS_CLINICAL_GRADE_INVALID");
  const hash=sha([item.nctId,norm(item.ticker),norm(item.drug),
   norm(item.indication),item.stage,item.grades]);
  const prev=updated.records.filter(e=>e.kind==="METRIC_SCORE_UPDATED"&&
   e.nctId===item.nctId&&e.stage==="post"&&norm(e.drug)===norm(item.drug)&&
   norm(e.indication)===norm(item.indication)&&
   e.metricIds.some(id=>["post-1-1","post-1-2"].includes(id))).at(-1);
  if(prev?.evidenceFingerprint===hash)continue;
  if(updated.records.some(e=>e.recordedAt>recordedAt))throw Error("RAAS_CLINICAL_BACKDATING");
  const event={
   eventId:sha([item.nctId,recordedAt,hash,"METRIC_SCORE_UPDATED"]),
   nctId:item.nctId,ticker:item.ticker,drug:item.drug,indication:item.indication,
   stage:"post",recordedAt,sourceAsOf,kind:"METRIC_SCORE_UPDATED",
   summary:"Source-backed BOTTOM endpoint magnitude heuristics: "+item.grades.length+
    "/30 narrow experimental metric proxies. No complete clinical adjudication or overall RAAS score.",
   scoreKind:"UNSCORED",score:null,scoreVersion:null,
   metricCoverage:item.grades.length,metricIds:item.grades.map(g=>g.metricId),
   sourceUrls:[...new Set(item.grades.map(g=>g.sourceUrl))],
   evidenceFingerprint:hash,metricGrades:item.grades
  };
  updated.records.push(event);added++;
 }
 updated.records.sort((a,b)=>a.recordedAt.localeCompare(b.recordedAt)||
  a.eventId.localeCompare(b.eventId));
 return {ledger:updated,added};
}
function main(){
 const load=(name,dir=data)=>JSON.parse(fs.readFileSync(path.join(dir,name),"utf8"));
 const pilot=load("raas-pilot-observations.json");
 const readout=load("phase3-public-readout-evidence-2026-11-01.json",
  path.join(root,"new-platform/frontend/public"));
 const ledger=load("raas-trial-score-history.json");
 const candidates=deriveClinicalCandidates(pilot,readout);
 const result=appendClinicalEvents(ledger,candidates,new Date().toISOString(),pilot.sourceAsOf);
 if(result.added)fs.writeFileSync(path.join(data,"raas-trial-score-history.json"),
  JSON.stringify(result.ledger,null,2)+"\n");
 process.stdout.write("RAAS BOTTOM clinical pilot: "+candidates.length+
  " exact-trial groups, "+candidates.reduce((s,x)=>s+x.grades.length,0)+
  " narrow research-only component grades, "+result.added+
  " new real-timestamp events, 0 approved overall scores.\n");
}
if(require.main===module)main();
module.exports={deriveClinicalCandidates,appendClinicalEvents,ruleId,band};
