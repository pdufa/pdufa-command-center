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
test("partial metrics remain 17 NCTs, zero independently validated full RAAS and zero FDA probabilities",()=>{
 assert.equal(status.uniqueNctsWithActualProvisionalMetricScores,17);
 assert.equal(status.totalAiCrosscheckedMetricReviews,82);
 assert.equal(status.totalIndependentMetricReviews,0);
 assert.equal(status.fullValidatedRaasScores,0);
 assert.equal(status.calibratedFdaPredictions,0);
 assert.equal(registry.summary.postedRegistryResults,337);
 assert.equal(registry.summary.protocolOnly,425);
 assert.equal(registry.summary.sourceFetchErrorsInLatestRun,0);
});
test("primary route exists and is linked from TOOLS, RAAS scan and evidence-gap worklist",()=>{
 const page=source("app/raas-762/page.tsx");
 const tools=source("app/tools/page.tsx");
 const scan=source("app/raas-scan/page.tsx");
 const backlog=source("app/raas-evidence-backlog/page.tsx");
 assert.match(page,/data-raas-primary-scoring-setup/);
 assert.match(page,/Raas762ScoringWorkspace/);
 assert.match(tools,/data-tools-primary-raas-762/);
 assert.match(tools,/href="\/raas-762"/);
 assert.match(scan,/href="\/raas-762"/);
 assert.match(backlog,/href="\/raas-762"/);
 assert.match(scan,/data-raas-readiness-executed/);
 assert.match(page,/fullValidatedRaasScores/);
});
test("762-row workspace has accessible 50-row pages, missing-value states and no fabricated ratings",()=>{
 const code=source("app/Raas762ScoringWorkspace.tsx");
 for(const marker of ["data-raas-762-scoring-workspace","records.length!==762",
  "new Set(x.records.map(r=>r.nctId)).size!==762",
  "stageResearchReviewsForUnverifiedTrial(trial,\"pre\")",
  "stageResearchReviewsForUnverifiedTrial(trial,\"post\")",
  "remainingTop:30-topReviewed","remainingBottom:30-bottomReviewed",
  "Not validated","N/A · never 0/100","RaasMetricGradebook",
  "RaasTrialHistoryButton","PAGE_SIZE=50",
  "caseRow(x)","source-verified-rows-unvalidated-scores","/raas-all-trials-partial-metric-ratings.csv"]){
  assert.ok(code.includes(marker),"Missing primary workspace safeguard: "+marker);
 }
 assert.match(code,/aria-label="RAAS 762 exact NCT scoring row table"/);
 assert.match(code,/role="alert"/);
 assert.match(code,/onChange=/);
 assert.match(code,/setPage\(0\)/);
 assert.doesNotMatch(code,/(?:overallScore|approvedScore)\s*:\s*(?:0|50|100)/);
 const compiled=ts.transpileModule(code,{fileName:"Raas762ScoringWorkspace.tsx",
  compilerOptions:{jsx:ts.JsxEmit.ReactJSX,module:ts.ModuleKind.ESNext,
   target:ts.ScriptTarget.ES2022},reportDiagnostics:true});
 assert.equal((compiled.diagnostics||[]).filter(x=>x.category===ts.DiagnosticCategory.Error).length,0);
});
