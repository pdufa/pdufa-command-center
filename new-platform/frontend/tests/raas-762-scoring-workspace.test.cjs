"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
const source=name=>fs.readFileSync(path.join(root,name),"utf8");
const status=JSON.parse(source("data/raas-all-trials-partial-metric-ratings-status.json"));
const registry=JSON.parse(source("data/raas-registry-evidence-status.json"));
const nct=/^NCT\d{8}$/;
const lines=x=>x.trimEnd().split(/\r?\n/);

test("complete 762-NCT trial ledger is one exact row per unique registry NCT",()=>{
 const ledger=lines(source("public/raas-trial-score-ledger.csv"));
 const columns=ledger[0].split(",");
 const rows=ledger.slice(1);
 const ids=rows.map(x=>x.slice(0,x.indexOf(",")));
 assert.equal(rows.length,762);
 assert.equal(new Set(ids).size,762);
 assert.ok(ids.every(x=>nct.test(x)));
 for(const field of ["nctId","ticker","sourceUrl","registrySourceAsOf",
  "topIndependentMetricReviewsOf30","bottomIndependentMetricReviewsOf30",
  "fullValidatedRaasScore","fullRaasScoreStatus"]){
  assert.ok(columns.includes(field),"Missing one-to-one ledger field "+field);
 }
 assert.equal(registry.summary.researchTrials,762);
 assert.equal(registry.summary.sourceRecordsStored,762);
 assert.equal(registry.summary.sourceRecordsStillMissing,0);
 assert.equal(registry.summary.approvedOverallRaasScores,0);
});
test("all 762 trial identities have 30 TOP and 30 BOTTOM research metric rows",()=>{
 const ledger=lines(source("public/raas-trial-score-ledger.csv")).slice(1);
 const ids=new Set(ledger.map(r=>r.split(",")[0]));
 const stage=lines(source("public/raas-all-trials-partial-metric-ratings.csv"));
 const fields=stage[0].split(",");
 for(const value of ["nctId","stage","metricReviewsOf30","missingMetricIds",
  "unscoredMetricCountOf30","full30MetricRaasScore","fdaPassCrlExtensionProbability"]){
  assert.ok(fields.includes(value),"Missing per-stage field "+value);
 }
 assert.equal(stage.length-1,1524);
 const pairCount=new Map(),stageById=new Map();
 for(const line of stage.slice(1)){
  const [id]=line.split(",");
  assert.ok(ids.has(id));
  pairCount.set(id,(pairCount.get(id)||0)+1);
  const mode=line.includes(",PRE_RESEARCH_ONLY,")?"TOP":
   line.includes(",POST_RESEARCH_ONLY,")?"BOTTOM":"INVALID";
  assert.notEqual(mode,"INVALID");
  const modes=stageById.get(id)||new Set();
  assert.ok(!modes.has(mode),"Duplicate stage "+id+" "+mode);
  modes.add(mode);stageById.set(id,modes);
 }
 assert.equal(pairCount.size,762);
 assert.ok([...pairCount.values()].every(x=>x===2));
 assert.ok([...stageById.values()].every(x=>x.has("TOP")&&x.has("BOTTOM")));
 assert.equal(status.researchTrials,762);
 assert.equal(status.trialStageRows,1524);
});
test("partial metrics now cover 21 NCTs, zero independently validated full RAAS and zero FDA probabilities",()=>{
 assert.equal(status.uniqueNctsWithActualProvisionalMetricScores,21);
 assert.equal(status.totalAiCrosscheckedMetricReviews,96);
 assert.equal(status.totalIndependentMetricReviews,0);
 assert.equal(status.fullValidatedRaasScores,0);
 assert.equal(status.calibratedFdaPredictions,0);
 assert.equal(registry.summary.postedRegistryResults,337);
 assert.equal(registry.summary.protocolOnly,425);
 assert.equal(registry.summary.sourceFetchErrorsInLatestRun,0);
});
test("retired 762 scoring route and RAAS scan show no active ratings while preserving archived source data",()=>{
 const page=source("app/raas-762/page.tsx");
 const tools=source("app/tools/page.tsx");
 const scan=source("app/raas-scan/page.tsx");
 const sourceOnly=source("app/Phase3SourceOnlySheets.tsx");
 assert.match(page,/data-raas-ratings-retired="raas-762"/);
 assert.match(scan,/data-raas-ratings-retired="raas-scan"/);
 assert.match(tools,/data-tools-primary-phase3/);
 assert.match(tools,/href="\/raas-top-bottom"/);
 assert.match(sourceOnly,/data-surveys-ratings-cancelled/);
 assert.match(sourceOnly,/<CapScreenedTopPhase3Spreadsheet classification=\{data\} query=\{query\}\/>/);
 assert.doesNotMatch(sourceOnly,/<RaasClinicalFiveCell/);
 assert.match(page,/Historical source records and trial data are preserved/);
});
test("762-row clinical research workspace keeps source safeguards and five-factor stage coverage",()=>{
 const ui=source("app/Raas762ScoringWorkspace.tsx");
 for(const marker of ["data-raas-762-scoring-workspace","records.length!==762",
 "new Set(x.records.map(r=>r.nctId)).size!==762",
 'const stage:"pre"|"post"=x.postedResults?"post":"pre"',
 "clinicalFiveForTrial(trial,stage,false)",
 "registryMetricLeads(x,stage,trial)","remaining:5-reviewed",
 "rows.length*5","RaasClinicalFiveCell","RaasTrialHistoryButton","PAGE_SIZE=50",
 "Not validated","N/A · never 0/100","source-verified-rows-unvalidated-scores"]){
  assert.ok(ui.includes(marker),"Missing clinical-five safeguard: "+marker);
 }
 assert.match(ui,/aria-label="RAAS 762 exact NCT scoring row table"/);
 assert.match(ui,/role="alert"/);
 assert.doesNotMatch(ui,/approvedOverallScore:\s*(?:0|50|100)/);
});

