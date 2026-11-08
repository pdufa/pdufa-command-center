#!/usr/bin/env node
/** A point-in-time RAAS SYSTEM self-audit evidence inventory. Unlike trial
 * score history, this tracks the confidence of the rating *methodology*.
 * Raw counts are explicitly NOT proof of predictive accuracy or validity.
 * Never reconstruct an earlier score from current/late evidence.
 */
"use strict";

// Permanent retirement: no historical artifact writer may execute as a command.
if (require.main === module) { process.stderr.write("RAAS_PERMANENTLY_RETIRED: this archived command cannot run or modify historical records.\n"); process.exit(78); }

const fs=require("node:fs"),path=require("node:path"),crypto=require("node:crypto");
const root=path.resolve(__dirname,"../new-platform/frontend");
const data=path.join(root,"data");
const hash=s=>crypto.createHash("sha256").update(s).digest("hex");
const sources=[
 "lib/raas-metric-specs.ts",
 "data/raas-active-2024-2025-pdufa-intake.json",
 "data/raas-historical-cases.json",
 "data/raas-historical-metric-snapshots.json",
 "data/raas-approved-calibrations.json",
 "data/raas-reviewed-snapshots.json",
 "data/raas-fda-three-way-accuracy-site-snapshot.json"
];
function makeAuditSnapshot(input,recordedAt){
 if(!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(recordedAt)||
  new Date(recordedAt).toISOString()!==recordedAt)throw Error("RAAS_SELF_AUDIT_BAD_TIME");
 const sourceBytes=sources.map(f=>{
  if(typeof input[f]!=="string")throw Error("RAAS_SELF_AUDIT_SOURCE_MISSING:"+f);
  return [f,input[f]];
 });
 const files=Object.fromEntries(sourceBytes.map(([n,s])=>[n,hash(s)]));
 const get=n=>JSON.parse(input[n]);
 const intake=get("data/raas-active-2024-2025-pdufa-intake.json"),
  trades=get("data/raas-historical-cases.json"),
  historical=get("data/raas-historical-metric-snapshots.json"),
  calibration=get("data/raas-approved-calibrations.json"),
  reviewed=get("data/raas-reviewed-snapshots.json"),
  fda=get("data/raas-fda-three-way-accuracy-site-snapshot.json");
 const ids=[...input["lib/raas-metric-specs.ts"].matchAll(/"id": "(?:pre|post)-\d+-\d+"/g)].length;
 if(ids!==60||intake.scope!=="RAAS_2024_2025_PDUFA_POINT_IN_TIME_INTAKE"||
  trades.scope!=="RAAS_HISTORICAL_EVENT_BACKTEST"||
  historical.scope!=="RAAS_HISTORICAL_METRIC_SNAPSHOTS"||
  calibration.scope!=="RAAS_VALIDATED_METRIC_CALIBRATIONS"||
  reviewed.scope!=="RAAS_REVIEWED_TRIAL_SNAPSHOTS"||
  fda.scope!=="RAAS_FDA_THREE_WAY_DECISION_ACCURACY_SITE_SNAPSHOT"||
  !Array.isArray(intake.yearAudits)||intake.yearAudits.length!==2||
  !Array.isArray(trades.cases)||!Array.isArray(historical.records)||
  !Array.isArray(calibration.entries)||!Array.isArray(reviewed.records)||
  !Number.isSafeInteger(fda.predecisionThreeWayIndependentlyVerifiedForecasts)||
  fda.predecisionThreeWayIndependentlyVerifiedForecasts<0)
  throw Error("RAAS_SELF_AUDIT_SOURCE_INVALID");
 const years=intake.yearAudits.filter(x=>[2024,2025].includes(x.year)&&
  x.status==="FULL_EVENT_CENSUS_AUDITED"&&
  typeof x.sourceUrl==="string"&&/^https:\/\//.test(x.sourceUrl)).length;
 const fingerprint=hash(JSON.stringify(files));
 return {
  eventId:hash(recordedAt+"|"+fingerprint),
  recordedAt,evidenceFingerprint:fingerprint,
  metricDefinitions:ids,verifiedYearAudits:years,
  rawHistoricalTradeRows:trades.cases.length,
  rawHistoricalMetricRows:historical.records.length,
  rawCalibrationRegistryEntries:calibration.entries.length,
  rawReviewedTrialSnapshots:reviewed.records.length,
  claimedPredecisionThreeWayForecasts:fda.predecisionThreeWayIndependentlyVerifiedForecasts,
  accuracyScore:null,accuracyPercent:null,
  status:"NOT_INDEPENDENTLY_RATED",
  note:"Source inventory only. Raw records are not accepted historical returns, approved calibrations, or independently checked outcomes. No predictive accuracy may be inferred.",
  sourceDigests:files
 };
}
function appendAuditSnapshot(ledger,snapshot){
 if(ledger.schemaVersion!==1||ledger.scope!=="RAAS_SELF_AUDIT_HISTORY"||
  !Array.isArray(ledger.records))throw Error("RAAS_SELF_AUDIT_LEDGER_INVALID");
 for(const r of ledger.records){
  if(!r?.eventId||!r.recordedAt||!r.evidenceFingerprint||r.accuracyScore!==null||
    r.accuracyPercent!==null)throw Error("RAAS_SELF_AUDIT_SAVED_SNAPSHOT_INVALID");
 }
 const last=ledger.records.at(-1);
 if(last&&snapshot.recordedAt<last.recordedAt)throw Error("RAAS_SELF_AUDIT_BACKDATING_DISALLOWED");
 if(last?.evidenceFingerprint===snapshot.evidenceFingerprint)return {ledger,added:0};
 if(ledger.records.some(r=>r.eventId===snapshot.eventId))
  throw Error("RAAS_SELF_AUDIT_DUPLICATE_EVENT");
 return {ledger:{...ledger,records:[...ledger.records,snapshot]},added:1};
}
function main(){
 const inputs=Object.fromEntries(sources.map(f=>[f,fs.readFileSync(path.join(root,f),"utf8")]));
 const name=path.join(data,"raas-self-audit-history.json");
 const ledger=JSON.parse(fs.readFileSync(name,"utf8"));
 const snapshot=makeAuditSnapshot(inputs,new Date().toISOString());
 const result=appendAuditSnapshot(ledger,snapshot);
 if(result.added)fs.writeFileSync(name,JSON.stringify(result.ledger,null,2)+"\n");
 process.stdout.write("RAAS system self-audit: "+result.added+" new source inventory snapshots, "+
  result.ledger.records.length+" retained; numerical accuracy remains unmeasured.\n");
}
if(require.main===module)main();
module.exports={sources,makeAuditSnapshot,appendAuditSnapshot};
