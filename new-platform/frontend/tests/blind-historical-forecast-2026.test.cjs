const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const ts=require("typescript");
const React=require("react");
const {renderToStaticMarkup}=require("react-dom/server");
const root=path.resolve(__dirname,"..");

require.extensions[".tsx"]=(module,filename)=>module._compile(
  ts.transpileModule(fs.readFileSync(filename,"utf8"),{
    compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,
      jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}
  }).outputText,filename
);

const blind=require("../data/blindHistoricalForecasts2026.json");
const revealed=require("../data/blindHistoricalComparisons2026.json");
const prospective=require("../data/fdaPredictionDecisionAudit.json");

test("the first historical challenge is immutable directional research with outcome sealed",()=>{
  assert.equal(blind.dataset,"BLIND_RETROSPECTIVE_RESEARCH_ONLY");
  assert.equal(blind.records.length,1);
  const r=blind.records[0];
  assert.equal(r.forecastId,"BLIND-INO3107-2026-10-30-V1");
  assert.equal(r.ticker,"INO");
  assert.deepEqual(r.exactNcts,["NCT04398433"]);
  assert.equal(r.clinicalPhase,"PHASE_1_2");
  assert.equal(r.predictedOutcome,"CRL");
  assert.equal(r.retrospective,true);
  assert.equal(r.originalPdufaDate,"2026-10-30");
  assert.ok(Date.parse(r.forecastCreatedAt)>Date.parse("2026-10-30T23:59:59Z"));
  assert.equal(r.actualOutcome,null);
  assert.equal(r.actualDecisionDate,null);
  assert.equal(r.actualDecisionSourceUrl,null);
  assert.equal(r.outcomeViewed,false);
  assert.equal(r.approvalProbability,null);
  assert.equal(r.crlProbability,null);
  assert.equal(r.independentCalibration,"NOT_VALIDATED");
  assert.equal(r.sourceFreezeCommit,"6eacacd2728ac265f1b4b23571e8edb1108d5afe");
  assert.match(r.primaryEvidenceUrl,/ino-20260630.htm/);
  assert.match(r.researchDossierPath,/2026-blind-ino3107-historical-challenge.md/);
});

test("SMMT prospectively frozen forecast and canonical FOCUS roster remains unchanged",()=>{
  assert.equal(prospective.records.length,1);
  assert.equal(prospective.records[0].ticker,"SMMT");
  assert.equal(prospective.records[0].predictionId,"HARMONI-SMMT-PDUFA-2026-11-14-V1");
  assert.equal(prospective.records[0].actualOutcome,"PENDING");
  assert.ok(prospective.records.every(r=>r.ticker!=="INO"));
  const focus=JSON.parse(fs.readFileSync(path.join(root,"../backend/app/data/focus_snapshot.json"),"utf8"));
  assert.equal(focus.records.length,32);
  assert.equal(focus.records.some(r=>r.nct==="NCT04398433"),false);
});

test("historical INO challenge remains a read-only archive, not an active panel",()=>{
  const quarantine=require("../data/historicalOutcomeAwareQuarantine2026.json");
  assert.equal(quarantine.quarantined.some(r=>r.ticker==="INO"),true);
  assert.equal(fs.existsSync(path.join(root,"app/BlindHistoricalPredictionPanel.tsx")),false);
  const chart=fs.readFileSync(path.join(root,"app/AssessmentLevelChart.tsx"),"utf8");
  const page=fs.readFileSync(path.join(root,"app/predictions/assessment/page.tsx"),"utf8");
  assert.doesNotMatch(page,/BlindHistoricalPredictionPanel/);
  assert.doesNotMatch(chart,/INO-3107|blindHistoricalForecasts2026|blindHistoricalComparisons2026/);
  assert.ok(page.includes("<AssessmentStatusPies {...pies}/>"));
  const model=fs.readFileSync(path.join(root,"lib/focus-assessment-chart.ts"),"utf8");
  assert.doesNotMatch(model,/blindHistoricalForecasts2026|blindHistoricalComparisons2026/);
});

test("separate, sourced outcome comparison preserves the frozen blind call and its retrospective status",()=>{
  assert.equal(revealed.dataset,"USER_AUTHORIZED_RETROSPECTIVE_BLIND_COMPARISONS");
  assert.equal(revealed.records.length,1);
  const o=revealed.records[0],p=blind.records[0];
  assert.equal(o.forecastId,p.forecastId);
  assert.equal(o.originalFreezeCommit,p.sourceFreezeCommit);
  assert.equal(o.frozenPredictedOutcome,p.predictedOutcome);
  assert.equal(o.originalForecastCreatedAt,p.forecastCreatedAt);
  assert.equal(o.trialId,p.exactNcts[0]);
  assert.equal(o.fdaApplicationId,"STN BL 125825/0");
  assert.equal(o.actualFdaActionDate,"2026-10-30");
  assert.equal(o.actualOutcome,"APPROVAL");
  assert.equal(o.approvalType,"ACCELERATED");
  assert.equal(o.outcomeMatch,"NOT_ACCURATE");
  assert.equal(o.excludedFromProspectiveAccuracy,true);
  assert.equal(o.excludedFromProspectiveCalibration,true);
  assert.ok(Date.parse(o.originalForecastCreatedAt)>Date.parse(o.actualFdaActionDate+"T23:59:59Z"));
  assert.match(o.actualFdaDecisionSourceUrl,/^https:\/\/www\.fda\.gov\/news-events\/press-announcements\/fda-approves-/);
  assert.match(o.officialFdaProductUrl,/^https:\/\/www\.fda\.gov\/vaccines-blood-biologics\//);
  assert.equal(p.actualOutcome,null);
  assert.equal(p.outcomeViewed,false);
  assert.equal(p.predictedOutcome,"CRL");
  assert.equal(prospective.records.length,1);
  assert.equal(prospective.records[0].actualOutcome,"PENDING");
  const model=fs.readFileSync(path.join(root,"lib/focus-assessment-chart.ts"),"utf8");
  assert.doesNotMatch(model,/blindHistoricalComparisons2026/);
});
