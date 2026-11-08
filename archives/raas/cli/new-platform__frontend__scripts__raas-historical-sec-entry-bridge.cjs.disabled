#!/usr/bin/env node
"use strict";
/** Export research-only SEC cover share source availability at proposed T-79 session.
 * No independently verified market capitalization, price or trading score.
 */
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,compilerOptions:{
 module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,esModuleInterop:true}}
 ).outputText,file);
const {activeSECAsOfEntryShares}=require("../lib/raas-historical-sec-entry-bridge.ts");
const cols=["ticker","application","proposedEntrySession","proposedExitSession",
 "currentSECShares","currentSECSharesMeasurementDate","currentSECFirstConservativeUse",
 "currentSECDisclosureAgeDays","sourceAtEntryStatus","currentSECSourceUrl",
 "earlierCoverShares","laterCoverShares","shareSnapshotDifference",
 "laterCoverAvailableAtEntry","laterCoverWasNotYetPublicAtEntry",
 "earlierSECUrl","laterSECUrl","entryMarketCapUsdMillions",
 "entryMarketCap300Mto10BValidated","adjustedHistoricalReturnPct","validatedRaasScore"];
const numeric=new Set(["currentSECShares","currentSECDisclosureAgeDays",
 "earlierCoverShares","laterCoverShares","shareSnapshotDifference",
 "entryMarketCapUsdMillions","adjustedHistoricalReturnPct","validatedRaasScore"]);
const cell=(key,v)=>{
 if(v===null||v===undefined)return "";
 if(numeric.has(key)){
  if(typeof v!=="number"||!Number.isFinite(v))throw Error("RAAS_SEC_ASOF_CSV_NUMBER_INVALID");
  return String(v);
 }
 const s=String(v);
 const safe=/^[\s\u0000-\u001f]*[=+\-@]/u.test(s)?"'"+s:s;
 return '"'+safe.replaceAll('"','""')+'"';
};
function csv(report){
 if(report?.scope!=="RAAS_2024_2025_SEC_SHARES_ASOF_T79_SESSION_RESEARCH"||
  report.status!=="RESEARCH_SOURCE_AVAILABILITY_ONLY"||
  report.independentlyValidatedEntryMarketCaps!==0||
  report.independentlyVerifiedPricePairs!==0||report.calibratedRaasScores!==0)
  throw Error("RAAS_SEC_ASOF_CSV_SCOPE_INVALID");
 return cols.join(",")+"\n"+report.rows.map(r=>cols.map(k=>cell(k,r[k])).join(",")).join("\n")+"\n";
}
function main(){
 try{
  const report=activeSECAsOfEntryShares();
  const root=path.resolve(__dirname,"..");
  const j=process.env.RAAS_SEC_ASOF_JSON||path.join(root,"raas-2024-2025-sec-cover-asof-entries.json");
  const c=process.env.RAAS_SEC_ASOF_CSV||path.join(root,"raas-2024-2025-sec-cover-asof-entries.csv");
  for(const out of [j,c])fs.mkdirSync(path.dirname(out),{recursive:true});
  fs.writeFileSync(j,JSON.stringify(report,null,2)+"\n");
  fs.writeFileSync(c,csv(report));
  const summary={status:report.status,cases:report.caseCount,
   preEntrySECCoverSources:report.coverFactsPublicAtProposedEntry,
   laterCoverNotPublicAtEntry:report.laterSnapshotsUnavailableAtEntry,
   validatedHistoricalMarketCaps:0,independentAdjustedPricePairs:0,approvedRaasScores:0};
  console.log(JSON.stringify(summary));
  if(process.env.GITHUB_STEP_SUMMARY)fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY,
   "### RAAS nine-case SEC share-count point-in-time research\n\n"+
   JSON.stringify(summary,null,2)+"\n\nNo trade, cap, 79-to-14 return or RAAS grade verified.\n");
 }catch(e){console.error("RAAS_SEC_ASOF_FATAL_"+String(e.message||e)
  .replace(/[^A-Z0-9_]/g,"_"));process.exitCode=1;}
}
if(require.main===module)main();
module.exports={csv};
