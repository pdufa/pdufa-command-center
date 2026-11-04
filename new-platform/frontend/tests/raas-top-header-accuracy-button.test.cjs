"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
const source=fs.readFileSync(path.join(root,"app/Phase3ReadoutSheets.tsx"),"utf8");
const css=fs.readFileSync(path.join(root,"app/Phase3ReadoutSheets.module.css"),"utf8");
const top=require("../data/raas-retrospective-top-cases.json");
const calibrations=require("../data/raas-approved-calibrations.json");
const reviewed=require("../data/raas-historical-cases.json");
const legacy=require("../data/raas-fda-three-way-accuracy-site-snapshot.json");
test("TOP accuracy button is directly below TOP-RAAS header and BOTTOM header stays unchanged",()=>{
 assert.match(source,/<th scope="col" title="Proposed phase-specific risk-adjusted appreciation score; grade not yet validated">\{bucket==="pre"\?<><span>TOP-RAAS<\/span><TopRaasAccuracyButton\/><\/>:<span>BOTTOM-RAAS<\/span>\}<\/th>/);
 assert.equal(source.split("<TopRaasAccuracyButton/>").length-1,1);
 assert.match(source,/data-raas-top-survey-accuracy="UNVERIFIED"/);
 assert.match(source,/data-raas-accuracy-scope="TOP_ONLY_NOT_LEGACY_COMBINED"/);
});
test("TOP button expands and collapses horizontally using keyboard-accessible live state",()=>{
 assert.match(source,/function TopRaasAccuracyButton\(\)\{[\s\S]*?useState\(false\)/);
 assert.match(source,/aria-expanded=\{open\}/);
 assert.match(source,/aria-controls="top-raas-accuracy-breakdown"/);
 assert.match(source,/onClick=\{\(\)=>setOpen\(value=>!value\)\}/);
 assert.match(source,/\{open&&<div id="top-raas-accuracy-breakdown"/);
 assert.match(source,/TOP Accuracy · N\/A/);
 assert.match(css,/\.topRaasAccuracyRow\{/);
 assert.match(css,/display:inline-flex;align-items:stretch/);
 assert.match(css,/\.topRaasAccuracyDetails\{/);
 assert.match(css,/border-left:1px solid/);
 assert.match(css,/\.topRaasAccuracyButton\[aria-expanded="true"\]/);
 assert.match(css,/@media\(max-width:640px\)/);
});
test("actual saved TOP figures remain distinct from combined legacy retrospective FDA rate",()=>{
 assert.equal(top.records.length,3);
 assert.equal(reviewed.cases.filter(x=>x.stage==="pre").length,0);
 assert.equal(calibrations.entries.filter(x=>x.stage==="pre").length,0);
 assert.equal(legacy.legacyRetrospectiveCases,146);
 assert.equal(legacy.legacyCorrect,102);
 assert.equal(legacy.legacyRetrospectiveAccuracyPct,69.86);
 assert.equal(legacy.alwaysApproveCorrect,106);
 assert.equal(legacy.alwaysApproveRetrospectiveAccuracyPct,72.6);
 assert.equal(Math.round((legacy.legacyRetrospectiveAccuracyPct-
  legacy.alwaysApproveRetrospectiveAccuracyPct)*100)/100,-2.74);
 assert.match(source,/legacy 146-case reading combines a different/);
 assert.match(source,/must not be used as TOP survey accuracy/);
 assert.match(source,/TOP prediction accuracy<\/dt><dd>N\/A/);
 assert.doesNotMatch(source,/TOP Accuracy · 69\.86/);
});
test("TOP button TypeScript/TSX compiles as a valid React component",()=>{
 const result=ts.transpileModule(source,{
  fileName:"Phase3ReadoutSheets.tsx",reportDiagnostics:true,
  compilerOptions:{jsx:ts.JsxEmit.ReactJSX,
   target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext}
 });
 const errors=(result.diagnostics||[]).filter(x=>x.category===ts.DiagnosticCategory.Error)
  .map(x=>ts.flattenDiagnosticMessageText(x.messageText," "));
 assert.deepEqual(errors,[]);
});
