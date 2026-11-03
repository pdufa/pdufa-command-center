"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path");
const m=require("../scripts/raas_historical_raw_market_cap_research.cjs");
const root=path.resolve(__dirname,"..");
const lead=require("../new-platform/frontend/data/raas-2020-sec-cover-share-leads.json").records[0];
const event=require("../new-platform/frontend/data/raas-historical-2020-primary-source-leads.json").records[0];
function bars(close,from="2020-07-22",days=100) {
 const out=[];let t=Date.parse(from+"T00:00:00Z");
 for(let k=0;k<days;k++,t+=86400000){
  const d=new Date(t),wd=d.getUTCDay();
  if(wd!==0&&wd!==6)out.push({date:d.toISOString().slice(0,10),
   open:close,close,high:close+0.1,low:close-0.1,volume:100});
 }
 return out;
}
test("real original SEC filing shows 56,059,865 shares only after its August 6 publication",()=>{
 const a=m.checkedLead(lead,event);
 assert.equal(a.sharesOutstanding,56059865);
 assert.equal(a.sharesMeasurementDate,"2020-08-03");
 assert.equal(a.filedDate,"2020-08-06");
 assert.equal(a.firstConservativeEntryDate,"2020-08-07");
 assert.equal(a.securityCurrency,"USD");
 assert.equal(event.pdufaTargetDate,"2020-10-30");
 assert.equal(event.actualFDAActionDate,"2020-10-26");
});
test("raw prices times historical shares, not split-adjusted vendor prices",()=>{
 const raw=bars(8),adjusted=bars(800);
 const x=m.examine(lead,event,raw,adjusted);
 assert.equal(x.status,"RAW_MARKET_CAP_DIAGNOSTICS_NOT_PROVEN_TRADING_ELIGIBILITY");
 const after=x.observations.find(r=>r.session==="2020-08-07");
 const before=x.observations.find(r=>r.session==="2020-08-05");
 assert.equal(before.historicMarketCapResearchMillions,null);
 assert.equal(after.historicMarketCapResearchMillions,448.48);
 assert.equal(after.within300mTo10bUnreviewed,true);
 assert.equal(after.adjustedClose,800);
 assert.equal(x.eventTradeCasesValidated,0);
 assert.equal(x.approvedRaasRatings,0);
 assert.ok(!x.observations.some(y=>y.session>="2020-10-26"&&
   y.beforeActualFDAAction===true));
});
test("raw and adjusted price requests cannot be silently interchanged",async()=>{
 let reads=[];
 const request=async (u,options)=>{
  const p=new URL(u);reads.push(p.searchParams.get("adjustment"));
  assert.equal(p.searchParams.get("feed"),"sip");
  assert.equal(p.searchParams.get("asof"),"2020-10-30");
  assert.equal(options.headers["APCA-API-KEY-ID"],"test_key");
  const adj=p.searchParams.get("adjustment"),c=adj==="raw"?8:800;
  return {ok:true,status:200,headers:{get:()=> "application/json"},
   text:async()=>JSON.stringify({symbol:"KALA",bars:[{t:"2020-08-07T00:00:00Z",
    o:c,h:c+0.1,l:c-0.1,c,v:100}],next_page_token:null})};
 };
 const one=await m.fetchBars("KALA","2020-10-30","2020-07-22","2020-10-29","raw","test_key","secret",request);
 const two=await m.fetchBars("KALA","2020-10-30","2020-07-22","2020-10-29","all","test_key","secret",request);
 assert.deepEqual(reads,["raw","all"]);
 assert.equal(one[0].close,8);
 assert.equal(two[0].close,800);
});
test("unmatched share facts, dates, calendars and false currencies fail closed",()=>{
 assert.throws(()=>m.checkedLead({...lead,sharesOutstanding:0},event),/RAAS_CAP_SOURCE/);
 assert.throws(()=>m.checkedLead({...lead,firstConservativeEntryDate:"2020-08-06"},event),/RAAS_CAP_SOURCE/);
 assert.throws(()=>m.checkedLead({...lead,rawCloseCurrency:"EUR"},event),/RAAS_CAP_SOURCE/);
 assert.throws(()=>m.checkedLead({...lead,ticker:"FAKE"},event),/RAAS_CAP_SOURCE/);
 assert.throws(()=>m.examine(lead,event,bars(8),bars(800,"2020-07-23")),/RAAS_CAP_PRICE_CALENDARS_MISMATCH/);
});
test("no credentials means no fabricated raw price or trading case",async()=>{
 const r=await m.execute({key:"",secret:""});
 assert.equal(r.status,"BLOCKED_MISSING_ALPACA_CREDENTIALS");
 assert.equal(r.cases.length,0);
});

