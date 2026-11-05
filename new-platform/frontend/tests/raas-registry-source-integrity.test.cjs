"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,
 compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,
 esModuleInterop:true,jsx:ts.JsxEmit.ReactJSX}}).outputText,file);
const index=require("../public/raas-registry-evidence-index.json");
const {parseRegistryEvidenceIndex}=require("../lib/raas-registry-evidence.ts");
const {auditRegistrySourceTrial,auditRegistrySourceIndex,
 registryEvidenceReviewerPacket}=require("../lib/raas-registry-source-integrity.ts");
const {buildTrialEvidenceBacklog}=require("../lib/raas-trial-evidence-backlog.ts");
const parsed=parseRegistryEvidenceIndex(index);
const audit=auditRegistrySourceIndex(parsed);
const backlog=buildTrialEvidenceBacklog(parsed);
const record=(nctId)=>parsed.records.find(x=>x.nctId===nctId);

test("all 762 exact registry records are integrity-audited with source-only factual counts",()=>{
 assert.equal(audit.totalTrials,762);
 assert.equal(audit.records.length,762);
 assert.equal(audit.trialsWithComparisons,170);
 assert.equal(audit.trialsWithNumericCI,149);
 assert.equal(audit.trialsWithSaeDenominators,306);
 assert.equal(backlog.totalTrials,762);
 assert.equal(backlog.trialsWithAnyProvisionalMetrics,21);
 assert.equal(backlog.provisionalMetricReviews,96);
 assert.equal(backlog.approvedScores,0);
 assert.equal(backlog.calibratedFdaPredictions,0);
 assert.equal(audit.flaggedFindings,
  Object.values(audit.issuesByCode).reduce((a,b)=>a+b,0));
 assert.equal(audit.flaggedTrials,backlog.sourceIntegrityFlaggedTrials);
 assert.equal(audit.flaggedFindings,backlog.sourceIntegrityFindings);
 for(const row of audit.records){
  const original=record(row.nctId);
  assert.equal(row.sourceHash,original.sourceHash);
  assert.equal(row.ticker,original.ticker);
  assert.equal(row.approvedRaasScore,null);
  assert.equal(row.calibratedFdaProbability,null);
 }
});
test("nonpositive reported odds ratio is flagged for interpretation, not corrected or scored",()=>{
 const raw=record("NCT00308737");
 assert.ok(raw&&raw.ticker==="MNKD"&&raw.postedResults);
 const study=auditRegistrySourceTrial(raw,parsed.sourceAsOf);
 const flag=study.issues.find(x=>x.code==="NONPOSITIVE_REPORTED_RATIO");
 assert.ok(flag);
 assert.match(flag.reportedValue,/Odds Ratio.*-2\.4767/);
 assert.match(flag.explanation,/transformed statistic or labeling mismatch/);
 assert.equal(study.approvedRaasScore,null);
 const original=raw.primaryResults.find(x=>x.title.includes("FEV1 Decrease"));
 assert.equal(original.comparisons[0].paramValue,"-2.4767");
 const work=backlog.items.find(x=>x.nctId===raw.nctId);
 assert.ok(work.sourceIntegrityIssueCodes.includes("NONPOSITIVE_REPORTED_RATIO"));
 assert.equal(work.stage,"unverified");
});
test("valid ungraded registry primary comparisons remain raw; safety OG/EG IDs are never joined",()=>{
 const raw=record("NCT00308308");
 assert.equal(raw.primaryResults[0].comparisons[0].paramValue,"0.24");
 const study=auditRegistrySourceTrial(raw,parsed.sourceAsOf);
 assert.ok(study.primaryComparisons>0);
 assert.ok(study.comparisonsWithNumericCI>0);
 assert.ok(study.safetyGroupsWithDenominators>0);
 assert.equal(study.issues.length,0);
 const packet=registryEvidenceReviewerPacket(raw,parsed.sourceAsOf);
 assert.equal(packet.scope,"RAAS_EXACT_NCT_REGISTRY_REVIEW_SOURCE_PACKET_NO_GRADES");
 assert.equal(packet.sourceHashOriginalRegistryReceipt,raw.sourceHash);
 assert.equal(packet.exactTrial.nctId,raw.nctId);
 assert.equal(packet.exactTrial.sourceUrl,raw.sourceUrl);
 assert.equal(packet.sourceReportedResults[0].comparisons[0].paramValue,"0.24");
 assert.equal(packet.sourceReportedSeriousEvents[0].groups[0].groupId,"EG000");
 assert.equal(packet.independentReviewerSignoff,null);
 assert.equal(packet.approvedRaasScore,null);
 assert.equal(packet.calibratedFdaProbability,null);
});
test("protocol-only FDA lead is never populated with imaginary registry results or an FDA forecast",()=>{
 const raw=record("NCT05208047");
 assert.ok(raw&&!raw.postedResults);
 const packet=registryEvidenceReviewerPacket(raw,parsed.sourceAsOf);
 assert.equal(packet.exactTrial.nctId,raw.nctId);
 assert.equal(packet.sourceReportedResults.length,0);
 assert.equal(packet.sourceReportedSeriousEvents.length,0);
 assert.equal(packet.approvedRaasScore,null);
 assert.equal(packet.calibratedFdaProbability,null);
 const work=backlog.items.find(x=>x.nctId===raw.nctId);
 assert.equal(work.stage,"post"); // separately dated issuer source, NOT registry
 assert.equal(work.priority,"FDA_ACCEPTED_PHASE3");
});
test("source integrity audit raises failures for synthetic mismatched arms, CI and impossible SAE denominators",()=>{
 const source=record("NCT00308308");
 const changed=structuredClone(source);
 changed.primaryResults[0].comparisons[0].groupIds=["OG000","UNKNOWN"];
 changed.primaryResults[0].comparisons[0].ciLowerLimit="2.5";
 changed.primaryResults[0].comparisons[0].ciUpperLimit="1.5";
 changed.seriousEventDetails[0].groups[0].numAffected=9999;
 const issues=auditRegistrySourceTrial(changed,parsed.sourceAsOf).issues.map(x=>x.code);
 for(const need of ["COMPARISON_ARM_NOT_IDENTIFIED","CI_LOWER_ABOVE_UPPER",
   "SAE_AFFECTED_EXCEEDS_AT_RISK"])assert.ok(issues.includes(need));
 const outside=structuredClone(source);
 outside.primaryResults[0].comparisons[0].paramValue="123";
 assert.ok(auditRegistrySourceTrial(outside,parsed.sourceAsOf).issues.some(
  x=>x.code==="POINT_ESTIMATE_OUTSIDE_CI"));
 const invalid=structuredClone(source);invalid.sourceUrl="https://fake.example.com/";
 assert.throws(()=>auditRegistrySourceTrial(invalid,parsed.sourceAsOf),
  /RAAS_REGISTRY_AUDIT_SOURCE_IDENTITY_INVALID/);
});
test("all-trial page exposes clinical integrity filter and exact NCT source packet",async()=>{
 const client=read("app/raas-evidence-backlog/EvidenceBacklogClient.tsx");
 const csvRoute=read("app/api/raas-evidence-backlog/route.ts");
 for(const needle of ["Filter clinical source interpretation flags",
  "sourceIntegrityIssueCount","sourceIntegrityIssues","data-raas-registry-source-packet",
  "data-raas-registry-source-interpretation-review",
  "primaryNumericCICount","saeDenominatorGroupCount"])
  assert.ok(client.includes(needle),"missing clinical source audit "+needle);
 assert.ok(csvRoute.includes("sourceIntegrityIssueCodes"));
 for(const name of ["app/raas-evidence-backlog/EvidenceBacklogClient.tsx",
  "app/api/raas-registry-source-packet/route.ts"]){
  const code=read(name);
  const output=ts.transpileModule(code,{fileName:name,reportDiagnostics:true,
   compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022,
    jsx:ts.JsxEmit.ReactJSX}});
  assert.deepEqual((output.diagnostics||[]).filter(x=>x.category===ts.DiagnosticCategory.Error),[]);
 }
 const {GET}=require("../app/api/raas-registry-source-packet/route.ts");
 const rootUrl="https://example.test/api/raas-registry-source-packet";
 const ok=GET(new Request(rootUrl+"?nctId=NCT00308737&ticker=MNKD"));
 assert.equal(ok.status,200);
 assert.match(ok.headers.get("Content-Disposition"),/MNKD-NCT00308737/);
 const out=await ok.json();
 assert.equal(out.exactTrial.nctId,"NCT00308737");
 assert.ok(out.audit.issues.some(x=>x.code==="NONPOSITIVE_REPORTED_RATIO"));
 assert.equal(out.approvedRaasScore,null);
 assert.equal(GET(new Request(rootUrl+"?nctId=NCT00308737&ticker=COGT")).status,404);
 assert.equal(GET(new Request(rootUrl+"?nctId=bad&ticker=MNKD")).status,400);
 const {GET:exportCSV}=require("../app/api/raas-evidence-backlog/route.ts");
 const csv=(await exportCSV().text());
 assert.equal(csv.split("\r\n").length-2,762);
 assert.ok(csv.includes("sourceIntegrityIssueCodes"));
 assert.ok(csv.includes("NONPOSITIVE_REPORTED_RATIO"));
});
