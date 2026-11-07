const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const app=path.resolve(__dirname,"../app");
const read=(name)=>fs.readFileSync(path.join(app,name),"utf8");

test("every POOL and FOCUS ticker cell uses the shared chart button",()=>{
 const pool=read("PoolMasterSpreadsheet.tsx");
 const focus=read("p3-post-data/page.tsx");
 assert.match(pool, /<TickerChartButton ticker=\{row\.ticker\}\/>/);
 assert.match(focus, /<TickerChartButton ticker=\{t\.ticker\}\/>/);
});

test("ticker chart is an in-page dialog, not an external window",()=>{
 const component=read("TickerChartButton.tsx");
 assert.match(component,/createPortal\(/);
 assert.match(component,/aria-modal="true"/);
 assert.match(component,/onClick=\{close\}/);
 assert.doesNotMatch(component,/window\.open\(/);
});

test("unregistered tickers use authenticated Alpaca-only chart route",()=>{
 const chart=read("AlpacaStockChart.tsx");
 const api=read("api/alpaca-ticker/[ticker]/route.ts");
 assert.match(chart,/\/api\/alpaca-ticker\//);
 assert.match(api,/hasSession/);
 assert.match(api,/x-pdufa-internal-key/);
});
