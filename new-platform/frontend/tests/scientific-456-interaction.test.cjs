const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const ts=require('typescript');
for(const ext of ['.ts','.tsx'])require.extensions[ext]=(m,f)=>m._compile(
 ts.transpileModule(fs.readFileSync(f,'utf8'),{compilerOptions:{
  module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,
  jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true
 }}).outputText,f
);
const React=require('react');
const {act,create}=require('react-test-renderer');
const Workspace=require('../app/Scientific456Workspace.tsx').default;
globalThis.IS_REACT_ACT_ENVIRONMENT=true;
// Next.js Link effects expect a browser-like global during React test rendering.
global.self=globalThis;
global.window={addEventListener(){},removeEventListener(){}};
const nct='NCT04576949';
const other='NCT00000002';
const uuid='11111111-1111-1111-1111-111111111111';
const report={
 kind:'EXECUTED_SCIENTIFIC_TRIAL_ASSESSMENT',contract:'SCIENTIFIC_1_6',
 runId:uuid,nct,level:4,name:'Safety and benefit-risk',
 mode:'CURRENT_EVIDENCE',cutoffDate:null,executedAt:'2026-11-15T00:00:00Z',
 engineVersion:'scientific-trial-v1.1.0/level-4',
 reportHash:'a'.repeat(64),executionStatus:'COMPLETED_WITH_LIMITATIONS',
 scientificStatus:'SOURCE_BOUND_ANALYSIS_NOT_VALIDATED',ownerReviewStatus:'OWNER_NOT_REVIEWED',
 score:{value:null,kind:'NOT_VALIDATED',method:'No validated clinical score'},
 fdaPrediction:{outcome:'ABSTAIN',probability:null,confidence:'NOT_VALIDATED'},
 checks:[{id:'benefit_risk_interpretation',state:'UNVERIFIED',explanation:'Risk-benefit unknown',locator:'review'}],
 risks:['Unverified safety evidence'],recommendations:['Review original harms'],
 limitations:['No calibrated probability'],
 evidence:{source_url:'https://clinicaltrials.gov/api/v2/studies/'+nct,
  captured_at:'2026-11-14T00:00:00Z',published_at:'2026-11-14',input_sha256:'b'.repeat(64)}
};
function text(tree){return JSON.stringify(tree.toJSON());}
test('history loads only exact-NCT 456 reports, leaving older/123 records separate',async()=>{
 const old=global.fetch;let tree;
 global.fetch=async url=>{
  assert.match(String(url),/contract=SCIENTIFIC_1_6/);
  return Response.json({nct,runs:[report,{...report,contract:'SCIENTIFIC_1_3',runId:'22222222-2222-2222-2222-222222222222'},
   {...report,nct:other,runId:'33333333-3333-3333-3333-333333333333'}],hasMore:false});
 };
 try{
  await act(async()=>{tree=create(React.createElement(Workspace,{cohort:'ASSESSMENTS',initialNct:nct}));});
  await act(async()=>{await Promise.resolve();});
  const output=text(tree);
  assert.match(output,/L04/);
  assert.match(output,/NOT VALIDATED/);
  assert.match(output,/ABSTAIN/);
  assert.match(output,/1 saved 456 research version/);
  assert.doesNotMatch(output,/33333333/);
  assert.doesNotMatch(output,/22222222/);
 }finally{if(tree)await act(async()=>tree.unmount());global.fetch=old;}
});
test('malformed nested findings are withheld instead of crashing the trial panel',async()=>{
 const old=global.fetch;let tree;
 global.fetch=async()=>Response.json({nct,runs:[
  {...report,runId:'44444444-4444-4444-4444-444444444444',checks:[null]},
  {...report,runId:'55555555-5555-5555-5555-555555555555',risks:[null]},
  {...report,runId:'66666666-6666-6666-6666-666666666666',evidence:null},
  report],hasMore:false});
 try{
  await act(async()=>{tree=create(React.createElement(Workspace,{cohort:'ASSESSMENTS',initialNct:nct}));});
  await act(async()=>{await Promise.resolve();});
  const output=text(tree);
  assert.match(output,/1 saved 456 research version/);
  assert.match(output,/Risk-benefit unknown/);
  for(const invalid of ['44444444','55555555','66666666'])assert.doesNotMatch(output,new RegExp(invalid));
 }finally{if(tree)await act(async()=>tree.unmount());global.fetch=old;}
});
test('changing selected NCT clears previously saved clinical evidence from display',async()=>{
 const old=global.fetch;let tree;
 global.fetch=async()=>Response.json({nct,runs:[report],hasMore:false});
 try{
  await act(async()=>{tree=create(React.createElement(Workspace,{cohort:'FOCUS',initialNct:nct}));});
  await act(async()=>{await Promise.resolve();});
  assert.match(text(tree),/Risk-benefit unknown/);
  await act(async()=>{
   tree.root.findByProps({'aria-label':'456 exact NCT'}).props.onChange({target:{value:other}});
  });
  const output=text(tree);
  assert.doesNotMatch(output,/Risk-benefit unknown/);
  assert.doesNotMatch(output,/Unverified safety evidence/);
  assert.match(output,/NCT00000002/);
 }finally{if(tree)await act(async()=>tree.unmount());global.fetch=old;}
});


test('load older research versions paginates by cursor and retains first page',async()=>{
 const oldFetch=global.fetch;let tree;
 const olderId='77777777-7777-7777-7777-777777777777';
 const cursor='2026-11-15T00:00:00+00:00|'+uuid;
 const calls=[];
 global.fetch=async url=>{
  const parsed=new URL(String(url),'https://owner.example.test');
  calls.push(parsed);
  assert.equal(parsed.searchParams.get('contract'),'SCIENTIFIC_1_6');
  if(parsed.searchParams.has('before')){
   assert.equal(parsed.searchParams.get('before'),cursor);
   return Response.json({nct,runs:[{...report,runId:olderId}],hasMore:false,nextCursor:null});
  }
  return Response.json({nct,runs:[report],hasMore:true,nextCursor:cursor});
 };
 try{
  await act(async()=>{tree=create(React.createElement(Workspace,{cohort:'ASSESSMENTS',initialNct:nct}));});
  await act(async()=>{await Promise.resolve();});
  assert.match(text(tree),/Load older 456 versions/);
  await act(async()=>{
   const button=tree.root.findAllByType('button').find(x=>x.props.children==='Load older 456 versions');
   assert.ok(button,'Older-history continuation button must be visible');
   button.props.onClick();
  });
  await act(async()=>{await Promise.resolve();});
  const output=text(tree);
  assert.equal(calls.length,2);
  assert.match(output,/2 saved 456 assessment versions|Saved 456 assessment versions/);
  assert.match(output,new RegExp(uuid));
  assert.match(output,new RegExp(olderId));
  assert.doesNotMatch(output,/Load older 456 versions/);
 }finally{if(tree)await act(async()=>tree.unmount());global.fetch=oldFetch;}
});
