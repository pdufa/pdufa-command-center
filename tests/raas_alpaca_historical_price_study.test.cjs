"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path");
const lib=require("../scripts/raas_alpaca_historical_price_study.cjs");
const root=path.resolve(__dirname,"..");
const top=JSON.parse(fs.readFileSync(path.join(root,"new-platform/frontend/data/raas-retrospective-top-cases.json"),"utf8"));
const bottom=JSON.parse(fs.readFileSync(path.join(root,"new-platform/frontend/data/raas-retrospective-source-cases.json"),"utf8"));
const cases=lib.originalWindows(top,bottom);
function dailyBars(win){
 const bars=[];
 for(let t=Date.parse(win.firstBarDate+"T00:00:00Z");
     t<=Date.parse(win.lastBarDate+"T00:00:00Z");t+=86400000){
  const d=new Date(t).toISOString().slice(0,10);
  const dow=new Date(t).getUTCDay();
  if(dow===0||dow===6)continue;
  const v=10+bars.length/100;
  bars.push({o:v,h:v+0.3,l:v-0.3,c:v+0.1,v:150000,t:d+"T00:00:00Z"});
 }
 return bars;
}
function response(w,bars,next=null){
 return {ok:true,status:200,headers:{get:x=>x==="content-type"?"application/json":null},
  text:async()=>JSON.stringify({symbol:w.ticker,bars,next_page_token:next})};
}
test("eight selected issuer+NCT windows stay research-only with actual date provenance",()=>{
 assert.equal(cases.length,8);
 assert.equal(cases.filter(x=>x.stage==="pre").length,3);
 assert.equal(cases.filter(x=>x.stage==="post").length,5);
 assert.equal(new Set(cases.map(x=>x.caseId)).size,8);
 assert.equal(new Set(cases.map(x=>x.ticker)).size,5);
 assert.ok(cases.every(x=>x.historicalCapOnlyAtSelectedEntry===true));
 assert.equal(cases.find(x=>x.ticker==="GERN"&&x.stage==="post").actualActionDate,"2024-06-06");
});
test("Alpaca request mandates SIP, 1Day, adjustment=all and historical ticker as-of, never IEX",async()=>{
 const w=cases.find(x=>x.ticker==="BBIO"&&x.stage==="pre");
 let called=false;
 await lib.downloadBars(w,"test-key","test-secret",async(url,opts)=>{
  called=true;
  const u=new URL(url);
  assert.equal(u.origin,"https://data.alpaca.markets");
  assert.equal(u.searchParams.get("timeframe"),"1Day");
  assert.equal(u.searchParams.get("feed"),"sip");
  assert.equal(u.searchParams.get("adjustment"),"all");
  assert.equal(u.searchParams.get("asof"),w.scheduledEventDate);
  assert.equal(u.searchParams.get("sort"),"asc");
  assert.equal(opts.headers["APCA-API-KEY-ID"],"test-key");
  assert.equal(opts.headers["APCA-API-SECRET-KEY"],"test-secret");
  return response(w,dailyBars(w));
 });
 assert.equal(called,true);
});
test("rejects invalid bars, wrong source identity and repeated sessions",()=>{
 const w=cases[0],bars=dailyBars(w);
 assert.ok(lib.parseBars({symbol:w.ticker,bars},w.ticker,w).length>30);
 assert.throws(()=>lib.parseBars({symbol:"WRONG",bars},w.ticker,w),
  /RAAS_ALPACA_RESPONSE_INVALID/);
 assert.throws(()=>lib.parseBars({symbol:w.ticker,bars:[bars[0],bars[0]]},w.ticker,w),
  /RAAS_ALPACA_DATE_OR_DUPLICATE_INVALID/);
 assert.throws(()=>lib.parseBars({symbol:w.ticker,bars:[{...bars[0],c:-3}]},w.ticker,w),
  /RAAS_ALPACA_BAR_INVALID/);
});
test("readout-dated TOP cannot enter before issuer guidance was available",()=>{
 const w=cases.find(x=>x.ticker==="GERN"&&x.stage==="pre");
 const bars=lib.parseBars({symbol:w.ticker,bars:dailyBars(w)},w.ticker,w);
 assert.equal(lib.studyWindow(w,bars,90,30).reason,
  "HISTORICAL_EVENT_NOT_YET_PUBLIC_AT_ENTRY");
 const usable=lib.studyWindow(w,bars,45,14);
 assert.equal(usable.status,"RETROSPECTIVE_PRICE_RESEARCH");
 assert.equal(usable.closeToCloseReturnPercent!==null,true);
 assert.equal(usable.afterAssumed1pctRoundTripCost,
  Math.round((usable.closeToCloseReturnPercent-1)*100)/100);
});
test("early FDA action censors later exits regardless of scheduled PDUFA",()=>{
 const w=cases.find(x=>x.ticker==="GERN"&&x.stage==="post");
 const bars=lib.parseBars({symbol:w.ticker,bars:dailyBars(w)},w.ticker,w);
 assert.equal(lib.studyWindow(w,bars,45,3).reason,
  "CENSORED_EARLY_FDA_OR_READOUT_ACTION");
 assert.equal(lib.studyWindow(w,bars,45,14).status,
  "RETROSPECTIVE_PRICE_RESEARCH");
});
test("no credentials means zero historical data rather than simulated returns",async()=>{
 const a=await lib.execute({key:"",secret:"",top,bottom});
 assert.equal(a.status,"BLOCKED_MISSING_ALPACA_CREDENTIALS");
 assert.equal(a.adjustedPricePoints,0);
 assert.equal(a.successfulCases,0);
 assert.equal(a.windowReturns.length,0);
 assert.equal(a.windowSummaries.length,0);
});
test("provider-denied bars do not silently fall back to IEX and falsely populate RAAS",async()=>{
 const result=await lib.execute({key:"k",secret:"s",top,bottom,
  request:async()=>({ok:false,status:403})});
 assert.equal(result.status,"PARTIAL_OR_BLOCKED");
 assert.equal(result.successfulCases,0);
 assert.equal(result.failures.length,8);
 assert.equal(result.windowReturns.length,0);
 assert.equal(result.adjustedPricePoints,0);
 assert.ok(result.failures.every(x=>x.reason==="RAAS_ALPACA_HTTP_403"));
});
test("synthetic provider fixture proves grid arithmetic but is never a real backtest",async()=>{
 let n=0;
 const result=await lib.execute({key:"test",secret:"test",top,bottom,
  request:async(url)=>{n++;const ticker=url.split("/stocks/")[1].split("/bars")[0];
   const params=new URL(url).searchParams;
   const win=cases.find(c=>c.ticker===ticker&&c.firstBarDate===params.get("start"));
   return response(win,dailyBars(win));}});
 assert.equal(n,8);
 assert.equal(result.status,"RESEARCH_PRICE_GRID_COLLECTED");
 assert.equal(result.successfulCases,8);
 assert.ok(result.windowReturns.length>100);
 assert.ok(result.windowSummaries.length>20);
 assert.ok(result.windowReturns.some(x=>x.reason==="CENSORED_EARLY_FDA_OR_READOUT_ACTION"));
 assert.ok(result.windowReturns.every(x=>!Object.hasOwn(x,"approvedRaasScore")));
 assert.ok(result.caveats.some(x=>x.includes("hindsight")));
});
