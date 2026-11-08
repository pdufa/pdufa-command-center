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
 assert.equal(graded,46);assert.equal(missing,4);assert.equal(full,7);
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
 assert.equal(status.classifiedSourceAcceptedGrades,46);
 assert.equal(status.classifiedMissingGrades,4);
 assert.equal(status.currentCapEligibility,"UNVERIFIED_FOR_ALL_HISTORICAL_ROWS");
});
test("unverified stage never produces a full clinical score, nor reinterprets missing as zero",()=>{
 const trial={nctId:"NCT07363577",ticker:"LBRX"};
 const unverified=clinicalFiveForTrial(trial,"pre",false);
 assert.equal(unverified.factors.length,5);
 assert.equal(unverified.researchScore,null);
 assert.equal(unverified.graded,5);
 assert.equal(unverified.missing,0);
 // Five research grades do not imply confirmed issuer readout or FDA validation.
 const source=JSON.parse(fs.readFileSync(path.join(root,"data/raas-reviewed-metric-assessments.json"),"utf8"));
 assert.equal(source.records.length,96);
});

test("previously saved research-only grades appear for 13 unclassified NCTs without fabricating a stage",()=>{
 const csv=fs.readFileSync(path.join(root,"public/raas-741-five-clinical-score-matrix.csv"),"utf8");
 const rows=csv.trim().split(/\r?\n/).slice(1).map(line=>line.slice(1,-1).split('","'));
 const recovered=rows.filter(r=>r[4]==="UNVERIFIED"&&Number(r[13])>0);
 assert.equal(recovered.length,13);
 assert.equal(recovered.reduce((n,r)=>n+Number(r[13]),0),50);
 assert.equal(recovered.filter(r=>Number(r[13])===5).length,4);
 assert.ok(recovered.every(r=>r[15]===""));
 const exception=recovered.filter(r=>r[16]==="REVIEWED_SOURCE_STAGE_DIFFERS_FROM_REGISTRY_PREVIEW");
 assert.equal(exception.length,1);
 assert.equal(exception[0][0],"NCT05208047");
 assert.equal(exception[0][6],"pre");
 assert.equal(exception[0][7],"post");
 const coverage=JSON.parse(fs.readFileSync(path.join(root,"data/raas-active-741-coverage.json"),"utf8"));
 assert.equal(coverage.recordedClinicalGradesAcross741,96);
 assert.equal(coverage.issuerStageClassifiedTrials,10);
 assert.equal(coverage.stageUnverifiedTrials,731);
});

test("all 741 research source queue keeps stage separate from registry posting and contains no invented numerical clinical grade",()=>{
 const csv=fs.readFileSync(path.join(root,"public/raas-741-trial-source-readiness.csv"),"utf8");
 const lines=csv.trim().split(/\r?\n/);
 assert.equal(lines.length,742);
 assert.match(lines[0],/primaryComparisonCount/);
 assert.match(lines[0],/safetyTermsWithArmDenominators/);
 assert.match(lines[0],/clinicalRAASDisclaimer/);
 const rows=lines.slice(1).map(line=>line.slice(1,-1).split('","'));
 assert.equal(new Set(rows.map(r=>r[0])).size,741);
 assert.equal(rows.filter(r=>r[4]==="UNVERIFIED").length,731);
 assert.equal(rows.filter(r=>r[7]==="YES").length,329);
 assert.equal(rows.filter(r=>r[5]==="UNAVAILABLE").length,2);
 assert.ok(rows.every(r=>r[19].includes("NOT a numerical clinical grade")));
 const c=JSON.parse(fs.readFileSync(path.join(root,"data/raas-active-741-coverage.json"),"utf8"));
 assert.equal(c.registryEvidenceLeadCensus.primaryComparisonResearchLeads,180);
 assert.equal(c.registryEvidenceLeadCensus.safetyArmDenominatorResearchLeads,243);
});