test("Heron SEC cover shares yield independent RAW capitalization leads only after May 6",()=>{
 const shares=require("../new-platform/frontend/data/raas-2020-sec-cover-share-leads.json").records;
 const events=require("../new-platform/frontend/data/raas-historical-2020-primary-source-leads.json").records;
 const h=shares.find(x=>x.ticker==="HRTX");
 const e=events.find(x=>x.ticker==="HRTX");
 assert.ok(h&&e);
 assert.equal(h.sharesOutstanding,90642154);
 assert.equal(h.sharesMeasurementDate,"2020-04-29");
 assert.equal(h.filedDate,"2020-05-06");
 assert.equal(h.firstConservativeEntryDate,"2020-05-07");
 assert.equal(e.actualFDAActionDate,"2020-06-26");
 assert.equal(m.checkedLead(h,e).ticker,"HRTX");
 const result=m.examine(h,e,bars(10,"2020-04-25",61),
  bars(1000,"2020-04-25",61));
 assert.equal(result.observations.find(x=>x.session==="2020-05-06").historicMarketCapResearchMillions,null);
 const after=result.observations.find(x=>x.session==="2020-05-07");
 assert.equal(after.historicMarketCapResearchMillions,906.42);
 assert.equal(after.adjustedClose,1000);
 assert.equal(after.within300mTo10bUnreviewed,true);
 assert.equal(result.eventTradeCasesValidated,0);
 assert.equal(result.approvedRaasRatings,0);
});

test("ESPR NDA 211616 and 211617 are distinct programs but one correlated issuer",()=>{
 const shares=require("../new-platform/frontend/data/raas-2020-sec-cover-share-leads.json").records;
 const events=require("../new-platform/frontend/data/raas-historical-2020-primary-source-leads.json").records;
 const espr=events.filter(x=>x.ticker==="ESPR");
 assert.equal(espr.length,2);
 assert.deepEqual(espr.map(x=>x.application),["NDA 211616","NDA 211617"]);
 assert.deepEqual(espr.map(x=>x.pdufaTargetDate),["2020-02-21","2020-02-26"]);
 assert.deepEqual(espr.map(x=>x.actualFDAActionDate),["2020-02-21","2020-02-26"]);
 assert.deepEqual(espr.map(x=>x.nctIds[0]),["NCT02666664","NCT03337308"]);
 for(const event of espr){
  const share=shares.find(x=>x.caseId===event.caseId);
  assert.ok(share);
  assert.equal(share.sharesOutstanding,27327409);
  assert.equal(share.sharesMeasurementDate,"2019-11-01");
  assert.equal(share.filedDate,"2019-11-06");
  assert.equal(share.firstConservativeEntryDate,"2019-11-07");
  assert.equal(share.sourceUrl.includes("20190930x10q"),true);
  assert.equal(m.checkedLead(share,event).ticker,"ESPR");
 }
 const counts=m.issuerExposureDiagnostics(events);
 assert.equal(counts.researchPrograms,6);
 assert.equal(counts.distinctResearchIssuers,5);
 assert.equal(counts.overlappingSameIssuerPairs,1);
 assert.equal(counts.overlaps[0].ticker,"ESPR");
 assert.equal(counts.overlaps[0].targetGapDays,5);
});
test("ESPR 2019 SEC fact cannot be multiplied by raw prices before first public date",()=>{
 const shares=require("../new-platform/frontend/data/raas-2020-sec-cover-share-leads.json").records;
 const events=require("../new-platform/frontend/data/raas-historical-2020-primary-source-leads.json").records;
 const s=shares.find(x=>x.caseId==="ESPR|NEXLETOL|NDA211616|2020");
 const e=events.find(x=>x.caseId===s.caseId);
 const raw=bars(38,"2019-11-04",114),adj=bars(3800,"2019-11-04",114);
 const x=m.examine(s,e,raw,adj);
 assert.equal(x.observations.find(x=>x.session==="2019-11-06").historicMarketCapResearchMillions,null);
 const after=x.observations.find(x=>x.session==="2019-11-07");
 assert.equal(after.historicMarketCapResearchMillions,1038.44);
 assert.equal(after.within300mTo10bUnreviewed,true);
 assert.equal(after.adjustedClose,3800);
 assert.equal(x.eventTradeCasesValidated,0);
 assert.equal(x.approvedRaasRatings,0);
});

test("ICPT May 11 shares are post-close research only, never 2020 CRL leakage",()=>{
 const shares=require("../new-platform/frontend/data/raas-2020-sec-cover-share-leads.json").records;
 const events=require("../new-platform/frontend/data/raas-historical-2020-primary-source-leads.json").records;
 const s=shares.find(x=>x.caseId==="ICPT|OCA_NASH|NDA212833|2020");
 const e=events.find(x=>x.caseId===s?.caseId);
 assert.ok(s&&e);
 assert.equal(s.sharesOutstanding,32937431);
 assert.equal(s.sharesMeasurementDate,"2020-03-31");
 assert.equal(s.filedDate,"2020-05-11");
 assert.equal(s.firstConservativeEntryDate,"2020-05-12");
 assert.equal(s.acceptedAfterCloseET,true);
 assert.equal(e.targetAnnouncementDate,"2020-01-17");
 assert.equal(e.actualFDAActionDate,"2020-06-26");
 assert.equal(m.checkedLead(s,e).ticker,"ICPT");
 const result=m.examine(s,e,bars(55,"2020-04-27",65),bars(5500,"2020-04-27",65));
 assert.equal(result.observations.find(x=>x.session==="2020-05-11").historicMarketCapResearchMillions,null);
 const first=result.observations.find(x=>x.session==="2020-05-12");
 assert.equal(first.historicMarketCapResearchMillions,1811.56);
 assert.equal(first.adjustedClose,5500);
 assert.equal(first.within300mTo10bUnreviewed,true);
 assert.equal(result.eventTradeCasesValidated,0);
 assert.equal(result.approvedRaasRatings,0);
 assert.ok(result.observations.filter(x=>x.session>="2020-06-26").every(x=>!x.beforeActualFDAAction));
});
