const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const ts=require("typescript");
const vm=require("node:vm");
const src=fs.readFileSync(path.join(__dirname,"../lib/peak-reported-evidence.proposed.ts"),"utf8");
const compiled=ts.transpileModule(src,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
const moduleExports={};vm.runInNewContext(compiled,{exports:moduleExports});
const rows=moduleExports.PEAK_REPORTED_EVIDENCE;
test("reported evidence maps to distinct valid SCIENCE question IDs",()=>{
 assert.equal(rows.length,11);
 assert.equal(new Set(rows.map(r=>r.assessmentId)).size,rows.length);
 for(const r of rows){assert.match(r.assessmentId,/^S(?:0[1-9]|[1-3][0-9]|40)$/);assert.ok(r.sourceUrl.startsWith("https://"));assert.ok(r.requiredFollowup.length>15);}
});
test("published evidence never implies verified, scored or predicted",()=>{
 for(const r of rows){assert.equal(r.status,"PUBLISHED_UNVERIFIED");assert.equal("score" in r,false);assert.equal("approvalProbability" in r,false);}
});
