"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const sheet=read("app/Phase3ReadoutSheets.tsx");
const style=read("app/Phase3ReadoutSheets.module.css");
const spec=read("lib/raas-metric-specs.ts");
const catalog=JSON.parse(spec.split('export const RAAS_METRIC_CATALOG:Readonly<Record<RaasStage,readonly RaasCategory[]>>=')[1].trim().replace(/;\s*$/,""));
test("TOP and BOTTOM have genuinely different scientific and timing ingredients",()=>{
 const a=catalog.pre,b=catalog.post;
 assert.equal(a.length,6);assert.equal(b.length,6);
 assert.equal(a.reduce((n,g)=>n+g.metrics.length,0),30);
 assert.equal(b.reduce((n,g)=>n+g.metrics.length,0),30);
 assert.equal(a.reduce((n,g)=>n+g.weight,0),100);
 assert.equal(b.reduce((n,g)=>n+g.weight,0),100);
 assert.notDeepEqual(a.map(g=>g.name),b.map(g=>g.name));
 const aNames=a.flatMap(g=>g.metrics.map(m=>m.name));
 const bNames=b.flatMap(g=>g.metrics.map(m=>m.name));
 assert.equal(new Set(aNames).size,30);assert.equal(new Set(bNames).size,30);
 assert.notDeepEqual(aNames,bNames);
 assert.ok(aNames.some(x=>/pivotal endpoint alignment/i.test(x)));
 assert.ok(bNames.some(x=>/primary endpoint and treatment effect/i.test(x)));
 assert.ok(aNames.some(x=>/readout window/i.test(x)));
 assert.ok(bNames.some(x=>/PDUFA/i.test(x)));
});
test("active stage survey shows exactly five clinical specifications, preserving separate source stages",()=>{
 assert.match(sheet,/function StageSurveyIngredients\(\{bucket\}:\{bucket:RaasStage\}\)/);
 assert.match(sheet,/const factors=clinicalFiveDefinitions\(bucket\)/);
 assert.equal(sheet.split("<StageSurveyIngredients bucket={bucket}/>").length-1,2);
 assert.match(sheet,/data-raas-stage-survey-ingredients=\{bucket\}/);
 assert.match(sheet,/TOP · before Phase 3 results/);
 assert.match(sheet,/FOCUS · after Phase 3 results/);
 assert.match(sheet,/f\.requiredEvidence/);
 assert.match(sheet,/f\.scoreRule/);
 assert.match(sheet,/f\.criticalRisk/);
 assert.match(sheet,/TOP Surveys/);
 assert.match(sheet,/FOCUS Surveys/);
});

test("five clinical sections expand horizontally while historical general survey remains distinct",()=>{
 assert.match(style,/\.stageSurveyGroup\[open\]\{display:flex;align-items:stretch;border:2px/);
 assert.match(style,/\.stageSurveyGroupIngredients\{display:flex;gap:7px;flex:1;min-width:0/);
 assert.match(sheet,/factors\.map\(\(f,i\)=>/);
 assert.match(sheet,/SURVEY_QUESTION_IDS\.length/);
 assert.match(sheet,/BENEFIT_GROUPS\.filter/);
 assert.match(sheet,/finalSurveyReadiness\(groups,rules/);
 assert.doesNotMatch(sheet,/RAAS_METRIC_CATALOG\["pre"\].*RAAS_METRIC_CATALOG\["post"\]/);
});

test("survey and synthesis TSX still parse after separate TOP/BOTTOM drill-down",()=>{
 const result=ts.transpileModule(sheet,{fileName:"Phase3ReadoutSheets.tsx",
  reportDiagnostics:true,compilerOptions:{jsx:ts.JsxEmit.ReactJSX,
   target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext}});
 assert.deepEqual((result.diagnostics||[]).filter(d=>d.category===ts.DiagnosticCategory.Error)
  .map(d=>ts.flattenDiagnosticMessageText(d.messageText," ")),[]);
});
