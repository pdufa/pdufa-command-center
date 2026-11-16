const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const ts=require('typescript');
for(const ext of ['.ts','.tsx'])require.extensions[ext]=(mod,file)=>mod._compile(
 ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{
  module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true
 }}).outputText,file
);
const {sortNumericRows}=require('../app/NumericSortSettings.tsx');
const snapshot=require('../data/focus123EvidenceReadiness20261115.json');
test('Overall Score is first FOCUS sort-popup option and has an explicit one-tap sort button',()=>{
 const code=fs.readFileSync(path.join(__dirname,'../app/focus/page.tsx'),'utf8');
 assert.match(code,/columns=\{\[\{id:"overall",label:"Overall prediction survey result — Evidence Readiness \/100"/);
 assert.match(code,/data-testid="focus-overall-sort-control"/);
 assert.match(code,/Sort Overall Score: High → Low/);
 assert.match(code,/Overall Score: Low → High/);
 assert.match(code,/sortNumericRows\(trials,sortRules/);
 assert.match(code,/if\(c==="overall"\)return savedScores\[t.nct\]\?\.overall\?\?null/);
});
test('Overall sorting uses exact NCT and numeric pooled check-weighted values in both directions',()=>{
 const grouped=new Map();
 for(const r of snapshot.rows){
  if(!grouped.has(r.nct))grouped.set(r.nct,[]);
  grouped.get(r.nct).push(r);
 }
 const records=[...grouped].map(([nct,levels])=>{
  assert.equal(levels.length,3);
  const good=levels.reduce((sum,x)=>sum+x.sourceVerified,0);
  const applicable=levels.reduce((sum,x)=>sum+x.applicable,0);
  return {nct,overall:Math.round(100*good/applicable)};
 });
 assert.equal(records.length,32);
 const get=(r,c)=>c==='overall'?r.overall:null;
 const desc=sortNumericRows(records,[{column:'overall',direction:'desc'}],get,r=>r.nct);
 const asc=sortNumericRows(records,[{column:'overall',direction:'asc'}],get,r=>r.nct);
 assert.equal(desc[0].overall,82);
 assert.equal(asc[0].overall,48);
 assert.ok(desc.every((v,i)=>i===0||desc[i-1].overall>=v.overall));
 assert.ok(asc.every((v,i)=>i===0||asc[i-1].overall<=v.overall));
});
