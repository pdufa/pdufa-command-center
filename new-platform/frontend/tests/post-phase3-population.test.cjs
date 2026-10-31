"use strict";
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const ts = require("typescript");

require.extensions[".ts"] = (mod, file) => mod._compile(
  ts.transpileModule(fs.readFileSync(file,"utf8"), {
    compilerOptions: { module:ts.ModuleKind.CommonJS, target:ts.ScriptTarget.ES2022 },
  }).outputText, file
);

const { parsePhase3CensusCsv } = require("../lib/phase3-census-rows.ts");
const { parsePhase3CensusSourceDirectory } = require("../lib/phase3-census-sources.ts");
const {
  selectPostPhase3PopulationTrials, PATIENT_POPULATION_DETAIL_SECTIONS, calculateTherapyCosts,
  PATIENT_POPULATION_MARKET_CAP_MIN, PATIENT_POPULATION_MARKET_CAP_MAX,
  PATIENT_POPULATION_BASELINE_TRIALS, PATIENT_POPULATION_BASELINE_COMPANIES,
} = require("../lib/post-phase3-population.ts");

const census = fs.readFileSync(path.join(__dirname,"../public/phase3-census-2026-10-26.csv"),"utf8");
const directory = JSON.parse(fs.readFileSync(path.join(__dirname,"../public/phase3-census-sources-2026-10-26.json"),"utf8"));
const inventory = parsePhase3CensusCsv(census);
const sources = parsePhase3CensusSourceDirectory(directory,inventory);
const rows = selectPostPhase3PopulationTrials(inventory,sources);

test("#1 post-Phase 3 scope is completed exact-NCT research records only, listed and within $300M-$10B", () => {
  assert.equal(PATIENT_POPULATION_MARKET_CAP_MIN,300_000_000);
  assert.equal(PATIENT_POPULATION_MARKET_CAP_MAX,10_000_000_000);
  assert.equal(PATIENT_POPULATION_BASELINE_TRIALS,375);
  assert.equal(PATIENT_POPULATION_BASELINE_COMPANIES,76);
  assert.equal(rows.length,375);
  assert.equal(new Set(rows.map(x=>x.trial.ticker)).size,76);
  assert.equal(new Set(rows.map(x=>x.trial.nctId)).size,375);
  for(const row of rows){
    assert.equal(row.trial.status,"COMPLETED");
    assert.ok(row.companySources.nctIds.includes(row.trial.nctId));
    assert.ok(row.companySources.marketCapUsd>=300_000_000);
    assert.ok(row.companySources.marketCapUsd<=10_000_000_000);
    assert.equal(row.diseasePopulation,null);
    assert.equal(row.eligibleUsPatients,null);
    assert.equal(row.eligibleGlobalPatients,null);
    assert.equal(row.projectedAdoption12MonthPct,null);
    assert.equal(row.adoptionEvidenceUrl,null);
    assert.equal(row.adoptionConfidence,null);
    assert.equal(row.therapyCostComparison,null);
    assert.equal(row.populationEvidenceCompleteness,null);
    assert.equal(row.populationLastVerified,null);
    assert.equal(row.trial.pipelineQualification,null);
  }
  assert.equal(PATIENT_POPULATION_DETAIL_SECTIONS.length,12);
});

test("therapy regimen totals and deltas require dated evidence and compatible cost bases",()=>{
  const mk=(drug,admin,priceBasis="NET")=>({
    therapy:"Therapy X",regimen:"10 mg oral daily for 12 months",
    drugCostFirst12MonthsUsd:drug,adminMonitoringFirst12MonthsUsd:admin,
    priceBasis,evidenceStatus:"MODELED",sourceUrl:"https://example.org/price",sourceDate:"2026-10-31",
  });
  const current=mk(9000,1000),proposed=mk(14000,2000);
  assert.deepEqual(calculateTherapyCosts({current,proposed}),{
    currentUsd:10000,proposedUsd:16000,costDifferenceUsd:6000,
  });
  assert.equal(calculateTherapyCosts({current,proposed:{...proposed,priceBasis:"WAC"}}).costDifferenceUsd,null);
  assert.equal(calculateTherapyCosts({current,proposed:{...proposed,sourceUrl:null}}).proposedUsd,null);
  assert.equal(calculateTherapyCosts({current,proposed:{...proposed,sourceDate:""}}).proposedUsd,null);
  assert.equal(calculateTherapyCosts({current,proposed:mk(-1,100)}).proposedUsd,null);
  assert.deepEqual(calculateTherapyCosts(null),{currentUsd:null,proposedUsd:null,costDifferenceUsd:null});
});
test("fail closed when sponsor cap or completed status is substituted", () => {
  const changed=structuredClone(sources);
  const first=rows[0].trial.ticker;
  changed.companies.find(x=>x.ticker===first).marketCapUsd=299_000_000;
  assert.throws(()=>selectPostPhase3PopulationTrials(inventory,changed),/market-cap|sponsor/);
  const old=structuredClone(inventory);
  old.rows.find(x=>x.status==="COMPLETED").status="RECRUITING";
  assert.throws(()=>selectPostPhase3PopulationTrials(old,sources),/baseline drifted/);
});

test("global #1 link and dedicated page retain source and unknown-estimate safeguards", () => {
  const read=file=>fs.readFileSync(path.join(__dirname,"../",file),"utf8");
  const nav=read("app/GlobalNavigation.tsx");
  const page=read("app/patient-population/PatientPopulationTab.tsx");
  const route=read("app/patient-population/page.tsx");
  assert.match(nav,/label:"#1",href:"\/patient-population"/);
  assert.match(route,/<PatientPopulationTab\s*\/>/);
  assert.match(page,/selectPostPhase3PopulationTrials/);
  assert.match(page,/parsePhase3CensusCsv/);
  assert.match(page,/parsePhase3CensusSourceDirectory/);
  assert.match(page,/PATIENT_POPULATION_DETAIL_SECTIONS\.map/);
  assert.match(page,/<details key=\{section.title\}>/);
  for(const column of ["Ticker / study","Drug","Indication","Total disease population","Eligible U.S. patients","Eligible global patients","Projected patient adoption (12 mo, %)","Current SOC cost ($/12 mo)","Proposed therapy cost ($/12 mo)","Cost difference ($)","Evidence completeness","Last updated","Details"]){
    assert.ok(page.includes(column), column);
  }
  assert.match(page,/Not assessed/);
  assert.match(page,/Not researched/);
  assert.match(page,/Needs source review/);
  assert.match(page,/Exact study source was not verified/);
  assert.doesNotMatch(page,/<details[^>]*\sopen(?:\s|>|=)/);
  assert.doesNotMatch(page,/placeTrade|executeOrder|approvalProbability\s*:/);
});
