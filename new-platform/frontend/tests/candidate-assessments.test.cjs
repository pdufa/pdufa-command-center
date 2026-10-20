const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const ts=require('typescript');
const React=require('react');
const {create,act}=require('react-test-renderer');
for(const ext of ['.ts','.tsx']) require.extensions[ext]=(module,file)=>module._compile(ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}}).outputText,file);
const {sortByAssessment,validateAssessmentIndex,scoreFor}=require('../lib/candidate-assessments.ts');
const {default:Detail,AssessmentProvider,AssessmentCells}=require('../app/CandidateAssessments.tsx');
global.IS_REACT_ACT_ENVIRONMENT=true;
const tuple=(points=0,coverage=0,complete=null)=>[complete,points,coverage,...[points,0,0,0,0,0,0],...[coverage,0,0,0,0,0,0]];
function index(records){return {modelVersion:'test-v1',status:'COMPLETE',version:'verified',workspaceVersion:'workspace',records,total:records.length,totals:{PIPELINE:{complete:0,partial:0,missing:records.length},GEM_JR:{complete:0,partial:0,missing:records.length},GEM:{complete:0,partial:0,missing:records.length}},registryLinked:0,computedAt:'2026-10-20'};}

test('a 12,000-candidate index validates every exact identity and rejects duplicate or inflated partial scores',()=>{
 const records=Array.from({length:12000},(_,i)=>['TRIAL|NCT'+String(i).padStart(8,'0'),tuple(),tuple(),tuple(),[]]);
 assert.equal(validateAssessmentIndex(index(records)).records.length,12000);
 assert.throws(()=>validateAssessmentIndex(index([records[0],records[0]])),/coverage/);
 const bad=['TRIAL|NCT00000001',tuple(20,20,100),tuple(),tuple(),[]];
 assert.throws(()=>validateAssessmentIndex(index([bad])),/score/);
 assert.throws(()=>validateAssessmentIndex(index([['exact',tuple(21,20),tuple(),tuple(),[]]])),/score/);
 const a=['exact',tuple(0,10),tuple(),tuple(),[]];
 assert.equal(scoreFor(a,'PIPELINE')[1],0);
 assert.equal(scoreFor(a,'PIPELINE')[2],10);
});

test('complete-score sorting does not elevate high partial points and never drops same-ticker trials',()=>{
 const rows=[{id:'partial',ticker:'SAME'},{id:'complete',ticker:'SAME'},{id:'missing',ticker:'SAME'}];
 const records=new Map([['partial',['partial',tuple(90,90),tuple(),tuple(),[]]],['complete',['complete',[50,50,100],tuple(),tuple(),[]]]]);
 assert.deepEqual(sortByAssessment(rows,records,'PIPELINE','score').map(r=>r.id),['complete','partial','missing']);
 assert.deepEqual(sortByAssessment(rows,records,'PIPELINE','coverage').map(r=>r.id),['complete','partial','missing']);
 assert.deepEqual(rows.map(r=>r.id),['partial','complete','missing']);
});

test('rendered candidate details expose seven categories per model, actual zero, missing measurements and dated sources',async()=>{
 const savedFetch=global.fetch;
 const model=(prefix)=>({score:null,observedPoints:0,coverage:5,status:'PARTIAL',categories:Array.from({length:7},(_,i)=>({id:prefix+(i+1),label:'Category '+i,maximum:5,observedPoints:0,coverage:i?0:5,status:i?'MISSING':'COMPLETE',metrics:[{id:'metric'+i,label:'Measurement '+i,maximum:5,value:i?null:0,points:i?null:0,coverage:i?0:5,status:i?'MISSING':'OBSERVED',rule:'Documented rule',source:i?'':'https://clinicaltrials.gov/study/NCT00000001',sourceDate:'2026-10-01',checkedAt:'2026-10-20',note:''}]}))});
 const detail={id:'TRIAL|NCT00000001',programId:'PDUFA-000001',nctId:'NCT00000001',modelVersion:'test-v1',asOf:'2026-10-20',models:{PIPELINE:model('P'),GEM_JR:model('J'),GEM:model('G')},riskFlags:[],qualification:{note:'Research only'},reportedStatistics:[{endpoint:'Primary',p_value:0,estimate:0}],data:{saved:0},history:[],changes:{},historyStatus:'SAVED'};
 global.fetch=async()=>({ok:true,json:async()=>detail});
 let root;
 try{
  await act(async()=>{root=create(React.createElement(Detail,{row:{id:detail.id,programId:detail.programId,ticker:'SAME'}}));});
  for(const [label,prefix] of [['PIPELINE','P'],['GEM JR','J'],['GEM','G']]){
   const button=root.root.findAllByType('button').find(b=>b.findAllByType('span').some(s=>s.children.includes(label)));
   await act(async()=>button.props.onClick());
   const cats=root.root.findAllByProps({className:'assessment-category'});
   assert.equal(cats.length,7);
   assert.ok(cats[0].findAllByType('strong').some(x=>x.children.join('').startsWith(prefix+'1')));
   assert.match(JSON.stringify(root.toJSON()),/Verified: /);
   assert.match(JSON.stringify(root.toJSON()),/MISSING/);
   assert.match(JSON.stringify(root.toJSON()),/0/);
  }
 }finally{if(root) await act(async()=>root.unmount());global.fetch=savedFetch;}
});

test('the shared table score cells open the exact candidate and distinguish reviewed zero from no evidence',async()=>{
 const savedFetch=global.fetch;
 const row={id:'TRIAL|NCT00000001',programId:'PDUFA-000001',ticker:'SAME'};
 global.fetch=async()=>({ok:true,json:async()=>index([[row.id,tuple(0,10),tuple(),tuple(),[]]])});
 let opened=0,root;
 try{
  await act(async()=>{root=create(React.createElement(AssessmentProvider,null,React.createElement('table',null,React.createElement('tbody',null,React.createElement('tr',null,React.createElement(AssessmentCells,{row,stage:'PIPELINE',onOpen:()=>opened++}))))));});
  assert.equal(root.root.findAllByType('td').length,9);
  assert.match(JSON.stringify(root.toJSON()),/0 observed/);
  assert.match(JSON.stringify(root.toJSON()),/Missing evidence/);
  await act(async()=>root.root.findAllByType('button')[0].props.onClick());
  assert.equal(opened,1);
 }finally{if(root)await act(async()=>root.unmount());global.fetch=savedFetch;}
});

test('a temporary published-source refresh recovers automatically without a user rescan',async()=>{
 const savedFetch=global.fetch;
 const row={id:'exact-refresh',ticker:'SAME'};
 let calls=0,root;
 global.fetch=async()=>++calls===1
   ? {ok:false,status:503,json:async()=>({error:'Fresh versioned candidate source unavailable'})}
   : {ok:true,status:200,json:async()=>index([[row.id,tuple(0,10),tuple(),tuple(),[]]])};
 try{
  await act(async()=>{root=create(React.createElement(AssessmentProvider,null,React.createElement('table',null,React.createElement('tbody',null,React.createElement('tr',null,React.createElement(AssessmentCells,{row,stage:'PIPELINE',onOpen(){}}))))));});
  assert.equal(calls,1);
  assert.match(JSON.stringify(root.toJSON()),/Scoring/);
  await act(async()=>{await new Promise(resolve=>setTimeout(resolve,2100));});
  assert.equal(calls,2);
  assert.match(JSON.stringify(root.toJSON()),/0 observed/);
 }finally{if(root)await act(async()=>root.unmount());global.fetch=savedFetch;}
});
