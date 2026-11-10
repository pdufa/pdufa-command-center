"use strict";
const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs"),path=require("node:path"),vm=require("node:vm"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
const c=ts.transpileModule(fs.readFileSync(path.join(root,"lib/acacia-safety-reconciliation.ts"),"utf8"),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022},reportDiagnostics:true});
assert.equal(c.diagnostics?.filter(x=>x.category===ts.DiagnosticCategory.Error).length||0,0);
const vmModule={exports:{}};vm.runInNewContext(c.outputText,{module:vmModule,exports:vmModule.exports});
const evaluate=vmModule.exports.evaluateAcaciaSafetyResearch;
const pilot=JSON.parse(fs.readFileSync(path.join(root,"data/acacia-pilot-prediction-workup-20261108.json"),"utf8"));
const clone=()=>structuredClone(pilot);
test("reconciles sponsor math internally, not across distinct reports",()=>{
 const x=evaluate(clone());assert.ok(x);
 assert.deepEqual(Array.from(x.contrasts.map(r=>r.differencePp)),[9.69,5.48,3.49,3.88]);
 assert.deepEqual(Array.from(x.contrasts.map(r=>r.relativeRisk)),[13.55,1.37,4.02,11.04]);
 assert.deepEqual(Array.from(x.contrasts.map(r=>Array.from(r.approximate95))),[[3.26,56.4],[0.94,2.01],[1.15,14.06],[1.44,84.91]]);
 assert.equal(x.sponsorMath.associated+x.sponsorMath.additional,x.sponsorMath.total);
 assert.equal(x.crossSource,"NOT_RECONCILED");
 assert.equal(x.interruption.randomizedDenominatorPercent,5.43);
 assert.equal(x.scientificGrade,null);assert.equal(x.regulatoryDecision,"ABSTAIN");
 assert.equal(x.accuracy,"NOT_CALIBRATED");
});
test("source identity, count, trial, phase, grade and prediction edits fail closed",()=>{
 const edits=[p=>p.nct="NCT00000000",p=>p.protocolCode="OTHER",p=>p.phaseIndependentReviewerVerified=true,
 p=>p.scientificFramework.independentlyGradedMethodPositions=1,p=>p.finalDecision.approval="APPROVAL",
 p=>p.publishedPrimary.finalSapVerified=true,p=>p.publishedPrimary.randomized.aficamten=259,
 p=>p.descriptiveSafety[0].treated=26,p=>p.descriptiveSafety[1].controlN=258,
 p=>p.descriptiveSafety[2].sourceDiscrepancy="RESOLVED",
 p=>p.sources.RESPONDER_ANALYSIS.url="https://invalid.example"];
 edits.forEach((edit,i)=>{const p=clone();edit(p);assert.equal(evaluate(p),null,"source guard "+i)});
});
test("visible pilot panel is read-only and source-specific",()=>{
 const u=fs.readFileSync(path.join(root,"app/predictions/assessment/PilotSafetyReconciliationPanel.tsx"),"utf8");
 const p=fs.readFileSync(path.join(root,"app/predictions/assessment/PilotPredictionWorkup.tsx"),"utf8");
 assert.match(u,/sponsor 12\/3 versus secondary paper 11\/1/);
 assert.match(u,/NOT RECONCILED/);
 assert.match(u,/Clinical grade: UNASSIGNED/);
 assert.match(u,/NOT CALIBRATED/);
 assert.ok(p.includes("<PilotSafetyReconciliationPanel nct={nct}/>"));
});
