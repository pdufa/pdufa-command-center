// Real saved research-register integrity and synthetic failure injections only.
// No clinical independence, prediction accuracy or live deployment is tested.
const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),ts=require('typescript');
for(const ext of ['.ts','.tsx'])require.extensions[ext]=(m,f)=>m._compile(ts.transpileModule(fs.readFileSync(f,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}}).outputText,f);
const React=require('react'),{act,create}=require('react-test-renderer');global.IS_REACT_ACT_ENVIRONMENT=true;
const {PEAK_KEY,validatePeakResearchView}=require('../lib/peak-research-view.ts');
const Component=require('../app/PeakResearchPanel.tsx').default;
const auth=require('../lib/auth.ts'),{NextRequest}=require('next/server');
const route=require('../app/api/phase3-research/peak-register/route.ts');
const read=name=>JSON.parse(fs.readFileSync(path.join(__dirname,'../../backend/app/',name),'utf8'));
function fixture(){
 const r=read('peak_research_register.json'),catalog=read('science_40_question_catalog.json').questions;
 r.questions=r.questions.map((q,i)=>({...q,question:catalog[i].question,layer:catalog[i].layer,layerName:catalog[i].layerName}));
 r.summary={questionRecords:40,questionsWithSourceObservations:r.questions.filter(q=>q.sourceIds.length).length,missingRequiredDocumentFamilies:r.requiredDocuments.length,historicalSourceContexts:r.historicalContexts.length,independentlyAdjudicatedHistoricalCycles:0};
 const leads=read('science_40_source_leads.json').cases[PEAK_KEY];
 return {schemaVersion:'peak-research-view-v1',exactKey:PEAK_KEY,asOf:'2026-10-28',tradeAuthorized:false,sheetWritesEnabled:false,productionSchedulingEnabled:false,researchRegister:r,
  science40:{exactKey:PEAK_KEY,asOf:'2026-10-28',totalAssessments:40,sourceLeadsDiscovered:10,independentlyReviewedAssessments:0,readinessGrade:'RELUCTANT',reviewedDepthLevels:[],tradeAuthorized:false,approvalProbability:null,records:catalog.map(q=>({id:q.id,independentlyReviewed:false,status:'NOT_SUBMITTED',sourceLead:leads[q.id]||null}))},
  outcome:{exactKey:PEAK_KEY,asOf:'2026-10-28',decision:'ABSTAIN',decisionReadinessGrade:'ABSTAIN',approvalProbability:null,nonapprovalProbability:null,confidence:null,modelValidated:false,tradeAuthorized:false,blockers:['Original documents and independent review remain missing.']}};
}
test('actual 40-question register reconciles sources, gaps, contexts and zero certification',()=>{
 const v=validatePeakResearchView(fixture());assert.equal(v.researchRegister.questions.length,40);assert.equal(v.researchRegister.summary.questionsWithSourceObservations,27);assert.equal(v.researchRegister.summary.missingRequiredDocumentFamilies,12);assert.equal(v.science40.sourceLeadsDiscovered,10);assert.equal(v.science40.independentlyReviewedAssessments,0);assert.equal(v.outcome.decisionReadinessGrade,'ABSTAIN');
});
test('cross-trial evidence, future sources and false independent/model claims are withheld',()=>{
 for(const mutate of [v=>v.exactKey='OTHER',v=>v.researchRegister.nctId='NCT00000001',v=>v.science40.independentlyReviewedAssessments=40,v=>v.outcome.modelValidated=true,v=>v.outcome.approvalProbability=.9,v=>v.science40.reviewedDepthLevels=[20],v=>v.sheetWritesEnabled=true,v=>v.researchRegister.questions[0].independentlyReviewed=true,v=>v.researchRegister.questions[0].sourceIds=['missing'],v=>v.researchRegister.sources[0].url='https://user:secret@example.org',v=>v.researchRegister.sources[0].observedOn='2026-10-29',v=>v.researchRegister.historicalContexts[0].modelEligible=true,v=>v.researchRegister.historicalContexts[0].reviewCycle=1,v=>v.researchRegister.summary.questionsWithSourceObservations=40]){
  const v=fixture();mutate(v);assert.throws(()=>validatePeakResearchView(v));
 }
});
test('panel reads only on expand and displays actual counts and abstention',async()=>{
 const original=global.fetch;let calls=0,renderer;
 global.fetch=async()=>{calls++;return {ok:true,json:async()=>fixture()};};
 try{
  await act(async()=>{renderer=create(React.createElement(Component));});assert.equal(calls,0);
  await act(async()=>{renderer.root.findAllByType('details')[0].props.onToggle({currentTarget:{open:true}});});
  assert.equal(calls,1);const html=JSON.stringify(renderer.toJSON());assert.match(html,/RELUCTANT/);assert.match(html,/ABSTAIN/);assert.match(html,/S40/);assert.match(html,/12/);assert.match(html,/original FDA assignment letter has not been examined/);
 }finally{if(renderer)await act(async()=>renderer.unmount());global.fetch=original;}
});
test('unverified upstream response hides source counts and findings',async()=>{
 const original=global.fetch;let renderer;const bad=fixture();bad.outcome.approvalProbability=.9;
 global.fetch=async()=>({ok:true,json:async()=>bad});
 try{await act(async()=>{renderer=create(React.createElement(Component));});await act(async()=>renderer.root.findAllByType('details')[0].props.onToggle({currentTarget:{open:true}}));const html=JSON.stringify(renderer.toJSON());assert.match(html,/could not be verified/);assert.doesNotMatch(html,/S40|27 have/);}finally{if(renderer)await act(async()=>renderer.unmount());global.fetch=original;}
});
test('unauthenticated proxy never reads backend and has no mutation method',async()=>{
 const original=global.fetch;global.fetch=async()=>assert.fail('Unauthenticated upstream read');
 try{const r=await route.GET(new NextRequest('https://dashboard.example/api/phase3-research/peak-register'));assert.equal(r.status,401);assert.equal(route.POST,undefined);}finally{global.fetch=original;}
});
test('authenticated proxy validates identity and withholds raw upstream errors',async()=>{
 const keys=['DASHBOARD_PASSWORD','SESSION_SIGNING_KEY','PDUFA_HOP_INTERNAL_API_KEY','PDUFA_HOP_API_BASE_URL'];
 const saved=Object.fromEntries(keys.map(k=>[k,process.env[k]])),original=global.fetch;
 Object.assign(process.env,{DASHBOARD_PASSWORD:'synthetic-password-only',SESSION_SIGNING_KEY:'synthetic-session-key-at-least-thirty-two',PDUFA_HOP_INTERNAL_API_KEY:'synthetic-internal-key',PDUFA_HOP_API_BASE_URL:'https://hop.example'});
 const req=()=>new NextRequest('https://dashboard.example/api/phase3-research/peak-register',{headers:{cookie:auth.COOKIE_NAME+'='+auth.makeSession()}});
 try{
  global.fetch=async(url,options)=>{assert.equal(url,'https://hop.example/api/internal/phase3-research/peak-register');assert.equal(options.redirect,'error');assert.equal(options.cache,'no-store');return {ok:true,json:async()=>fixture()};};
  const good=await route.GET(req());assert.equal(good.status,200);assert.match(good.headers.get('cache-control'),/no-store/);assert.equal((await good.json()).science40.independentlyReviewedAssessments,0);
  global.fetch=async()=>({ok:false,status:403,json:async()=>({secret:'must never echo'})});const bad=await route.GET(req());assert.equal(bad.status,503);assert.doesNotMatch(JSON.stringify(await bad.json()),/must never echo|synthetic-internal-key/);
 }finally{global.fetch=original;for(const k of keys)if(saved[k]===undefined)delete process.env[k];else process.env[k]=saved[k];}
});
