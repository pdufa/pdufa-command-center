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
const {default:Chart,StockPlot}=require("../app/AlpacaStockChart.tsx");
const chartSource=fs.readFileSync(path.join(__dirname,"../app/AlpacaStockChart.tsx"),"utf8");
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
test("WT indicators are selected by exact Program ID and never leak into another trial's chart",()=>{
 assert.match(workspace,/const preference=wtTrialPreferences\[programId\]\|\|emptyWtPreference\(\)/);
 assert.match(workspace,/const selectedStage=preference\.stage/);
 assert.match(workspace,/const chartIndicatorKeys=selectedStage\?preference\.keys\[selectedStage\]:\[\]/);
 assert.match(workspace,/wtIndicatorKeys=\{chartIndicatorKeys\}/);
 assert.match(workspace,/changeWtTrialIndicators\(programId,selectedStage,keys\)/);
 assert.match(workspace,/id=\{"wt-chart-"\+programId\}/);
 assert.match(workspace,/WT_TRIAL_INDICATORS_KEY/);
 assert.match(workspace,/window\.localStorage\.setItem\(/);
 assert.match(workspace,/readWtPreferences\(window\.localStorage\.getItem\(/);
 assert.match(workspace,/\^PDUFA-\\d\{6,\}\$/);
 assert.doesNotMatch(workspace,/<WtTopChecklist programs=/);
 assert.match(sections,/onChange=\{e=>updateChecked\(/);
 assert.match(sections,/chartDescriptionForWtCheck\(item\.key\)/);
 assert.match(sections,/onClick=\{\(\)=>updateChecked\(\[\]\)\}/);
 assert.doesNotMatch(sections,/method:"POST"/);
});

test("Zero selections hide every technical study, volume pane and range line but retain price candles",()=>{
 const bars=Array.from({length:12},(_,i)=>({
  date:"2026-10-"+String(i+1).padStart(2,"0"),
  open:10+i*.1,high:11+i*.1,low:9+i*.1,close:10.5+i*.1,
  volume:1000+i*40,sma20:10,sma50:10,ema10:10,ema20:10,ema50:10,
  rsi:55,macd:1,signal:.5,atr:.4
 }));
 const bare=renderToStaticMarkup(React.createElement(StockPlot,{
  bars,large:true,candle:true,visibleStudies:new Set()
 }));
 assert.match(bare,/Alpaca daily price only/);
 assert.match(bare,/aria-label="Alpaca daily price only/);
 assert.doesNotMatch(bare,/RSI14:|MACD\(|ATR14:|Daily volume|Prior 10D/);
 assert.match(bare,/<rect /,"Candlesticks are not removed when indicators are off");
 const overlay=renderToStaticMarkup(React.createElement(StockPlot,{
  bars,large:true,candle:true,visibleStudies:new Set(["sma20","rsi","volume","atr","range"])
 }));
 assert.match(overlay,/RSI14:/);
 assert.match(overlay,/ATR14:/);
 assert.match(overlay,/Daily volume/);
 assert.match(overlay,/Prior 10D high/);
 assert.doesNotMatch(overlay,/MACD\(/);
});
test("WT readout badges are displayed only for checked chartable indicators",()=>{
 assert.match(chartSource,/visibleReadouts=studyReadouts\.filter\(\(\[key\]\)=>!wtControlled\|\|visibleStudies\.has\(key\)\)/);
 assert.match(chartSource,/expanded&&visibleReadouts\.length>0&&/);
 assert.match(chartSource,/wtControlled\?chartStudiesForWtChecks\(wtIndicatorKeys\):studies\?DEFAULT_SERIES:\[\]/);
 assert.ok(!workspace.includes("wtChartSelection.keys:undefined"),"Every WT stock chart must have explicit empty array fallback");
});

test("Alpaca lines carry readable names at their endpoints without inventing hidden studies",()=>{
 const bars=Array.from({length:80},(_,i)=>({
   date:new Date(Date.UTC(2026,6,1+i)).toISOString().slice(0,10),
   open:15+i*.04,high:16+i*.04,low:14+i*.04,close:15.4+i*.04,
   volume:150000+i*100,sma20:15.1+i*.04,sma50:14.9+i*.04,
   ema10:15.5+i*.04,ema20:15.2+i*.04,ema50:15+i*.04,
   rsi:55,macd:.45,signal:.4,atr:.65
 }));
 const active=renderToStaticMarkup(React.createElement(StockPlot,{
   bars,large:true,candle:true,
   visibleStudies:new Set(["sma20","sma50","ema10","ema20","ema50","range","rsi","macd","atr"])
 }));
 for(const label of ["SMA20","SMA50","EMA10","EMA20","EMA50","Prior 10D high","Prior 10D low"]){
   assert.match(active,new RegExp('>'+label+'<\\/text>'),"Line should be named directly: "+label);
 }
 for(const label of ["RSI14","MACD","Signal","ATR14"]){
   assert.match(active,new RegExp('>'+label+'<\\/text>'),"Subpanel line should be named directly: "+label);
 }
 assert.match(active,/paint-order="stroke"/,"Visible text halo over busy chart");
 const none=renderToStaticMarkup(React.createElement(StockPlot,{
   bars,large:true,candle:true,visibleStudies:new Set()
 }));
 for(const name of ["SMA20","SMA50","EMA10","EMA20","Prior 10D high","ATR14"]){
   assert.doesNotMatch(none,new RegExp('>'+name+'<\\/text>'),"No label for hidden study "+name);
 }
 const price=renderToStaticMarkup(React.createElement(StockPlot,{
   bars,large:true,candle:false,visibleStudies:new Set()
 }));
 assert.match(price,/>PRICE<\/text>/,"Line mode names the price itself");
});