test("clinical source leads remain separate from five-factor numeric grades",()=>{
 const ui=source("app/Raas762ScoringWorkspace.tsx");
 assert.match(ui,/registryMetricLeads\(x,stage,trial\)/);
 assert.match(ui,/lead\.metricIds\.filter\(id=>id\.startsWith\(stage\+"-1-"\)\)/);
 assert.match(ui,/new Set\(sourceLeads\.flatMap\(lead=>lead\.metricIds\)\)\.size/);
 assert.match(ui,/\{x\.reviewed\}\/5/);
 assert.match(ui,/No matching registry lead/);
 assert.match(ui,/Not validated/);
 assert.doesNotMatch(ui,/approvedOverallScore:\s*x\.leadMetricCount/);
});

test("missing registry source worklist exposes exact gap NCTs without fake grades",()=>{
 const code=source("app/Raas762ScoringWorkspace.tsx");
 for(const marker of [
  'data-raas-registry-source-gap-queue="requires-primary-source-research"',
  'const sourceGaps=useMemo(()=>rows.filter(r=>r.sourceLeads.length===0)',
  'Source discovery worklist',
  'x.evidence.registeredInterventions',
  'x.evidence.registryLastUpdated',
  'x.evidence.primaryDefinitions.length===0',
  'setLeadFilter("no-leads")',
  'A trial shown as completed does not establish successful efficacy'
 ])assert.ok(code.includes(marker),"Missing registry gap queue safeguard: "+marker);
 const registryIndex=JSON.parse(source("public/raas-registry-evidence-index.json"));
 const withoutEndpoints=registryIndex.records.filter(x=>
  !x.postedResults&&x.primaryDefinitions.length===0);
 assert.deepEqual(withoutEndpoints.map(x=>x.nctId).sort(),[
  "NCT00017407","NCT00033904","NCT00039000",
  "NCT00048113","NCT00048295","NCT00486980"
 ].sort());
 assert.ok(withoutEndpoints.every(x=>x.postedPrimaryOutcomeCount===0));
 assert.ok(withoutEndpoints.every(x=>x.registeredConditions.length>0));
});

test("six historically sourced registry-gap cases retain exact identity and no automated grades",()=>{
 const data=JSON.parse(source("data/raas-historical-six-gap-source-leads.json"));
 const code=source("app/Raas762ScoringWorkspace.tsx");
 const ids=["NCT00017407","NCT00033904","NCT00039000","NCT00048113",
  "NCT00048295","NCT00486980"].sort();
 assert.equal(data.scope,"RAAS_HISTORICAL_SIX_REGISTRY_SOURCE_GAP_RESEARCH_ONLY");
 assert.equal(data.records.length,6);
 assert.deepEqual(data.records.map(r=>r.nctId).sort(),ids);
 assert.equal(new Set(data.records.map(r=>r.nctId)).size,6);
 assert.ok(data.records.every(r=>r.scoreEligible===false));
 assert.ok(data.records.every(r=>r.nextAction&&r.identityBasis));
 assert.equal(data.records.filter(r=>r.evidenceType==="PROGRAM_LEVEL_SPONSOR_LEAD_UNMAPPED").length,2);
 assert.equal(data.records.filter(r=>r.evidenceType==="EXACT_NCT_PUBLICATION_LEAD").length,1);
 assert.equal(data.records.filter(r=>r.evidenceType==="SOURCE_SEARCH_PENDING").length,1);
 assert.equal(data.records.filter(r=>r.evidenceType==="EXACT_REGISTRY_WITHDRAWAL_NO_ENROLMENT").length,1);
 assert.match(code,/historicalSixGapSources\.records/);
 assert.match(code,/historicalSourceByNct\.get\(x\.trial\.nctId\)/);
 assert.match(code,/Historical source investigation \(unscored\)/);
 assert.match(code,/Numeric RAAS grade: N\/A/);
 assert.match(code,/historical.*source/i);
});
