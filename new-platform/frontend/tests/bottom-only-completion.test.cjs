"use strict";
const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
require.extensions[".ts"]=(m,f)=>m._compile(ts.transpileModule(fs.readFileSync(f,"utf8"),{
 fileName:f,compilerOptions:{module:1,target:9,esModuleInterop:true}
}).outputText,f);
const {bottomOnlyReport}=require("../lib/bottom-only-completion.ts");
const {GET}=require("../app/api/bottom-only-completion/route.ts");
const baseline=require("../data/bottomOnlyBaseline20261107.json");
const matrix=require("../data/bottomOnly190Baseline20261107.json");
const facts=require("../data/bottomOnlyReviewedFacts20261107.json");
const history=require("../data/bottomOnlyResearchHistory20261107.json");
const top=require("../data/topOnlyBaseline20261107.json");
const report=bottomOnlyReport(),ids=new Set(baseline.records.map(r=>r.nctId));
test("BOTTOM is 23 exact frozen post-readout NCTs, never TOP",()=>{
 assert.equal(report.trialCount,23);assert.equal(ids.size,23);
 assert.equal(new Set(report.trials.map(t=>t.nctId)).size,23);
 assert.equal(matrix.headers.length,190);assert.equal(matrix.rows.length,23);
 assert.equal(report.allFieldsAccounted,23);assert.equal(report.allMetricsEvaluated,23);
 for(const r of report.trials){assert.equal(r.cohort,"BOTTOM");assert.equal(r.phase,"PHASE3");
  assert.ok(!top.records.some(t=>t.nctId===r.nctId));assert.ok(ids.has(r.nctId));
  assert.equal(r.fields.length,190);assert.equal(r.metrics.length,30);
  assert.equal(new Set(r.metrics.map(m=>m.id)).size,30);
  assert.equal(r.metrics.filter(m=>m.activeInClinicalModel).length,5);
  assert.equal(r.metrics.reduce((n,m)=>n+m.activeClinicalWeightPercent,0),100);
  assert.ok(r.fields.every(f=>f.exportValue!==""));
 }
});
test("190 original columns and source values retain exact order",()=>{
 const original=new Map(matrix.rows.map(r=>[r[0],r]));
 assert.deepEqual(report.headers,matrix.headers);
 for(const t of report.trials){const row=original.get(t.nctId);assert.equal(row.length,190);
  for(let i=0;i<190;i++){const val=row[i];if(val.trim()&&val!=="UNSCORED"){
    assert.equal(t.fields[i].exportValue,val,"Original non-placeholder value must never be overwritten "+t.nctId+" column "+i);
  }}
 }
});
test("evidence leads are not fabricated numerical scores or retrospective forecasts",()=>{
 assert.equal(report.additionalSourceFacts,facts.records.length);
 assert.ok(facts.records.length>=11);
 for(const t of report.trials){
  assert.equal(t.clinicalFullScore===null,t.clinicalScoredFactors!==5);
  assert.equal(t.metrics.filter(m=>m.activeInClinicalModel&&m.score!==null).length,t.clinicalScoredFactors);
  assert.equal(t.legacyThirtyMetricFullScore,null);
  for(const m of t.metrics){if(m.score!==null){
   assert.ok(m.sourceUrl&&m.benchmarkSourceUrl&&m.sourceDate&&m.assessedAt);
   assert.ok(m.observedResult&&m.uncertaintyReview&&m.criticalRiskReview);
  }}
 }
});
test("exact ENERGIZE OLE evidence is classified as exploratory and supports only post 1-4",()=>{
 const t=report.trials.find(x=>x.nctId==="NCT04770753");assert.ok(t);
 const f=t.additionalReviewedFacts.find(x=>x.question===4);assert.ok(f);
 assert.match(f.classification,/EXPLORATORY/);assert.match(f.criticalLimit,/not independent/i);
 const grade=t.metrics.find(x=>x.id==="post-1-4");
 assert.equal(grade.score,50);assert.equal(t.clinicalScoredFactors,5);
 assert.ok(t.clinicalFullScore!==null);
 assert.equal(t.readoutOutcome,"PRIMARY_ENDPOINT_MET");
});
test("company Phase3 reported safety is only qualitative when full arm tables absent",()=>{
 for(const id of ["NCT06445023","NCT06455202"]){
  const t=report.trials.find(x=>x.nctId===id);assert.ok(t);
  assert.ok(t.additionalReviewedFacts.some(f=>f.question===3&&/qualitative|insufficient/i.test(f.criticalLimit)));
  assert.equal(t.metrics.find(x=>x.id==="post-1-5").score,null);
  assert.ok(t.additionalReviewedFacts.some(f=>f.question===19));
 }
});
test("saved observed primary outcome remains distinct from five-factor research score",()=>{
 const mixed=report.trials.find(x=>x.nctId==="NCT05031780");
 const failure=report.trials.find(x=>x.nctId==="NCT05144256");
 assert.equal(mixed.readoutOutcome,"MIXED_COPRIMARY_RESULTS");
 assert.equal(failure.readoutOutcome,"PRIMARY_ENDPOINT_NOT_MET");
 assert.equal(failure.clinicalFullScore,null);
 assert.equal(report.completeThirtyMetricOverallScores,0);
});
test("BOTTOM history has one initial immutable identity-linked snapshot for every exact NCT",()=>{
 assert.equal(history.records.length,23);
 assert.deepEqual(new Set(history.records.map(r=>r.nctId)),ids);
 assert.equal(new Set(history.records.map(r=>r.eventId)).size,23);
});
test("BOTTOM exports exact 190 columns and 690 metric dispositions",async()=>{
 const summary=await GET(new Request("http://localhost/api/bottom-only-completion"));
 assert.equal(summary.status,200);const payload=await summary.json();
 assert.equal(payload.trialCount,23);assert.equal(payload.rows.length,23);assert.equal(payload.totalQuestionCount,690);
 const exportCsv=await GET(new Request("http://localhost/api/bottom-only-completion?format=csv"));
 assert.equal(exportCsv.status,200);
 const head=(await exportCsv.text()).replace(/^\uFEFF/,"").split(/\r?\n/)[0];
 assert.ok(head.includes('"NCT"'));assert.ok(head.includes('"Q30'));
 const metricExport=await GET(new Request("http://localhost/api/bottom-only-completion?format=metrics"));
 assert.equal(metricExport.status,200);assert.equal((await metricExport.text()).split(/\r?\n/).filter(Boolean).length,1+23*30);
 const factExport=await GET(new Request("http://localhost/api/bottom-only-completion?format=facts"));
 assert.equal(factExport.status,200);
 const invalid=await GET(new Request("http://localhost/api/bottom-only-completion?nctId=NCT00000000"));
 assert.equal(invalid.status,404);
 const exact=await GET(new Request("http://localhost/api/bottom-only-completion?nctId=NCT04770753"));
 const result=await exact.json();assert.equal(result.trial.nctId,"NCT04770753");
 assert.equal(result.history.length,3);
});
test("BOTTOM renderer is horizontally expandable and TOP invocation remains untouched",()=>{
 const parent=fs.readFileSync(path.join(__dirname,"../app/Phase3SourceOnlySheets.tsx"),"utf8");
 const ui=fs.readFileSync(path.join(__dirname,"../app/BottomOnlyCompletionSheet.tsx"),"utf8");
 assert.match(parent,/<TopOnlyCompletionSheet query=\{query\}\/>/);
 assert.match(parent,/<BottomOnlyCompletionSheet query=\{query\}\/>/);
 assert.match(ui,/bottom-detail-/);assert.match(ui,/aria-expanded/);
 assert.match(ui,/190 data fields/);assert.match(ui,/history/);
});
test('saved five-factor score events preserve historical state and one additive ENERGIZE change',()=>{
 const events=require('../data/bottomOnlyScoreHistory20261107.json').records;
 assert.equal(events.length,24);assert.equal(events.filter(e=>e.eventType==='RESEARCH_SCORE_SNAPSHOT').length,23);
 const change=events.find(e=>e.nctId==='NCT04770753'&&e.eventType==='RESEARCH_SCORE_CHANGE');assert.ok(change);
 assert.equal(change.previousClinicalFullScore,null);assert.equal(change.clinicalFullScore,55);assert.equal(change.clinicalScoredFactors,5);
 assert.equal(new Set(events.map(e=>e.eventId)).size,events.length);
 assert.ok(events.every(e=>ids.has(e.nctId)));
});

