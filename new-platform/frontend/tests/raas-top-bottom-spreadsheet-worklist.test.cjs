"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,
 compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,
 esModuleInterop:true}}).outputText,file);
const {buildTopBottomRaasMetricWorklist:worklist}=
 require("../lib/raas-top-bottom-spreadsheet-worklist.ts");
const {parsePhase3CensusCsv}=
 require("../lib/phase3-census-rows.ts");
const {classifyPhase3Readouts}=
 require("../lib/phase3-public-readout.ts");
const csv=fs.readFileSync(path.join(root,"public/phase3-census-2026-10-26.csv"),"utf8");
const evidence=JSON.parse(fs.readFileSync(path.join(root,
 "public/phase3-public-readout-evidence-2026-11-01.json"),"utf8"));
const result=classifyPhase3Readouts(evidence,parsePhase3CensusCsv(csv).rows);

test("strictly classified TOP/BOTTOM spreadsheets generate exactly 30 metric requirements each",()=>{
 assert.equal(result.total,741);
 assert.equal(result.pre.length,2);
 assert.equal(result.post.length,8);
 assert.equal(result.unverified.length,731);
 for(const [stage,rows,label] of [["pre",result.pre,"TOP"],
  ["post",result.post,"BOTTOM"]]){
  const x=worklist(stage,rows);
  assert.equal(x.summary.sheet,label);
  assert.equal(x.summary.classifiedTrials,rows.length);
  assert.equal(x.summary.metricRequirementRows,rows.length*30);
  assert.equal(x.summary.approvedOverallRaasScores,0);
  assert.equal(x.summary.calibratedFdaForecasts,0);
  const l=x.csv.trimEnd().split("\r\n");
  assert.equal(l.length,rows.length*30+1);
  assert.match(l[0],/nctId,ticker,phase3Spreadsheet,readoutEvidenceKind/);
  assert.match(l[0],/existingProvisionalScoreOrBlank/);
  assert.match(l[0],/fullValidatedRaasScore,fdaPassCrlExtensionProbability/);
  assert.ok(l.slice(1).every(t=>t.includes(","+label+",")));
  assert.ok(l.slice(1).every(t=>t.includes("NOT_VALIDATED")||
   t.includes("MISSING_DOCUMENTED_METRIC_REVIEW")));
 }
});
test("unverified NCTs and both non-issuer 762/11k research rosters cannot acquire stage ratings",()=>{
 assert.ok(result.unverified.length>700);
 for(const stage of ["pre","post"]){
  assert.throws(()=>worklist(stage,[result.unverified[0]]),
   /RAAS_STAGE_SHEET_UNVERIFIED_OR_MISMATCHED_ROW/);
  assert.throws(()=>worklist(stage,[result.unverified[0],...result.pre]),
   /RAAS_STAGE_SHEET_UNVERIFIED_OR_MISMATCHED_ROW/);
 }
 assert.throws(()=>worklist("pre",result.post),
  /RAAS_STAGE_SHEET_UNVERIFIED_OR_MISMATCHED_ROW/);
 assert.throws(()=>worklist("post",result.pre),
  /RAAS_STAGE_SHEET_UNVERIFIED_OR_MISMATCHED_ROW/);
 assert.throws(()=>worklist("pool",result.pre),/RAAS_ONLY_TOP_BOTTOM_SHEETS/);
 assert.throws(()=>worklist("unverified",result.pre),/RAAS_ONLY_TOP_BOTTOM_SHEETS/);
});
test("no duplicates, wrong ticker/identity, or absent issuer evidence are allowed",()=>{
 const row=result.pre[0];
 assert.throws(()=>worklist("pre",[row,row]),
  /RAAS_STAGE_SHEET_UNVERIFIED_OR_MISMATCHED_ROW/);
 assert.throws(()=>worklist("pre",[{...row,ticker:"OTHER"}]),
  /RAAS_STAGE_SHEET_UNVERIFIED_OR_MISMATCHED_ROW/);
 assert.throws(()=>worklist("pre",[{...row,evidence:null}]),
  /RAAS_STAGE_SHEET_UNVERIFIED_OR_MISMATCHED_ROW/);
 assert.throws(()=>worklist("pre",[{...row,nctId:"NCT00000000"}]),
  /RAAS_STAGE_SHEET_UNVERIFIED_OR_MISMATCHED_ROW/);
 assert.throws(()=>worklist("pre",[{...row,evidence:{
  ...row.evidence,kind:"POST_PUBLIC_READOUT"
 }}]),/RAAS_STAGE_SHEET_UNVERIFIED_OR_MISMATCHED_ROW/);
});
test("stage-specific UI only exposes RAAS export under TOP and BOTTOM sheets",()=>{
 const s=fs.readFileSync(path.join(root,"app/Phase3ReadoutSheets.tsx"),"utf8");
 assert.match(s,/buildTopBottomRaasMetricWorklist\(bucket,rows\)/);
 assert.match(s,/data-raas-stage-only-export=/);
 assert.match(s,/downloadTopBottomRaasWorklist\(bucket,matched\)/);
 assert.match(s,/No new RAAS score: not in either verified TOP or BOTTOM spreadsheet/);
 assert.doesNotMatch(s,/downloadTopBottomRaasWorklist\("unverified"/);
});
