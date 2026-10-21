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
 const oldFetch=global.fetch, oldDocument=global.document;
 global.document={hidden:false};
 let unavailable=false,shown=false,root;
 const checks=Array.from({length:10},(_,i)=>({id:i===9?'email':'check'+i,
  label:i===9?'PDUFA email count':'Check '+i,state:'good',summary:i===9?'0 emails · 0 unread':'Verified',
  detail:'Read-only verification',checkedAt:new Date().toISOString()}));
 global.fetch=async()=>unavailable?{ok:false,json:async()=>({error:'Unavailable'})}:
  {ok:true,json:async()=>({checkedAt:new Date().toISOString(),checks})};
 const button=name=>root.root.findAllByType('button').find(b=>JSON.stringify(b.children).includes(name));
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
 }finally{
  if(root)await act(async()=>root.unmount());
  global.fetch=oldFetch;
  if(oldDocument===undefined)delete global.document;else global.document=oldDocument;
 }
});
