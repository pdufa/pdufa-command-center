"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const frontend=path.resolve(__dirname,"..");
const repo=path.resolve(frontend,"../..");
const capture=require(path.join(repo,"scripts/raas_self_audit_history_capture.cjs"));
const read=p=>fs.readFileSync(path.join(frontend,p),"utf8");
const inputs=()=>Object.fromEntries(capture.sources.map(f=>[f,read(f)]));
const first="2026-11-04T05:30:00.000Z",second="2026-11-04T05:31:00.000Z";
test("saved RAAS system history retains dated source inventories without invented accuracy",()=>{
 const d=JSON.parse(read("data/raas-self-audit-history.json"));
 assert.equal(d.scope,"RAAS_SELF_AUDIT_HISTORY");
 assert.ok(d.records.length>=1);
 assert.ok(d.records.every(x=>x.accuracyScore===null&&x.accuracyPercent===null));
 assert.ok(d.records.every(x=>x.status==="NOT_INDEPENDENTLY_RATED"));
 assert.equal(new Set(d.records.map(x=>x.eventId)).size,d.records.length);
});
test("system snapshot contains auditable source counts, not a score",()=>{
 const snap=capture.makeAuditSnapshot(inputs(),first);
 assert.equal(snap.metricDefinitions,60);
 assert.equal(snap.verifiedYearAudits,0);
 assert.equal(snap.rawCalibrationRegistryEntries,0);
 assert.equal(snap.rawReviewedTrialSnapshots,0);
 assert.equal(snap.claimedPredecisionThreeWayForecasts,0);
 assert.equal(snap.accuracyScore,null);
 assert.equal(snap.accuracyPercent,null);
 assert.equal(snap.status,"NOT_INDEPENDENTLY_RATED");
 assert.match(snap.note,/not accepted historical returns/);
});
test("system audit events append only when tracked source changes",()=>{
 const e={schemaVersion:1,scope:"RAAS_SELF_AUDIT_HISTORY",note:"isolated fixture",records:[]};
 const x=capture.makeAuditSnapshot(inputs(),first);
 const a=capture.appendAuditSnapshot(e,x);
 assert.equal(a.added,1);
 const replay=capture.appendAuditSnapshot(a.ledger,capture.makeAuditSnapshot(inputs(),second));
 assert.equal(replay.added,0);
 assert.deepEqual(a.ledger.records,replay.ledger.records);
 const altered=inputs();
 altered["data/raas-active-2024-2025-pdufa-intake.json"]=
  altered["data/raas-active-2024-2025-pdufa-intake.json"].replace(
   "Active two-year source-reviewed PDUFA intake","Active two-year source-reviewed PDUFA intake — rereviewed");
 const later=capture.appendAuditSnapshot(a.ledger,capture.makeAuditSnapshot(altered,second));
 assert.equal(later.added,1);
 assert.equal(later.ledger.records.length,2);
 assert.equal(later.ledger.records[0].eventId,x.eventId);
 assert.equal(later.ledger.records[1].accuracyScore,null);
 assert.throws(()=>capture.appendAuditSnapshot(later.ledger,x),/BACKDATING/);
});
test("no silent source-schema or metric-count failure",()=>{
 const source=inputs();
 source["lib/raas-metric-specs.ts"]=source["lib/raas-metric-specs.ts"].replace('"id": "pre-1-1"','"id": "removed-1"');
 assert.throws(()=>capture.makeAuditSnapshot(source,first),/SOURCE_INVALID/);
});
test("self-rating history and third trial spreadsheet are wired",()=>{
 const auditPage=read("app/raas-scan/page.tsx");
 const meta=read("app/raas-scan/RaasSelfAuditHistoryButton.tsx");
 const trials=read("app/Phase3ReadoutSheets.tsx");
 const button=read("app/RaasTrialHistoryButton.tsx");
 const workflow=fs.readFileSync(path.join(repo,".github/workflows/pdufa-nightly-scoring-then-repair.yml"),"utf8");
 assert.match(auditPage,/<RaasSelfAuditHistoryButton audit=\{selfAudit\}\/>/);
 assert.match(meta,/data-raas-system-history-button/);
 assert.match(meta,/RAAS Accuracy · N\/A/);
 assert.match(meta,/Independent accuracy not measurable/);
 assert.match(meta,/aria-expanded=\{open\}/);
 assert.match(trials,/<RaasTrialHistoryButton row=\{row\} bucket=\{null\}\/>/);
 assert.match(button,/bucket:RaasStage\|null/);
 assert.match(button,/UNVERIFIED/);
 assert.match(workflow,/node scripts\/raas_self_audit_history_capture\.cjs/);
 assert.match(workflow,/raas-self-audit-history\.json/);
 for(const [src,file] of [[auditPage,"page.tsx"],[meta,"RaasSelfAuditHistoryButton.tsx"],
  [trials,"Phase3ReadoutSheets.tsx"],[button,"RaasTrialHistoryButton.tsx"]]){
  const out=ts.transpileModule(src,{fileName:file,reportDiagnostics:true,
   compilerOptions:{jsx:ts.JsxEmit.ReactJSX,target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext}});
  assert.deepEqual((out.diagnostics||[]).filter(d=>d.category===ts.DiagnosticCategory.Error).map(d=>d.code),[]);
 }
});
