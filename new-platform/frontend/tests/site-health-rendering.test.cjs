const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const ts=require('typescript');
const React=require('react');
const {create,act}=require('react-test-renderer');
for(const ext of ['.ts','.tsx'])require.extensions[ext]=(module,filename)=>module._compile(ts.transpileModule(fs.readFileSync(filename,'utf8'),{
 compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}
}).outputText,filename);
require.extensions['.css']=module=>{module.exports={__esModule:true,default:new Proxy({},{get:(_,key)=>key})};};
const SiteHealthStatus=require('../app/SiteHealthStatus.tsx').default;
global.IS_REACT_ACT_ENVIRONMENT=true;

test('Header control opens and closes its own dialog; zero mail is visible; failed refresh removes green',async()=>{
 const oldFetch=global.fetch, oldDocument=global.document, oldWindow=global.window;
 global.document=new EventTarget(); global.document.hidden=false;
 global.window=new EventTarget();
 let unavailable=false,shown=false,root;
 const checks=Array.from({length:10},(_,i)=>({id:i===9?'email':'check'+i,
  label:i===9?'PDUFA email count':'Check '+i,state:'good',summary:i===9?'0 emails · 0 unread':'Verified',
  detail:'Read-only verification',checkedAt:new Date().toISOString()}));
 global.fetch=async()=>unavailable?{ok:false,json:async()=>({error:'Unavailable'})}:
  {ok:true,json:async()=>({checkedAt:new Date().toISOString(),checks})};
 try{
  await act(async()=>{root=create(React.createElement(SiteHealthStatus),{createNodeMock:element=>element.type==='dialog'?{
   showModal(){shown=true;},close(){shown=false;element.props.onClose();}
  }:null});});
  const trigger=root.root.findAllByType('button')[0];
  assert.match(trigger.props.className,/good/);
  await act(async()=>trigger.props.onClick());
  assert.equal(shown,true);
  assert.equal(root.root.findAllByType('button')[0].props['aria-expanded'],true);
  assert.equal(root.root.findAllByType('details').length,10);
  assert.match(JSON.stringify(root.toJSON()),/0 emails · 0 unread/);
  const close=root.root.findAllByType('button').find(b=>b.children.includes('Close ×'));
  await act(async()=>close.props.onClick());
  assert.equal(shown,false);
  unavailable=true;
  const refresh=root.root.findAllByType('button').find(b=>b.children.includes('Refresh status'));
  await act(async()=>refresh.props.onClick());
  assert.match(root.root.findAllByType('button')[0].props.className,/unknown/);
  assert.equal(root.root.findAllByType('details').length,10);
  assert.match(JSON.stringify(root.toJSON()),/Count unavailable/);
  assert.match(JSON.stringify(root.toJSON()),/Last verified · refresh required · Verified/);
  assert.match(JSON.stringify(root.toJSON()),/Read-only verification/);
  assert.doesNotMatch(JSON.stringify(root.toJSON()),/0 emails · 0 unread/);
 }finally{
  if(root)await act(async()=>root.unmount());
  global.fetch=oldFetch;
  if(oldDocument===undefined)delete global.document;else global.document=oldDocument;
  if(oldWindow===undefined)delete global.window;else global.window=oldWindow;
 }
});

test('Pending health rows say Checking, then display received results despite device/server clock differences',async()=>{
 const oldFetch=global.fetch,oldDocument=global.document,oldWindow=global.window;
 global.document=new EventTarget();global.document.hidden=false;global.window=new EventTarget();
 let root,complete;
 global.fetch=()=>new Promise(resolve=>{complete=resolve;});
 try{
  await act(async()=>{root=create(React.createElement(SiteHealthStatus));});
  assert.equal(root.root.findAllByType('details').length,10);
  for(const detail of root.root.findAllByType('details')){
   assert.equal(detail.findByType('small').children.join(''),'Checking');
  }
  assert.ok(!JSON.stringify(root.toJSON()).includes('Count unavailable'));
  const future=new Date(Date.now()+3*3600000).toISOString();
  const checks=Array.from({length:10},(_,i)=>({id:'check'+i,label:'Check '+i,state:'good',summary:'Connected',detail:'Verified',checkedAt:future}));
  await act(async()=>complete({ok:true,status:200,json:async()=>({checkedAt:future,checks})}));
  assert.match(root.root.findAllByType('button')[0].props.className,/good/);
  assert.ok(!JSON.stringify(root.toJSON()).includes('Refresh required'));
 }finally{
  if(root)await act(async()=>root.unmount());global.fetch=oldFetch;
  if(oldDocument===undefined)delete global.document;else global.document=oldDocument;
  if(oldWindow===undefined)delete global.window;else global.window=oldWindow;
 }
});

test('Returning from a hidden mobile page checks immediately and never overlaps requests',async()=>{
 const oldFetch=global.fetch,oldDocument=global.document,oldWindow=global.window;
 global.document=new EventTarget();global.document.hidden=true;global.window=new EventTarget();
 let calls=0,root,complete;
 global.fetch=()=>{calls++;return new Promise(resolve=>{complete=resolve;});};
 try{
  await act(async()=>{root=create(React.createElement(SiteHealthStatus));});
  assert.equal(calls,0);
  await act(async()=>{global.document.hidden=false;global.document.dispatchEvent(new Event('visibilitychange'));});
  assert.equal(calls,1);
  await act(async()=>global.window.dispatchEvent(new Event('focus')));
  assert.equal(calls,1,'Focus must not overlap the visibility refresh');
  await act(async()=>complete({ok:false,status:401}));
  assert.match(JSON.stringify(root.toJSON()),/Sign-in expired/);
 }finally{
  if(root)await act(async()=>root.unmount());global.fetch=oldFetch;
  if(oldDocument===undefined)delete global.document;else global.document=oldDocument;
  if(oldWindow===undefined)delete global.window;else global.window=oldWindow;
 }
});
