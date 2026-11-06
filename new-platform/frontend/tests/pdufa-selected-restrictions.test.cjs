"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const Module=require("node:module");
const ts=require("typescript");
const root=path.resolve(__dirname,"..");
const sourcePath=path.join(root,"lib/pdufa-selected-restrictions.ts");
const compiled=ts.transpileModule(fs.readFileSync(sourcePath,"utf8"),{
 compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}
}).outputText;
const unit=new Module(sourcePath,module);unit.filename=sourcePath;unit.paths=module.paths;
unit._compile(compiled,sourcePath);
const p=unit.exports;
const ledger=JSON.parse(fs.readFileSync(path.join(root,"public/phase3-unified-classifications-2026-11-05.json"),"utf8"));
const audit=p.auditCensus(ledger.rows,"2026-11-06");
test("23 selected controls; all seven user-unselected restrictions OFF",()=>{
 assert.equal(p.ENABLED_POLICY.length,23);
 assert.equal(p.DISABLED_POLICY.length,7);
 assert.ok(p.ENABLED_POLICY.every(r=>r.enabled));
 assert.ok(p.DISABLED_POLICY.every(r=>!r.enabled));
 assert.equal(new Set([...p.ENABLED_POLICY,...p.DISABLED_POLICY].map(r=>r.id)).size,30);
});
test("762 exact NCTs reconcile to latest registry: 258 active, 501 historical, 3 unknown",()=>{
 assert.equal(audit.trialCount,762);
 assert.deepEqual(audit.lifecycle,{ACTIVE:258,HISTORICAL:501,VERIFY:3});
 assert.equal(audit.lifecycle.ACTIVE+audit.lifecycle.HISTORICAL+audit.lifecycle.VERIFY,762);
 assert.equal(audit.qualification,"NOT_VERIFIED");
 assert.equal(audit.rules.length,23);
 for(const rule of audit.rules)
  assert.equal(rule.counts.PASS+rule.counts.FAIL+rule.counts.UNKNOWN,762);
});
test("Closed study exclusion applies only to Active Phase View; unknown is not a failure",()=>{
 const active=audit.rules.find(r=>r.id==="activeview");
 assert.deepEqual(active.counts,{PASS:258,FAIL:501,UNKNOWN:3});
 assert.equal(p.trialLifecycle("SUSPENDED"),"VERIFY");
 assert.equal(p.trialLifecycle("UNKNOWN"),"VERIFY");
 assert.equal(p.trialLifecycle("COMPLETED"),"HISTORICAL");
 assert.equal(p.trialLifecycle("ACTIVE_NOT_RECRUITING"),"ACTIVE");
});
test("Unknown financial and application evidence never becomes arbitrary zero or PASS",()=>{
 const trial=ledger.rows.find(r=>r.registryStatus==="COMPLETED");
 assert.ok(trial);
 for(const id of ["public","cap","fda","identity","rights","dedup","capdate"])
  assert.equal(p.auditPolicyRule(id,trial,"2026-11-06").status,"UNKNOWN",id);
 assert.equal(p.auditPolicyRule("activeprog",trial,"2026-11-06").status,"UNKNOWN");
});
test("Immutable market-cap observations reject overwrites and bad sources",()=>{
 const next={nctId:"NCT00000001",ticker:"TEST",usd:300000000,basis:"ENTRY",observedAt:"2026-11-05",sourceUrl:"https://example.com/issuer"};
 const one=p.appendCapSnapshot([],next);
 assert.equal(one.length,1);
 assert.throws(()=>p.appendCapSnapshot(one,next),/IMMUTABLE_CAP/);
 assert.throws(()=>p.appendCapSnapshot([], {...next,usd:0}),/CAP_SOURCE_INVALID/);
 const two=p.appendCapSnapshot(one,{...next,basis:"CURRENT",observedAt:"2026-11-06"});
 assert.equal(two.length,2);
 assert.equal(two[0].usd,300000000);
});
