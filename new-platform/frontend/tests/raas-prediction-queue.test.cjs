"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const ts=require("typescript"),fs=require("node:fs");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,
 compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,esModuleInterop:true}}
).outputText,file);
const {buildRaasPredictionQueue,summarizeRaasPredictionQueue}=require("../lib/raas-prediction-queue.ts");
const accepted=require("../data/raas-current-accepted-fda-applications.json");
const leads=require("../data/raas-v2-top8-2026-source-intake.json");
const accuracy=require("../data/raas-fda-three-way-accuracy-site-snapshot.json");
const partial=require("../data/raas-all-trials-partial-metric-ratings-status.json");
const queue=buildRaasPredictionQueue(accepted.applications,leads.records,accepted.issuer.ticker);
test("tracks every separate accepted application and dated original-goal lead",()=>{
 const s=summarizeRaasPredictionQueue(queue);
 assert.equal(queue.length,accepted.applications.length+leads.records.length);
 assert.equal(new Set(queue.map(x=>x.key)).size,queue.length);
 assert.equal(s.phase3SourceEligible,1);
 assert.equal(s.phase2Excluded,2);
 assert.equal(s.researchLeadsUnverified,leads.records.length);
 assert.equal(s.certifiedThreeWayForecasts,0);
 assert.equal(s.allAbstain,true);
 assert.equal(queue.filter(x=>x.ticker==="COGT").length,3);
});
test("never transforms preliminary clinical evidence into FDA probabilities",()=>{
 assert.ok(queue.every(x=>x.decision==="ABSTAIN"));
 assert.ok(queue.every(x=>x.blockers.length>=2));
 assert.ok(queue.every(x=>["PASS","CRL","EXTENSION"].every(kind=>x.probabilities[kind]===null)));
 assert.equal(accuracy.predecisionThreeWayIndependentlyVerifiedForecasts,0);
 assert.equal(partial.fullValidatedRaasScores,0);
 assert.equal(partial.uniqueNctsWithActualProvisionalMetricScores,17);
});
test("formal FDA target revision is not a new original review cycle",()=>{
 const revisions=queue.filter(x=>x.blockers.some(y=>y.includes("formal date revision")));
 assert.ok(revisions.length>0);
 assert.ok(revisions.every(x=>x.kind==="ISSUER_GOAL_LEAD"));
});
test("malformed dates, spoofed sources and repeated application keys are rejected",()=>{
 const a=accepted.applications[0];
 assert.throws(()=>buildRaasPredictionQueue([a,{...a}],[]),/INVALID/);
 assert.throws(()=>buildRaasPredictionQueue([{...a,pdufaTargetDate:"2026-02-30"}],[]),/INVALID/);
 assert.throws(()=>buildRaasPredictionQueue([{...a,applicationAcceptedSourceUrl:"http://unsafe.example"}],[]),/INVALID/);
});
test("predictions page is a full RAAS workspace and the prior PEAK pilot remains preserved",()=>{
 const page=fs.readFileSync(require("node:path").join(__dirname,"../app/predictions/page.tsx"),"utf8");
 assert.match(page,/data-raas-prediction-overview/);
 assert.match(page,/data-raas-fda-forecast-cohort/);
 assert.match(page,/data-raas-pre-readout-phase3/);
 assert.match(page,/data-raas-validation-control/);
 assert.match(page,/href="\/prediction-pilot"/);
 assert.doesNotMatch(page,/redirect\(/);
});
