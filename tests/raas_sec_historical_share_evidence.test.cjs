"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const m=require("../scripts/raas_sec_historical_share_evidence.cjs");
const registry="ticker,company,cik10,exchange,sic,sic_description,status\nABC,ABC Pharma,0000000123,Nasdaq,2834,Pharma,OK\nDEF,DEF Biotech,0000000456,Nasdaq,2834,Pharma,OK\n";
const archive="event_key,ticker,pdufa_date,actual_outcome\nABC|2024-11-20|druga,ABC,2024-11-20,APPROVED\nDEF|2024-10-20|drugb,DEF,2024-10-20,CRL\nOTHER|2020-03-10|drugx,OTHER,2020-03-10,APPROVED\n";
const fact=(shares,end,filed,accn="0000000123-24-000001")=>({val:shares,end,filed,form:"10-Q",accn});
const payload=(cik=123,shares=[fact(33000000,"2024-06-30","2024-08-01")])=>({cik,units:{shares}});
test("SEC current-company registry identity does not imply historical eligibility",()=>{
 const a=m.issuers(registry);
 assert.equal(a.map.get("ABC").cik,"0000000123");
 assert.equal(a.map.get("ABC").exchange,"Nasdaq");
 assert.equal(a.conflicts.length,0);
});
test("valid SEC share facts must match CIK and original dated filing",()=>{
 const x=m.sourceFacts(payload(),"0000000123");
 assert.equal(x.length,1);
 assert.equal(x[0].filed,"2024-08-01");
 assert.equal(x[0].shares,33000000);
 assert.match(x[0].sourceUrl,/www\.sec\.gov\/Archives\/edgar/);
 assert.throws(()=>m.sourceFacts(payload(999),"0000000123"),/SEC_COMPANY_IDENTITY_MISMATCH/);
});
test("as-of research rejects future filings, stale shares, ambiguous classes, and amended lookahead",()=>{
 const history=m.sourceFacts(payload(123,[
  fact(20000000,"2023-12-31","2024-02-20"),
  fact(33000000,"2024-06-30","2024-08-01"),
  fact(70000000,"2024-09-30","2024-12-01")
 ]),"0000000123");
 assert.equal(m.latestVisible(history,"2024-07-01").shares,20000000);
 assert.equal(m.latestVisible(history,"2024-11-01").shares,33000000);
 assert.equal(m.latestVisible(history,"2024-11-01").status,"SEC_PUBLIC_COVER_SHARES_RESEARCH_ONLY");
 assert.equal(m.latestVisible(history,"2024-11-01").marketCapAtEntryVerified,false);
 assert.equal(m.latestVisible(history,"2022-01-01"),null);
 const ambiguous=m.sourceFacts(payload(123,[
  fact(33000000,"2024-06-30","2024-08-01"),
  fact(50000000,"2024-06-30","2024-08-01","0000000123-24-000002")
 ]),"0000000123");
 assert.equal(m.latestVisible(ambiguous,"2024-11-01").status,
  "MULTIPLE_SHARE_VALUES_REQUIRE_CLASS_REVIEW");
});
test("SEC requests are pinned to official concept endpoint and identify the crawler",async()=>{
 const req=async(url,opt)=>{
  const u=new URL(url);assert.equal(u.hostname,"data.sec.gov");
  assert.match(u.pathname,/companyconcept\/CIK0000000123\/dei\/EntityCommonStockSharesOutstanding.json$/);
  assert.match(opt.headers["User-Agent"],/PDUFA-Command-Center/);
  return {ok:true,status:200,text:async()=>JSON.stringify(payload())};
 };
 assert.equal((await m.getFacts("0000000123",req)).length,1);
 await assert.rejects(m.getFacts("0000000123",async()=>({ok:false,status:403})),
  /SEC_HTTP_403/);
});
test("complete archive retains unknown and source failures instead of fabricated market caps",async()=>{
 const req=async url=>{
  if(url.includes("CIK0000000456"))return {ok:false,status:403};
  return {ok:true,status:200,text:async()=>JSON.stringify(payload())};
 };
 const x=await m.execute({archiveCsv:archive,registryCsv:registry,request:req,pause:async()=>{}});
 assert.equal(x.archivedEvents,3);
 assert.equal(x.issuersQueried,2);
 assert.equal(x.requests.filter(y=>y.status==="SEC_SOURCE_UNAVAILABLE").length,1);
 assert.equal(x.eventsWithShareFacts,1);
 assert.equal(x.cases.find(c=>c.ticker==="OTHER").status,"MISSING_CURRENT_REGISTRY_CIK");
 assert.ok(x.cases.every(c=>c.marketCapAtEntryVerified===false));
 assert.ok(x.cases.every(c=>c.pdufaFirstPublicDateVerified===false));
});
