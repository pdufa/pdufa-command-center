const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const ts=require("typescript");
const React=require("react");
const {renderToStaticMarkup}=require("react-dom/server");
require.extensions[".tsx"]=(mod,file)=>mod._compile(ts.transpileModule(fs.readFileSync(file,"utf8"),{
 compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,
 jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}
}).outputText,file);
const {validAdvancedUniverseTotals,AdvancedUniverseTotalsView}=
 require("../app/AdvancedUniverseTotals.tsx");
function totals(){
 const levels=Object.fromEntries(Array.from({length:12},(_,i)=>[String(i+9),{active:5,deferred:0,reviewed:0}]));
 return {scope:"SCIENTIFIC_LEVELS_09_TO_20",methodVersion:"scientific-advanced-research-queue-v1",
  programs:2,readyPrograms:1,blockedPrograms:1,noActiveGapPrograms:0,
  activeTasks:60,deferredCriteria:0,reviewedCriteria:0,byLevel:levels};
}
test("whole-universe research counts render without FDA probability claim",()=>{
 const data=totals();assert.equal(validAdvancedUniverseTotals(data),true);
 const html=renderToStaticMarkup(React.createElement(AdvancedUniverseTotalsView,{data}));
 assert.match(html,/60 source-review tasks/);
 assert.match(html,/1 with unverified intake/);
 assert.match(html,/View Levels 9–20 backlog breakdown/);
 assert.match(html,/not scientific scores/);
 for(let l=9;l<=20;l++)assert.match(html,new RegExp("L"+String(l).padStart(2,"0")));
});
test("misleading or inconsistent aggregate values fail closed",()=>{
 for(const change of [
  d=>{d.programs=3;},
  d=>{d.activeTasks=55;},
  d=>{d.byLevel["19"].reviewed=1;},
  d=>{d.byLevel["15"].active=Number.NaN;},
  d=>{d.byLevel["12"].deferred=-1;},
  d=>{d.readyPrograms=999;},
  d=>{d.scope="FOCUS_ONLY";},
 ]){
  const data=totals();change(data);assert.equal(validAdvancedUniverseTotals(data),false);
 }
});
test("assessment page includes protected whole-universe totals widget",()=>{
 const page=fs.readFileSync(path.join(__dirname,"../app/assessments/page.tsx"),"utf8");
 assert.match(page,/import AdvancedUniverseTotals/);
 assert.match(page,/<AdvancedUniverseTotals\\s*\\/>/);
});
