"use strict";
const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const ts=require("typescript");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(fs.readFileSync(file,"utf8"),{
  compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}
}).outputText,file);

const {parsePhase3CensusCsv}=require("../lib/phase3-census-rows.ts");
const {parsePhase3CensusSourceDirectory}=require("../lib/phase3-census-sources.ts");
const {selectPostPhase3PopulationTrials}=require("../lib/post-phase3-population.ts");
const {EMPTY_PATIENT_POPULATION_FILTERS,filterPatientPopulationRows}=require("../lib/patient-population-filters.ts");
const original=fs.readFileSync(path.join(__dirname,"../public/phase3-census-2026-10-26.csv"),"utf8");
const directory=JSON.parse(fs.readFileSync(path.join(__dirname,"../public/phase3-census-sources-2026-10-26.json"),"utf8"));
const census=parsePhase3CensusCsv(original);
const sources=parsePhase3CensusSourceDirectory(directory,census);
const rows=selectPostPhase3PopulationTrials(census,sources);
const empty=()=>structuredClone(EMPTY_PATIENT_POPULATION_FILTERS);
const filter=(data,config,source={})=>filterPatientPopulationRows(data,config,source);

test("all columns default to unfiltered 375 completed records, no scope widening",()=>{
 const matched=filter(rows,empty());
 assert.equal(matched.length,375);
 assert.equal(new Set(matched.map(r=>r.trial.ticker)).size,76);
 assert.ok(matched.every(r=>r.trial.status==="COMPLETED" && r.companySources.marketCapUsd>=300_000_000 && r.companySources.marketCapUsd<=10_000_000_000));
});
test("ticker/study filters are scoped to correct exact rows, and text source availability remains unknown until loaded",()=>{
 const t=rows[0];
 const f=empty();f.ticker=t.trial.nctId;
 assert.deepEqual(filter(rows,f).map(r=>r.trial.nctId),[t.trial.nctId]);
 f.ticker="";f.drug.status="available";
 assert.equal(filter(rows,f).length,0);
 f.drug.status="missing";
 assert.equal(filter(rows,f).length,375);
 const details={ [t.trial.nctId]:{drug:"Research Drug X",indication:"Condition Z"} };
 f.drug.status="available";f.drug.search="drug x";
 assert.deepEqual(filter(rows,f,details).map(r=>r.trial.nctId),[t.trial.nctId]);
 f.indication.search="condition z";
 assert.equal(filter(rows,f,details).length,1);
 f.indication.search="condition absent";
 assert.equal(filter(rows,f,details).length,0);
});
test("patient counts, evidence percentage and dates filter independently and jointly",()=>{
 const [one,two]=rows;
 const assessed={...one,diseasePopulation:150000,eligibleUsPatients:25000,eligibleGlobalPatients:40000,
    populationEvidenceCompleteness:86,populationLastVerified:"2026-10-30"};
 const data=[assessed,two];
 const f=empty();
 f.diseasePopulation={status:"available",minimum:"100000",maximum:"200000"};
 assert.deepEqual(filter(data,f),[assessed]);
 f.eligibleUsPatients={status:"all",minimum:"24000",maximum:"30000"};
 f.eligibleGlobalPatients={status:"all",minimum:"39000",maximum:"41000"};
 f.evidence={status:"available",minimum:"80",maximum:"90"};
 f.lastUpdated={status:"available",from:"2026-10-01",to:"2026-10-31"};
 assert.deepEqual(filter(data,f),[assessed]);
 f.evidence.minimum="90";
 assert.equal(filter(data,f).length,0);
 f.evidence.minimum="80";
 f.lastUpdated.from="2026-11-01";
 assert.equal(filter(data,f).length,0);
 f.lastUpdated.from="";
 f.eligibleGlobalPatients.minimum="40001";
 assert.equal(filter(data,f).length,0);
});
test("missing evidence is discoverable but never passes a numeric or date threshold",()=>{
 const f=empty();
 f.diseasePopulation.status="missing";
 assert.equal(filter(rows,f).length,375);
 f.diseasePopulation.minimum="0";
 assert.equal(filter(rows,f).length,0);
 const d=empty();d.lastUpdated.status="missing";
 assert.equal(filter(rows,d).length,375);
 d.lastUpdated.from="2026-01-01";
 assert.equal(filter(rows,d).length,0);
});
test("bad range values fail closed and missing data remains null",()=>{
 const [one]=rows;
 const data=[{...one,diseasePopulation:200000}];
 const f=empty();
 for(const minimum of ["-1","abc","NaN","10n"]){
   f.diseasePopulation.minimum=minimum;
   assert.equal(filter(data,f).length,0);
 }
 f.diseasePopulation.minimum="300000";
 f.diseasePopulation.maximum="400000";
 assert.equal(filter(data,f).length,0);
 assert.equal(rows[0].diseasePopulation,null);
});
test("UI contains independent filters and global reset without changing the source selector",()=>{
 const read=file=>fs.readFileSync(path.join(__dirname,"../",file),"utf8");
 const ui=read("app/patient-population/PatientPopulationTab.tsx");
 for(const name of ["Filter ticker, study or company","textColumn(\"drug\"","textColumn(\"indication\"",
  'numberColumn("diseasePopulation"','numberColumn("eligibleUsPatients"','numberColumn("eligibleGlobalPatients"',
  'numberColumn("evidence"',"Last updated from","Last updated through","Clear all filters"]){
    assert.ok(ui.includes(name),name);
 }
 assert.match(ui,/filterPatientPopulationRows/);
 assert.match(ui,/selectPostPhase3PopulationTrials/);
 assert.match(ui,/<details key=\{section.title\}>/);
 assert.doesNotMatch(ui,/<details[^>]*\sopen(?:\s|>|=)/);
});
