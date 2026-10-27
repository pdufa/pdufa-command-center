const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os'),crypto=require('node:crypto'),ts=require('typescript');
for(const ext of ['.ts'])require.extensions[ext]=(m,file)=>m._compile(ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,esModuleInterop:true}}).outputText,file);
const {parseReviewedDecisionManifest,validateDecisionIdentity,MAX_REVIEWED_MANIFEST_BYTES}=require('../lib/decision-reviewed-manifest.ts');
const {loadReviewedDecisionEvidence}=require('../lib/decision-reviewed-store.ts');
const {assessDecisionWorkstream}=require('../lib/decision-workstream.ts');
const identity={exactKey:'TRIAL|NCT12345678',programId:'PDUFA-123456',trialId:'NCT12345678',ticker:'TEST',stage:'GEM_JR'};
const asOf='2026-10-26T12:00:00Z';
// Invented schema/transport fixtures only; these are not reviewed scientific or FDA records.
function manifest(){return {schemaVersion:1,identity:{...identity},researchOnly:true,modelValidated:false,probability:null,tradeAuthorized:false,evidence:{
 identity:{...identity},science:null,outcome:null,
 target:{programId:identity.programId,asOf,diseaseSubtype:'',indication:'',mechanism:'',primaryEndpoint:''},
 history:[],coverage:{asOf,windowStart:'2020-01-01',windowEnd:'2025-01-01',eligibleApplications:0,reviewedDecisions:0,approved:0,crl:0,withdrawn:0,unresolved:0,sourceCoverageConfirmed:false,includesNonApprovals:false},
 chronology:{},main:null,calibrationRows:[],holdout:null}};}
const prediction=()=>({programId:'PDUFA-234567',predictedAt:'2024-01-01',decisionAt:'2024-02-01',predictionCapturedAt:'2024-01-02',decisionObservedAt:'2024-02-02',predictionSource:'https://example.org/frozen',decisionSource:'https://www.fda.gov/example',probability:.5,approved:false,reviewStatus:'PENDING'});
const source=()=>({sourceUrl:'https://www.fda.gov/example',publishedAt:'2024-02-01',observedAt:'2024-02-02',decisionAt:'2024-02-01',predictionCutoff:asOf,independentlyReviewed:false});
const market=()=>({programId:identity.programId,ticker:identity.ticker,observedAt:'2024-01-01',capturedAt:'2024-01-02',adjustedClose:10,currency:'USD',priceSource:'https://example.org/price',adjustmentMethod:'RAW',corporateActionsReviewed:false,verifiedBy:''});
function structuredManifest(){const m=manifest();Object.assign(m.evidence,{
 science:{programId:identity.programId,trialId:identity.trialId,asOf,status:'PARTIAL',sourceStatus:'UNVERIFIED',reviewedLevels:1,requiredLevels:20,criticalFindingsResolved:false},
 history:[{programId:'PDUFA-234567',decisionAt:'2024-02-01',diseaseSubtype:'A',indication:'B',mechanism:'C',primaryEndpoint:'D',trialPhase:3,outcome:'CRL',sourceUrl:'https://www.fda.gov/example',independentlyReviewed:false}],
 chronology:{'PDUFA-234567':[source()]},calibrationRows:[prediction()],
 main:{programId:identity.programId,ticker:identity.ticker,asOf,restrictionsReviewed:false,unresolvedCriticalRisks:1,marketEntry:market(),marketExit:null},
 holdout:{training:[{...prediction(),applicationNumber:'NDA123456',modelVersion:'research-v1',subgroup:'example'}],rows:[],plan:{modelVersion:'research-v1',planSource:'https://example.org/plan',frozenAt:'2024-01-01',holdoutStart:'2024-01-02',holdoutEnd:'2025-01-01',evaluatedAt:asOf,trainingProgramIds:['PDUFA-234567'],holdoutProgramIds:[]}},
 });return m;}

