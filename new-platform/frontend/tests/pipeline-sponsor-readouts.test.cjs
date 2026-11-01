"use strict";
const {test}=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(fs.readFileSync(file,"utf8"),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,file);
const {SPONSOR_PHASE3_READOUTS,getSponsorPhase3Readout,sponsorReadoutProgramCount}=require("../lib/pipeline-source-reported-readouts.ts");
test("three exact pivotal NCT sources represent one single drug-indication program, never 3 marketed products",()=>{
 assert.equal(SPONSOR_PHASE3_READOUTS.length,3);
 assert.equal(sponsorReadoutProgramCount(),1);
 assert.deepEqual(SPONSOR_PHASE3_READOUTS.map(x=>x.nctId),["NCT05507203","NCT05507216","NCT05535946"]);
 for(const row of SPONSOR_PHASE3_READOUTS){
  assert.equal(row.ticker,"ABVX");
  assert.equal(row.reviewerStatus,"REVIEW_REQUIRED");
  assert.equal(row.programEligibility,"NOT_ESTABLISHED");
  assert.equal(row.pdufaTarget,null);
  assert.equal(row.sourceType,"ORIGINAL_SPONSOR_TOPLINE");
  assert.match(row.sourceUrl,/^https:\/\/ir\.abivax\.com\/news-releases\//);
  assert.match(row.sourcePublished,/^20\d\d-\d\d-\d\d$/);
  assert.equal(row.comparator,"placebo");
  assert.ok(row.treatmentEvents<=row.treatmentN&&row.placeboEvents<=row.placeboN);
  assert.ok(row.caveat.length>60);
 }
});
test("exact source data preserve prespecified 50mg reported placebo-adjusted effects, not simplistic raw-rate subtraction",()=>{
 const [a,b,c]=SPONSOR_PHASE3_READOUTS;
 assert.deepEqual([a.weeks,a.treatmentEvents,a.treatmentN,a.placeboEvents,a.placeboN,a.placeboAdjustedDifferencePp],[8,69,318,4,158,19.3]);
 assert.deepEqual([b.weeks,b.treatmentEvents,b.treatmentN,b.placeboEvents,b.placeboN,b.placeboAdjustedDifferencePp],[8,63,318,10,159,13.4]);
 assert.deepEqual([c.weeks,c.treatmentEvents,c.treatmentN,c.placeboEvents,c.placeboN,c.placeboAdjustedDifferencePp],[44,100,195,20,192,40.3]);
 assert.match(b.caveat,/25 mg/);
 assert.match(c.caveat,/responder/i);
});
test("incorrect ticker, unknown NCT and malformed study identifiers get no evidence",()=>{
 assert.equal(getSponsorPhase3Readout("NCT05507203","WRONG"),null);
 assert.equal(getSponsorPhase3Readout("NCT00000000","ABVX"),null);
 assert.equal(getSponsorPhase3Readout("NCT05507203 ","ABVX"),null);
 assert.equal(getSponsorPhase3Readout("NCT05507203","ABVX").study,"ABTECT-1 · pivotal induction (Study 105)");
});
test("sponsor data shown as collapsed, explicitly unreviewed primary source, in both Pipeline views",()=>{
 const ui=fs.readFileSync(path.join(__dirname,"../app/PipelineSponsorReadout.tsx"),"utf8");
 const dossiers=fs.readFileSync(path.join(__dirname,"../app/PipelineFourViews.tsx"),"utf8");
 const workspace=fs.readFileSync(path.join(__dirname,"../app/FunnelWorkspace.tsx"),"utf8");
 assert.ok(ui.includes('return <details'));
 assert.ok(ui.includes("awaiting independent review"));
 assert.ok(ui.includes("Not a comparison to an approved competitor"));
 assert.ok(dossiers.includes('<PipelineSponsorReadout nctId={row.nctId} ticker={row.ticker}/>'));
 assert.ok(workspace.includes('<PipelineSponsorReadout nctId={r.nctId} ticker={r.ticker}/>'));
});
