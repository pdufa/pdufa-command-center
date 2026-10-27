"use strict";
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const { spawnSync } = require("node:child_process");
const ts = require("typescript");
const React = require("react");
const { renderToStaticMarkup } = require("react-dom/server");
for (const ext of [".ts",".tsx"]) require.extensions[ext] = (mod, file) => mod._compile(
  ts.transpileModule(fs.readFileSync(file,"utf8"),{compilerOptions:{
    module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX,
  }}).outputText,file);
const { parsePhase3CensusCsv } = require("../lib/phase3-census-rows.ts");
const { parsePhase3CensusSourceDirectory, sourcesForPhase3Trial, FDA_RESEARCH_LINKS } = require("../lib/phase3-census-sources.ts");
const { buildPhase3EvidenceGapCsv, PIPELINE_GATE_AUTOMATION } = require("../lib/phase3-census-evidence-gaps.ts");
const Details = require("../app/installation-audit/phase3-census/Phase3EvidenceDetails.tsx").default;
const root = path.join(__dirname,"../../..");
const input = fs.readFileSync(path.join(__dirname,"../public/phase3-census-2026-10-26.csv"),"utf8");
const source = JSON.parse(fs.readFileSync(path.join(__dirname,"../public/phase3-census-sources-2026-10-26.json"),"utf8"));
const inventory = parsePhase3CensusCsv(input);
const copy = value => JSON.parse(JSON.stringify(value));

test("all 741 trial pointers reproduce from exact saved issuer, cap and configured source inputs",()=>{
  const result = spawnSync("python3",["scripts/build_phase3_census_sources.py","--check"],{cwd:root,encoding:"utf8"});
  assert.equal(result.status,0,result.stderr||result.stdout);
  for(const item of source.inputs) assert.equal(item.sha256,
    crypto.createHash("sha256").update(fs.readFileSync(path.join(root,item.path))).digest("hex"));
  const before=JSON.stringify(inventory);
  const directory=parsePhase3CensusSourceDirectory(source,inventory);
  assert.equal(directory.companies.length,130);
  assert.equal(directory.companies.reduce((sum,c)=>sum+c.nctIds.length,0),741);
  for(const trial of inventory.rows){
    const c=sourcesForPhase3Trial(trial,directory);
    assert.ok(c.nctIds.includes(trial.nctId));
    assert.ok(c.leadSponsorNames.includes(trial.company));
    assert.equal(c.secSubmissionsUrl,"https://data.sec.gov/submissions/CIK"+c.cik+".json");
    assert.equal(trial.pipelineQualification,null);
    assert.equal(trial.fdaPdufaVerification,false);
  }
  assert.equal(JSON.stringify(inventory),before);
});

test("missing, duplicate, wrong-issuer and forged FDA-qualified manifests cannot be exported",()=>{
  const mutations=[
    x=>{x.companies.pop();},
    x=>{x.companies[0].nctIds.push(x.companies[1].nctIds[0]);},
    x=>{[x.companies[0].nctIds[0],x.companies[1].nctIds[0]]=[x.companies[1].nctIds[0],x.companies[0].nctIds[0]];},
    x=>{x.companies[0].secFilingsUrl=x.companies[1].secFilingsUrl;},
    x=>{x.companies[0].secSubmissionsUrl="https://data.sec.gov.evil.invalid/submissions/CIK0001956827.json";},
    x=>{x.companies[0].marketCapSourceUrl=x.companies[1].marketCapSourceUrl;},
    x=>{x.companies[0].marketCapUsd=NaN;},
    x=>{x.companies[0].marketCapUsd=299999999;},
    x=>{x.companies[0].marketCapCheckedAt="2027-01-01T00:00:00Z";},
    x=>{x.companies[0].configuredIssuerHomepages=["javascript:alert(1)"];},
    x=>{x.companies[0].configuredIssuerHomepages=["https://issuer.example@evil.invalid/"];},
    x=>{x.companies[0].qualifiedPipeline=true;},
    x=>{x.fdaPdufaVerification=true;},
    x=>{x.scope="VERIFIED_FDA_APPLICATIONS";},
    x=>{x.inputs[0].sha256="0".repeat(64);},
  ];
  for(const mutate of mutations){
    const value=copy(source);mutate(value);
    assert.throws(()=>parsePhase3CensusSourceDirectory(value,inventory));
    assert.throws(()=>buildPhase3EvidenceGapCsv(input,value));
  }
  assert.throws(()=>sourcesForPhase3Trial({...inventory.rows[0],ticker:inventory.rows.find(r=>r.ticker!==inventory.rows[0].ticker).ticker},source));
  assert.throws(()=>buildPhase3EvidenceGapCsv(input,undefined));
});
test("every frozen input hash and historical path is pinned without live-source fallback",()=>{
 for(let i=0;i<source.inputs.length;i++){
  const changed=copy(source);changed.inputs[i].sha256='0'.repeat(64);
  assert.throws(()=>parsePhase3CensusSourceDirectory(changed,inventory));
 }
 const changed=copy(source);changed.inputs[2].path='data/phase_pipeline_market_caps.csv';
 assert.throws(()=>parsePhase3CensusSourceDirectory(changed,inventory));
});