test('partial manifest is accepted as transport and cannot certify evidence or a prediction',()=>{
 const input=manifest(),out=parseReviewedDecisionManifest(input,identity);
 assert.notEqual(out,input.evidence);assert.deepEqual(out,input.evidence);
 const result=assessDecisionWorkstream(identity,null,null,null,out,new Date(asOf));
 assert.equal(result.status,'NOT_READY');assert.equal(result.modelValidated,false);assert.equal(result.probability,null);assert.equal(result.tradeAuthorized,false);
 out.target.indication='changed';assert.equal(input.evidence.target.indication,'');
 assert.deepEqual(parseReviewedDecisionManifest(structuredManifest(),identity),structuredManifest().evidence);
});
test('outer and inner identity, assessment stage, trial, program and ticker must match exactly',()=>{
 for(const changes of [{stage:'GEM'},{programId:'PDUFA-999999'},{trialId:'NCT87654321'},{ticker:'OTHER'},{exactKey:'other'}]){
  for(const location of ['identity','evidence']){
   const m=manifest();Object.assign(location==='identity'?m.identity:m.evidence.identity,changes);
   assert.throws(()=>parseReviewedDecisionManifest(m,identity));
  }
 }
 for(const changes of [{programId:'../secret'},{stage:'WT'},{trialId:''},{exactKey:'x'.repeat(513)},{ticker:'invalid ticker'}])
  assert.throws(()=>validateDecisionIdentity({...identity,...changes}));
 const m=structuredManifest();m.evidence.science.trialId='NCT87654321';assert.throws(()=>parseReviewedDecisionManifest(m,identity));
});
test('source-cited scientific dossier stays partial and is bound to the exact requested identity',()=>{
 const m=manifest();m.evidence.scienceDossier={identity:{...identity},asOf,drug:'Example',indication:'Example indication',companyCik:'0000000001',fdaApplication:null,layers:[],levels:[]};
 assert.deepEqual(parseReviewedDecisionManifest(m,identity).scienceDossier,m.evidence.scienceDossier);
 assert.equal(assessDecisionWorkstream(identity,null,null,null,parseReviewedDecisionManifest(m,identity),new Date(asOf)).status,'NOT_READY');
 m.evidence.scienceDossier.identity.stage='GEM';assert.throws(()=>parseReviewedDecisionManifest(m,identity));
 m.evidence.scienceDossier.identity.stage=identity.stage;m.evidence.scienceDossier.ordersEnabled=true;
 assert.throws(()=>parseReviewedDecisionManifest(m,identity));
});
test('application and company mapping assertions are optional transport metadata, not independently verified identities',()=>{
 for(const links of [{outcomeApplicationNumber:null,mainCompanyCik:null},{outcomeApplicationNumber:'NDA123456',mainCompanyCik:'0000000001'},
  {outcomeApplicationNumber:'NDA999999',mainCompanyCik:'0000000002'}]){
  const m=manifest();Object.assign(m.evidence,links);
  const out=parseReviewedDecisionManifest(m,identity);
  assert.equal(out.outcomeApplicationNumber,links.outcomeApplicationNumber);assert.equal(out.mainCompanyCik,links.mainCompanyCik);
  assert.equal(assessDecisionWorkstream(identity,null,null,null,out,new Date(asOf)).status,'NOT_READY');
 }
 for(const links of [{outcomeApplicationNumber:123456},{mainCompanyCik:true},{outcomeApplicationNumber:'x'.repeat(2049)}]){
  const m=manifest();Object.assign(m.evidence,links);assert.throws(()=>parseReviewedDecisionManifest(m,identity));
 }
});
test('unrecognized schema fields and any model-validation or trading-control promotion are rejected',()=>{
 for(const change of [{schemaVersion:2},{researchOnly:false},{modelValidated:true},{probability:.8},{tradeAuthorized:true},{ordersEnabled:true},{manifestSha256:'forged'}])
  assert.throws(()=>parseReviewedDecisionManifest(Object.assign(manifest(),change),identity));
 const m=manifest();m.evidence.target.tradeCall='BUY';assert.throws(()=>parseReviewedDecisionManifest(m,identity));
});
test('every nested gate input is checked for primitive types, bounded arrays and finite values',()=>{
 for(const mutate of [m=>m.evidence.history=null,m=>m.evidence.science.reviewedLevels='20',m=>m.evidence.science.criticalFindingsResolved='true',
  m=>m.evidence.coverage.eligibleApplications=-1,m=>m.evidence.coverage.includesNonApprovals=1,
  m=>m.evidence.history[0].trialPhase=NaN,m=>m.evidence.history[0].outcome='APPROVAL',
  m=>m.evidence.main.marketEntry.adjustedClose=Infinity,m=>m.evidence.main.marketEntry.corporateActionsReviewed='true',
  m=>m.evidence.calibrationRows[0].probability=1.1,m=>m.evidence.calibrationRows[0].approved='false',
  m=>m.evidence.holdout.plan.holdoutProgramIds='PDUFA-234567',m=>m.evidence.holdout.training[0].modelVersion={},
  m=>m.evidence.chronology['PDUFA-234567'][0].independentlyReviewed=1,
  m=>m.evidence.calibrationRows=Array.from({length:2001},prediction),m=>m.evidence.chronology['invalid']=[source()]]){
  const m=structuredManifest();mutate(m);assert.throws(()=>parseReviewedDecisionManifest(m,identity));
 }
});
test('credentials and unsupported schemes cannot reach any source link consumer',()=>{
 for(const url of ['javascript:alert(1)','http://www.fda.gov/example','https://reviewer:secret@example.org/source']){
  for(const mutate of [m=>m.evidence.history[0].sourceUrl=url,m=>m.evidence.chronology['PDUFA-234567'][0].sourceUrl=url,
   m=>m.evidence.main.marketEntry.priceSource=url,m=>m.evidence.calibrationRows[0].predictionSource=url,
   m=>m.evidence.holdout.plan.planSource=url]){
   const m=structuredManifest();mutate(m);assert.throws(()=>parseReviewedDecisionManifest(m,identity));
  }
 }
});
test('filesystem loader is opt-in, bounded, and never follows a manifest-file symlink',async()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'decision-reviewed-')),filename=path.join(dir,identity.programId+'.'+identity.stage+'.json');
 try{
  assert.equal((await loadReviewedDecisionEvidence(identity,undefined)).status,'UNCONFIGURED');
  assert.equal((await loadReviewedDecisionEvidence(identity,'relative')).status,'INVALID');
  assert.equal((await loadReviewedDecisionEvidence(identity,dir)).status,'MISSING');
  const bytes=JSON.stringify(manifest());fs.writeFileSync(filename,bytes);
  const out=await loadReviewedDecisionEvidence(identity,dir);
  assert.equal(out.status,'AVAILABLE_FOR_REVIEW');assert.equal(out.manifestSha256,crypto.createHash('sha256').update(bytes).digest('hex'));
  assert.equal(fs.readFileSync(filename,'utf8'),bytes);
  fs.writeFileSync(filename,'{malformed');assert.equal((await loadReviewedDecisionEvidence(identity,dir)).status,'INVALID');
  fs.writeFileSync(filename,' '.repeat(MAX_REVIEWED_MANIFEST_BYTES+1));assert.equal((await loadReviewedDecisionEvidence(identity,dir)).status,'INVALID');
  fs.unlinkSync(filename);const other=path.join(dir,'other.json');fs.writeFileSync(other,bytes);fs.symlinkSync(other,filename);
  assert.equal((await loadReviewedDecisionEvidence(identity,dir)).status,'INVALID');
 }finally{fs.rmSync(dir,{recursive:true,force:true});}
});

