"use strict";
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const ts = require("typescript");

require.extensions[".ts"] = (mod, file) => mod._compile(
  ts.transpileModule(fs.readFileSync(file,"utf8"), {
    compilerOptions: {module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022},
  }).outputText,file
);
const { PHASE3_CENSUS_SNAPSHOT, PHASE3_CENSUS_SOURCE, auditPhase3CensusSnapshot } =
  require("../lib/phase3-census-snapshot.ts");
const original = JSON.parse(fs.readFileSync(
  path.join(__dirname,"../../../data/phase3_all_years_300m_10b_status.json"),"utf8"
));
const ui = fs.readFileSync(path.join(__dirname,"../app/installation-audit/page.tsx"),"utf8");

test("dated Phase 3 census is pinned to actual, source-backed file and precise scope",()=>{
  for(const key of Object.keys(PHASE3_CENSUS_SNAPSHOT))
    assert.deepEqual(PHASE3_CENSUS_SNAPSHOT[key],original[key],key);
  const r=auditPhase3CensusSnapshot(original);
  assert.equal(r.matchedPhase3Trials,741);
  assert.equal(r.matchedCompanies,130);
  assert.equal(r.industryPhase3Examined,25020);
  assert.equal(r.unavailableMarketCapTickers,300);
  assert.equal(r.unavailableMarketCapTrialRecords,10);
  assert.equal(r.eligibleMarketCapTickers,182);
  assert.equal(r.source,PHASE3_CENSUS_SOURCE);
  assert.equal(r.qualifiedPipelineTotal,null);
  assert.equal(r.qualifiedFdaDesignationCount,null);
  assert.equal(r.completePipelineQualification,false);
});

test("invalid and fabricated Phase 3/market-cap totals are refused",()=>{
  for(const patch of [
    {registry_phase3_industry_trials_examined:740},
    {unique_companies_with_matching_trials:183},
    {unique_phase3_trials_in_verified_market_cap_range:NaN},
    {market_cap_eligible_tickers:-1},
    {market_cap_unavailable_tickers:Infinity},
    {complete_registry_pagination:false},
    {coverage_note:"Fully qualified trading Pipeline"},
    {scope:"qualified FDA PDUFA candidate list"},
    {qualifiedPipelineTotal:741},
    {pipelineQualifiedTrials:741},
    {fdaDesignationCount:741},
    {generated_at:"not a date"},
    {market_cap_unavailable_tickers:1000000},
  ]) assert.throws(()=>auditPhase3CensusSnapshot({...original,...patch}),/Phase 3 census snapshot refused/);
  assert.throws(()=>auditPhase3CensusSnapshot(null));
  assert.throws(()=>auditPhase3CensusSnapshot([]));
});

test("MAIN tracker visibly demarcates research census from Pipeline score/membership",()=>{
  assert.match(ui,/Phase 3 company \/ market-cap census — research snapshot only/);
  assert.match(ui,/NOT the qualified Pipeline candidate total/);
  assert.match(ui,/Qualified Pipeline count: NOT ESTABLISHED/);
  assert.match(ui,/phase3Census\.matchedPhase3Trials/);
  assert.match(ui,/phase3Census\.industryPhase3Examined/);
  assert.match(ui,/phase3Census\.matchedCompanies/);
  assert.match(ui,/phase3Census\.unavailableMarketCapTickers/);
  assert.match(ui,/phase3Census\.unavailableMarketCapTrialRecords/);
  assert.match(ui,/October 26, 2026 at 12:21 UTC/);
  assert.match(ui,/Full FDA designation totals/);
  const names=[...ui.matchAll(/component: "([^"]+)"/g)].map(x=>x[1]);
  assert.equal(names.length,15);
  assert.equal(names.filter(x=>x==="Pipeline").length,1);
  assert.match(ui,/POOL \/ PIPELINE/);
  assert.match(ui,/8 PM Pacific/);
  assert.doesNotMatch(ui,/\bonClick=|\bonSubmit=|\bfetch\(|\buseEffect\(/);
});
