const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),ts=require('typescript');
require.extensions['.ts']=(m,f)=>m._compile(ts.transpileModule(fs.readFileSync(f,'utf8'),{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,esModuleInterop:true}}).outputText,f);
const root=path.resolve(__dirname,'..'),read=f=>fs.readFileSync(path.join(root,f),'utf8');
const {masterBuildTasks}=require('../app/installation-audit/master-build-tasks.ts');
const {activeInstallationTasks,isActiveInstallationTask}=require('../lib/installation-active-requirements.ts');
const {auditMedicalInventory,auditOutcomeSources}=require('../lib/installation-analysis-readiness.ts');
test('retirement preserves original task identities while excluding obsolete prerequisites',()=>{
 const active=activeInstallationTasks(masterBuildTasks);assert.ok(active.length>0);assert.equal(new Set(active.map(t=>t.id)).size,active.length);
 for(const task of active){assert.equal(masterBuildTasks[task.section][task.task],task.label);assert.equal(task.id,`${String(task.section+1).padStart(2,'0')}-${String(task.task+1).padStart(3,'0')}`);assert.doesNotMatch(task.label,/\braas\b|\bgem(?:\s+jr)?\b/i);}
 assert.equal(isActiveInstallationTask(0,0,'Install RAAS model'),false);
 assert.ok(!active.some(t=>['05-004','06-025','03-004','03-005','08-047'].includes(t.id)));
 for(const id of ['01-002','13-001','13-002','13-003','13-004','08-060','08-062'])assert.ok(active.some(t=>t.id===id),id);
});
test('tracker and API share an active projection without changing saved acceptance evidence',()=>{
 const progress=read('app/installation-audit/MasterBuildProgress.tsx'),api=read('app/api/installation-audit/live-task-evidence/route.ts');
 assert.match(progress,/activeInstallationTasks\(masterBuildTasks\)/);assert.match(api,/activeInstallationTasks\(masterBuildTasks\)/);
 assert.match(progress,/does not claim additional work completed or restart completed installation work/);
 const registry=JSON.parse(read('public/installation-audit/task-evidence.json'));
 for(const id of Object.keys(registry.tasks)){const [section,task]=id.split('-').map(Number);assert.ok(masterBuildTasks[section-1]?.[task-1],id);}
 assert.match(api,/candidate\?\.status==="Verified" && !hasTaskAcceptance/);
});
test('live installation source checks do not call a retired rating feed',()=>{
 const ui=read('app/installation-audit/ScientificOutcomeLive.tsx');
 assert.doesNotMatch(ui,/science-outcome-gates|candidate-assessments|\/api\/assessments|auditScienceIndex|scores\[/);
 assert.match(ui,/\/api\/preview\/deep-medical-intelligence/);assert.match(ui,/Inventory coverage does not certify medical interpretation/);
 const main=read('app/main/page.tsx');assert.doesNotMatch(main,/does not disable RAAS/);assert.match(main,/RAAS is permanently retired/);
});
test('independent source counts cannot claim scientific completion from inventory alone',()=>{
 const valid={schemaVersion:1,asOf:'2026-11-08',inventory:{poolTrials:100,focusTrials:2,applications:1,metadataScreenedTrials:100,sourceExtractedTrials:2,fullyReviewedTrials:0,incompleteTrials:100,completedDecisions:0,sourceDocuments:5},applications:[{}]};
 const result=auditMedicalInventory(valid);assert.equal(result.fullyReviewedTrials,0);assert.equal(result.completedDecisions,0);
 assert.throws(()=>auditMedicalInventory({...valid,inventory:{...valid.inventory,fullyReviewedTrials:3}}),/does not reconcile/);
 assert.throws(()=>auditMedicalInventory({...valid,applications:[]}),/does not reconcile/);
});
test('FDA retrieval is separate from calibrated prediction acceptance',()=>{
 const valid={status:'RESEARCH_ONLY',checkedAt:'2026-11-08T00:00:00Z',publishedLetters:458,approvedApplications:1000,sourcePageReviewRows:10,independentlyVerifiedReviewCycles:0,modelValidated:false,predictionAvailable:false,probability:null,denominatorComplete:false,modelEligibleReviewCycles:0};
 assert.equal(auditOutcomeSources(valid).independentlyVerifiedReviewCycles,0);
 for(const change of [{probability:.9},{modelValidated:true},{predictionAvailable:true},{modelEligibleReviewCycles:1}])assert.throws(()=>auditOutcomeSources({...valid,...change}),/cannot certify/);
});

test('read-only live tracker preserves prior status records and never returns retired task gates',async()=>{
 const {GET}=require('../app/api/installation-audit/live-task-evidence/route.ts');
 const originalFetch=global.fetch,base=process.env.PDUFA_API_BASE_URL,key=process.env.PDUFA_INTERNAL_API_KEY;
 const before=read('public/installation-audit/task-evidence.json'),registry=JSON.parse(before);
 try{
  delete process.env.PDUFA_API_BASE_URL;delete process.env.PDUFA_INTERNAL_API_KEY;
  global.fetch=async()=>new Response('{}',{status:200,headers:{'content-type':'application/json'}});
  const response=await GET(new Request('http://localhost/api/installation-audit/live-task-evidence'));
  const result=await response.json(),active=activeInstallationTasks(masterBuildTasks),ids=new Set(active.map(t=>t.id));
  assert.equal(result.taskCount,active.length);assert.equal(result.automatedAcceptanceCoverage,0);
  assert.ok(Object.keys(result.tasks).every(id=>ids.has(id)));
  for(const [id,evidence]of Object.entries(registry.tasks))if(ids.has(id))assert.deepEqual(result.tasks[id],evidence,id);
  assert.equal(read('public/installation-audit/task-evidence.json'),before);
 }finally{
  global.fetch=originalFetch;
  if(base===undefined)delete process.env.PDUFA_API_BASE_URL;else process.env.PDUFA_API_BASE_URL=base;
  if(key===undefined)delete process.env.PDUFA_INTERNAL_API_KEY;else process.env.PDUFA_INTERNAL_API_KEY=key;
 }
});
