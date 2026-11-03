"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,
 compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,esModuleInterop:true}}
).outputText,file);
const {raasSpreadsheetSummary,raasSpreadsheetExport}=require("../lib/raas-spreadsheet-status.ts");
test("Exact trial with documented pilot maps sources but never a fabricated total score",()=>{
 const top=raasSpreadsheetSummary({nctId:"NCT07363577",ticker:"LBRX"});
 assert.equal(top.stage,"pre");assert.equal(top.mappedAreas,5);
 assert.equal(top.missingAreas,25);assert.equal(top.approvedScore,null);
 assert.equal(top.approvedMetrics,0);assert.equal(top.state,"PENDING_VALIDATION");
 const bottom=raasSpreadsheetSummary({nctId:"NCT06445023",ticker:"CLDX"});
 assert.equal(bottom.stage,"post");assert.equal(bottom.mappedAreas,3);
 assert.equal(bottom.approvedScore,null);
});
test("Unclassified registry row must not be silently designated TOP or BOTTOM",()=>{
 const row=raasSpreadsheetSummary({nctId:"NCT99999999",ticker:"CLDX"});
 assert.equal(row.stage,null);assert.equal(row.mappedAreas,null);
 assert.equal(row.approvedScore,null);assert.equal(row.state,"STAGE_UNVERIFIED");
 assert.deepEqual([...raasSpreadsheetExport({nctId:"NCT99999999",ticker:"CLDX"})],
  ["UNCLASSIFIED","","","STAGE_UNVERIFIED"]);
});
test("Wrong issuer never inherits another trial's mapped RAAS evidence",()=>{
 const wrong=raasSpreadsheetSummary({nctId:"NCT07363577",ticker:"CLDX",classifiedStage:"pre"});
 assert.equal(wrong.stage,"pre");assert.equal(wrong.mappedAreas,0);
 assert.equal(wrong.approvedScore,null);
 const provenPost=raasSpreadsheetSummary({nctId:"NCT99999999",ticker:"CLDX",confirmedPostReadout:true});
 assert.equal(provenPost.stage,"post");assert.equal(provenPost.mappedAreas,0);
 assert.equal(provenPost.approvedScore,null);
});
test("Misidentified or wrong-therapy rows cannot inherit scores or mapped areas",()=>{
 const invalid=raasSpreadsheetSummary({nctId:"",ticker:"CLDX"});
 assert.equal(invalid.state,"INVALID_IDENTITY");
 const wrongTherapy=raasSpreadsheetSummary({nctId:"NCT07363577",ticker:"LBRX",
  drug:"not the documented therapy",classifiedStage:"pre"});
 assert.equal(wrongTherapy.mappedAreas,0);
 assert.equal(wrongTherapy.approvedScore,null);
});
test("Every primary trial spreadsheet and its CSV has a deliberate RAAS status field",()=>{
 const root=path.join(__dirname,"..");
 for(const rel of ["app/ToolsResultsSpreadsheet.tsx","app/ToolsOpeningTrialGrid.tsx",
    "app/Phase3RegistryPostingSheets.tsx"]){
  const code=fs.readFileSync(path.join(root,rel),"utf8");
  assert.match(code,/RaasSpreadsheetStatus/);
 }
 for(const rel of ["app/Phase3ReadoutSheets.tsx",
    "app/Phase3RegistryPostingSheets.tsx","lib/tools-spreadsheet.ts"]){
  const code=fs.readFileSync(path.join(root,rel),"utf8");
  assert.match(code,/raasSpreadsheetExport/);
 }
 const cell=fs.readFileSync(path.join(root,"app/RaasSpreadsheetStatus.tsx"),"utf8");
 assert.match(cell,/data-raas-spreadsheet-cell/);
 assert.match(cell,/source areas/);
 assert.match(cell,/Missing inputs are not zero/);
 for(const rel of ["lib/raas-spreadsheet-status.ts","app/RaasSpreadsheetStatus.tsx"]){
  const code=fs.readFileSync(path.join(root,rel),"utf8");
  const compile=ts.transpileModule(code,{
   fileName:rel,reportDiagnostics:true,
   compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022,
    jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}
  });
  assert.deepEqual((compile.diagnostics||[]).filter(x=>x.category===ts.DiagnosticCategory.Error),[]);
 }
});