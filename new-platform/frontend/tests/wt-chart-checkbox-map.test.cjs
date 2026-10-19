const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const ts=require("typescript");
const React=require("react");
const {renderToStaticMarkup}=require("react-dom/server");
for(const ext of [".ts",".tsx"]){
 require.extensions[ext]=(loaded,file)=>{
  const out=ts.transpileModule(fs.readFileSync(file,"utf8"),{
   compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,
    jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}
  }).outputText;
  loaded._compile(out,file);
 };
}
const map=require("../lib/wt-chart-indicator-map.ts");
const {WT_CHECK_KEYS}=require("../lib/wt-entry-stay-exit.ts");
const Chart=require("../app/AlpacaStockChart.tsx").default;
const workspace=fs.readFileSync(path.join(__dirname,"../app/Workspace.tsx"),"utf8");
const sections=fs.readFileSync(path.join(__dirname,"../app/WtTradingSections.tsx"),"utf8");
const top=fs.readFileSync(path.join(__dirname,"../app/WtTopChecklist.tsx"),"utf8");

test("All chart mappings are existing ENTRY STAY EXIT checkboxes, deduplicated in a deterministic overlay order",()=>{
 const checkKeys=new Set(WT_CHECK_KEYS);
 assert.equal(WT_CHECK_KEYS.length,26);
 for(const [key,studies] of Object.entries(map.WT_CHECK_TO_STUDIES)){
  assert.ok(checkKeys.has(key),"Unknown checkbox "+key);
  assert.ok(studies.length>0,key);
  for(const study of studies)assert.ok(map.WT_CHART_STUDIES.includes(study),"Unknown chart study "+study);
 }
 assert.deepEqual(map.chartStudiesForWtChecks([]),[]);
 assert.deepEqual(map.chartStudiesForWtChecks(["entry-trend"]),["sma20","sma50"]);
 assert.deepEqual(map.chartStudiesForWtChecks(["entry-trend","stay-trend","exit-two-close"]),["sma20","sma50"]);
 assert.deepEqual(map.chartStudiesForWtChecks(["entry-base","stay-rsi","entry-atr","entry-rvol"]),
  ["rsi","volume","atr","range"]);
});
test("Non-chartable risk, financing, FDA dates, entry stops, STAY and unvalidated plateau do not invent overlays",()=>{
 const dataOnly=["entry-score","entry-dollar","entry-trigger","entry-stop","stay-trailing",
  "stay-pdufa","stay-signal","exit-score","exit-plateau","exit-pdufa","exit-action"];
 assert.deepEqual(map.chartStudiesForWtChecks(dataOnly),[]);
 for(const key of dataOnly){
  assert.equal(map.WT_CHECK_TO_STUDIES[key],undefined);
  assert.match(map.chartDescriptionForWtCheck(key),/Research data only/);
 }
 assert.deepEqual(map.chartStudiesForWtChecks(["exit-atr-trail"]),["atr"]);
 assert.match(map.chartDescriptionForWtCheck("exit-atr-trail"),/no trailing stop/);
 assert.match(map.chartDescriptionForWtCheck("entry-rvol"),/not a verified RVOL/);
 assert.match(map.chartDescriptionForWtCheck("exit-support"),/not confirmed support/);
});
test("Exact-program controlled WT chart has no studies with no selected checkboxes",()=>{
 const empty=renderToStaticMarkup(React.createElement(Chart,{
   programId:"PDUFA-000123",ticker:"TEST",wtIndicatorKeys:[]
 }));
 assert.match(empty,/No studies selected/);
 assert.match(empty,/price chart only/);
 assert.doesNotMatch(empty,/HIDE STUDIES/);
 const active=renderToStaticMarkup(React.createElement(Chart,{
   programId:"PDUFA-000123",ticker:"TEST",wtIndicatorKeys:["entry-trend","entry-rsi","entry-atr"]
 }));
 assert.match(active,/SMA20/);
 assert.match(active,/SMA50/);
 assert.match(active,/RSI14/);
 assert.match(active,/ATR14/);
 assert.doesNotMatch(active,/HIDE STUDIES/);
 const normal=renderToStaticMarkup(React.createElement(Chart,{
   programId:"PDUFA-000456",ticker:"OTHER"
 }));
 assert.match(normal,/HIDE STUDIES/);
});
test("Main WT checkboxes target only the matching program chart, never a saved stage or a broker order",()=>{
 assert.match(workspace,/setWtChartSelection\(\{programId,keys\}\)/);
 assert.match(workspace,/wtIndicatorKeys=\{wtChartSelection\.programId===programId\?wtChartSelection\.keys:undefined\}/);
 assert.match(workspace,/id=\{"wt-chart-"\+programId\}/);
 assert.match(top,/onChartControlsChange\?\.\(id,\[\]\)/);
 assert.match(top,/onCheckedKeysChange=\{keys=>/);
 assert.match(sections,/onChange=\{e=>updateChecked\(/);
 assert.match(sections,/chartDescriptionForWtCheck\(item\.key\)/);
 assert.match(sections,/onClick=\{\(\)=>updateChecked\(\[\]\)\}/);
 assert.doesNotMatch(sections,/method:"POST"/);
});
