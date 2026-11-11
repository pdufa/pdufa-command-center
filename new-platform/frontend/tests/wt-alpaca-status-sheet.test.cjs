"use strict";
const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const ts=require("typescript");
const React=require("react");
const {renderToStaticMarkup}=require("react-dom/server");

for(const ext of [".ts",".tsx"]){
 require.extensions[ext]=(mod,filename)=>{
  const compiled=ts.transpileModule(fs.readFileSync(filename,"utf8"),{
   compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,
    jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true},
  }).outputText;
  mod._compile(compiled,filename);
 };
}

const StatusSheet=require("../app/WtAlpacaStatusSheet.tsx").default;
const {WT_ETRADE_CANDIDATES}=require("../lib/wt-etrade-order-draft.ts");

test("WT exposes a dedicated status route with each exact ticker and permanent program",()=>{
 const route=fs.readFileSync(path.join(__dirname,"../app/wt/status/page.tsx"),"utf8");
 const wt=fs.readFileSync(path.join(__dirname,"../app/WtEtradeOrderPrep.tsx"),"utf8");
 assert.match(route,/WtAlpacaStatusSheet/);
 assert.match(wt,/href="\/wt\/status"/);
 assert.match(wt,/\/wt\/status#/);
 assert.deepEqual(WT_ETRADE_CANDIDATES.map(x=>x.ticker),["SVRA","CAPR"]);
 const html=renderToStaticMarkup(React.createElement(StatusSheet));
 assert.match(html,/WT · Alpaca ticker status sheets/);
 for(const candidate of WT_ETRADE_CANDIDATES){
  assert.match(html,new RegExp("id=\""+candidate.ticker+"\""));
  assert.ok(html.includes(candidate.programId));
  assert.ok(html.includes(candidate.nct));
  assert.match(html,new RegExp("aria-label=\""+candidate.ticker+" actual, threshold and status metrics\""));
 }
});
test("Every ticker displays eight independent rows with actual, threshold and status columns",()=>{
 const html=renderToStaticMarkup(React.createElement(StatusSheet));
 assert.equal((html.match(/Not evaluable without verified Alpaca history/g)||[]).length,16);
 assert.equal((html.match(/>UNAVAILABLE<\/strong>/g)||[]).length>=16,true);
 for(const label of [
  "10-session base","Stabilizing lows","Confirmed close above trigger",
  "Positive moving-average trend","Relative volume (RVOL20)",
  "RSI14 momentum","20-day average dollar volume","ATR14 daily volatility",
  "Actual reading","BUY requirement","Status",
 ])assert.ok(html.includes(label),label);
 assert.match(html,/FOCUS snapshot/);
 assert.match(html,/Alpaca completed daily OHLCV/);
});
test("Unknown data is not displayed as a passing or failing signal",()=>{
 const html=renderToStaticMarkup(React.createElement(StatusSheet));
 assert.match(html,/LOADING ALPACA/);
 assert.doesNotMatch(html,/TECHNICAL BUY SETUP/);
 assert.match(html,/No verified|UNAVAILABLE/i);
});
test("Status screen is read only, refreshes authenticated Alpaca exact-program data, and never connects to E*TRADE trading",()=>{
 const src=fs.readFileSync(path.join(__dirname,"../app/WtAlpacaStatusSheet.tsx"),"utf8");
 assert.match(src,/data-wt-status-sheet="read-only"/);
 assert.match(src,/fetch\("\/api\/alpaca-chart\//);
 assert.match(src,/encodeURIComponent\(candidate.programId\)/);
 assert.match(src,/received.programId!==candidate.programId/);
 assert.match(src,/received.ticker!==candidate.ticker/);
 assert.match(src,/cache:"no-store"/);
 assert.match(src,/setInterval\(\(\)=>void refresh\(\),300000\)/);
 assert.match(src,/NO ORDERS/);
 assert.match(src,/NOT AUTHORIZED · NOT PREVIEWED · NOT SUBMITTED/);
 assert.doesNotMatch(src,/\/orders\/(?:preview|place|cancel)/);
 assert.doesNotMatch(src,/method:\s*["']POST/);
 assert.doesNotMatch(src,/ALPACA_SECRET_KEY|ETRADE_SANDBOX_CONSUMER_SECRET/);
});
