#!/usr/bin/env node
/** Append genuinely captured TOP/BOTTOM source-evidence changes to a common
 * cross-stage RAAS journal. This does NOT calculate provisional/validated
 * investment scores and NEVER reconstructs historical forecast timestamps.
 *
 * CLI: node scripts/raas_trial_history_capture.cjs
 * No credential, network call, third-party package or write to source feeds.
 */
"use strict";
const fs=require("node:fs"),path=require("node:path"),crypto=require("node:crypto");
const root=path.resolve(__dirname,"..");
const rel="new-platform/frontend/data/";
const sha=s=>crypto.createHash("sha256").update(s).digest("hex");
const norm=s=>String(s||"").trim().replace(/\s+/g," ").toLowerCase();
const uri=s=>typeof s==="string"&&/^https:\/\/[^\s/]+\/\S*/.test(s);
const validNct=s=>/^NCT\d{8}$/.test(s);
const validDay=s=>/^\d{4}-\d{2}-\d{2}$/.test(s)&&!Number.isNaN(Date.parse(s+"T00:00:00Z"));
const programKey=x=>[x.nctId,norm(x.drug),norm(x.indication)].join("|");
const eventKey=x=>programKey(x)+"|"+x.stage;
function collectSourceCandidates(feeds){
 const byKey=new Map();
 for(const feed of feeds){
  if(!validDay(feed.sourceAsOf)||!Array.isArray(feed.records))throw Error("RAAS_HISTORY_INPUT_INVALID");
  for(const r of feed.records){
   if(!validNct(r.nctId)||!r.ticker?.trim()||!r.drug?.trim()||!r.indication?.trim()||
      !["pre","post"].includes(r.stage)||!Array.isArray(r.observations))
    throw Error("RAAS_HISTORY_TRIAL_IDENTITY_INVALID");
   const k=eventKey(r),old=byKey.get(k);
   if(old&&norm(old.ticker)!==norm(r.ticker))
    throw Error("RAAS_HISTORY_ISSUER_CONFLICT:"+k);
   const v=old||{nctId:r.nctId,ticker:r.ticker,drug:r.drug,indication:r.indication,
      stage:r.stage,sourceAsOf:feed.sourceAsOf,observations:[]};
   if(feed.sourceAsOf>v.sourceAsOf)v.sourceAsOf=feed.sourceAsOf;
   for(const o of r.observations){
    if(!o.id||!Array.isArray(o.metricIds)||!uri(o.sourceUrl)||
       o.metricIds.some(id=>!String(id).startsWith(r.stage==="pre"?"pre-":"post-")))
      throw Error("RAAS_HISTORY_SOURCE_INVALID:"+k);
    v.observations.push({...o,_captureSource:feed.scope||"RAAS_RESEARCH"});
   }
   byKey.set(k,v);
  }
 }
 return [...byKey.values()].map(v=>{
  const observations=[...v.observations].sort((a,b)=>String(a._captureSource+a.id).localeCompare(String(b._captureSource+b.id)));
  const metricIds=[...new Set(observations.flatMap(o=>o.metricIds))].sort();
  const sourceUrls=[...new Set(observations.map(o=>o.sourceUrl))].sort();
  if(metricIds.length>30||sourceUrls.length>100)throw Error("RAAS_HISTORY_SOURCE_LIMIT_EXCEEDED");
  return {...v,observations:undefined,
    metricIds,sourceUrls,metricCoverage:metricIds.length,
    evidenceFingerprint:sha(JSON.stringify({stage:v.stage,nctId:v.nctId,
      ticker:norm(v.ticker),drug:norm(v.drug),indication:norm(v.indication),
      observations}))};
 }).sort((a,b)=>eventKey(a).localeCompare(eventKey(b)));
}
/** Upsert is FORBIDDEN; append only on a changed evidence fingerprint.
 * Existing stage and prior score events remain immutable, even after migration.
 */
function appendSourceCaptures(ledger,candidates,recordedAt){
 if(ledger.schemaVersion!==1||ledger.scope!=="RAAS_TRIAL_SCORE_HISTORY"||
   !Array.isArray(ledger.records)||!/^\d{4}-\d{2}-\d{2}T/.test(recordedAt)||
   Number.isNaN(Date.parse(recordedAt)))
  throw Error("RAAS_HISTORY_LEDGER_INVALID");
 const result={...ledger,records:[...ledger.records]};
 let added=0;
 for(const c of candidates){
  if(c.sourceAsOf>recordedAt.slice(0,10))throw Error("RAAS_HISTORY_FUTURE_SOURCE");
  const matches=result.records.filter(x=>eventKey(x)===eventKey(c));
  const last=matches.at(-1);
  if(last?.evidenceFingerprint===c.evidenceFingerprint)continue;
  const migrated=!last&&result.records.some(x=>programKey(x)===programKey(c)&&x.stage!==c.stage);
  const kind=last?"EVIDENCE_UPDATED":migrated?"STAGE_ADDED":"FIRST_CAPTURE";
  const id=sha(JSON.stringify([programKey(c),c.stage,recordedAt,c.evidenceFingerprint,kind]));
  if(result.records.some(e=>e.eventId===id))throw Error("RAAS_HISTORY_DUPLICATE_EVENT");
  result.records.push({
   eventId:id,nctId:c.nctId,ticker:c.ticker,drug:c.drug,indication:c.indication,
   stage:c.stage,recordedAt,sourceAsOf:c.sourceAsOf,kind,
   summary:(migrated?"New stage; prior TOP/BOTTOM history retained. ":
     kind==="EVIDENCE_UPDATED"?"Saved research evidence changed. ":"First captured source-backed trial research. ")+
     c.metricCoverage+"/30 RAAS metric areas have source leads; no overall RAAS score calculated.",
   scoreKind:"UNSCORED",score:null,scoreVersion:null,
   metricCoverage:c.metricCoverage,metricIds:c.metricIds,
   sourceUrls:c.sourceUrls,evidenceFingerprint:c.evidenceFingerprint
  });
  added++;
 }
 result.records.sort((a,b)=>a.recordedAt.localeCompare(b.recordedAt)||a.eventId.localeCompare(b.eventId));
 return {ledger:result,added};
}
function main(){
 const get=n=>JSON.parse(fs.readFileSync(path.join(root,rel+n),"utf8"));
 const location=path.join(root,rel+"raas-trial-score-history.json");
 const old=get("raas-trial-score-history.json");
 const candidates=collectSourceCandidates([get("raas-pilot-observations.json"),get("raas-prospective-source-baselines.json")]);
 const {ledger,added}=appendSourceCaptures(old,candidates,new Date().toISOString());
 if(added)fs.writeFileSync(location,JSON.stringify(ledger,null,2)+"\n");
 process.stdout.write("RAAS trial history: "+added+" new source-evidence snapshots, "+ledger.records.length+" preserved records. No overall scores fabricated.\n");
}
if(require.main===module)main();
module.exports={collectSourceCandidates,appendSourceCaptures,programKey,eventKey};
