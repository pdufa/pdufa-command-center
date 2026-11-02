"use strict";
const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs"),ts=require("typescript");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(fs.readFileSync(file,"utf8"),
 {compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,file);
const {observedSeriousEventRate}=require("../lib/registry-observation-math.ts");
test("reported serious-event group frequency uses explicit at-risk denominator and one decimal",()=>{
 assert.equal(observedSeriousEventRate(9,60),15);
 assert.equal(observedSeriousEventRate(1,9),11.1);
 assert.equal(observedSeriousEventRate(0,19),0);
 assert.equal(observedSeriousEventRate(8,8),100);
});
test("invalid numerators and denominators cannot create reported event incidence",()=>{
 for(const args of [[4,0],[-1,5],[6,5],[1.5,10],[1,2.3],[NaN,8],[1,Infinity]]){
  assert.equal(observedSeriousEventRate(...args),null);
 }
});
test("source packet detail is explicit exact-NCT on-demand; no fabricated clinical claim",()=>{
 const ui=fs.readFileSync(require("node:path").join(__dirname,"../app/ToolsOpeningTrialGrid.tsx"),"utf8");
 assert.match(ui,/function RegistryMeasuredDetail/);
 assert.match(ui,/\/api\/tools-trial-evidence\?nct=/);
 assert.match(ui,/item\.nctId!==nctId/);
 assert.match(ui,/observedSeriousEventRate\(group\.affected,group\.atRisk\)/);
 assert.match(ui,/No effectiveness or stock ranking/);
 assert.match(ui,/\/\^NCT\\d\{8\}\$\/\.test\(row\.nctId\)/);
});
