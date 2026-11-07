const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const ts=require("typescript");
const React=require("react");
const {renderToStaticMarkup}=require("react-dom/server");

for(const extension of [".ts",".tsx"]){
  require.extensions[extension]=(module,filename)=>module._compile(
    ts.transpileModule(fs.readFileSync(filename,"utf8"),{
      compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,
        jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}
    }).outputText,filename);
}

test("MAIN status page reports dated release proof without promoting old installation gates",()=>{
  const Page=require("../app/main/page.tsx").default;
  const html=renderToStaticMarkup(React.createElement(Page)).split("<!-- -->").join("");
  assert.match(html,/MAIN · Technical status and prediction readiness/);
  assert.match(html,/November 7, 2026/);
  assert.match(html,/87654a48/);
  assert.match(html,/Production deployment: READY/);
  assert.match(html,/Verified production runtime smoke/);
  assert.match(html,/42394008611/);
  assert.match(html,/2,698 of 11,644/);
  assert.match(html,/<strong>not<\/strong> 2,698 completed/);
  assert.match(html,/not.*complete technical acceptance/);
  assert.match(html,/1 of 31/);
  assert.match(html,/Current 31-gate scope · final FOCUS trials only/);
  assert.match(html,/Final trial acceptance · 29 FOCUS trials only/);
  assert.match(html,/29 unique NCTs/);
  assert.match(html,/203 trial-specific evidence checks/);
  assert.match(html,/0 independently verified/);
  assert.match(html,/only trial records/);
  assert.doesNotMatch(html,/Current 31-gate scope · POOL \/ FOCUS \/ TOOLS/);
  assert.match(html,/pool-focus\.exact-handoff/);
  assert.match(html,/focus\.current-eligibility/);
  assert.match(html,/focus\.nightly-sync/);
  assert.match(html,/tools\.wt-runtime/);
  assert.match(html,/31 applicable checks/);
  assert.doesNotMatch(html,/gem-jr-gem-wt|GEM JR|GEM 6/);
  assert.match(html,/core-platform\.deployment/);
  assert.match(html,/final-acceptance\.evidence/);
  assert.match(html,/30 requiring fresh verification/);
  assert.match(html,/No archived scan is restored/);
  assert.match(html,/2026-10-26/);
  assert.match(html,/Still open/);
  assert.match(html,/Not certified/);
  assert.match(html,/ABSTAIN/);
  assert.match(html,/not a third active trial list/);
  assert.match(html,/UNKNOWN/);
  assert.match(html,/No scan is dispatched/);
  assert.doesNotMatch(html,/FDA approval probability.*\d+%/);
});

test("MAIN is reachable without adding a new active population tab",()=>{
  const nav=fs.readFileSync(path.join(__dirname,"../app/GlobalNavigation.tsx"),"utf8");
  const home=fs.readFileSync(path.join(__dirname,"../app/page.tsx"),"utf8");
  for(const entry of ['{label:"POOL",href:"/pool"}','{label:"FOCUS",href:"/focus"}',
    '{label:"TOOLS",href:"/tools"}']) assert.ok(nav.includes(entry),entry);
  assert.equal(nav.split(' {label:"').length-1,3);
  assert.ok(home.includes('<Link href="/main">MAIN'));
  assert.ok(!nav.includes('label:"GEM"')&&!nav.includes('label:"TOP"'));
});
