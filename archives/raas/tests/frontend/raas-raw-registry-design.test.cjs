"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,
 compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,esModuleInterop:true}}
).outputText,file);
const {rawRaasRegistryDesignDiagnostic:grade}=require("../lib/raas-raw-registry-design.ts");
const {parseRegistryEvidenceIndex}=require("../lib/raas-registry-evidence.ts");
const index=parseRegistryEvidenceIndex(JSON.parse(
 fs.readFileSync(path.join(root,"public/raas-registry-evidence-index.json"),"utf8")));
const e=(override={})=>({...index.records[0],
 registeredPhases:["PHASE3"],
 registeredDesign:{allocation:"RANDOMIZED",masking:"QUADRUPLE",
  interventionModel:"PARALLEL",studyType:"INTERVENTIONAL",
  enrollment:420,enrollmentType:"ESTIMATED"},
 primaryDefinitions:[{measure:"Symptoms severity",timeFrame:"Week 12"}],
 registeredInterventions:["Drug A","Matching placebo"],...override});
const evaluate=(x)=>grade(x,{nctId:x.nctId,ticker:x.ticker});
test("source-backed exploratory 4/4 study-design diagnostic, never a 60-metric RAAS prediction",()=>{
 const s=e();const g=evaluate(s);
 assert.equal(g.score,100);assert.equal(g.knownFacets,4);
 assert.equal(g.lowerBound,100);assert.equal(g.upperBound,100);
 assert.equal(g.overallRaasScore,null);
 assert.equal(g.kind,"RESEARCH_DESIGN_DIAGNOSTIC_NOT_OVERALL_RAAS");
 assert.equal(g.ruleVersion,"raas-registry-design-v1");
 assert.equal(g.sourceUrl,s.sourceUrl);
});
test("observed unblinded nonrandomized single-group limitations are not mistaken for missing",()=>{
 const s=e({registeredDesign:{
  allocation:"NON_RANDOMIZED",masking:"NONE",interventionModel:"SINGLE_GROUP",
  studyType:"INTERVENTIONAL",enrollment:48,enrollmentType:"ACTUAL"},
  registeredInterventions:["Investigational drug"]});
 const g=evaluate(s);
 assert.equal(g.score,25);assert.equal(g.knownFacets,4);
 assert.equal(g.unknownFacets,0);
 assert.equal(g.facets.filter(f=>f.status==="OBSERVED_LIMITATION").length,3);
 assert.equal(g.facets.filter(f=>f.status==="UNKNOWN").length,0);
});
test("missing intervention comparator stays unknown; only >=3 known facets graded",()=>{
 const x=e({registeredInterventions:["Drug A"]});
 const g=evaluate(x);
 assert.equal(g.knownFacets,3);assert.equal(g.unknownFacets,1);
 assert.equal(g.lowerBound,75);assert.equal(g.upperBound,100);
 assert.equal(g.score,100);
 const old=e({registeredDesign:undefined});
 assert.equal(evaluate(old).score,null);
 assert.equal(evaluate(old).knownFacets,2);
});
test("invalid source association never yields a score; all registry records get audited",()=>{
 const trial=index.records[0];
 assert.equal(grade(trial,{nctId:"NCT99999999",ticker:trial.ticker}),null);
 assert.equal(grade(trial,{nctId:trial.nctId,ticker:"WRONG"}),null);
 assert.equal(index.records.length,762);
 for(const x of index.records){
  const d=evaluate(x);
  assert.ok(d);
  assert.equal(d.overallRaasScore,null);
  assert.ok(d.score===null||[0,25,50,75,100].includes(d.score));
  assert.ok(d.knownFacets>=0&&d.knownFacets<=4);
 }
});
test("both TOP/BOTTOM scorecards and the all-trial table show raw design diagnostic separately",()=>{
 const ui=fs.readFileSync(path.join(root,"app/RaasFullUniverseScores.tsx"),"utf8");
 const card=fs.readFileSync(path.join(root,"app/RaasMetricGradebook.tsx"),"utf8");
 const book=fs.readFileSync(path.join(root,"lib/raas-metric-gradebook.ts"),"utf8");
 assert.match(ui,/data-raas-raw-design-grade=\{x\.row\.nctId\}/);
 assert.match(ui,/data-raas-raw-design-graded="true"/);
 assert.match(card,/data-raas-raw-design-diagnostic=\{row\.nctId\}/);
 assert.match(card,/This diagnostic is excluded from the 30-metric weighted RAAS total/);
 assert.match(book,/rawDesignDiagnostic:rawRaasRegistryDesignDiagnostic/);
 for(const p of ["app/RaasFullUniverseScores.tsx","app/RaasMetricGradebook.tsx",
  "lib/raas-raw-registry-design.ts"]){
  const code=fs.readFileSync(path.join(root,p),"utf8");
  const out=ts.transpileModule(code,{fileName:p,reportDiagnostics:true,
   compilerOptions:{jsx:ts.JsxEmit.ReactJSX,module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}});
  assert.deepEqual((out.diagnostics||[]).filter(x=>x.category===ts.DiagnosticCategory.Error),[]);
 }
});
