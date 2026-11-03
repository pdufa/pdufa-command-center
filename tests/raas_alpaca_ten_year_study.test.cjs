"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path");
const m=require("../scripts/raas_alpaca_ten_year_study.cjs");
const root=path.resolve(__dirname,"..");
const intake=JSON.parse(fs.readFileSync(path.join(root,
 "new-platform/frontend/data/raas-ten-year-pdufa-intake.json"),"utf8"));
const csv=fs.readFileSync(path.join(root,"data/historical_assessed_decisions.csv"),"utf8");
function fixture(event="2019-07-03",ticker="TEST"){
 const bars=[];
 const end=Date.parse(event+"T00:00:00Z");
 for(let t=end-100*86400000;t<=end;t+=86400000) {
  const day=new Date(t),dow=day.getUTCDay();
  if(dow===0||dow===6)continue;
  const d=day.toISOString().slice(0,10),n=bars.length;
  const c=10+n*.1;
  bars.push({date:d,open:c-.1,high:c+.2,low:c-.3,close:c,volume:1000});
 }
 const caps=bars.map(b=>({session:b.date,usdMillions:1250,
  sharesSourcePublishedAt:"2018-01-01",
  sourceUrl:"https://example.org/historical-cap",
  sharesSourceUrl:"https://example.org/dated-shares"}));
 return {caseId:"test-one",ticker,programId:"trial-drug-indication",nctIds:["NCT12345678"],
  pdufaDate:event,pdufaFirstPublicDate:"2018-09-01",
  pdufaSourceUrl:"https://example.org/dated-pdufa-announcement",
  phase3ReadoutDate:"2018-05-01",
  phase3SourceUrl:"https://example.org/dated-phase3-readout",
  actualFDAActionDate:event,
  actualFDAActionSourceUrl:"https://example.org/fda-action",reviewStatus:"SOURCE_REVIEWED",
  historicalMarketCaps:caps,bars};
}
function response(ticker,bars){
 return {ok:true,headers:{get:()=>"application/json"},
  text:async()=>JSON.stringify({symbol:ticker,bars:bars.map(b=>({
   o:b.open,h:b.high,l:b.low,c:b.close,v:b.volume,t:b.date+"T00:00:00Z"
  })),next_page_token:null})};
}
test("all ten years are explicitly incomplete; archive cases never become verified trades",()=>{
 const discovery=m.candidateQueue(csv);
 assert.ok(discovery.length>20,"archive should contain multiple FDA candidate events");
 assert.ok(discovery.every(x=>x.pdufaDate>="2016-01-01"&&x.pdufaDate<="2025-12-31"));
 assert.ok(discovery.every(x=>x.evidenceStatus==="ARCHIVE_CANDIDATE_NOT_SOURCE_VERIFIED"));
 assert.equal(m.intakeRecords(intake).accepted.length,0);
 assert.equal(m.intakeRecords(intake).complete,false);
 assert.equal(m.chooseWindow([],false).winner,null);
});
test("PDUFA, Phase3 publication, exact historical cap and audit are all required",()=>{
 const good=fixture();
 assert.equal(m.validRecord(good),true);
 assert.equal(m.validRecord({...good,reviewStatus:"DISCOVERY"}),false);
 assert.equal(m.validRecord({...good,nctIds:["BAD"]}),false);
 assert.equal(m.validRecord({...good,pdufaFirstPublicDate:null}),false);
 assert.equal(m.validRecord({...good,historicalMarketCaps:[{
  ...good.historicalMarketCaps[0],sharesSourcePublishedAt:"2020-01-01"
 }]}),false);
 const x=m.intakeRecords({...intake,records:[good]});
 assert.equal(x.accepted.length,1);
 assert.equal(x.complete,false);
});
test("full T-90 through T-3 grid uses calendar-day offsets, exact daily cap and cost",()=>{
 const f=fixture(),bars=f.bars;
 assert.equal(m.grid(f,bars).length,3828);
 const x=m.windowPrice(f,bars,60,14);
 assert.equal(x.status,"POINT_IN_TIME_PRICE_RESEARCH");
 assert.ok(x.grossReturnPct>0);
 assert.equal(x.netReturnPct,Math.round((x.grossReturnPct-1)*100)/100);
 assert.equal(x.marketCapAtEntryMillions,1250);
});
test("blocks missing caps and cap outside $300M-$10B at entry",()=>{
 const a=fixture(),bars=a.bars;
 a.historicalMarketCaps=[];
 assert.equal(m.windowPrice(a,bars,60,14).reason,
  "MISSING_ENTRY_DAY_HISTORICAL_MARKET_CAP");
 a.historicalMarketCaps=fixture().historicalMarketCaps.map(x=>({...x,usdMillions:299}));
 assert.equal(m.windowPrice(a,bars,60,14).reason,
  "HISTORICAL_CAP_OUT_OF_300M_10B_RANGE");
});
test("blocks look-ahead PDUFA or Phase3 knowledge and early FDA decision",()=>{
 const a=fixture(),bars=a.bars;
 a.pdufaFirstPublicDate="2019-07-02";
 assert.equal(m.windowPrice(a,bars,60,14).reason,"EVENT_NOT_PUBLIC_AT_ENTRY");
 a.pdufaFirstPublicDate="2018-09-01";
 a.actualFDAActionDate="2019-05-01";
 assert.equal(m.windowPrice(a,bars,60,14).reason,"FDA_ACTION_EARLIER_THAN_EXIT");
});
test("never claims optimal holdout window without full census and 30 distinct issuers",()=>{
 const rows=[{caseId:"case",ticker:"TST",entryDate:"2019-05-01",year:2019,
  entryLeadDays:79,exitLeadDays:14,netReturnPct:12,
  status:"POINT_IN_TIME_PRICE_RESEARCH"}];
 assert.equal(m.chooseWindow(rows,false).winner,null);
 assert.equal(m.chooseWindow(rows,true).winner,null);
 assert.equal(m.chooseWindow(rows,true).status,"BLOCKED_INSUFFICIENT_ISSUER_DISJOINT_SAMPLE");
});
test("event archive can download adjusted prices but cannot silently score ineligible research",async()=>{
 const f=fixture();
 const c=[{ticker:f.ticker,pdufaDate:f.pdufaDate,eventKey:"TEST|2019-07-03|drug"}];
 const run=await m.execute({key:"fake",secret:"fake",candidates:c,intake,
  request:async(url,opts)=>{
   const u=new URL(url);
   assert.equal(u.searchParams.get("feed"),"sip");
   assert.equal(u.searchParams.get("adjustment"),"all");
   assert.equal(u.searchParams.get("asof"),f.pdufaDate);
   assert.equal(opts.headers["APCA-API-KEY-ID"],"fake");
   return response(f.ticker,f.bars);
  }});
 assert.equal(run.priceEventKeysCollected,1);
 assert.equal(run.historicalDailyBarsCollected,f.bars.length);
 assert.equal(run.eligibleWindowRows,0);
 assert.equal(run.selectedWindow.winner,null);
 assert.equal(run.status,"PARTIAL_CENSUS_RESEARCH_ONLY");
});
test("one reviewed synthetic issuer yields grid research, never a ten-year winner",async()=>{
 const f=fixture(), {bars,...record}=f;
 const res=await m.execute({key:"fake",secret:"fake",candidates:[],
  intake:{...intake,records:[record]},request:async()=>response(f.ticker,bars)});
 assert.equal(res.reviewedEvents,1);
 assert.ok(res.eligibleWindowRows>100);
 assert.equal(res.selectedWindow.winner,null);
 assert.equal(res.tenYearCensusComplete,false);
});
