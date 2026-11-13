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
  assert.match(html,/Current MAIN scope · 7 gates · Core Platform and Pipeline only/);
  assert.match(html,/Core Platform \(3\)/);
  assert.match(html,/Pipeline \(4\)/);
  assert.match(html,/other six former sections \(24 gates\)/);
  assert.match(html,/Final trial acceptance · 32 FOCUS trials only/);
  assert.match(html,/32 unique NCTs/);
  assert.match(html,/203 trial-specific evidence checks/);
  assert.match(html,/0 independently verified/);
  assert.match(html,/only trial records/);
  assert.doesNotMatch(html,/Current 31-gate scope/);
  assert.match(html,/7 active MAIN gates/);
  assert.match(html,/core-platform\.code/);
  assert.match(html,/core-platform\.runtime/);
  assert.match(html,/pipeline\.code/);
  assert.match(html,/pipeline\.deployment/);
  assert.match(html,/pipeline\.runtime/);
  assert.match(html,/pipeline\.evidence/);
  assert.doesNotMatch(html,/pool-focus\.exact-handoff|focus\.current-eligibility|focus\.nightly-sync|tools\.wt-runtime/);
  assert.doesNotMatch(html,/gem-jr-gem-wt|GEM JR|GEM 6/);
  assert.match(html,/core-platform\.deployment/);
  assert.doesNotMatch(html,/final-acceptance\.evidence|results-reporting\.code|investment-analysis\.code|regulatory-intelligence\.code|evidence-verification\.code/);
  assert.match(html,/6 without historical verification/);
  assert.match(html,/no archived scan is restored/);
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
  assert.equal(nav.split(' {label:"').length-1,10);
  assert.ok(nav.includes('{label:"COMPANY",href:"/company"}'));
  assert.ok(nav.includes('{label:"NEWS",href:"/news"}'));
  assert.ok(nav.includes('{label:"CAL",href:"/cal"}'));
  assert.ok(nav.indexOf('label:"CAL"')>nav.indexOf('label:"FOCUS"'));
  assert.ok(nav.indexOf('label:"CAL"')<nav.indexOf('label:"PREDICTIONS"'));
  assert.ok(nav.includes('{label:"ASSESMENTS",href:"/predictions/assessment"}'));
  assert.ok(nav.indexOf('label:"ASSESMENTS"')>nav.indexOf('label:"PREDICTIONS"'));
  assert.ok(nav.indexOf('label:"ASSESMENTS"')<nav.indexOf('label:"TOOLS"'));
  assert.ok(nav.includes('{label:"INSTALLATION",href:"/installation-audit"}'));
  assert.ok(nav.indexOf('label:"INSTALLATION"')>nav.indexOf('label:"TOOLS"'));
  assert.ok(nav.includes('{label:"PREDICTIONS",href:"/predictions"}'));
  assert.ok(home.includes('<Link href="/main">MAIN'));
  assert.ok(!nav.includes('label:"GEM"')&&!nav.includes('label:"TOP"'));
});
