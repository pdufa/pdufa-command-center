const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const ts=require("typescript");
const React=require("react");
const {renderToStaticMarkup}=require("react-dom/server");

const root=path.resolve(__dirname,"..");
const roster=JSON.parse(fs.readFileSync(path.join(root,"data/p3PostDataActive.json"),"utf8"));
const component=path.join(root,"app/predictions/FocusPredictionNavigator.tsx");
require.extensions[".css"]=(module)=>{module.exports=new Proxy({}, {get:(_obj,key)=>String(key)});};
require.extensions[".tsx"]=(module,filename)=>module._compile(ts.transpileModule(
  fs.readFileSync(filename,"utf8"),{compilerOptions:{
    module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,
    jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true
  }}
).outputText,filename);

test("prediction navigator uses only uniquely identified FOCUS rows",()=>{
  const source=fs.readFileSync(component,"utf8");
  assert.match(source,/import focusRoster from "\.\.\/\.\.\/data\/p3PostDataActive\.json"/);
  assert.equal(new Set(roster.records.map(r=>r.nct)).size,roster.records.length);
  assert.ok(roster.records.every(r=>/^NCT\d{8}$/.test(r.nct)));
  assert.ok(roster.records.every(r=>/^[A-Z0-9.-]+$/.test(r.ticker)));
  const symbols=new Set(roster.records.map(r=>r.ticker));
  const html=renderToStaticMarkup(React.createElement(require(component).default));
  const firstTicker=Array.from(symbols).sort((a,b)=>a.localeCompare(b))[0];
  const initialTrialButtons=roster.records.filter(r=>r.ticker===firstTicker).length;
  assert.equal((html.match(/aria-pressed="(?:true|false)"/g)||[]).length,symbols.size+initialTrialButtons);
  for(const ticker of symbols)assert.ok(html.includes(">"+ticker+"</strong>"),"Ticker missing: "+ticker);
  assert.match(html,new RegExp(roster.records.length+"<!-- --> exact-NCT trials|"+roster.records.length+" exact-NCT trials"));
  assert.match(html,/aria-label="Previous FOCUS ticker"/);
  assert.match(html,/aria-label="Next FOCUS ticker"/);
});

test("each exact-NCT choice preserves abstention and no invented numerical odds",()=>{
  const source=fs.readFileSync(component,"utf8");
  assert.match(source,/onClick=\{\(\)=>chooseTicker\(group\.ticker\)\}/);
  assert.match(source,/onClick=\{\(\)=>setNct\(row\.nct\)\}/);
  assert.match(source,/selectedGroup\?\.trials\.map\(/);
  assert.match(source,/FDA Approval/);
  assert.match(source,/Complete Response Letter \(CRL\)/);
  assert.match(source,/FDA Review Delay \/ Extension/);
  assert.match(source,/ABSTAIN/);
  assert.match(source,/NOT VALIDATED/);
  assert.match(source,/recordedPdufaDate/);
  assert.doesNotMatch(source,/approvalProbability:\s*\d|certaintyPercent:\s*\d/);
  const page=fs.readFileSync(path.join(root,"app/predictions/page.tsx"),"utf8");
  assert.match(page,/<FocusPredictionNavigator\/>/);
  assert.match(page,/No numerical forecast has been prospectively calibrated or released/);
});
