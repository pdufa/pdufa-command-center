const test=require("node:test");const assert=require("node:assert/strict");const fs=require("node:fs");const path=require("node:path");const Module=require("node:module");const ts=require("typescript");const f=path.resolve(__dirname,"../lib/decision-fda-coverage.ts");const js=ts.transpileModule(fs.readFileSync(f,"utf8"),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020}}).outputText;const m=new Module(f,module);m.filename=f;m.paths=module.paths;m._compile(js,f);const {assessFdaDecisionCoverage}=m.exports;
test("incomplete CRL population blocks readiness",()=>assert.equal(assessFdaDecisionCoverage(20,3,0).status,"NOT_READY"));
test("approval-only historical sample blocks readiness",()=>assert.equal(assessFdaDecisionCoverage(20,0,0,true).status,"NOT_READY"));
test("unresolved outcomes block readiness",()=>assert.equal(assessFdaDecisionCoverage(20,3,1,true).status,"NOT_READY"));
test("even complete declared coverage remains review-required",()=>assert.equal(assessFdaDecisionCoverage(20,3,0,true).status,"REVIEW_REQUIRED"));
test("invalid record counts fail closed",()=>assert.equal(assessFdaDecisionCoverage(-1,3,0,true).status,"NOT_READY"));
