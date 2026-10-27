"use strict";
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const ts = require("typescript");

require.extensions[".ts"] = (mod,file) => mod._compile(
  ts.transpileModule(fs.readFileSync(file,"utf8"), {
    compilerOptions: {module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022},
  }).outputText,file
);
const { parsePhase3CensusCsv, PHASE3_CENSUS_CSV_PATH, PHASE3_CENSUS_EXPECTED_ROWS } =
  require("../lib/phase3-census-rows.ts");
const raw = fs.readFileSync(path.join(__dirname,"../../../data/snapshots/phase3-census-2026-10-26/phase3_all_years_300m_10b_trials.csv"),"utf8");
const publicCopy = fs.readFileSync(path.join(__dirname,"../public/phase3-census-2026-10-26.csv"),"utf8");
const main = fs.readFileSync(path.join(__dirname,"../app/installation-audit/page.tsx"),"utf8");
const explorer = fs.readFileSync(path.join(__dirname,"../app/installation-audit/phase3-census/Phase3CensusExplorer.tsx"),"utf8");
const page = fs.readFileSync(path.join(__dirname,"../app/installation-audit/phase3-census/page.tsx"),"utf8");

test("public 741-row CSV is an exact duplicate of its frozen dated source",()=>{
  assert.equal(publicCopy,raw);
  assert.equal(PHASE3_CENSUS_CSV_PATH,"/phase3-census-2026-10-26.csv");
  const d = parsePhase3CensusCsv(publicCopy);
  assert.equal(d.rows.length,PHASE3_CENSUS_EXPECTED_ROWS);
  assert.equal(d.rows.length,741);
  assert.equal(d.uniqueCompanies,130);
  assert.equal(d.qualifiedPipelineTotal,null);
  assert.equal(d.pdufaQualifiedCount,null);
  assert.ok(d.rows.every(row=>row.pipelineQualification===null && row.fdaPdufaVerification===false));
});

test("quote-aware parser retains actual company commas and exactly reconciles every registry status",()=>{
  const d=parsePhase3CensusCsv(publicCopy);
  assert.equal(d.rows.find(r=>r.nctId==="NCT02667236").company,"Aclaris Therapeutics, Inc.");
  assert.deepEqual(d.statusCounts,{
    RECRUITING:111, ACTIVE_NOT_RECRUITING:108,
    ENROLLING_BY_INVITATION:22, NOT_YET_RECRUITING:13,
    COMPLETED:375, TERMINATED:85, WITHDRAWN:24, UNKNOWN:3,
  });
  assert.equal(Object.values(d.statusCounts).reduce((a,b)=>a+b,0),741);
  assert.equal(new Set(d.rows.map(x=>x.nctId)).size,741);
  assert.ok(d.rows.every(row=>row.sourceUrl==="https://clinicaltrials.gov/study/"+row.nctId));
});

test("invalid source identity, forged FDA status, edited header and omitted/duplicate trial rows fail closed",()=>{
  for(const value of [
    raw.slice(0,-100),
    raw.replace("nct_id,ticker,company,status,source_url","nct_id,ticker,company,pdufa_approved,source_url"),
    raw.replace("NCT03905109","NCT02249988"),
    raw.replace("NCT02249988","NCT00000000"),
    raw.replace("COMPLETED","FDA_APPROVED"),
    raw.replace("https://clinicaltrials.gov/study/NCT02249988","https://example.org/study/NCT02249988"),
    raw.replace("Abivax S.A.","=HYPERLINK(123)"),
    raw + "NCT12345678,FAKE,Fake Co,RECRUITING,https://clinicaltrials.gov/study/NCT12345678\r\n",
  ]) assert.throws(()=>parsePhase3CensusCsv(value),/Research inventory unavailable/);
  assert.throws(()=>parsePhase3CensusCsv(""));
});

test("MAIN entry and trial explorer expose original links, bounded paging, no trading action",()=>{
  assert.match(main,/Explore all 741 trial records by company, ticker and registry status/);
  assert.match(main,/href="\/installation-audit\/phase3-census"/);
  assert.match(page,/Phase 3 market-cap census — trial-level research inventory/);
  assert.match(page,/not a complete qualified Pipeline/);
  assert.match(explorer,/PHASE3_CENSUS_CSV_PATH/);
  assert.match(explorer,/parsePhase3CensusCsv/);
  assert.match(explorer,/sourceUrl/);
  assert.match(explorer,/statusCounts/);
  assert.match(explorer,/PAGE_SIZE = 35/);
  assert.match(explorer,/Qualified Pipeline: NOT ESTABLISHED/);
  assert.match(explorer,/No trial is automatically qualified/);
  assert.doesNotMatch(explorer,/\b(?:POST|PUT|PATCH|DELETE)\b|runScan\(|placeTrade\(|saveGrade\(|candidateApprovalProbability|useServerAction/);
});
