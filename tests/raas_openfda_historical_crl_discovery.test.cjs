"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const m=require("../scripts/raas_openfda_historical_crl_discovery.cjs");
const crl=(date,app="NDA 209510",id="letter1.pdf")=>({
 letter_date:date,application_number:[app],company_name:"ACACIA PHARMA LTD",
 file_name:id,letter_type:"COMPLETE RESPONSE",
 text:"This OCR text was published years after the original letter date"});
const response=(records,total,updated="2026-10-05")=>({
 ok:true,status:200,text:async()=>JSON.stringify({
 meta:{last_updated:updated,results:{total}},results:records
 })});
test("strict letter date and NDA/BLA identity prevent date substitutions",()=>{
 assert.equal(m.parseLetterDate("10/05/2018"),"2018-10-05");
 assert.equal(m.parseLetterDate("2/18/2022"),"2022-02-18");
 assert.equal(m.parseLetterDate("02/31/2022"),null);
 assert.equal(m.parseLetterDate("2022-02-18"),null);
 assert.equal(m.applicationNumber("NDA 209510"),"NDA 209510");
 assert.equal(m.applicationNumber("bla125713"),"BLA 125713");
 assert.equal(m.applicationNumber("ANDA 012345"),null);
});
test("official source records never promote CRL letter text as first-public evidence",()=>{
 const r=m.parseCRLRecords([crl("10/05/2018"),crl("2/18/2022","BLA 125713","letter2.pdf"),
  crl("10/05/2018"),{...crl("11/01/2018"),letter_type:"APPROVAL"},
  crl("02/31/2022"),crl("10/01/2015")]);
 assert.equal(r.records.length,2);
 assert.equal(r.nonCrl,1);
 assert.equal(r.unparseable,1);
 assert.equal(r.otherYears,1);
 const row=r.records[0];
 assert.equal(row.letterDate,"2018-10-05");
 assert.equal(row.originalPdufaTargetDate,null);
 assert.equal(row.originalPublicCRLDisclosureDate,null);
 assert.equal(row.preDecisionInformationEligible,false);
 assert.equal(row.eligibleForRaasCalibration,false);
 assert.equal(row.actualFdaActionType,"CRL");
 assert.equal(row.currentIssuerTicker,null);
 assert.match(row.sourceUrl,/api\.fda\.gov\/transparency\/crl\.json/);
 assert.equal(JSON.stringify(r).includes("OCR text"),false);
});
test("pagination completes all official FDA result pages, preserves year counts, no scores",async()=>{
 const many=Array.from({length:50},(_,i)=>crl("08/03/2020","NDA 209510","file-"+i+".pdf"));
 const last=crl("09/04/2021","BLA 125713","last.pdf");
 let pages=[];
 const request=async url=>{
  const u=new URL(url);
  assert.equal(u.origin,"https://api.fda.gov");
  assert.equal(u.pathname,"/transparency/crl.json");
  const skip=+u.searchParams.get("skip");
  assert.equal(+u.searchParams.get("limit"),50);
  pages.push(skip);
  return response(skip===0?many:[last],51);
 };
 const r=await m.execute({request});
 assert.deepEqual(pages,[0,50]);
 assert.equal(r.sourceRecordsFetched,51);
 assert.equal(r.crlApplicationLetterLeads,51);
 assert.equal(r.countsByLetterYear[2020],50);
 assert.equal(r.countsByLetterYear[2021],1);
 assert.ok(r.cases.every(x=>!x.eligibleForRaasCalibration));
 assert.equal(r.status,"FDA_CRL_DOCUMENTS_RETRIEVED_INCOMPLETE_EVENT_DENOMINATOR");
});
test("source total changes, invalid shape, HTTP denial and incomplete pages fail closed",async()=>{
 await assert.rejects(m.getPage(0,async()=>({ok:false,status:403})),/RAAS_CRL_HTTP_403/);
 await assert.rejects(m.getPage(0,async()=>({ok:true,text:async()=>JSON.stringify({results:[]})})),
  /RAAS_CRL_PAGE_SCHEMA_INVALID/);
 await assert.rejects(m.execute({request:async url=>{
  const skip=+new URL(url).searchParams.get("skip");
  return response(skip===0?Array(50).fill(crl("01/01/2020")):[],60);
 }}),/RAAS_CRL_INCOMPLETE_EMPTY_PAGE/);
 await assert.rejects(m.execute({request:async url=>{
  const skip=+new URL(url).searchParams.get("skip");
  return response(skip===0?Array(50).fill(crl("01/01/2020")):[crl("01/01/2020")],
   skip===0?51:52);
 }}),/RAAS_CRL_PAGINATION_CHANGED/);
});
test("multiple applications on one CRL are separate outcomes, not multiple public tickers",()=>{
 const a=m.parseCRLRecords([{...crl("04/05/2019"),
  application_number:["NDA 209510","BLA 125713"],company_name:"Acacia Ltd"}]);
 assert.equal(a.records.length,2);
 assert.notEqual(a.records[0].caseId,a.records[1].caseId);
 assert.ok(a.records.every(x=>x.currentIssuerTicker===null&&x.marketCapAtEntryVerified===false));
});
