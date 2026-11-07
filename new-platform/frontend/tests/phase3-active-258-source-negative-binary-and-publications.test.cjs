"use strict";
const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs"),ts=require("typescript");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(fs.readFileSync(file,"utf8"),{
 fileName:file,compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,esModuleInterop:true}
}).outputText,file);
const {activePhase3Cohorts}=require("../lib/phase3-active-cohorts.ts");
const {activeOfficialRegistryRecords}=require("../lib/phase3-active-official-registry.ts");
const {phase3RegistryBinaryFact,phase3PeerReviewedFact,phase3PeerEvidenceIntegrity,
 PHASE3_PEER_FACT_COUNT}=require("../lib/phase3-source-fact-enrichment.ts");
const {GET}=require("../app/api/phase3-active-190-coverage/route.ts");

test("258 official records explicitly document absence of comparator-coded arms or named placebo only when warranted",()=>{
 const ids=new Set([...activePhase3Cohorts.pre,...activePhase3Cohorts.post].map(r=>r.nctId));
 assert.equal(ids.size,258);
 const noCode=activeOfficialRegistryRecords.filter(r=>!r.comparators);
 const noName=activeOfficialRegistryRecords.filter(r=>!/\bplacebo\b/i.test(r.interventionNames));
 assert.equal(noCode.length,88);
 assert.equal(noName.length,144);
 for(const record of activeOfficialRegistryRecords){
  const c=phase3RegistryBinaryFact(record.nctId,11);
  const p=phase3RegistryBinaryFact(record.nctId,27);
  assert.equal(c!==null,!record.comparators);
  assert.equal(p!==null,!/\bplacebo\b/i.test(record.interventionNames));
  if(c){assert.equal(c.status,"SOURCE_FACT_ONLY");assert.match(c.evidence,/NOT proof/);}
  if(p){assert.equal(p.status,"SOURCE_FACT_ONLY");assert.match(p.evidence,/not a prediction/);}
 }
});
test("peer-reviewed and FDA facts are source-only, exact-NCT and preserve observed mixed results",()=>{
 const ids=new Set([...activePhase3Cohorts.pre,...activePhase3Cohorts.post].map(r=>r.nctId));
 assert.equal(PHASE3_PEER_FACT_COUNT,27);
 assert.match(phase3PeerReviewedFact("NCT04716231",21).evidence,/Week 104/);
 assert.match(phase3PeerReviewedFact("NCT05243550",20).evidence,/SINGLE-ARM/);
 assert.match(phase3PeerReviewedFact("NCT05243550",26).evidence,/98%/);
 assert.match(phase3PeerReviewedFact("NCT05453968",20).evidence,/NONRANDOMIZED/);
 assert.equal(phase3PeerReviewedFact("NCT05453968",3).raasScore,null);
 assert.ok(phase3PeerEvidenceIntegrity(ids));
 const rise=phase3PeerReviewedFact("NCT05031780",20);
 assert.match(rise.evidence,/0\.1213/);
 assert.match(rise.evidence,/Do NOT mark both co-primary/);
 assert.equal(rise.clinicalRating,null);
 assert.equal(rise.raasScore,null);
 assert.match(phase3PeerReviewedFact("NCT05257408",28).sourceUrl,/fda\.gov/);
 assert.equal(phase3PeerReviewedFact("NCT02598661",21).question,21);
 assert.equal(phase3PeerReviewedFact("NCT00000000",20),null);
});
test("documented binary registry negatives count as facts, never synthetic clinical ratings",async()=>{
 const response=await GET(new Request("http://localhost/api/phase3-active-190-coverage"));
 assert.equal(response.status,200,await response.clone().text());
 const d=await response.json();
 assert.equal(d.totals.trials,258);
 assert.equal(d.totals.columnsPerTrial,190);
 assert.equal(d.totals.expectedCells,258*190);
 assert.equal(d.totals.questionSlots,258*30);
 assert.equal(d.totals.predictedQuestions,61);
 assert.equal(d.totals.clinicalRatedTrials,6);
 assert.equal(d.totals.raasScoredTrials,0);
 assert.ok(d.totals.documentedQuestions>=3000);
 assert.ok(d.totals.unscoredQuestions<4700);
 const comparator=d.perQuestion.find(q=>q.number===11);
 const placebo=d.perQuestion.find(q=>q.number===27);
 assert.equal(comparator.unscored,0);
 assert.equal(placebo.unscored,0);
 assert.equal(comparator.predicted,1);
 assert.equal(placebo.predicted,1);
 assert.equal(d.totals.documentedQuestions+d.totals.predictedQuestions+
  d.totals.unscoredQuestions,d.totals.questionSlots);
});

test("documentary clinical facts join phase-first provenance but never become reviewed grades",()=>{
 const phase=fs.readFileSync(require.resolve("../lib/phase-first-report.ts"),"utf8");
 assert.match(phase,/peerEvidence\.facts/);
 assert.match(phase,/fact\.question===20\?"benefitRisk"/);
 assert.match(phase,/fact\.question===21\?"phase3Results"/);
 assert.match(phase,/fact\.question===28\?"fdaOutcome"/);
 assert.match(phase,/Historical observed evidence only, not a numerical clinical or FDA prediction/);
});
