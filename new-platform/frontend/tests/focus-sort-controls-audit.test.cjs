const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const ts=require('typescript');
const React=require('react');
const TestRenderer=require('react-test-renderer');
const {act}=TestRenderer;
globalThis.IS_REACT_ACT_ENVIRONMENT=true;
for(const ext of ['.ts','.tsx']){
 require.extensions[ext]=(mod,file)=>mod._compile(
  ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{
   module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,
   jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true
  }}).outputText,file
 );
}
const {default:NumericSortSettings,sortNumericRows}=require('../app/NumericSortSettings.tsx');
const focus=fs.readFileSync(path.join(__dirname,'../app/focus/page.tsx'),'utf8');
const popup=fs.readFileSync(path.join(__dirname,'../app/NumericSortSettings.tsx'),'utf8');
const snapshot=require('../data/focus123EvidenceReadiness20261115.json');
const cols=[
 {id:'overall',label:'Overall prediction survey result — Evidence Readiness /100',shortLabel:'Overall Score /100'},
 {id:'level1',label:'L01'},
 {id:'level2',label:'L02'},
 {id:'level3',label:'L03'},
 {id:'direction',label:'FDA direction',disabled:true,unavailableReason:'no validated prediction'},
 {id:'level4',label:'L04',disabled:true,unavailableReason:'level not yet scored'}
];
const findButton=(root,name)=>{
 const buttons=root.findAll(x=>x.type==='button'&&x.props.children===name);
 assert.equal(buttons.length,1,'Missing button '+name);
 return buttons[0];
};
test('interactive FOCUS single-column popup actually applies chosen direction',async()=>{
 const applied=[];
 let tree;
 function Harness(){
  const [active,setActive]=React.useState([]);
  return React.createElement(NumericSortSettings,{scope:'focus',columns:cols,activeRules:active,
   onApply:(value)=>{applied.push(value);setActive(value)}});
 }
 await act(async()=>{tree=TestRenderer.create(React.createElement(Harness))});
 await act(async()=>tree.root.findByProps({'aria-label':'Column Sort Popup'}).props.onClick());
 const column=tree.root.findByProps({'aria-label':'Column to sort'});
 assert.equal(column.props.value,'overall');
 const options=column.findAllByType('option');
 assert.equal(React.Children.toArray(options[0].props.children).join(''),'Overall Score /100');
 assert.equal(options.find(o=>o.props.value==='level4').props.disabled,true);
 assert.equal(options.find(o=>o.props.value==='direction').props.disabled,true);
 const direction=tree.root.findByProps({'aria-label':'Column sort direction'});
 assert.equal(direction.props.value,'desc');
 await act(async()=>direction.props.onChange({target:{value:'asc'}}));
 await act(async()=>findButton(tree.root,'Apply Sort').props.onClick());
 assert.deepEqual(applied.at(-1),[{column:'overall',direction:'asc'}]);
 assert.equal(tree.root.findAllByProps({role:'dialog'}).length,0);
 // The selected column and direction MUST be remembered when reopening the popup.
 await act(async()=>tree.root.findByProps({'aria-label':'Column Sort Popup'}).props.onClick());
 assert.equal(tree.root.findByProps({'aria-label':'Column to sort'}).props.value,'overall');
 assert.equal(tree.root.findByProps({'aria-label':'Column sort direction'}).props.value,'asc');
 await act(async()=>findButton(tree.root,'Reset').props.onClick());
 assert.deepEqual(applied.at(-1),[]);
 await act(async()=>tree.unmount());
});
test('one-tap externally applied sort is reflected in both popups; pending choices cannot apply',async()=>{
 let tree;
 function Harness(){
  const [active,setActive]=React.useState([]);
  return React.createElement('div',null,
    React.createElement('button',{id:'external',onClick:()=>setActive([{column:'level3',direction:'asc'}])},'Sort by Level 3'),
    React.createElement(NumericSortSettings,{scope:'focus',columns:cols,activeRules:active,onApply:setActive})
  );
 }
 await act(async()=>{tree=TestRenderer.create(React.createElement(Harness))});
 await act(async()=>findButton(tree.root,'Sort by Level 3').props.onClick());
 await act(async()=>tree.root.findByProps({'aria-label':'Column Sort Popup'}).props.onClick());
 assert.equal(tree.root.findByProps({'aria-label':'Column to sort'}).props.value,'level3');
 assert.equal(tree.root.findByProps({'aria-label':'Column sort direction'}).props.value,'asc');
 await act(async()=>tree.root.findByProps({'aria-label':'Column to sort'}).props.onChange({target:{value:'level4'}}));
 assert.equal(findButton(tree.root,'Apply Sort').props.disabled,true);
 await act(async()=>tree.root.findByProps({'aria-label':'Close column sort popup'}).props.onClick());
 await act(async()=>tree.root.findByProps({'aria-label':'Sort Display'}).props.onClick());
 assert.equal(tree.root.findByProps({'aria-label':'Priority 1 column'}).props.value,'level3');
 await act(async()=>tree.root.findByProps({'aria-label':'Close sorting popup'}).props.onClick());
 await act(async()=>tree.unmount());
});
test('FOCUS has no working sort action for unscored levels or FDA direction, but retains them visibly as unavailable',()=>{
 assert.match(focus,/onApply=\{applyFocusSort\} activeRules=\{sortRules\}/);
 assert.match(focus,/shortLabel:"Overall Score \/100"/);
 for(let i=4;i<=20;i++)assert.match(focus,new RegExp('id:"level'+i+'",label:".*?",disabled:true,unavailableReason:"level not yet scored"'));
 assert.match(focus,/id:"direction",label:"FDA prediction direction",disabled:true,unavailableReason:"no validated prediction"/);
 assert.match(focus,/data-testid="focus-sort-all-tied-notice"/);
 assert.match(popup,/const openQuick=\(\)=>/);
 assert.match(popup,/const openAdvanced=\(\)=>/);
 assert.match(popup,/onEscape/);
});
test('source-verified 32-trial Overall and levels 1-3 remain exactly sortable',()=>{
 const grouped=new Map();
 for(const row of snapshot.rows){const group=grouped.get(row.nct)||[];group.push(row);grouped.set(row.nct,group)}
 const records=[...grouped].map(([nct,levels])=>{
  assert.equal(levels.length,3);
  return {nct,score:Math.round(100*levels.reduce((s,x)=>s+x.sourceVerified,0)/
   levels.reduce((s,x)=>s+x.applicable,0))};
 });
 assert.equal(records.length,32);
 const desc=sortNumericRows(records,[{column:'overall',direction:'desc'}],t=>t.score,t=>t.nct);
 const asc=sortNumericRows(records,[{column:'overall',direction:'asc'}],t=>t.score,t=>t.nct);
 assert.equal(desc[0].score,82);
 assert.equal(asc[0].score,48);
 assert.equal(new Set(desc.map(r=>r.nct)).size,32);
 assert.ok(desc.every((r,i)=>i===0||desc[i-1].score>=r.score));
 assert.ok(asc.every((r,i)=>i===0||asc[i-1].score<=r.score));
});
