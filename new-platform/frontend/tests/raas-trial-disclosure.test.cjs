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
const specs=fs.readFileSync(path.join(root,"lib/raas-metric-specs.ts"),"utf8");
const catalogJson=specs.split('export const RAAS_METRIC_CATALOG:Readonly<Record<RaasStage,readonly RaasCategory[]>>=')[1];
assert.ok(catalogJson,"RAAS canonical metric catalog must be present");
const catalog=JSON.parse(catalogJson.trim().replace(/;\s*$/,""));
test("both documented release spreadsheets place RAAS before Surveys and SURVEY",()=>{
 const headerAt=table.indexOf('<th scope="col" title="Proposed phase-specific risk-adjusted appreciation score');
 const surveysAt=table.indexOf('sortedHeader("survey","Survey Ratings"',headerAt);
 const synthesisAt=table.indexOf('sortedHeader("synthesis","SURVEY"',surveysAt);
 assert.ok(headerAt>0&&surveysAt>headerAt&&synthesisAt>surveysAt);
 const raasAt=table.indexOf("<TrialRaasDisclosure row={row}");
 const surveyButtonAt=table.indexOf('onSurveyOpen(row,"details")',raasAt);
 const synthesisButtonAt=table.indexOf('onSurveyOpen(row,"synthesis")',surveyButtonAt);
 assert.ok(raasAt>0&&surveyButtonAt>raasAt&&synthesisButtonAt>surveyButtonAt);
 assert.match(table,/benefitFeed=\{benefitFeed\} onResearchRequest=\{onRaasOpen\}/);
 assert.match(table,/colSpan=\{\(bucket==="post"\?11:10\)/);
});
test("per-trial TOP and BOTTOM RAAS begin closed with four-stage drilldown",()=>{
 assert.match(raas,/const label=isTop\?"TOP-RAAS":"BOTTOM-RAAS"/);
 assert.match(raas,/data-raas-phase=\{bucket\} data-raas-trial=\{row.nctId\}/);
 assert.match(raas,/groups.map\(\(group,i\)=><details/);
 assert.match(raas,/group.metrics.map\(\(metric,j\)=><details/);
 assert.doesNotMatch(raas,/<details[^>]*\sopen(?:\s|=|>)/);
 assert.match(styles,/\.factor\[open\]\{display:flex;flex-wrap:nowrap/);
 assert.match(styles,/\.metric\[open\]\{display:flex/);
 assert.match(raas,/ENTRY/);
 assert.match(raas,/CURRENT/);
 assert.match(raas,/EXIT/);
 assert.match(raas,/— \/ 100 · Not scored/);
 assert.match(raas,/name=\{groupName\}/);
 assert.match(raas,/name=\{"raas-metric-"/);
});
test("exactly 30 metric definitions in each stage, with 6 groups and 100 percent total weight",()=>{
 for(const [stage,groups] of Object.entries(catalog)){
  assert.ok(["pre","post"].includes(stage));
  assert.equal(groups.length,6,stage+" six groups");
  assert.equal(groups.reduce((sum,x)=>sum+x.weight,0),100,stage+" 100% weight");
  assert.equal(groups.reduce((sum,x)=>sum+x.metrics.length,0),30,stage+" 30 metrics");
  const ids=groups.flatMap(x=>x.metrics.map(y=>y.id));
  assert.equal(new Set(ids).size,30,stage+" unique metric IDs");
  for(const g of groups){
   assert.equal(g.metrics.length,5,g.name+" five component metrics");
   for(const m of g.metrics){
    assert.ok(m.name&&m.requiredEvidence&&m.scoreRule&&m.criticalRisk,m.id+" complete definitions");
    assert.ok(Array.isArray(m.relatedFieldIds),m.id+" source map");
   }
  }
 }
 assert.equal(Object.keys(catalog).length,2);
});
test("no scores invented; related research data is only displayed as candidate evidence",()=>{
 assert.match(raas,/Missing inputs are not zeros/);
 assert.match(raas,/evidence coverage is not a RAAS score/);
 assert.match(raas,/Related research fields · not a metric score/);
 assert.match(raas,/exactReadoutBenefit\(row,benefitFeed\)/);
 assert.match(raas,/Pending validated calculation/);
 assert.match(raas,/PilotEvidence/);
 assert.match(raas,/computeRaasScore\(/);
 assert.match(specs,/precommitted/);
 assert.match(specs,/missing data/i);
});
test("RAAS, catalog and spreadsheet TypeScript parse without syntax errors",()=>{
 for(const [name,code] of [["table",table],["raas",raas],["catalog",specs]]){
  const result=ts.transpileModule(code,{fileName:name+(name==="catalog"?".ts":".tsx"),reportDiagnostics:true,compilerOptions:{jsx:ts.JsxEmit.ReactJSX,target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext}});
  assert.deepEqual((result.diagnostics||[]).filter(d=>d.category===ts.DiagnosticCategory.Error).map(d=>ts.flattenDiagnosticMessageText(d.messageText," ")),[],name+" syntax");
 }
});
