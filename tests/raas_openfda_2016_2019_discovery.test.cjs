"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const m=require("../scripts/raas_openfda_2016_2019_discovery.cjs");
const sample=[
 {application_number:"NDA022222",sponsor_name:"ACME BIOPHARMA",
  products:[{brand_name:"Alpha"}],
  submissions:[
   {submission_type:"ORIG",submission_number:"1",submission_status:"AP",submission_status_date:"20161110"},
   {submission_type:"ORIG",submission_number:"1",submission_status:"AP",submission_status_date:"20161110"},
   {submission_type:"SUPPL",submission_number:"2",submission_status:"AP",submission_status_date:"20170101"},
   {submission_type:"ORIG",submission_number:"2",submission_status:"CR",submission_status_date:"20161210"}]},
 {application_number:"ANDA012345",submissions:[
   {submission_type:"ORIG",submission_number:"1",submission_status:"AP",submission_status_date:"20161201"}]},
 {application_number:"BLA123456",sponsor_name:"BIO GROUP",submissions:[
   {submission_type:"ORIG",submission_number:"1",submission_status:"AP",submission_status_date:"20161223"}]}
];
const fake=body=>({ok:true,status:200,text:async()=>JSON.stringify(body)});
test("only dated original NDA/BLA approvals can become discovery leads",()=>{
 const rows=m.extract(sample,2016);
 assert.equal(rows.length,2);
 assert.ok(rows.every(r=>r.status==="FDA_APPROVAL_DISCOVERY_ONLY"));
 assert.ok(rows.every(r=>r.historicalPdufaTargetDate===null));
 assert.ok(rows.every(r=>r.historicalTargetFirstPublicDate===null));
 assert.ok(rows.every(r=>r.historicalMarketCapMillions===null));
 assert.ok(rows.every(r=>r.listedIssuerTicker===null));
 assert.ok(rows.every(r=>r.fdaRecordUrl.startsWith("https://api.fda.gov/drug/drugsfda.json?")));
});
test("queries only official FDA endpoint and requested actual action year",()=>{
 const u=new URL(m.buildUrl(2017,99));
 assert.equal(u.origin,"https://api.fda.gov");
 assert.equal(u.pathname,"/drug/drugsfda.json");
 assert.ok(u.searchParams.get("search").includes("20170101 TO 20171231"));
 assert.ok(u.searchParams.get("search").includes("submission_status:AP"));
 assert.equal(u.searchParams.get("skip"),"99");
});
test("FDA pagination must fully cover every page before claiming a year was searched",async()=>{
 let n=0;
 const request=async(url)=>{
  n++;
  const u=new URL(url),skip=+u.searchParams.get("skip");
  return fake({meta:{results:{total:100}},
   results:skip===0?Array.from({length:99},()=>sample[0]):[sample[2]]});
 };
 const r=await m.scanYear(2016,request);
 assert.equal(n,2);
 assert.equal(r.applicationsSearched,100);
 assert.equal(r.candidates.length,2);
 assert.equal(r.pages,2);
});
test("malformed API results cannot create evidence from missing or uncertain action dates",async()=>{
 await assert.rejects(m.scanYear(2016,async()=>fake({results:[],meta:{}})),
  /OPENFDA_PAYLOAD_INVALID/);
 const a=m.extract([{application_number:"NDA123456",submissions:[
  {submission_type:"ORIG",submission_number:"1",submission_status:"AP",submission_status_date:"20160231"}
 ]}],2016);
 assert.equal(a.length,0);
});
test("failure in one year marks entire output partial, no fictional year completeness",async()=>{
 const req=async(url)=>{
  const q=new URL(url).searchParams.get("search");
  if(q.includes("2017"))return {ok:false,status:401};
  return fake({meta:{results:{total:1}},results:sample.slice(0,1)});
 };
 const result=await m.run({request:req,years:[2016,2017]});
 assert.equal(result.status,"PARTIAL_OR_FAILED");
 assert.deepEqual(result.completedYears,[2016]);
 assert.equal(result.failures[0].year,2017);
 assert.ok(result.limitations.some(x=>x.includes("NOT")));
 assert.ok(result.candidates.every(x=>x.historicalPdufaTargetDate===null));
});
