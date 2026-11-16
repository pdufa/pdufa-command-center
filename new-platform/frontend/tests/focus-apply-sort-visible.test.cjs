const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const ts=require('typescript');
for(const ext of ['.ts','.tsx'])require.extensions[ext]=(mod,file)=>mod._compile(ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}}).outputText,file);
const {sortNumericRows}=require('../app/NumericSortSettings.tsx');
const snapshot=require('../data/focus123EvidenceReadiness20261115.json');
const main=fs.readFileSync(path.join(__dirname,'../app/focus/page.tsx'),'utf8');
const popup=fs.readFileSync(path.join(__dirname,'../app/NumericSortSettings.tsx'),'utf8');

test('FOCUS sort popup defaults to high→low and dropdown fits iPhone width without clipping',()=>{
 assert.match(popup,/scope==="focus"\?"desc":"asc"/);
 assert.match(popup,/width:"min\(460px,100%\)",maxWidth:"100%",boxSizing:"border-box"/);
 assert.match(popup,/aria-label="Column to sort"/);
 assert.match(popup,/display:"block",width:"100%",maxWidth:"100%"/);
 assert.match(popup,/onApply\(next\)/);
});
test('Apply Sort and one-tap Overall button show a real active-sort status and navigate to visible results',()=>{
 assert.match(main,/onApply=\{applyFocusSort\}/);
 assert.match(main,/onClick=\{\(\)=>applyFocusSort\(\[\{column:"overall"/);
 assert.match(main,/window\.requestAnimationFrame\(\(\)=>window\.requestAnimationFrame\(/);
 assert.match(main,/document\.getElementById\('focus-sort-feedback'\)\?\.scrollIntoView/);
 assert.match(main,/tableScrollRef\.current\?\.scrollTo\(\{left:0,behavior:'auto'\}\)/);
 assert.match(main,/id="focus-sort-feedback" data-testid="focus-sort-feedback" role="status"/);
 assert.match(main,/aria-live="polite"/);
 assert.match(main,/Sort applied:/);
 assert.match(main,/data-testid="focus-sort-confirmation-rows"/);
 assert.ok(main.indexOf('id="focus-sort-feedback"')<main.indexOf('data-testid="focus-mobile-score-view"'));
});
test('Numerical FOCUS Overall sorted high→low changes first row, and Low→High is confirmed',()=>{
 const map=new Map();
 for(const r of snapshot.rows){
  const prior=map.get(r.nct)||[];
  prior.push(r);map.set(r.nct,prior);
 }
 const records=[...map].map(([nct,parts])=>({nct,ticker:'x',value:Math.round(100*parts.reduce((s,x)=>s+x.sourceVerified,0)/parts.reduce((s,x)=>s+x.applicable,0))}));
 assert.equal(records.length,32);
 const desc=sortNumericRows(records,[{column:'overall',direction:'desc'}],(r)=>r.value,r=>r.nct);
 const asc=sortNumericRows(records,[{column:'overall',direction:'asc'}],(r)=>r.value,r=>r.nct);
 assert.equal(desc[0].value,82);
 assert.equal(asc[0].value,48);
 assert.ok(desc.every((v,i)=>i===0||desc[i-1].value>=v.value));
 assert.ok(asc.every((v,i)=>i===0||asc[i-1].value<=v.value));
});
