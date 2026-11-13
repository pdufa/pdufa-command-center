'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),ts=require('typescript');
require.extensions['.ts']=(m,f)=>m._compile(ts.transpileModule(fs.readFileSync(f,'utf8'),{
 compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,esModuleInterop:true}
}).outputText,f);
const {indications,linkToDiseases,phaseColumn,phaseCounts,uniqueTrials,selectedRows}=require('../lib/indication-intelligence.ts');
const nodes=[
 {id:'onc',name:'Oncology',parentId:null},
 {id:'breast',name:'Breast cancer',parentId:'onc',sourceId:'mesh-1'},
 {id:'lung',name:'Lung cancer',parentId:'onc',sourceId:'mesh-2'}
];
const index={byId:new Map(nodes.map(n=>[n.id,n])),unique:nodes};
const trial=(nct,indication,stage='Phase 1',ticker='IAM')=>({
 nct,ticker,company:'Example',drug:'Candidate',indication,stage,focus:false,
 sourceUrl:'https://clinicaltrials.gov/study/'+nct
});
test('multiple indications are retained for one exact trial without inflating trial counts',()=>{
 const rows=linkToDiseases([trial('NCT01234567','Breast cancer | Lung cancer')],index);
 assert.equal(rows.length,2);
 assert.equal(uniqueTrials(rows),1);
 assert.equal(uniqueTrials(selectedRows(rows,index,'onc','',false,null)),1);
 assert.equal(phaseCounts(rows).P1,1);
});
test('unknown and ambiguous disease text never becomes an inferred clinical match',()=>{
 const rows=linkToDiseases([trial('NCT01234567','advanced resistant cancer')],index);
 assert.equal(rows[0].classificationId,null);
 assert.equal(rows[0].matchStatus,'UNMAPPED');
 assert.equal(selectedRows(rows,index,'onc','',false,null).length,0);
 assert.equal(selectedRows(rows,index,null,'NCT01234567',false,null).length,1);
});
test('combined phases and regulatory stages stay separate',()=>{
 assert.equal(phaseColumn('Phase 1/2'),'P1/2');
 assert.equal(phaseColumn('Phase 2/3'),'P2/3');
 assert.equal(phaseColumn('Phase 3 Results'),'RESULTS');
 assert.equal(phaseColumn('FDA Acceptance'),'FDA');
 assert.equal(phaseColumn('Not Applicable'),'OTHER');
});
test('FOCUS filtering requires exact NCT + ticker identity',()=>{
 const rows=linkToDiseases([
  {...trial('NCT01234567','Breast cancer'),focus:true},
  trial('NCT09876543','Breast cancer','Phase 3','OTHER')
 ],index);
 assert.equal(selectedRows(rows,index,'onc','',true,null).length,1);
 assert.deepEqual(indications('Breast cancer; Lung cancer'),['Breast cancer','Lung cancer']);
});
test('shared UI is embedded in POOL and FOCUS and routed from INDICATIONS',()=>{
 const read=p=>fs.readFileSync(path.join(__dirname,'../',p),'utf8');
 assert.match(read('app/FunnelWorkspace.tsx'),/<IndicationIntelligence mode="pool"\/>/);
 assert.match(read('app/focus/page.tsx'),/<IndicationIntelligence mode="focus"\/>/);
 assert.match(read('app/indications/page.tsx'),/<IndicationIntelligence mode="indications"\/>/);
 const endpoint=read('app/api/scope-funnel/route.ts');
 assert.match(endpoint,/hasSession\(/);
 assert.match(endpoint,/view==="indications"/);
 assert.match(endpoint,/focusKeys\.has\(nct\+"\|"\+ticker\)/);
});
