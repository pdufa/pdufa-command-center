"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const {rows,norm,crosswalk}=require("../scripts/raas_match_fda_2016_2019_sponsors.cjs");
const registry='ticker,company,status\nABCD,"Alpha, Biopharma Inc.",OK\nABCD2,Alpha Biopharma Inc.,OFF\nBIOX,Bio Health Corporation,OK\nOTHER,Similar Biopharma Inc.,OK\nDUP1,Duplicate Biotech Inc.,OK\nDUP2,Duplicate Biotech Corp,OK\n';
const item=(id,sponsor,year=2016)=>({
 id,year,status:"FDA_APPROVAL_DISCOVERY_ONLY",applicationNumber:id.split("|")[0],
 actualApprovalDate:year+"-03-01",sponsorName:sponsor,productNames:["EXAMPLE"],
 fdaRecordUrl:"https://api.fda.gov/drug/drugsfda.json?search=test"
});
const sample={scope:"FDA_DRUGS_AT_FDA_2016_2019_APPROVAL_DISCOVERY_NOT_PDUFA_CENSUS",
 candidates:[item("NDA123456|ORIG|1|20160301","Alpha, Biopharma Inc."),
 item("NDA123457|ORIG|1|20160301","Bio Health Corp"),
 item("NDA123458|ORIG|1|20160301","Alpha Biopharma Holdings"),
 item("NDA123459|ORIG|1|20160301","Duplicate Biotech Inc.") ]
};
test("CSV handles quoted commas and names without inventing aliases",()=>{
 const a=rows(registry);
 assert.equal(a.length,6);
 assert.equal(a[0].company,"Alpha, Biopharma Inc.");
 assert.equal(norm("Bio Health Corp"),norm("Bio Health Corporation"));
 assert.notEqual(norm("Alpha, Biopharma Inc."),norm("Alpha Biopharma Holdings"));
});
test("exact current registry matching is only an unverified historical lead",()=>{
 const r=crosswalk(sample,registry);
 assert.equal(r.totalFdaActionLeads,4);
 assert.equal(r.exactCurrentNameLeads,2);
 assert.equal(r.ambiguous,1);
 assert.equal(r.noExactMatch,1);
 const first=r.rows[0];
 assert.equal(first.candidateTicker,"ABCD");
 assert.equal(first.status,"EXACT_NAME_PUBLIC_REGISTRY_LEAD");
 assert.equal(first.historicalMarketCapVerified,false);
 assert.equal(first.historicalListingVerified,false);
 assert.equal(first.pdufaTargetFirstPublicVerified,false);
 assert.equal(first.commercialRightsVerified,false);
 assert.equal(r.status,"RESEARCH_LEADS_NOT_HISTORICAL_ELIGIBILITY");
});
test("ineligible source identity, repeated data and malformed registry fail closed",()=>{
 assert.throws(()=>crosswalk({...sample,scope:"VERIFIED_TRADE"},registry),
  /RAAS_FDA_DISCOVERY_INVALID/);
 assert.throws(()=>crosswalk({...sample,candidates:[sample.candidates[0],sample.candidates[0]]},registry),
  /RAAS_FDA_CANDIDATE_INVALID/);
 assert.throws(()=>crosswalk(sample,"bad,csv\n1,2"),/RAAS_COMPANY_REGISTRY_INVALID/);
});