test("every BOTTOM trial has five traceable rating-input packets without fabricated scores",()=>{
 for(const trial of report.trials){
  assert.equal(trial.clinicalFactors.length,5);
  for(const factor of trial.clinicalFactors){
   assert.equal(factor.reviewEvidenceCount,factor.reviewEvidence.length);
   assert.ok(["NUMERICAL_RESEARCH_GRADE_PRESENT","EVIDENCE_FOUND_SCIENTIFIC_GRADING_REQUIRED","SOURCE_DISCOVERY_OR_DISCLOSURE_REQUIRED"].includes(factor.ratingReadiness));
   for(const item of factor.reviewEvidence){
    assert.ok(Number.isInteger(item.question)&&item.question>=1&&item.question<=30);
    assert.match(item.sourceUrl,/^https:\/\//);
    assert.ok(item.evidence.trim().length>10);
    assert.notEqual(item.assessmentStatus,"REVIEWED_NUMERICAL_GRADE");
   }
  }
  assert.ok(trial.clinicalFactors.find(f=>f.id==="post-1-1")?.reviewEvidenceCount>0);
 }
});
test("BOTTOM factor research export contains every exact trial and all 115 rating packets",async()=>{
 const response=await GET(new Request("http://localhost/api/bottom-only-completion?format=rating-evidence"));
 assert.equal(response.status,200);
 const csv=await response.text();assert.match(csv,/Factor ID/);assert.match(csv,/Rating readiness/);
 const lines=csv.split(/\r?\n/).filter(Boolean);assert.ok(lines.length>=116);
 for(const id of ids)assert.ok(csv.includes(id),"missing factor packet: "+id);
 const ui=fs.readFileSync(path.join(__dirname,"../app/BottomOnlyCompletionSheet.tsx"),"utf8");
 assert.match(ui,/rating-evidence/);assert.match(ui,/reviewEvidence\.map/);
});
