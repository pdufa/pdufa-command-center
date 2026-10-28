"use strict";
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const ts = require("typescript");
require.extensions[".ts"] = (mod, filename) => mod._compile(
  ts.transpileModule(fs.readFileSync(filename,"utf8"),{
    compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022},
  }).outputText, filename
);
const { parsePhase3CensusCsv } = require("../lib/phase3-census-rows.ts");
const {
  PIPELINE_REVIEW_GATES, assessmentForPhase3CensusRow,
  summarizePhase3EvidenceGaps, buildPhase3EvidenceGapCsv,
} = require("../lib/phase3-census-evidence-gaps.ts");
const input = fs.readFileSync(
  path.join(__dirname,"../public/phase3-census-2026-10-26.csv"),"utf8");
const directoryValue = JSON.parse(fs.readFileSync(
  path.join(__dirname,"../public/phase3-census-sources-2026-10-26.json"),"utf8"));
const view = fs.readFileSync(
  path.join(__dirname,"../app/installation-audit/phase3-census/Phase3CensusExplorer.tsx"),"utf8");
const details = fs.readFileSync(
  path.join(__dirname,"../app/installation-audit/phase3-census/Phase3EvidenceDetails.tsx"),"utf8");

test("all original 741 NCTs have exactly 2 historical census claims and five unverified evidence gates",()=>{
  const inv=parsePhase3CensusCsv(input);
  const before=JSON.stringify(inv);
  const sum=summarizePhase3EvidenceGaps(inv);
  assert.deepEqual([sum.registryOpenRecords,sum.registryClosedRecords,sum.registryUnknownRecords],[254,484,3]);
  assert.equal(sum.total,741);
  assert.equal(sum.qualifiedPipelineTotal,null);
  assert.equal(sum.fdaPdufaQualifiedTotal,null);
  assert.equal(sum.evidenceVerifiedComplete,false);
  assert.equal(PIPELINE_REVIEW_GATES.length,7);
  assert.equal(PIPELINE_REVIEW_GATES.filter(g=>g.state==="CENSUS_ONLY").length,2);
  assert.equal(PIPELINE_REVIEW_GATES.filter(g=>g.state==="NOT_VERIFIED").length,5);
  for(const row of inv.rows){
    const assessed=assessmentForPhase3CensusRow(row);
    assert.equal(assessed.qualifiedPipeline,null);
    assert.equal(assessed.fdaDecisionProbability,null);
    assert.equal(assessed.sourceVerifiedPipelineEligibility,false);
    assert.equal(assessed.missingEvidenceGateCount,5);
    assert.equal(Object.keys(assessed.gates).length,7);
    assert.equal(assessed.registrySource,"https://clinicaltrials.gov/study/"+row.nctId);
  }
  assert.equal(JSON.stringify(inv),before);
});

test("CLOSED registry trial does not infer a disqualified drug and OPEN is not qualified",()=>{
  const inv=parsePhase3CensusCsv(input);
  const status={"COMPLETED":"REGISTRY_CLOSED_RECORD","TERMINATED":"REGISTRY_CLOSED_RECORD",
    "WITHDRAWN":"REGISTRY_CLOSED_RECORD","RECRUITING":"REGISTRY_OPEN_RECORD",
    "ACTIVE_NOT_RECRUITING":"REGISTRY_OPEN_RECORD","ENROLLING_BY_INVITATION":"REGISTRY_OPEN_RECORD",
    "NOT_YET_RECRUITING":"REGISTRY_OPEN_RECORD","UNKNOWN":"REGISTRY_UNKNOWN"};
  for(const row of inv.rows){
    const assessed=assessmentForPhase3CensusRow(row);
    assert.equal(assessed.registryGroup,status[row.status]);
    assert.equal(assessed.qualifiedPipeline,null);
  }
});

test("complete evidence-gap CSV has 741 unique source rows with zero fabricated FDA decisions",()=>{
  const csv=buildPhase3EvidenceGapCsv(input,directoryValue);
  const lines=csv.trimEnd().split("\r\n");
  assert.equal(lines.length,742);
  assert.equal(lines[0].slice(1,-1).split('","').length,36);
  assert.match(lines[0],/"full_pipeline_qualification"/);
  assert.match(lines[0],/"fda_probability"/);
  assert.equal((csv.match(/"NOT_ESTABLISHED"/g)||[]).length,741);
  assert.equal((csv.match(/"NOT_AVAILABLE"/g)||[]).length,741);
  assert.equal((csv.match(/"REVIEW_ORIGINAL_SOURCES_BEFORE_PIPELINE_QUALIFICATION"/g)||[]).length,741);
  assert.equal((csv.match(/"CENSUS_ONLY"/g)||[]).length,1482);
  assert.equal((csv.match(/"NOT_VERIFIED"/g)||[]).length,3705);
  assert.doesNotMatch(csv,/"PASS"|"APPROVED"|"FULLY_VERIFIED"|"PDUFA_PROBABILITY"/);
});

test("forged candidates, altered totals and incomplete source fail closed",()=>{
  const inv=parsePhase3CensusCsv(input);
  const clone={...inv,rows:[...inv.rows]};
  clone.rows[0]={...clone.rows[0],pipelineQualification:"QUALIFIED"};
  assert.throws(()=>summarizePhase3EvidenceGaps(clone),/Pipeline evidence gap worksheet blocked/);
  assert.throws(()=>assessmentForPhase3CensusRow({...inv.rows[0],fdaPdufaVerification:true}));
  assert.throws(()=>assessmentForPhase3CensusRow({...inv.rows[0],sourceUrl:"https://fake.invalid"}));
  assert.throws(()=>assessmentForPhase3CensusRow({...inv.rows[0],status:"FDA_APPROVED"}));
  assert.throws(()=>summarizePhase3EvidenceGaps({...inv,qualifiedPipelineTotal:741}));
  assert.throws(()=>summarizePhase3EvidenceGaps({...inv,rows:[...inv.rows,inv.rows[0]]}));
  assert.throws(()=>summarizePhase3EvidenceGaps({...inv,rows:inv.rows.slice(1)}));
  assert.throws(()=>buildPhase3EvidenceGapCsv(input.slice(0,-140),directoryValue));
  assert.throws(()=>buildPhase3EvidenceGapCsv(input.replace("COMPLETED","FDA_APPROVED"),directoryValue));
});

test("read-only original NCT UI shows exactly seven gaps and downloadable 741-row source checklist",()=>{
  assert.match(view,/Download 741-row Pipeline evidence-gap checklist \(CSV\)/);
  assert.match(view,/buildPhase3EvidenceGapCsv\(rawSource,sourceDirectory\)/);
  assert.match(view,/summarizePhase3EvidenceGaps\(data\)/);
  assert.match(view,/View seven evidence gates/);
  assert.match(view,/Phase3EvidenceDetails trial=\{row\}/);
  assert.match(details,/PIPELINE: NOT QUALIFIED \/ NOT DETERMINED/);
  assert.match(details,/PIPELINE_REVIEW_GATES\.map/);
  assert.match(details,/Five independent evidence gates remain unverified/);
  assert.match(details,/A CLOSED registry trial is NOT proof|does not establish whether the company continues developing its drug/);
  assert.doesNotMatch(view+details,/placeTrade\(|submitOrder\(|runScan\(|saveGrade\(|enableAutoTrade\(/);
});
