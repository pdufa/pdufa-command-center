// Synthetic software-contract fixtures only; no FDA prediction accuracy is tested.
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),ts=require('typescript');
for(const extension of ['.ts','.tsx'])require.extensions[extension]=(module,file)=>module._compile(ts.transpileModule(fs.readFileSync(file,'utf8'),{
 compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}
}).outputText,file);
const {parsePilotRun,evaluatePilotRun}=require('../lib/pilot-assessment-run.ts');
const {investigation}=require('./fixtures/decision-investigation.cjs');
const asOf='2026-10-27T20:00:00Z',now=new Date('2026-10-27T21:00:00Z');
const expected={exactKey:'TRIAL|NCT90000001',nctId:'NCT90000001'};
function fixture(){return {
 schemaVersion:1,runId:'synthetic-contract-only',...expected,drug:'Synthetic contract drug',indication:'Synthetic indication',asOf,
 decisionTarget:{date:'2026-11-30',status:'SPONSOR_REPORTED',sourceIds:['current-source']},
 sources:[{id:'current-source',url:'https://example.org/contract-source',publishedOn:'2026-10-01',observedAt:'2026-10-27T19:00:00Z',captureStatus:'TEXT_OBSERVED',sourceClass:'SYNTHETIC_CONTRACT',notes:['Not actual clinical evidence.']},
  {id:'historical-source',url:'https://www.fda.gov/media/contract/download',publishedOn:null,observedAt:'2026-10-27T19:00:00Z',captureStatus:'TEXT_OBSERVED',sourceClass:'SYNTHETIC_CONTRACT',notes:['Not an actual FDA observation.']}],
 findings:[{id:'support',domain:'Clinical evidence',approvalDirection:'SUPPORTS_APPROVAL',text:'Synthetic supporting finding.',sourceIds:['current-source']},
  {id:'oppose',domain:'Safety evidence',approvalDirection:'OPPOSES_APPROVAL',text:'Synthetic opposing finding.',sourceIds:['current-source']}],
 history:[{id:'example',drug:'Synthetic historical drug',nctId:'NCT90000002',applicationId:'NDA900002',actionObserved:'APPROVAL',actionDate:'2020-01-01',sourceIds:['historical-source'],similarities:['Synthetic comparison.'],differences:['Synthetic difference.'],modelEligible:false}],
 science:{status:'NEEDS_REVIEWED_PROTOCOL',requiredLevels:20,requiredAssessments:40,requiredLayers:8,completedAssessments:0,notes:['No scientific protocol has been executed.']},
 adversarial:{supportingFindingIds:['support'],opposingFindingIds:['oppose'],notes:['Unreviewed synthetic challenge.']},
 timing:{totalSeconds:null,collectionSeconds:null,comparisonSeconds:null,scienceSeconds:null,predictionSeconds:null,measurementBasis:'No time measurement is fabricated.'},
 blockers:['Synthetic fixture has no independently verified scientific evidence.'],
};}
const assess=(run=fixture(),identity=expected)=>evaluatePilotRun(run,identity,now);
test('persisted source-linked record is reusable but evidence gaps force explicit abstention',()=>{
 const result=assess();assert.equal(result.status,'INCOMPLETE');assert.equal(result.preliminaryOutcome,'INDETERMINATE');
 assert.equal(result.run.runId,'synthetic-contract-only');assert.equal(result.sources.usableFindingCount,2);assert.equal(result.sources.unknownPublicationDate,1);
 assert.equal(result.science,null);assert.equal(result.independentlyVerifiedHistoricalCycles,0);
 assert.equal(result.approvalProbability,null);assert.equal(result.nonapprovalProbability,null);assert.equal(result.confidence,null);
 assert.equal(result.modelValidated,false);assert.equal(result.tradeAuthorized,false);assert.match(result.issues.join(' '),/40-assessment/);assert.match(result.issues.join(' '),/case-level PASS\/FAIL decision method/);
});
test('no target, source URL or declared data completeness can supply a calibrated prediction model',()=>{
 const run=fixture();run.sources[1].publishedOn='2020-01-01';run.blockers=[];
 const result=assess(run);assert.equal(result.preliminaryOutcome,'INDETERMINATE');assert.equal(result.modelValidated,false);assert.equal(result.approvalProbability,null);
});
test('cross-trial selected identity withholds the entire wrong record and its facts',()=>{
 for(const identity of [{...expected,nctId:'NCT90000003'},{...expected,exactKey:'TRIAL|NCT90000003'}]){
  const result=assess(fixture(),identity);assert.equal(result.status,'INVALID');assert.equal(result.run,null);assert.equal(result.sources.usableFindingCount,0);
 }
});
test('future cutoffs and invalid observation dates cannot enter the displayed assessment',()=>{
 const future=fixture();future.asOf='2026-10-28T00:00:00Z';assert.equal(assess(future).run,null);
 for(const stamp of ['2026-02-30T00:00:00Z','2026-10-27T19:00:00','2026-10-27T25:00:00Z']){
  const run=fixture();run.sources[0].observedAt=stamp;assert.equal(assess(run).status,'INVALID');
 }
});
test('post-cutoff source observations hide affected findings and prevent challenge readiness',()=>{
 const run=fixture();run.sources[0].observedAt='2026-10-27T20:00:01Z';const result=assess(run);
 assert.equal(result.sources.usableFindingCount,0);assert.deepEqual(result.usableFindingIds,[]);assert.match(result.issues.join(' '),/post-cutoff citations/);assert.match(result.issues.join(' '),/opposing argument/);
});
test('publication after observation or cutoff cannot be backdated into a finding',()=>{
 const run=fixture();run.sources[0].publishedOn='2026-10-28';const result=assess(run);
 assert.equal(result.sources.usableFindingCount,0);assert.match(result.issues.join(' '),/publication chronology/);
});
test('unavailable or unknown citations cannot support clinical findings or target verification',()=>{
 for(const mutate of [r=>r.sources[0].captureStatus='UNAVAILABLE',r=>r.findings[0].sourceIds=['unknown'],r=>r.findings[0].sourceIds=[]]){
  const run=fixture();mutate(run);const result=assess(run);assert.ok(result.sources.usableFindingCount<2);assert.equal(result.preliminaryOutcome,'INDETERMINATE');
 }
 const run=fixture();run.decisionTarget.sourceIds=['unknown'];assert.match(assess(run).issues.join(' '),/sponsor-reported FDA target/);
});
test('current or future historical outcomes cannot become valid past comparators',()=>{
 for(const mutate of [r=>r.history[0].nctId=r.nctId,r=>r.history[0].actionDate='2026-10-27',r=>r.history[0].actionDate=null,r=>r.history[0].sourceIds=['unknown']]){
  const run=fixture();mutate(run);const result=assess(run);assert.deepEqual(result.usableHistoricalIds,[]);assert.equal(result.independentlyVerifiedHistoricalCycles,0);
 }
});
test('adversarial references must cite actual opposing and supporting usable findings',()=>{
 for(const mutate of [r=>r.adversarial.opposingFindingIds=['support'],r=>r.adversarial.supportingFindingIds=['unknown'],r=>r.adversarial.opposingFindingIds=[]]){
  const run=fixture();mutate(run);assert.match(assess(run).issues.join(' '),/argument is missing or inconsistent/);
 }
});
test('caller attempts to promote verification, scores, completed assessments or predictions are rejected',()=>{
 for(const mutate of [r=>r.modelValidated=true,r=>r.probability=.95,r=>r.confidence=.95,r=>r.tradeAuthorized=true,r=>r.history[0].modelEligible=true,r=>r.sources[0].independentlyVerified=true,r=>r.science.completedAssessments=40]){
  const run=fixture();mutate(run);assert.equal(assess(run).status,'INVALID');assert.throws(()=>parsePilotRun(run));
 }
});
test('bounded arrays, distinct identifiers and safe source links are mandatory',()=>{
 for(const mutate of [r=>r.sources=Array(201).fill(r.sources[0]),r=>r.findings[1].id='support',r=>r.sources[1].id='current-source',r=>r.sources[0].url='http://example.org/source',r=>r.sources[0].url='https://user:secret@example.org/source',r=>r.history[0].sourceIds=['historical-source','historical-source']]){
  const run=fixture();mutate(run);assert.equal(assess(run).status,'INVALID');
 }
});
test('unmeasured durations remain null and inconsistent measured totals are explicitly flagged',()=>{
 assert.equal(assess().run.timing.totalSeconds,null);
 const run=fixture();run.timing.totalSeconds=5;run.timing.collectionSeconds=6;assert.match(assess(run).issues.join(' '),/durations exceed total/);
 for(const value of [-1,NaN,Infinity,'45']){const run=fixture();run.timing.totalSeconds=value;assert.equal(assess(run).status,'INVALID');}
});
test('optional existing SCIENCE dossier is audited only with actual matching program context',()=>{
 const run=fixture();run.identity={...expected,trialId:expected.nctId,programId:'PDUFA-900001',ticker:'TEST',stage:'GEM'};delete run.identity.nctId;
 run.scienceDossier=investigation(run.identity,asOf,run.indication);const result=assess(run);
 assert.equal(result.science.completedAssessments,40);assert.equal(result.science.status,'READY_FOR_RESEARCH_REVIEW');assert.equal(result.modelValidated,false);assert.equal(result.preliminaryOutcome,'INDETERMINATE');
 const mismatch=fixture();mismatch.identity=run.identity;mismatch.scienceDossier=investigation(run.identity,asOf,'different indication');
 assert.equal(assess(mismatch).science,null);assert.match(assess(mismatch).issues.join(' '),/drug or indication differs/);
});
test('persisted component renders the saved record and keeps historical context collapsed',()=>{
 const React=require('react'),{renderToStaticMarkup}=require('react-dom/server');
 const Component=require('../app/prediction-pilot/PersistedPilotResult.tsx').default;
 const html=renderToStaticMarkup(React.createElement(Component,{run:fixture(),expectedIdentity:expected}));
 assert.match(html,/Saved first-trial assessment/);assert.match(html,/INDETERMINATE/);assert.match(html,/Synthetic supporting finding/);assert.match(html,/0\/40 completed assessment records/);
 assert.match(html,/Not measured/);assert.match(html,/0 independently verified eligible cycles/);assert.match(html,/Historical context/);assert.doesNotMatch(html,/<details[^>]*\sopen(?:\s|=|>)/);
 const wrong=renderToStaticMarkup(React.createElement(Component,{run:fixture(),expectedIdentity:{...expected,nctId:'NCT90000003'}}));
 assert.doesNotMatch(wrong,/Synthetic supporting finding/);assert.match(wrong,/assessment unavailable/);
});