test("741-row export includes exact source pointers and methods without promoting any gate",()=>{
  const csv=buildPhase3EvidenceGapCsv(input,source);
  const records=csv.trimEnd().split("\r\n").map(line=>[...line.matchAll(/"((?:[^"]|"")*)"/g)].map(m=>m[1].replaceAll('""','"')));
  const header=records.shift();
  assert.equal(records.length,741);assert.equal(header.length,36);
  for(const cells of records){
    const row=Object.fromEntries(header.map((key,i)=>[key,cells[i]]));
    const original=inventory.rows.find(r=>r.nctId===row.nct_id);
    const c=sourcesForPhase3Trial(original,source);
    assert.equal(row.company_sec_filings_research_url,c.secFilingsUrl);
    assert.equal(row.saved_market_cap_checked_at,c.marketCapCheckedAt);
    assert.equal(row.clinicaltrials_api_research_url,"https://clinicaltrials.gov/api/v2/studies/"+row.nct_id);
    assert.equal(row.fda_cder_general_research_url,FDA_RESEARCH_LINKS[0].url);
    assert.equal(row.source_link_scope,"RESEARCH_POINTERS_ONLY");
    assert.equal(row.full_pipeline_qualification,"NOT_ESTABLISHED");
    assert.equal(row.fda_probability,"NOT_AVAILABLE");
    assert.equal(row.fda_us_pathway,"NOT_VERIFIED");
    assert.equal(row.fda_us_pathway_check_mode,"DOCUMENT_RECONCILIATION");
  }
  assert.deepEqual(Object.values(PIPELINE_GATE_AUTOMATION).map(g=>g.mode).sort(),[
    "DOCUMENT_RECONCILIATION","DOCUMENT_RECONCILIATION","DOCUMENT_RECONCILIATION","DOCUMENT_RECONCILIATION",
    "RULE_BY_RULE","STRUCTURED_RECHECK","STRUCTURED_RECHECK"]);
});

test("rendered checklist has dated company sources and clearly general FDA links",()=>{
  const directory=parsePhase3CensusSourceDirectory(source,inventory);
  const trial=inventory.rows[0];
  const company=sourcesForPhase3Trial(trial,directory);
  const html=renderToStaticMarkup(React.createElement(Details,{trial,directory}));
  assert.match(html,/Research links only/);
  assert.match(html,/does not refresh these saved company inputs/);
  assert.match(html,/No trial-specific FDA\/PDUFA document has been established/);
  assert.ok(html.includes(company.secFilingsUrl.replaceAll("&","&amp;")));
  assert.ok(html.includes(company.marketCapCheckedAt));
  assert.ok(html.includes(FDA_RESEARCH_LINKS[0].url));
  assert.ok(html.includes(FDA_RESEARCH_LINKS[1].url));
  assert.equal((html.match(/<th scope="row"/g)||[]).length,7);
  assert.equal((html.match(/Structured recheck possible/g)||[]).length,2);
  assert.equal((html.match(/Original-document reconciliation/g)||[]).length,4);
  assert.match(html,/Five independent evidence gates remain unverified/);
  assert.doesNotMatch(html,/href="javascript:|FDA probability: [0-9]|QUALIFIED: YES/);
});
