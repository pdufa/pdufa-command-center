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
  const html=renderToStaticMarkup(React.createElement(Page));
  assert.match(html,/MAIN · Technical status and prediction readiness/);
  assert.match(html,/November 7, 2026/);
  assert.match(html,/87654a48/);
  assert.match(html,/Production deployment: READY/);
  assert.match(html,/1 of 31/);
  assert.match(html,/2026-10-26/);
  assert.match(html,/Still open/);
  assert.match(html,/Not certified/);
  assert.match(html,/ABSTAIN/);
  assert.match(html,/not a third active trial list/);
  assert.match(html,/UNKNOWN/);
  assert.match(html,/No scan is dispatched/);
  assert.doesNotMatch(html,/FDA approval probability.*\d+%/);
});

test("MAIN navigation is a control page and the two active population routes are preserved",()=>{
  const source=fs.readFileSync(path.join(__dirname,"../app/GlobalNavigation.tsx"),"utf8");
  for(const entry of ['{label:"POOL",href:"/pool"}','{label:"FOCUS",href:"/focus"}',
    '{label:"MAIN",href:"/main"}'])assert.ok(source.includes(entry),entry);
  assert.ok(!source.includes('label:"GEM"')&&!source.includes('label:"TOP"'));
});
