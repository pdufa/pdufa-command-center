"use strict";
/** Run an honest RAAS source-readiness scan. No prediction creation or ingestion. */
const fs=require("node:fs");
const path=require("node:path");
const ts=require("typescript");
require.extensions[".ts"]=(mod,file)=>{
 const source=fs.readFileSync(file,"utf8");
 const output=ts.transpileModule(source,{
  fileName:file,
  compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,esModuleInterop:true}
 });
 mod._compile(output.outputText,file);
};
const {executeRaasReadinessScan}=require("../lib/raas-readiness-scan.ts");
const report=executeRaasReadinessScan();
const generatedAtUtc=new Date().toISOString();
const output={...report,generatedAtUtc,gitSha:process.env.GITHUB_SHA||null};
const target=process.env.RAAS_SCAN_OUTPUT||path.join(process.cwd(),"raas-readiness-result.json");
fs.mkdirSync(path.dirname(target),{recursive:true});
fs.writeFileSync(target,JSON.stringify(output,null,2)+"\n");
const s=report.summary;
const message=[
 "# RAAS evidence readiness scan",
 "Execution: "+report.scanExecution+" · source snapshot: "+report.sourceAsOf,
 "Metric definitions inspected: "+s.metricsInspected+"/60 (TOP "+s.preMetricsInspected+", BOTTOM "+s.postMetricsInspected+")",
 "Metrics with qualifying historical research holdouts: "+s.reviewEligibleMetrics+"/60",
 "Approved metric calibrations: "+s.approvedMetricCalibrations+"/60",
 "Valid historical event-window cases: "+s.historicalAcceptedCases,
 "Recorded prospective trial issuers: "+s.prospectiveIssuers+"; dated source facts: "+s.prospectiveSourceFacts,
 "Retrospectively selected examples (not forecasts): "+s.retrospectiveResearchWindows,
 "Nominal second-source price matches (not adjusted returns): "+s.independentlyConfirmedNominalCloses+"/"+s.nominalClosePoints,
 "Pre-entry SEC share bridges: "+s.secShareBridgeCases+"/"+s.retrospectiveResearchWindows,
 "Primary FDA post-exit checks: "+s.fdaPrimaryCrosschecks,
 "Final numerical RAAS validation: "+report.finalScoring,
 "",
 "This result audits committed dated sources. Success means the audit executed, NOT that scores were validated."
];
for(const x of message)console.log(x);
if(process.env.GITHUB_STEP_SUMMARY){
 const lines=["## RAAS read-only evidence readiness","",...message.slice(1).map(x=>"- "+x)];
 fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY,lines.join("\n")+"\n");
}
if(s.metricsInspected!==60||report.finalScoring==="ALL_STAGES_VALIDATED"&&s.approvedMetricCalibrations!==60){
 throw Error("RAAS_READINESS_SCAN_INVARIANT_FAILED");
}
