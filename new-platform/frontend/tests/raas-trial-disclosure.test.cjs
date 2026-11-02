"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const ts=require("typescript");
const root=path.resolve(__dirname,"..");
const table=fs.readFileSync(path.join(root,"app/Phase3ReadoutSheets.tsx"),"utf8");
const raas=fs.readFileSync(path.join(root,"app/TrialRaasDisclosure.tsx"),"utf8");
const styles=fs.readFileSync(path.join(root,"app/TrialRaasDisclosure.module.css"),"utf8");
test("both documented release spreadsheets place RAAS before Surveys and SURVEY",()=>{
 const headerAt=table.indexOf('<th scope="col" title="Proposed phase-specific risk-adjusted appreciation score');
 const surveysAt=table.indexOf('sortedHeader("survey","Survey Ratings"',headerAt);
 const synthesisAt=table.indexOf('sortedHeader("synthesis","SURVEY"',surveysAt);
 assert.ok(headerAt>0&&surveysAt>headerAt&&synthesisAt>surveysAt);
 const raasAt=table.indexOf("<TrialRaasDisclosure row={row}");
 const surveyButtonAt=table.indexOf('onSurveyOpen(row,"details")',raasAt);
 const synthesisButtonAt=table.indexOf('onSurveyOpen(row,"synthesis")',surveyButtonAt);
 assert.ok(raasAt>0&&surveyButtonAt>raasAt&&synthesisButtonAt>surveyButtonAt);
 assert.match(table,/onRaasOpen=\{onResearchSort\}/);
 assert.match(table,/colSpan=\{\(bucket==="post"\?11:10\)/);
});
test("per-trial TOP and BOTTOM RAAS are closed by default with independent six-group ingredients",()=>{
 assert.match(raas,/const label=isTop\?"TOP-RAAS":"BOTTOM-RAAS"/);
 assert.match(raas,/data-raas-phase=\{bucket\} data-raas-trial=\{row.nctId\}/);
 assert.match(raas,/groups.map\(\(group,i\)=><details/);
 assert.doesNotMatch(raas,/<details[^>]*\sopen(?:\s|=|>)/);
 assert.match(styles,/\.factor\[open\]\{display:flex;flex-wrap:nowrap/);
 assert.match(raas,/ENTRY/);
 assert.match(raas,/CURRENT/);
 assert.match(raas,/EXIT/);
 assert.match(raas,/— \/ 100 · Not scored/);
});
test("each independent RAAS weighting sums to 100 without declaring numeric trial ratings",()=>{
 const top=raas.match(/const TOP:readonly Ingredient\[\]=\[([\s\S]*?)\];\nconst BOTTOM/);
 const bottom=raas.match(/const BOTTOM:readonly Ingredient\[\]=\[([\s\S]*?)\];\nexport default/);
 assert.ok(top&&bottom);
 for(const [phase,match] of [["TOP",top],["BOTTOM",bottom]]){
   const weights=[...match[1].matchAll(/weight:(\d+)/g)].map(x=>Number(x[1]));
   assert.equal(weights.length,6,phase+" six categories");
   assert.equal(weights.reduce((a,b)=>a+b,0),100,phase+" total weight");
 }
 assert.match(raas,/Missing inputs are not zeros/);
 assert.match(raas,/evidence coverage is not a RAAS score/);
});
test("RAAS and spreadsheet JSX parse without TSX syntax errors",()=>{
 for(const [name,code] of [["table",table],["raas",raas]]){
  const result=ts.transpileModule(code,{fileName:name+".tsx",reportDiagnostics:true,compilerOptions:{jsx:ts.JsxEmit.ReactJSX,target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext}});
  assert.deepEqual((result.diagnostics||[]).filter(d=>d.category===ts.DiagnosticCategory.Error).map(d=>ts.flattenDiagnosticMessageText(d.messageText," ")),[],name+" syntax");
 }
});
