const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),ts=require('typescript');
for(const ext of ['.ts','.tsx'])require.extensions[ext]=(m,f)=>m._compile(ts.transpileModule(fs.readFileSync(f,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}}).outputText,f);
const engine=require('../lib/trial-level-assessment.ts'),runner=require('../lib/level16-assessment-runner.ts'),data=require('../data/level16AssessmentEvidence.json');
const {NextRequest}=require('next/server'),auth=require('../lib/auth.ts'),api=require('../app/api/assessments/trial/route.ts');
const React=require('react'),{act,create}=require('react-test-renderer');globalThis.IS_REACT_ACT_ENVIRONMENT=true;
const UI=require('../app/TrialLevelAssessment.tsx').default;
process.env.DASHBOARD_PASSWORD='SYNTHETIC_ASSESSMENT_PASSWORD';process.env.SESSION_SIGNING_KEY='SYNTHETIC_ASSESSMENT_KEY_0123456789012345';
const fixture=nct=>({protocolSection:{identificationModule:{nctId:nct},statusModule:{overallStatus:'COMPLETED',lastUpdatePostDateStruct:{date:'2026-01-01'}},designModule:{phases:['PHASE3'],designInfo:{allocation:'RANDOMIZED'}},conditionsModule:{conditions:['Synthetic indication']},eligibilityModule:{eligibilityCriteria:'Synthetic test population'},outcomesModule:{primaryOutcomes:[{measure:'Synthetic endpoint'}]}}});
const input=level=>({nct:'NCT04576949',level,mode:'CURRENT_EVIDENCE'});
function request(body,headers={}){return new NextRequest('https://owner.example.test/api/assessments/trial',{method:'POST',headers:{origin:'https://owner.example.test','content-type':'application/json',cookie:auth.COOKIE_NAME+'='+auth.makeSession(),...headers},body:JSON.stringify(body)});}
test('all six selected levels invoke distinct intended processors on retained valid trial evidence',()=>{
 for(let level=1;level<=6;level++){
  const a=runner.runAssessment({scope:'ONE',nct:'NCT04576949',level});
  assert.equal(a.trials[0].levels.length,1);assert.equal(a.trials[0].levels[0].level,level);
  assert.deepEqual(a.trials[0].levels[0].checks,runner.processLevel(level,data.trials.find(t=>t.nct==='NCT04576949')));
 }
});
test('current registry adapter never carries forward retained research or historical outcomes',async()=>{
 const original=global.fetch;global.fetch=async()=>Response.json({...fixture('NCT00000001'),actualFdaOutcome:'APPROVED',resultsSection:{outcomeMeasuresModule:{}}});
 try{for(let level=1;level<=6;level++){
  const run=await engine.executeTrial({...input(level),nct:'NCT00000001'});
  assert.equal(run.result.levels.length,1);assert.equal(run.result.levels[0].level,level);assert.equal(run.engineVersion,`phase-first-level-${level}-v1`);
  assert.equal(run.fdaPrediction.outcome,'ABSTAIN');assert.equal(run.score,null);assert.equal(run.result.applicationMappingStatus,'NOT_MAPPED_APPLICATION_CYCLE');assert.doesNotMatch(JSON.stringify(run),/APPROVED|ORCA/);
 }}finally{global.fetch=original;}
});
test('historical cutoff and outcome isolation fail closed BEFORE any source retrieval or persistence',async()=>{
 const original=global.fetch;let calls=0;global.fetch=async()=>{calls++;throw Error('Must not read outcomes');};
 try{
  for(const cutoffDate of [undefined,'2026-02-30','2099-01-01'])assert.throws(()=>engine.parseTrialRequest({...input(3),mode:'BLIND_HISTORICAL',cutoffDate}),/cutoff/);
  await assert.rejects(engine.executeTrial({...input(3),mode:'BLIND_HISTORICAL',cutoffDate:'2025-01-01'}),/outcome-isolated/);
  const response=await api.POST(request({...input(3),mode:'BLIND_HISTORICAL',cutoffDate:'2025-01-01'}));assert.equal(response.status,409);assert.equal(calls,0);
 }finally{global.fetch=original;}
});
test('wrong NCT, invalid source version and injected request claims are rejected',()=>{
 assert.throws(()=>engine.registryTrial('NCT00000002',JSON.stringify(fixture('NCT00000001')),new Date().toISOString()),/exact NCT/);
 const f=fixture('NCT00000001');f.protocolSection.statusModule.lastUpdatePostDateStruct.date='2099-01-01';assert.throws(()=>engine.registryTrial('NCT00000001',JSON.stringify(f),new Date().toISOString()),/version date/);
 for(const extra of [{score:99},{outcome:'APPROVAL'},{cutoffDate:'2025-01-01'},{role:'owner'},{sources:[]}])assert.throws(()=>engine.parseTrialRequest({...input(1),...extra}));
});
test('authenticated API requires a successful save acknowledgement for every level and retrieves history',async()=>{
 const original=global.fetch,saved=[];process.env.PDUFA_API_BASE_URL='https://backend.example.test';process.env.PDUFA_INTERNAL_API_KEY='synthetic-key';
 global.fetch=async(url,init={})=>{
  if(String(url).startsWith('https://clinicaltrials.gov/'))return Response.json(fixture('NCT04576949'));
  assert.equal(init.headers['X-Pdufa-Internal-Key'],'synthetic-key');
  if(init.method==='POST'){const report=JSON.parse(init.body);saved.push(report);return Response.json({...report,savedToDatabase:true});}
  return Response.json({nct:'NCT04576949',runs:saved.map(r=>({...r,savedToDatabase:true}))});
 };
 try{
  for(let level=1;level<=6;level++){const response=await api.POST(request(input(level)));assert.equal(response.status,200);const run=await response.json();assert.equal(run.savedToDatabase,true);assert.equal(run.level,level);}
  const response=await api.GET(new NextRequest('https://owner.example.test/api/assessments/trial?nct=NCT04576949',{headers:{cookie:auth.COOKIE_NAME+'='+auth.makeSession()}}));assert.equal(response.status,200);assert.equal((await response.json()).runs.length,6);
  global.fetch=async(url)=>String(url).includes('clinicaltrials.gov')?Response.json(fixture('NCT04576949')):Response.json({error:'database down'},{status:503});
  const failed=await api.POST(request(input(1)));assert.equal(failed.status,503);assert.equal((await failed.json()).savedToDatabase,undefined);
 }finally{global.fetch=original;delete process.env.PDUFA_API_BASE_URL;delete process.env.PDUFA_INTERNAL_API_KEY;}
});
test('authorization, origin, body bounds and missing persistent backend prevent execution',async()=>{
 const original=global.fetch;let calls=0;global.fetch=async()=>{calls++;throw Error('No network expected');};
 try{
  assert.equal((await api.POST(request(input(1),{cookie:'forged'}))).status,401);
  assert.equal((await api.POST(request(input(1),{origin:'https://evil.test'}))).status,403);
  assert.equal((await api.POST(request({...input(1),padding:'x'.repeat(2048)}))).status,413);
  assert.equal((await api.POST(request(input(1)))).status,503);assert.equal(calls,0);
 }finally{global.fetch=original;}
});
test('UI selects level, runs only on click, shows persisted results and blocks blind mode',async()=>{
 const original=global.fetch;let tree,calls=0;
 global.fetch=async(_url,init)=>{calls++;const v=JSON.parse(init.body);return Response.json({...await sample(v.level),savedToDatabase:true});};
 async function sample(level){const t=engine.registryTrial('NCT04576949',JSON.stringify(fixture('NCT04576949')),new Date().toISOString());return {runId:'synthetic',nct:t.nct,level,engineVersion:'test',executedAt:'2026-11-14',savedToDatabase:true,status:'PARTIAL_RESEARCH_ENGINE',scoreStatus:'NO_VALIDATED_SCORING_ALGORITHM',fdaPrediction:{outcome:'ABSTAIN',calibration:'NO_VALIDATED_FDA_MODEL'},result:runner.assessTrial(t,'2026-11-14',level),evidence:{url:t.registryUrl,versionDate:t.registryVersionDate,retrievedAt:t.retrievedAt}};}
 try{
  await act(async()=>{tree=create(React.createElement(UI,{selectedNct:'NCT04576949'}));});assert.equal(calls,0);
  await act(async()=>{tree.root.findAllByType('select')[0].props.onChange({target:{value:'5'}});});
  await act(async()=>{await tree.root.findAllByType('button')[0].props.onClick();await new Promise(r=>setImmediate(r));});assert.equal(calls,1);assert.match(JSON.stringify(tree.toJSON()),/Saved to backend history/);
  await act(async()=>{tree.root.findAllByType('select')[1].props.onChange({target:{value:'BLIND_HISTORICAL'}});});assert.equal(tree.root.findAllByType('button')[0].props.disabled,true);
 }finally{if(tree)await act(async()=>tree.unmount());global.fetch=original;}
});
