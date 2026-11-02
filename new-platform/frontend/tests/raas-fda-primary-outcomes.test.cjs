"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const ts=require("typescript");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}
).outputText,file);
const raw=require("../data/raas-fda-primary-outcomes.json");
const post=require("../data/raas-retrospective-source-cases.json");
const top=require("../data/raas-retrospective-top-cases.json");
const original=require("../data/raas-historical-cases.json");
const metric=require("../data/raas-historical-metric-snapshots.json");
const calibrated=require("../data/raas-approved-calibrations.json");
const reviewed=require("../data/raas-reviewed-snapshots.json");
const {parseRetrospectiveFeed}=require("../lib/raas-retrospective-intake.ts");
const {
 parseFdaPrimaryOutcomes,fdaPrimaryOutcomeForCase,fdaPrimaryOutcomeSummary
}=require("../lib/raas-fda-primary-outcomes.ts");
const feed=parseRetrospectiveFeed(post);
const copy=()=>JSON.parse(JSON.stringify(raw));

test("Five independently sourced FDA outcomes exactly match retrospective BOTTOM drug, indication and action",()=>{
 const data=parseFdaPrimaryOutcomes(raw,feed);
 assert.equal(data.records.length,5);
 assert.deepEqual(new Set(data.records.map(r=>r.ticker)),
  new Set(["VRNA","URGN","GERN","MDGL","BBIO"]));
 assert.deepEqual(fdaPrimaryOutcomeSummary(data,feed),
  {crosschecked:5,total:5,notCrosschecked:0});
 for(const r of post.records){
  const action=fdaPrimaryOutcomeForCase(data,r.id);
  assert.ok(action);
  assert.equal(action.decisionDate,r.realizedFDAAction.date);
  assert.equal(action.decision,"APPROVED");
  assert.equal(action.sourceType,"FDA_PRIMARY_PAGE");
  assert.ok(action.decisionDate>r.exit.date);
  assert.match(action.fdaUrl,/^https:\/\/www\.fda\.gov\//);
 }
});
test("Historical FDA crosschecks never create backdated RAAS scores or change TOP research",()=>{
 parseFdaPrimaryOutcomes(raw,feed);
 assert.equal(original.cases.length,0);
 assert.equal(metric.records.length,0);
 assert.equal(calibrated.entries.length,0);
 assert.equal(reviewed.records.length,0);
 assert.equal(top.records.length,3);
 assert.equal(fdaPrimaryOutcomeForCase(raw,"nonexistent"),null);
});
test("Different ticker, drug, indication, action date, or unregistered case cannot contaminate outcome links",()=>{
 for(const update of [
  {ticker:"WRONG"},
  {drug:"another drug"},
  {indication:"different condition"},
  {decisionDate:"2024-06-25"},
  {caseId:"unregistered"},
  {decision:"CRL"},
  {fdaUrl:"https://www.fda.gov.evil.test/drugs/foo"},
  {fdaUrl:"https://attacker@www.fda.gov/drugs/foo"},
  {sourceType:"ISSUER_RELEASE"},
  {scope:"BACKTEST_READY"},
  {reviewedAt:"2024-01-01"}
 ]){
  const mutated=copy();
  mutated.records[0]={...mutated.records[0],...update};
  assert.throws(()=>parseFdaPrimaryOutcomes(mutated,feed),/RAAS_FDA_ACTION_CROSSCHECK_MISMATCH/);
 }
});
test("Crosscheck also rejects duplicate cases and primary sources recorded before later decisions",()=>{
 const duplicated=copy();duplicated.records.push(duplicated.records[0]);
 assert.throws(()=>parseFdaPrimaryOutcomes(duplicated,feed),/RAAS_FDA_ACTION_CROSSCHECK_MISMATCH/);
 const future=copy();future.sourceAsOf="2027-01-01";
 assert.throws(()=>parseFdaPrimaryOutcomes(future,feed),/RAAS_FDA_SOURCE_LEDGER_INVALID/);
 const preexit=copy();preexit.records[0].decisionDate="2024-05-10";
 assert.throws(()=>parseFdaPrimaryOutcomes(preexit,feed),/RAAS_FDA_ACTION_CROSSCHECK_MISMATCH/);
});
test("History page surfaces a separated accessible FDA outcome audit and explicit after-exit limits",()=>{
 const page=fs.readFileSync(require.resolve("../app/raas-history/page.tsx"),"utf8");
 assert.match(page,/parseFdaPrimaryOutcomes\(fdaPrimaryOutcomeData,post\)/);
 assert.match(page,/data-fda-primary-outcome=/);
 assert.match(page,/FDA action occurred/);
 assert.match(page,/after.*selected historical exit/);
 assert.match(page,/No RAAS score is assigned/);
 assert.match(page,/do not increase the count of valid backtested RAAS predictions/);
 assert.match(page,/fdaPrimarySummary\.crosschecked/);
});
