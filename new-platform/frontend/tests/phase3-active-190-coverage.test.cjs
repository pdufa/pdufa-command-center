"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),ts=require("typescript");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,
 compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,esModuleInterop:true}}
).outputText,file);
const {GET}=require("../app/api/phase3-active-190-coverage/route.ts");

test("active TOP and BOTTOM 190-column evidence matrix covers exactly 258 NCTs without fabricated scores",async()=>{
 const r=await GET(new Request("http://localhost/api/phase3-active-190-coverage"));
 assert.equal(r.status,200,await r.clone().text());
 const data=await r.json();
 const n=data.totals;
 assert.equal(n.trials,258);
 assert.equal(n.columnsPerTrial,190);
 assert.equal(n.expectedCells,258*190);
 assert.equal(n.preTrials,229);
 assert.equal(n.postTrials,29);
 assert.equal(n.questionSlots,258*30);
 assert.equal(n.documentedQuestions+n.predictedQuestions+n.unscoredQuestions,258*30);
 assert.equal(data.rows.length,258);
 assert.equal(new Set(data.rows.map(r=>r.nctId)).size,258);
 for(const row of data.rows){
  assert.match(row.nctId,/^NCT\d{8}$/);
  assert.equal(row.columnCount,190);
  assert.equal(row.documentedQuestions+row.predictedQuestions+row.unscoredQuestions,30);
  assert.ok(row.nonemptyCells>=40&&row.nonemptyCells<=190);
  assert.ok(row.numericQuestionScores<=row.predictedQuestions);
  assert.equal(row.clinicalResearchRating===null,row.clinicalScoredFactors===0);
  assert.ok(row.missingQuestionNumbers.every(x=>x>=1&&x<=30));
 }
 const agio=data.rows.filter(r=>r.ticker==="AGIO");
 const ions=data.rows.filter(r=>r.ticker==="IONS");
 assert.equal(agio.length,9);
 assert.equal(ions.length,12);
 assert.equal(ions.filter(r=>r.cohort==="POST_DATA").length,3);
 assert.equal(ions.filter(r=>r.cohort==="PRE_DATA").length,9);
});

test("active coverage CSV preserves one row per exact trial",async()=>{
 const r=await GET(new Request("http://localhost/api/phase3-active-190-coverage?format=csv"));
 assert.equal(r.status,200);
 const lines=(await r.text()).trim().split(/\r?\n/);
 assert.equal(lines.length,259);
 assert.match(lines[0],/Evidence-backed questions/);
});

test("rejects invalid coverage format",async()=>{
 const r=await GET(new Request("http://localhost/api/phase3-active-190-coverage?format=invalid"));
 assert.equal(r.status,400);
});
