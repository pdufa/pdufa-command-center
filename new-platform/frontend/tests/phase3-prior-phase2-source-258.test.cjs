"use strict";
const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs"),ts=require("typescript");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(fs.readFileSync(file,"utf8"),{
 fileName:file,compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,esModuleInterop:true}
}).outputText,file);
const {sourceObservation}=require("../lib/phase3-universal-questions.ts");
const {activePhase3Cohorts}=require("../lib/phase3-active-cohorts.ts");
const {GET}=require("../app/api/phase3-active-prior-phase2/route.ts");
const {GET:coverage}=require("../app/api/phase3-active-190-coverage/route.ts");
const active=[...activePhase3Cohorts.pre,...activePhase3Cohorts.post].map(x=>x.nctId);

test("prior efficacy and long-term observed clinical endpoints use exact prior NCT citations and no numeric grades",()=>{
 const q16=active.filter(id=>sourceObservation(id,16));
 const q21=active.filter(id=>sourceObservation(id,21));
 assert.equal(q16.length,16);
 assert.equal(q21.length,4);
 for(const id of q16){
  const fact=sourceObservation(id,16);
  assert.equal(fact.documentationScore,100);
  assert.match(fact.sourceUrl,/^https:\/\/clinicaltrials\.gov\/study\/NCT\d{8}$/);
  assert.match(fact.description,/NOT effect-size estimates|NOT a positive clinical verdict/);
 }
 for(const id of q21){
  const fact=sourceObservation(id,21);
  assert.match(fact.sourceUrl,/^https:\/\/clinicaltrials\.gov\/study\/NCT\d{8}$/);
  assert.match(fact.description,/extended follow-up/);
 }
 assert.match(sourceObservation("NCT05515536",16).description,/0\.1440/);
 assert.equal(sourceObservation("NCT00000000",16),null);
});
test("candidate predecessor audit lists all 258 active trials, never promotes candidate research to scored efficacy",async()=>{
 const response=await GET(new Request("http://localhost/api/phase3-active-prior-phase2"));
 assert.equal(response.status,200,await response.clone().text());
 const data=await response.json();
 assert.equal(data.rows.length,258);
 assert.equal(new Set(data.rows.map(x=>x.nctId)).size,258);
 assert.deepEqual(data.totals,{
  activeTrials:258,top:235,bottom:23,exactNctUnique:258,
  candidatePredecessorTrialCount:46,candidatePriorStudyRows:67,
  priorPostedResultsTrials:20,priorPrimaryPValueTrials:13,
  registeredPriorOutcomeSlots:16,registeredExtendedFollowUpSlots:4
 });
 const sample=data.rows.find(x=>x.nctId==="NCT05515536");
 assert.ok(sample.candidatePriorStudies.length);
 assert.match(sample.crosswalkReview,/not independently adjudicated/);
 assert.equal(sample.priorEfficacyEndpointDocumented,true);
 assert.equal(sample.priorLongTermOutcomeDocumented,true);
 assert.equal(data.rows.filter(x=>x.priorEfficacyEndpointDocumented).length,16);
 assert.equal(data.rows.filter(x=>x.priorLongTermOutcomeDocumented).length,4);
 const csv=await GET(new Request("http://localhost/api/phase3-active-prior-phase2?format=csv"));
 assert.equal(csv.status,200);
 assert.equal((await csv.text()).trim().split("\r\n").length,259);
});
test("saved 190 matrix documents prior efficacy and timeframes as source facts but no invented clinical grade",async()=>{
 const response=await coverage(new Request("http://localhost/api/phase3-active-190-coverage"));
 assert.equal(response.status,200,await response.clone().text());
 const data=await response.json();
 assert.equal(data.totals.trials,258);
 assert.equal(data.totals.columnsPerTrial,190);
 assert.equal(data.totals.expectedCells,49020);
 assert.ok(data.totals.documentedQuestions>=3040);
 assert.ok(data.totals.unscoredQuestions<=4639);
 assert.equal(data.totals.raasScoredTrials,0);
 assert.equal(data.totals.clinicalRatedTrials,6);
});
