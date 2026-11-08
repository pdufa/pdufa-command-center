#!/usr/bin/env node
/** Nightly capture of ONLY source-confirmed, explicitly exploratory RAAS
 * component grades. It never substitutes a partial score for overall RAAS
 * or reconstructs an earlier trading signal.
 */
"use strict";
const fs=require("node:fs"),path=require("node:path"),crypto=require("node:crypto");
const root=path.resolve(__dirname,"..");
const data=path.join(root,"new-platform/frontend/data");
const sha=v=>crypto.createHash("sha256").update(typeof v==="string"?v:JSON.stringify(v)).digest("hex");
const norm=s=>String(s||"").trim().toLowerCase().replace(/\s+/g," ");
const key=r=>[r.nctId,norm(r.ticker),norm(r.drug),norm(r.indication),r.stage].join("|");
const sourceOk=s=>typeof s==="string"&&/^https:\/\/[^\s/]+\/\S+/.test(s);
const ruleId="timing-specificity-exploratory-2026-11-02-v1";
function windowFromSource(s){
 const first=String(s||"").trim().split(/\.\s+/)[0]||"";
 const spans=first.match(/\b(?:first|second) half of 20\d{2}\b|\bH[12]\s+20\d{2}\b|\bQ[1-4]\s+20\d{2}\b|\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+20\d{2}\b/gi);
 if(!spans||spans.length!==1)return null;
 const w=norm(spans[0]);
 const half=w.match(/^h([12]) (20\d{2})$/);
 if(half)return (half[1]==="1"?"First":"Second")+" half of "+half[2];
 const month=w.match(/^(jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec) (20\d{2})$/);
 if(month){
  const labels={jan:"January",feb:"February",mar:"March",apr:"April",jun:"June",
   jul:"July",aug:"August",sep:"September",sept:"September",oct:"October",nov:"November",dec:"December"};
  return labels[month[1]]+" "+month[2];
 }
 return w;
}
function timingGrade(text){
 const w=norm(text);
 if(/^(first|second) half of 20\d{2}$/.test(w))return 50;
 if(/^q[1-4] 20\d{2}$/.test(w))return 75;
 if(/^(january|february|march|april|may|june|july|august|september|october|november|december) 20\d{2}$/.test(w))return 100;
 if(/^20\d{2}$/.test(w))return 25;
 return null;
}
function deriveCandidates(pilot,prospective){
 if(pilot.scope!=="HISTORICAL_PHASE3_RAAS_PILOT_OBSERVATIONS"||
  prospective.scope!=="RAAS_PROSPECTIVE_SOURCE_BASELINES"||
  pilot.sourceAsOf!==prospective.sourceAsOf||
  !Array.isArray(pilot.records)||!Array.isArray(prospective.records))
  throw Error("RAAS_PROVISIONAL_SOURCE_INVALID");
 const result=new Map();
 for(const row of pilot.records){
  if(row.stage!=="pre"||!/^NCT\d{8}$/.test(row.nctId))continue;
  for(const o of row.observations){
   if(o.kind!=="readout_window"||!o.metricIds.includes("pre-4-1")||
    !sourceOk(o.sourceUrl)||o.assessmentDate>pilot.sourceAsOf)continue;
   const score=timingGrade(o.valueText);
   if(score===null)continue;
   const k=key(row);
   if(result.has(k))throw Error("RAAS_PROVISIONAL_DUPLICATE_METRIC:"+k);
   result.set(k,{...row,score,inputs:o.valueText,sourceUrl:o.sourceUrl,
    sourceDate:o.assessmentDate,observationId:o.id});
  }
 }
 for(const row of prospective.records){
  if(row.stage!=="pre"||!/^NCT\d{8}$/.test(row.nctId)||row.capturedOn>prospective.sourceAsOf)continue;
  const k=key(row);
  if(result.has(k))continue; // prefer dated pilot fact where it exists
  for(const o of row.observations){
   if(o.kind!=="PHASE3_READOUT_GUIDANCE"||!o.metricIds.includes("pre-4-1")||
    !sourceOk(o.sourceUrl)||o.sourcePublishedAt>prospective.sourceAsOf||
    o.sourcePublishedAt>row.capturedOn)continue;
   const inputs=windowFromSource(o.valueText),score=inputs?timingGrade(inputs):null;
   if(score===null)continue;
   if(result.has(k))throw Error("RAAS_PROVISIONAL_DUPLICATE_METRIC:"+k);
   result.set(k,{...row,score,inputs,sourceUrl:o.sourceUrl,
    sourceDate:o.sourcePublishedAt,observationId:o.id});
  }
 }
 return [...result.values()].sort((a,b)=>key(a).localeCompare(key(b)));
}
function appendProvisionalMetricEvents(ledger,candidates,recordedAt,sourceAsOf){
 if(ledger.schemaVersion!==1||ledger.scope!=="RAAS_TRIAL_SCORE_HISTORY"||
  !Array.isArray(ledger.records)||!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(recordedAt)||
  new Date(recordedAt).toISOString()!==recordedAt||
  sourceAsOf>recordedAt.slice(0,10))throw Error("RAAS_PROVISIONAL_HISTORY_INVALID");
 const updated={...ledger,records:[...ledger.records]};
 let added=0;
 for(const c of candidates){
  const fingerprint=sha({nctId:c.nctId,ticker:norm(c.ticker),
   drug:norm(c.drug),indication:norm(c.indication),stage:c.stage,
   score:c.score,inputs:c.inputs,sourceUrl:c.sourceUrl,
   sourceDate:c.sourceDate,observationId:c.observationId,ruleId});
  const before=updated.records.filter(e=>e.kind==="METRIC_SCORE_UPDATED"&&
   e.nctId===c.nctId&&norm(e.ticker)===norm(c.ticker)&&
   norm(e.drug)===norm(c.drug)&&norm(e.indication)===norm(c.indication)&&
   e.stage===c.stage&&e.metricIds.includes("pre-4-1")).at(-1);
  if(before?.evidenceFingerprint===fingerprint)continue;
  if(updated.records.some(e=>e.recordedAt>recordedAt))throw Error("RAAS_PROVISIONAL_BACKDATING");
  const grade={metricId:"pre-4-1",score:c.score,
   ruleId,observationId:c.observationId,
   sourceUrl:c.sourceUrl,sourceDate:c.sourceDate,
   label:"Readout window specificity (research only)",inputs:c.inputs,
   explanation:"Predeclared exploratory window bins: year 25; half-year 50; quarter 75; single month 100. Sponsor precision is not the probability of meeting a date."};
  const event={
   eventId:sha([key(c),recordedAt,fingerprint,"METRIC_SCORE_UPDATED"]),
   nctId:c.nctId,ticker:c.ticker,drug:c.drug,indication:c.indication,
   stage:c.stage,recordedAt,sourceAsOf,kind:"METRIC_SCORE_UPDATED",
   summary:"New research-only timing specificity component "+c.score+
    "/100 from source dated "+c.sourceDate+". 1/30 metric grades; overall RAAS not scored.",
   scoreKind:"UNSCORED",score:null,scoreVersion:null,
   metricCoverage:1,metricIds:["pre-4-1"],
   sourceUrls:[c.sourceUrl],evidenceFingerprint:fingerprint,metricGrades:[grade]
  };
  updated.records.push(event);added++;
 }
 updated.records.sort((a,b)=>a.recordedAt.localeCompare(b.recordedAt)||a.eventId.localeCompare(b.eventId));
 return {ledger:updated,added};
}
function main(){
 const load=n=>JSON.parse(fs.readFileSync(path.join(data,n),"utf8"));
 const pilot=load("raas-pilot-observations.json");
 const prospect=load("raas-prospective-source-baselines.json");
 const ledger=load("raas-trial-score-history.json");
 const candidates=deriveCandidates(pilot,prospect);
 const {ledger:updated,added}=appendProvisionalMetricEvents(ledger,candidates,new Date().toISOString(),pilot.sourceAsOf);
 if(added)fs.writeFileSync(path.join(data,"raas-trial-score-history.json"),JSON.stringify(updated,null,2)+"\n");
 process.stdout.write("RAAS experimental metric: "+candidates.length+" source-supported trial grades; "+
  added+" new snapshots; 0 certified overall scores.\n");
}
if(require.main===module)main();
module.exports={timingGrade,windowFromSource,deriveCandidates,appendProvisionalMetricEvents,ruleId};
