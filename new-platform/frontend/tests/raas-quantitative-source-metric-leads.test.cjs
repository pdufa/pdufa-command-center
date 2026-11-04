"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,
 compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,esModuleInterop:true}}
).outputText,file);
const registry=require("../lib/raas-registry-evidence.ts");
const sample=(published=true)=>({
 nctId:"NCT12345678",ticker:"TEST",sourceUrl:"https://clinicaltrials.gov/study/NCT12345678",
 sourceHash:"b".repeat(64),retrievedAt:"2026-11-04T18:16:16Z",
 registryLastUpdated:"2026-11-03",resultsFirstPosted:published?"2026-11-01":null,
 registryStatus:"COMPLETED",registeredPhases:["PHASE3"],registeredConditions:["Condition A"],
 registeredInterventions:["Drug A","Matching placebo"],registeredDesign:{allocation:"RANDOMIZED",
 masking:"DOUBLE",interventionModel:"PARALLEL",studyType:"INTERVENTIONAL",
 enrollment:210,enrollmentType:"ACTUAL"},
 primaryDefinitions:[{measure:"Change in symptoms",timeFrame:"Week 12"}],
 postedResults:published,postedPrimaryOutcomeCount:published?1:0,postedOtherOutcomeCount:0,
 primaryResults:published?[{title:"Change in symptoms",timeFrame:"Week 12",
  unit:"points",analysisCount:1,pValues:["0.0006"],
  groups:[{id:"OG000",title:"Drug A"},{id:"OG001",title:"Placebo"}],
  measurements:[{groupId:"OG000",value:"-22.5"},{groupId:"OG001",value:"-13.5"}],
  comparisons:[{groupIds:["OG000","OG001"],pValue:"0.0006",
   method:"MMRM",paramType:"MEAN_DIFFERENCE",paramValue:"-9.0",
   ciPctValue:"95",ciLowerLimit:"-12.1",ciUpperLimit:"-5.9"}]}]:[],
 seriousAdverseEventTermCount:published?1:0,
 seriousEventDetails:published?[{term:"Infections",groups:[
  {groupId:"EG000",numAffected:3,numAtRisk:100,numEvents:3},
  {groupId:"EG001",numAffected:7,numAtRisk:110,numEvents:7}]}]:[],
 evidenceState:published?"POSTED_RESULTS_UNGRADED":"PROTOCOL_ONLY"
});
const trial=x=>({nctId:x.nctId,ticker:x.ticker,drug:"Drug A"});
test("actual numerical registry facts are mapped to exact RAAS BOTTOM ingredient slots without converting them to grades",()=>{
 const e=sample(),xs=registry.registryMetricLeads(e,"post",trial(e));
 const f=x=>xs.filter(a=>a.kind===x);
 const effects=f("POSTED_PRIMARY_CONTRAST_RAW_MEASUREMENT");
 const cis=f("POSTED_PRIMARY_CI_WIDTH_RAW_MEASUREMENT");
 const p=f("POSTED_PRIMARY_P_VALUE_RAW_MEASUREMENT");
 const adverse=f("POSTED_SAE_AFFECTED_RATE_RAW_MEASUREMENT");
 assert.equal(effects.length,1);
 assert.equal(effects[0].measurement.value,-9);
 assert.deepEqual(effects[0].metricIds,["post-1-1"]);
 assert.equal(cis.length,1);assert.ok(Math.abs(cis[0].measurement.value-6.2)<1e-9);
 assert.deepEqual(cis[0].metricIds,["post-1-3"]);
 assert.equal(p.length,1);assert.equal(p[0].measurement.value,0.0006);
 assert.equal(adverse.length,2);assert.equal(adverse[0].measurement.value,3);
 assert.equal(adverse[1].measurement.value,6.36);
 assert.deepEqual(adverse[0].metricIds,["post-1-5"]);
 for(const x of [...effects,...cis,...p,...adverse]){
  assert.ok(!Object.hasOwn(x,"score")&&!Object.hasOwn(x,"grade"));
  assert.equal(x.sourceUrl,e.sourceUrl);
  assert.equal(x.sourceDate,e.resultsFirstPosted);
 }
});
test("unknown drug and unpublished outcomes never yield treatment-effect measurements",()=>{
 const e=sample();
 assert.equal(registry.registryMetricLeads(e,"post",{...trial(e),drug:"Other drug"}).length,0);
 assert.equal(registry.registryMetricLeads(sample(false),"post",trial(e)).length,0);
 assert.ok(registry.registryMetricLeads(sample(false),"pre",trial(e)).every(x=>x.measurement===null));
});
test("malformed numeric values, absent matched pair, and impossible adverse rates cannot produce derived efficacy facts",()=>{
 const e=sample();
 e.primaryResults[0].comparisons[0].paramValue="n/a";
 e.primaryResults[0].comparisons[0].ciLowerLimit="n/a";
 e.primaryResults[0].comparisons[0].pValue="<0.001";
 e.seriousEventDetails[0].groups[0].numAffected=101;
 const xs=registry.registryMetricLeads(e,"post",trial(e));
 assert.equal(xs.filter(x=>x.kind==="POSTED_PRIMARY_CONTRAST_RAW_MEASUREMENT").length,0);
 assert.equal(xs.filter(x=>x.kind==="POSTED_PRIMARY_CI_WIDTH_RAW_MEASUREMENT").length,0);
 assert.equal(xs.filter(x=>x.kind==="POSTED_PRIMARY_P_VALUE_RAW_MEASUREMENT").length,0);
 assert.equal(xs.filter(x=>x.kind==="POSTED_SAE_AFFECTED_RATE_RAW_MEASUREMENT").length,1);
});
test("source numerical observations are rendered under the existing 30-metric evidence, not overall RAAS",()=>{
 const book=fs.readFileSync(path.join(root,"lib/raas-metric-gradebook.ts"),"utf8");
 const panel=fs.readFileSync(path.join(root,"app/RaasMetricGradebook.tsx"),"utf8");
 assert.match(book,/registryMetricLeads\(registry,stage,trial\)/);
 assert.match(panel,/lead\.measurement\.value\.toLocaleString/);
 assert.match(panel,/Overall RAAS: N\/A/);
 const out=ts.transpileModule(panel,{fileName:"RaasMetricGradebook.tsx",
  reportDiagnostics:true,compilerOptions:{jsx:ts.JsxEmit.ReactJSX,module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}});
 assert.deepEqual((out.diagnostics||[]).filter(x=>x.category===ts.DiagnosticCategory.Error),[]);
});
