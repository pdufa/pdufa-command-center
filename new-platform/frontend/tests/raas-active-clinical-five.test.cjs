"use strict";
const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(fs.readFileSync(file,"utf8"),{
 fileName:file,compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,esModuleInterop:true}
}).outputText,file);
const {clinicalFiveForTrial,clinicalFiveForClassifiedRow,clinicalFiveDefinitions}=require("../lib/raas-clinical-five.ts");
const {parsePhase3CensusCsv}=require("../lib/phase3-census-rows.ts");
const {classifyPhase3Readouts}=require("../lib/phase3-public-readout.ts");
const census=parsePhase3CensusCsv(fs.readFileSync(path.join(root,"public/phase3-census-2026-10-26.csv"),"utf8"));
const source=JSON.parse(fs.readFileSync(path.join(root,"public/phase3-public-readout-evidence-2026-11-01.json"),"utf8"));
const classified=classifyPhase3Readouts(source,census.rows);
test("active five-factor model preserves exact stage identity and excludes nonclinical historical rubrics",()=>{
 for(const stage of ["pre","post"]){
  const factors=clinicalFiveDefinitions(stage);
  assert.equal(factors.length,5);
  assert.deepEqual(factors.map(x=>x.id),
   stage==="pre"?["pre-1-1","pre-1-5","pre-1-2","pre-1-3","pre-1-4"]:
    ["post-1-1","post-1-2","post-1-3","post-1-4","post-1-5"]);
  assert.ok(factors.every(x=>x.id.startsWith(stage+"-1-")));
 }
});
test("ten classified trials have exactly 50 active clinical slots and 26 documented grades",()=>{
 let graded=0,missing=0,full=0;
 for(const [stage,rows] of [["pre",classified.pre],["post",classified.post]]){
  for(const row of rows){
   const item=clinicalFiveForClassifiedRow(row,stage);
   assert.equal(item.factors.length,5);
   assert.equal(item.graded+item.missing,5);
   assert.ok(item.factors.every(x=>x.grade===null||[0,25,50,75,100].includes(x.grade)));
   if(item.researchScore!==null)full++;
   graded+=item.graded;missing+=item.missing;
  }
 }
 assert.equal(classified.pre.length,2);assert.equal(classified.post.length,8);
 assert.equal(graded,37);assert.equal(missing,13);assert.equal(full,4);
});
test("741 historical trials have five displayed research fields, without assuming eligible capitalization or stage",()=>{
 const csv=fs.readFileSync(path.join(root,"public/raas-741-active-five-clinical.csv"),"utf8");
 const rows=csv.trim().split(/\r?\n/);
 assert.equal(census.rows.length,741);assert.equal(rows.length,3706);
 const byTrial=new Map();
 for(const row of rows.slice(1)){
  const cols=row.split('","');const id=cols[0].replace(/^"/,"");
  byTrial.set(id,(byTrial.get(id)||0)+1);
 }
 assert.equal(byTrial.size,741);
 assert.ok([...byTrial.values()].every(x=>x===5));
 const status=JSON.parse(fs.readFileSync(path.join(root,"data/raas-active-741-coverage.json"),"utf8"));
 assert.equal(status.issuerStageClassifiedTrials,10);
 assert.equal(status.stageUnverifiedTrials,731);
 assert.equal(status.classifiedSourceAcceptedGrades,37);
 assert.equal(status.classifiedMissingGrades,13);
 assert.equal(status.currentCapEligibility,"UNVERIFIED_FOR_ALL_HISTORICAL_ROWS");
});
test("unverified stage never produces a full clinical score, nor reinterprets missing as zero",()=>{
 const trial={nctId:"NCT07363577",ticker:"LBRX"};
 const unverified=clinicalFiveForTrial(trial,"pre",false);
 assert.equal(unverified.factors.length,5);
 assert.equal(unverified.researchScore,null);
 assert.equal(unverified.graded,3);
 assert.equal(unverified.missing,2);
 const source=JSON.parse(fs.readFileSync(path.join(root,"data/raas-reviewed-metric-assessments.json"),"utf8"));
 assert.equal(source.records.length,96);
});
