"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path");
const m=require("../scripts/raas_active_two_year_study.cjs");
const root=path.resolve(__dirname,"..");
const config=require("../new-platform/frontend/data/raas-active-study-config.json");
const intake=require("../new-platform/frontend/data/raas-active-2024-2025-pdufa-intake.json");
const csv=fs.readFileSync(path.join(root,"data/historical_assessed_decisions.csv"),"utf8");
const venues=require("../new-platform/frontend/data/raas-alpaca-venue-exceptions.json").records;
function event(year,ticker){
 const pdufaDate=year+"-07-26",bars=[];
 for(let t=Date.parse(year+"-04-15T00:00:00Z");t<=Date.parse(year+"-07-26T00:00:00Z");t+=86400000){
  const d=new Date(t),dow=d.getUTCDay();if(dow===0||dow===6)continue;
  const date=d.toISOString().slice(0,10),close=12+bars.length*.02;
  bars.push({date,open:close-.1,high:close+.2,low:close-.2,close,volume:30000});
 }
 return {caseId:ticker+"-"+year,ticker,programId:"PDUFA_PROGRAM_"+year,
  nctIds:["NCT12345678"],pdufaDate,pdufaFirstPublicDate:(+year-1)+"-06-01",
  pdufaSourceUrl:"https://example.org/target",phase3ReadoutDate:(+year-1)+"-09-01",
  phase3SourceUrl:"https://example.org/phase3",actualFDAActionDate:pdufaDate,
  actualFDAActionSourceUrl:"https://example.org/outcome",reviewStatus:"SOURCE_REVIEWED",
  historicalMarketCaps:bars.map(b=>({session:b.date,usdMillions:1500,
   sharesSourcePublishedAt:(+year-1)+"-12-01",sourceUrl:"https://example.org/historic-cap",
   sharesSourceUrl:"https://example.org/shares"})),bars};
}
function response(ticker,bars){
 return {ok:true,headers:{get:()=>"application/json"},
  text:async()=>JSON.stringify({symbol:ticker,bars:bars.map(b=>({
   o:b.open,h:b.high,l:b.low,c:b.close,v:b.volume,t:b.date+"T00:00:00Z"
  })),next_page_token:null})};
}
test("2024–2025 is the entire active two-year scope while prior years stay archived",()=>{
 assert.equal(m.verifyConfig(config).studyDurationYears,2);
 assert.equal(config.trainYear,2024);
 assert.equal(config.holdoutYear,2025);
 assert.equal(config.minimumIndependentTrainIssuers,30);
 assert.equal(config.minimumIndependentHoldoutIssuers,30);
 assert.equal(config.historicalMarketCapUsdMillionsMin,300);
 assert.equal(config.historicalMarketCapUsdMillionsMax,10000);
 const q=m.discoveryQueue(csv,config);
 assert.ok(q.length>0);
 assert.ok(q.every(c=>c.pdufaDate>="2024-01-01"&&c.pdufaDate<="2025-12-31"));
 assert.ok(q.every(c=>c.evidenceStatus==="ARCHIVE_CANDIDATE_NOT_SOURCE_VERIFIED"));
 assert.ok(q.every(c=>c.pdufaDate.slice(0,4)==="2024"||c.pdufaDate.slice(0,4)==="2025"));
 assert.deepEqual(m.reviewIntake(intake,config).years.map(x=>x.year),[2024,2025]);
 assert.equal(m.reviewIntake(intake,config).complete,false);
 assert.equal(m.reviewIntake(intake,config).accepted.length,0);
});
test("foreign year or changed window cannot enter active source-reviewed population",()=>{
 const old=event(2020,"OLD"),{bars,...record}=old;
 assert.throws(()=>m.reviewIntake({...intake,records:[record]},config),/OUT_OF_PERIOD_EVENT_FORBIDDEN/);
 assert.throws(()=>m.verifyConfig({...config,startDate:"2016-01-01"}),/ACTIVE_SCOPE_INVALID/);
 assert.throws(()=>m.verifyConfig({...config,minimumIndependentTrainIssuers:1}),/ACTIVE_SCOPE_INVALID/);
 assert.throws(()=>m.reviewIntake({...intake,yearAudits:[...intake.yearAudits,
  {year:2023,status:"NOT_AUDITED"}]},config),/INTAKE_INVALID/);
 assert.throws(()=>m.reviewIntake({...intake,yearAudits:intake.yearAudits.map(x=>({
  ...x,status:"FULL_EVENT_CENSUS_AUDITED",sourceUrl:null
 }))},config),/CENSUS_YEAR_INVALID/);
});
test("2024 training and 2025 holdout require 30 distinct nonoverlapping issuers each",()=>{
 assert.equal(m.selectResearchWindow([],false,config).winner,null);
 assert.equal(m.selectResearchWindow([],false,config).status,
  "BLOCKED_INCOMPLETE_2024_2025_EVENT_CENSUS");
 assert.equal(m.selectResearchWindow([],true,config).status,
  "BLOCKED_INSUFFICIENT_2024_2025_ISSUER_DISJOINT_HOLDOUT");
 const example=(year,ticker)=>({caseId:year+"|"+ticker,year,ticker,
  entryDate:year+"-04-22",entryLeadDays:79,exitLeadDays:14,
  netReturnPct:8,status:"POINT_IN_TIME_PRICE_RESEARCH"});
 const data=[...Array.from({length:30},(_,i)=>example(2024,"T"+i)),
  ...Array.from({length:30},(_,i)=>example(2025,"H"+i))];
 const report=m.selectResearchWindow(data,true,config);
 assert.equal(report.status,"RESEARCH_COMPARISON_REQUIRES_INDEPENDENT_VALIDATION");
 assert.equal(report.winner,null);
 assert.equal(report.approvedTradingWindow,null);
 assert.equal(report.researchComparison.train.n,30);
 assert.equal(report.researchComparison.holdout.n,30);
 const duplicate=[...Array.from({length:30},(_,i)=>example(2024,"T"+i)),
  ...Array.from({length:30},(_,i)=>example(2025,"T"+i))];
 assert.equal(m.selectResearchWindow(duplicate,true,config).winner,null);
 assert.equal(m.selectResearchWindow(duplicate,true,config).status,
  "BLOCKED_INSUFFICIENT_2024_2025_ISSUER_DISJOINT_HOLDOUT");
 assert.throws(()=>m.selectResearchWindow([example(2020,"BAD")],true,config),
  /WINDOW_OUT_OF_SCOPE/);
});
test("2024/2025 source-reviewed synthetic entries yield only research rows, never a trading winner",async()=>{
 const a=event(2024,"TOP"),b=event(2025,"BOT");
 const records=[a,b].map(({bars,...rec})=>rec),seen=[];
 const r=await m.execute({config,intake:{...intake,records},
  csv:"event_key,ticker,pdufa_date\n",venueExceptions:[],
  key:"fake",secret:"fake",request:async(url,opts)=>{
   const u=new URL(url),ticker=u.pathname.split("/")[3];
   assert.equal(u.searchParams.get("adjustment"),"all");
   assert.equal(u.searchParams.get("feed"),"sip");
   assert.ok(["2024-07-26","2025-07-26"].includes(u.searchParams.get("asof")));
   assert.equal(opts.headers["APCA-API-KEY-ID"],"fake");
   seen.push(ticker);
   return response(ticker,(ticker==="TOP"?a:b).bars);
  }});
 assert.deepEqual(seen.sort(),["BOT","TOP"]);
 assert.equal(r.studyDurationYears,2);
 assert.deepEqual(Object.keys(r.years),["2024","2025"]);
 assert.equal(r.sourceReviewedIntakeCases,2);
 assert.equal(r.discoveryCandidates,0);
 assert.equal(r.fullYearCensusAudited,0);
 assert.equal(r.independentTradingCasesValidated,0);
 assert.equal(r.approvedRaasMetricCalibrations,0);
 assert.equal(r.approvedTradingWindow,null);
 assert.equal(r.selection.winner,null);
 assert.ok(r.provisionalWindowArithmeticRows>0);
 assert.equal(r.status,"INCOMPLETE_2024_2025_CENSUS_RESEARCH_ONLY");
});
test("vendor venue exception and no API credentials remain explicit coverage blockers",async()=>{
 const q=m.discoveryQueue(csv,config),zeal=q.find(x=>x.ticker==="ZEAL");
 assert.ok(zeal);
 const noKeys=await m.execute({config,intake,csv,venueExceptions:venues,
  key:"",secret:"",request:async()=>{throw Error("must not query vendor");}});
 assert.equal(noKeys.status,"BLOCKED_MISSING_ALPACA_CREDENTIALS");
 assert.equal(noKeys.priceResearchEventsCollected,0);
 assert.equal(noKeys.independentTradingCasesValidated,0);
 const out=await m.execute({config,intake,
  csv:"event_key,ticker,pdufa_date\nZEAL-2024,ZEAL,2024-12-22,CRL\n",
  venueExceptions:venues,key:"fake",secret:"fake",request:async()=>{
   throw Error("Alpaca should not query non-US ticker");
  }});
 assert.equal(out.nonUSVenueGaps,1);
 assert.equal(out.priceResearchEventsCollected,0);
 assert.equal(out.priceStatuses[0].status,"OUTSIDE_ALPACA_US_STOCK_FEED");
 assert.equal(out.approvedRaasMetricCalibrations,0);
});
test("refuses to turn duplicate, weak or future-source claims into reviewed trade cases",()=>{
 const x=event(2024,"DUP"),{bars,...record}=x;
 const r=m.reviewIntake({...intake,records:[record,{...record}]},config);
 assert.equal(r.accepted.length,1);
 assert.equal(r.rejected.length,1);
 const forgery={...record,historicalMarketCaps:record.historicalMarketCaps.map(c=>({
  ...c,sharesSourcePublishedAt:"2026-01-01"
 }))};
 const invalid=m.reviewIntake({...intake,records:[forgery]},config);
 assert.equal(invalid.accepted.length,0);
 assert.equal(invalid.rejected.length,1);
});
