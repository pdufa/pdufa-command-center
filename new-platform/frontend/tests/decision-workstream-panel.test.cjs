const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),ts=require('typescript');
const React=require('react'),{create,act}=require('react-test-renderer');
for(const ext of ['.ts','.tsx'])require.extensions[ext]=(m,file)=>m._compile(ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}}).outputText,file);
const Panel=require('../app/DecisionWorkstream.tsx').default;
global.IS_REACT_ACT_ENVIRONMENT=true;
const identity={exactKey:'TRIAL|NCT00000001',programId:'PDUFA-000001',trialId:'NCT00000001',ticker:'TEST',stage:'PIPELINE'};
// Synthetic source transport fixtures; these counts are not independently verified FDA evidence.
const source={status:'RESEARCH_ONLY',checkedAt:'2026-10-26T12:00:00Z',publishedLetters:458,approvedApplications:29416,sourcePageReviewRows:154,independentlyVerifiedReviewCycles:0,modelEligibleReviewCycles:0,modelValidated:false,predictionAvailable:false,probability:null,denominatorComplete:false};
const response=value=>({ok:true,json:async()=>value});
const text=root=>{const flatten=node=>node==null?'':typeof node==='string'?node:Array.isArray(node)?node.map(flatten).join(''):flatten(node.children);return flatten(root.toJSON());};

test('archive connection shows source progress without making trial evidence ready',async()=>{
 const saved=global.fetch,calls=[];let root;
 global.fetch=async(url,options)=>{calls.push([url,options]);return response(source);};
 try {
  await act(async()=>{root=create(React.createElement(Panel,{...identity,detail:null}));});
  assert.match(text(root),/458 published CRL records/);
  assert.match(text(root),/0 reviewed matches connected to this trial/);
  assert.match(text(root),/NOT_READY/);assert.match(text(root),/Approval probability: unavailable/);
  assert.match(text(root),/Trading authorization: disabled/);
  assert.equal(calls.length,1);assert.equal(calls[0][0],'/api/hop/readiness');
  assert.equal(calls[0][1].cache,'no-store');assert.equal(calls[0][1].method,undefined);
  assert.equal(root.root.findAllByType('caption').length,1);
 } finally {if(root)await act(async()=>root.unmount());global.fetch=saved;}
});

test('a source which claims validated predictions has its counts withheld',async()=>{
 const saved=global.fetch;let root;
 global.fetch=async()=>response({...source,modelValidated:true});
 try {
  await act(async()=>{root=create(React.createElement(Panel,{...identity,detail:null}));});
  assert.match(text(root),/counts withheld/);assert.doesNotMatch(text(root),/458 published/);
  assert.match(text(root),/NOT_READY/);
 } finally {if(root)await act(async()=>root.unmount());global.fetch=saved;}
});

test('late source response for a previous program or stage cannot populate current trial',async()=>{
 const saved=global.fetch,pending=[];let root;
 global.fetch=(url,options)=>new Promise(resolve=>pending.push({url,options,resolve}));
 try {
  await act(async()=>{root=create(React.createElement(Panel,{...identity,detail:null}));});
  await act(async()=>{root.update(React.createElement(Panel,{...identity,programId:'PDUFA-000002',trialId:'NCT00000002',exactKey:'TRIAL|NCT00000002',stage:'GEM',detail:null}));});
  assert.equal(pending[0].options.signal.aborted,true);
  await act(async()=>{pending[0].resolve(response(source));});
  assert.doesNotMatch(text(root),/458 published/);
  assert.match(text(root),/Checking read-only/);
  assert.ok(pending.some(r=>r.url.includes('PDUFA-000002')&&r.url.includes('stage=GEM')&&r.url.includes('identity=TRIAL%7CNCT00000002')));
  await act(async()=>{for(const p of pending.slice(1))p.resolve({ok:false,status:503});});
  assert.doesNotMatch(text(root),/458 published/);assert.match(text(root),/no evidence inferred/);
 } finally {if(root)await act(async()=>root.unmount());global.fetch=saved;}
});

test('an assessment belonging to another exact trial displays identity failure',async()=>{
 const saved=global.fetch;let root;
 global.fetch=async()=>response(source);
 try {
  await act(async()=>{root=create(React.createElement(Panel,{...identity,detail:{id:'other',programId:identity.programId,nctId:identity.trialId}}));});
  assert.match(text(root),/Candidate assessment identity differs/);
  assert.match(text(root),/NOT_READY/);
 } finally {if(root)await act(async()=>root.unmount());global.fetch=saved;}
});
