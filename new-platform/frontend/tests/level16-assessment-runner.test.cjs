const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),ts=require('typescript');
require.extensions['.ts']=(m,f)=>m._compile(ts.transpileModule(fs.readFileSync(f,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,esModuleInterop:true}}).outputText,f);
const r=require('../lib/level16-assessment-runner.ts'),original=require('../data/level16AssessmentEvidence.json');
const copy=()=>structuredClone(original),orca=d=>d.trials.find(t=>t.nct==='NCT04576949');
test('one trial executes six levels without fabricating owner acceptance or persistence',()=>{
 const a=r.runAssessment({scope:'ONE',nct:'NCT04576949'});assert.equal(a.summary.trialsProcessed,1);assert.equal(a.summary.levelsProcessed,6);
 assert.match(a.runId,/^[a-f0-9-]{36}$/);assert.equal(a.sourceMode,'COLLECTED_EVIDENCE_NO_NEW_RETRIEVAL');assert.equal(a.savedToDatabase,false);
 assert.ok(a.trials[0].levels.every(l=>l.ownerReviewStatus==='OWNER_NOT_REVIEWED'&&!l.externalReviewerRequired&&l.approvalProbability===null));
});
test('all-FOCUS mode processes all 32 trials and 192 levels with 23 provisional cycles',()=>{
 const a=r.runAssessment({scope:'ALL'});assert.equal(a.summary.trialsProcessed,32);assert.equal(a.summary.levelsProcessed,192);
 assert.deepEqual(a.trials.map(t=>t.nct),original.trials.map(t=>t.nct));assert.equal(new Set(a.trials.flatMap(t=>t.provisionalApplicationCycleIds)).size,23);
 assert.deepEqual(a.trials.filter(t=>!t.provisionalApplicationCycleIds.length).map(t=>t.nct).sort(),['NCT05031780','NCT06553768','NCT06747468']);
});
test('unmapped trials run without invented application relationships',()=>{
 const a=r.runAssessment({scope:'ONE',nct:'NCT06747468'});assert.equal(a.trials[0].applicationMappingStatus,'NOT_MAPPED_APPLICATION_CYCLE');
 assert.equal(a.trials[0].levels[1].checks.find(c=>c.id==='application').state,'OWNER_CHECK_REQUIRED');
});
test('non-FOCUS identities and caller review, role, source or phase claims are rejected',()=>{
 for(const input of [{scope:'ONE',nct:'NCT00000001'},{scope:'ALL',nct:'NCT04576949'},{scope:'ALL',reviewed:true},{scope:'ALL',role:'admin'},{scope:'ALL',sourceUrl:'https://example.test'},{scope:'ALL',phase:'PHASE3'}])assert.throws(()=>r.runAssessment(input),/FOCUS|extra fields/);
});
test('Level 1 checks exact source identity; matching receipt does not authenticate it',()=>{
 const t=orca(copy());t.registryUrl='https://clinicaltrials.gov/api/v2/studies/NCT05206370';assert.equal(r.processLevel(1,t)[0].state,'MISSING_EVIDENCE');assert.match(r.processLevel(1,orca(original))[0].reason,/not source authentication/);
});
test('Level 2 preserves missing phase/status and later levels abstain without phase',()=>{
 const t=orca(copy());t.phases=[];t.registryStatus=null;assert.equal(r.processLevel(2,t).find(c=>c.id==='status').state,'MISSING_EVIDENCE');
 assert.ok(r.assessTrial(t).levels.slice(2).every(l=>l.researchStatus==='PHASE_UNRESOLVED'));
});
test('Level 3 never substitutes endpoints or posting status for demonstrated efficacy',()=>{
 const t=orca(copy());t.reportedClinicalResultsPresent=false;t.reportedComparisons=[];t.registryResultsPresent=true;
 assert.ok(t.primaryEndpoints.length);assert.equal(r.processLevel(3,t)[0].state,'MISSING_EVIDENCE');
});
test('Phase 1/2 assessments do not require future Phase 3 evidence',()=>{
 for(const phase of ['PHASE1','PHASE2']){const t=orca(copy());t.phases=[phase];for(const level of [3,5])assert.equal(r.processLevel(level,t).find(c=>c.id==='future-phase3').state,'NOT_YET_EXPECTED');}
 assert.ok(!r.processLevel(3,orca(original)).some(c=>c.id==='future-phase3'));
});
test('Level 4 records missing protocol without claiming deficient execution',()=>{
 const t=orca(copy());t.protocolCollected=false;assert.equal(r.processLevel(4,t)[0].state,'MISSING_EVIDENCE');assert.match(r.processLevel(4,t)[0].reason,/owner checking/);
});
test('Level 5 retains protocol/SAP version conflict and unknown lock/unblinding',()=>{
 const t=r.runAssessment({scope:'ONE',nct:'NCT04576949'}).trials[0];assert.equal(t.levels[4].researchStatus,'CONFLICTS_TO_RECONCILE');
 assert.equal(t.statisticalChronology.actualUnblindingDate,null);assert.equal(t.statisticalChronology.prespecificationConclusion,'UNRESOLVED');
});
test('reported percentage and interval inconsistencies become conflicts, never FDA scores',()=>{
 const d=copy();orca(d).reportedComparisons[0].activePct=99;orca(d).reportedComparisons[0].ci95Reported=[99,100];const a=r.runAssessment({scope:'ONE',nct:'NCT04576949'},d);
 assert.equal(a.trials[0].levels[2].researchStatus,'CONFLICTS_TO_RECONCILE');assert.equal(a.trials[0].levels[4].checks.find(c=>c.id.endsWith('-ci')).state,'CONFLICTING_EVIDENCE');assert.equal(a.approvalProbability,null);
});
test('Level 6 separates available endpoints from medical importance',()=>{
 const checks=r.processLevel(6,orca(original));assert.equal(checks[0].state,'EVIDENCE_AVAILABLE');assert.equal(checks[1].state,'OWNER_CHECK_REQUIRED');
});
test('future source versions, UTC cutoff violations and naive retrieval dates fail closed',()=>{
 for(const change of [t=>t.registryVersionDate='2099-01-01',t=>t.retrievedAt='2099-01-01T00:00:00Z',t=>t.retrievedAt='2026-11-14T23:00:00-05:00',t=>t.retrievedAt='2026-11-14T01:00:00']){const d=copy();change(orca(d));assert.throws(()=>r.runAssessment({scope:'ALL'},d),/CUTOFF/);}
});
test('cross-trial contamination, duplicate identities and invented mappings are rejected',()=>{
 let d=copy();orca(d).nct='NCT05206370';assert.throws(()=>r.runAssessment({scope:'ALL'},d),/IDENTITY/);
 d=copy();orca(d).levels[0].facts[0].sourceUrl='https://example.test/other';assert.throws(()=>r.runAssessment({scope:'ALL'},d),/UNBOUND/);
 d=copy();d.trials.find(t=>t.nct==='NCT05031780').provisionalApplicationCycleIds=['invented'];assert.throws(()=>r.runAssessment({scope:'ALL'},d),/MAPPING/);
});
test('no source package can self-certify owner review or blind historical eligibility',()=>{
 for(const change of [d=>d.ownerReviewStatus='OWNER_ACCEPTED_WITH_LIMITATIONS',d=>d.historicalPredictionInputPermitted=true,d=>d.externalVerificationRequired=true]){const d=copy();change(d);assert.throws(()=>r.runAssessment({scope:'ALL'},d),/PACKAGE/);}
 const a=r.runAssessment({scope:'ALL'}),b=r.runAssessment({scope:'ALL'});assert.notEqual(a.runId,b.runId);assert.equal(a.historicalPredictionInputPermitted,false);
});