const {NextRequest}=require('next/server'),auth=require('../lib/auth.ts'),route=require('../app/api/decision-evidence/[programId]/route.ts');
const keys=['DASHBOARD_PASSWORD','SESSION_SIGNING_KEY','PDUFA_DECISION_EVIDENCE_DIR'];
const env=()=>Object.fromEntries(keys.map(k=>[k,process.env[k]]));
const restore=saved=>{for(const [k,v]of Object.entries(saved)){if(v===undefined)delete process.env[k];else process.env[k]=v;}};
const context=()=>({params:Promise.resolve({programId:identity.programId})});
function request(query={},authenticated=true){
 const params=new URLSearchParams({identity:identity.exactKey,trialId:identity.trialId,ticker:identity.ticker,stage:identity.stage,...query});
 return new NextRequest('https://dashboard.example/api/decision-evidence/'+identity.programId+'?'+params,{headers:authenticated?{Cookie:auth.COOKIE_NAME+'='+auth.makeSession()}:undefined});
}
test('route authenticates before identity or filesystem reads and exposes no write handlers',async()=>{
 const saved=env();try{
  process.env.DASHBOARD_PASSWORD='test-only-reviewed-password';process.env.SESSION_SIGNING_KEY='s'.repeat(40);
  process.env.PDUFA_DECISION_EVIDENCE_DIR='/must/not/read';
  assert.equal((await route.GET(request({},false),context())).status,401);
  delete process.env.DASHBOARD_PASSWORD;assert.equal((await route.GET(request({},false),context())).status,401);
  assert.equal(route.POST,undefined);assert.equal(route.PUT,undefined);assert.equal(route.DELETE,undefined);
 }finally{restore(saved);}
});
test('authenticated route withholds missing, malformed and cross-trial source records',async()=>{
 const saved=env(),dir=fs.mkdtempSync(path.join(os.tmpdir(),'decision-route-')),filename=path.join(dir,identity.programId+'.'+identity.stage+'.json');
 try{
  process.env.DASHBOARD_PASSWORD='test-only-reviewed-password';process.env.SESSION_SIGNING_KEY='s'.repeat(40);
  delete process.env.PDUFA_DECISION_EVIDENCE_DIR;
  assert.equal((await route.GET(request(),context())).status,503);
  process.env.PDUFA_DECISION_EVIDENCE_DIR=dir;
  assert.equal((await route.GET(request(),context())).status,404);
  assert.equal((await route.GET(request({stage:'WT'}),context())).status,422);
  assert.equal((await route.GET(request({identity:''}),context())).status,422);
  fs.writeFileSync(filename,JSON.stringify(manifest()));
  assert.equal((await route.GET(request({trialId:'NCT87654321'}),context())).status,503);
  fs.writeFileSync(filename,'{broken');const invalid=await route.GET(request(),context());
  assert.equal(invalid.status,503);assert.doesNotMatch(JSON.stringify(await invalid.json()),new RegExp(dir));
 }finally{restore(saved);fs.rmSync(dir,{recursive:true,force:true});}
});
test('authenticated partial evidence is delivered with fixed research controls, identity and no-store caching',async()=>{
 const saved=env(),dir=fs.mkdtempSync(path.join(os.tmpdir(),'decision-route-'));try{
  process.env.DASHBOARD_PASSWORD='test-only-reviewed-password';process.env.SESSION_SIGNING_KEY='s'.repeat(40);process.env.PDUFA_DECISION_EVIDENCE_DIR=dir;
  fs.writeFileSync(path.join(dir,identity.programId+'.'+identity.stage+'.json'),JSON.stringify(manifest()));
  const res=await route.GET(request(),context()),body=await res.json();
  assert.equal(res.status,200);assert.equal(res.headers.get('Cache-Control'),'private, no-store');
  assert.deepEqual(body.identity,identity);assert.equal(body.researchOnly,true);assert.equal(body.modelValidated,false);assert.equal(body.probability,null);assert.equal(body.tradeAuthorized,false);
  assert.match(body.manifestSha256,/^[a-f0-9]{64}$/);assert.deepEqual(parseReviewedDecisionManifest(body,identity),manifest().evidence);
 }finally{restore(saved);fs.rmSync(dir,{recursive:true,force:true});}
});
