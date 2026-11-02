"use strict";
const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const ts=require("typescript");
for(const ext of [".ts",".tsx"])require.extensions[ext]=(mod,file)=>mod._compile(
 ts.transpileModule(fs.readFileSync(file,"utf8"),{compilerOptions:{
 module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true
 }}).outputText,file);
const {auditTrialRatings}=require("../lib/tools-rating-engine.ts");
const {parseBenefitFeed}=require("../lib/benefit-assessments.ts");
const row={
 nctId:"NCT12345678",ticker:"TICK",drug:"Research Therapy",indication:"Rare Condition",stage:"Phase 3 Results",
 timeline:{
 phase3DataRelease:{date:"2026-10-15",sourceUrl:"https://clinicaltrials.gov/study/NCT12345678",status:"VERIFIED"},
 pdufaTarget:{date:"2026-11-28",sourceUrl:"https://www.fda.gov/drugs",status:"VERIFIED"}
 }
};
const mkFact=(value,status="VERIFIED")=>({
 value,status,sourceUrl:"https://clinicaltrials.gov/study/NCT12345678",
 sourceDate:"2026-10-15",method:"Read original study record and verify the source",confidence:"HIGH"
});
const feed=parseBenefitFeed({schemaVersion:1,sourceAsOf:"2026-11-01",records:[{
 nctId:row.nctId,ticker:row.ticker,drug:row.drug,indication:row.indication,
 facts:{
 clinicalBenefit:mkFact("Source-reported endpoint"),
 safetyAdvantage:mkFact("Reported adverse-event data"),
 closestCompetitor:mkFact("Competitor identity"),
 eligibleUsPatients:mkFact("Estimated eligible subset","MODELED"),
 payerAccess:mkFact("Payer evidence"),
 valuationImpact:mkFact("Pricing and valuation scenario","MODELED")
 },advantages:[]
}]});
test("M source verified/model/missing counts and A PDUFA receipt reflect only evidence",()=>{
 const result=auditTrialRatings(row,"2026-11-01",feed);
 assert.equal(result.verifiedFields,4);
 assert.equal(result.modeledFields,2);
 assert.equal(result.verifiedFields+result.modeledFields+result.missingFields,result.totalFields);
 assert.equal(result.ingredient.VER.label,"4");
 assert.equal(result.ingredient.MOD.label,"2");
 assert.equal(result.ingredient.MISS.label,String(result.missingFields));
 assert.equal(result.ingredient.FDA.label,"27 days");
 assert.equal(result.group.A.label,"Window open");
 assert.equal(result.ingredient.ER.links.length,6);
 assert.equal(result.ingredient.CL.kind,"coverage");
 assert.match(result.ingredient.CL.label,/1\/\d+ verified/);
 assert.equal(result.ingredient.SAF.links.length,1);
 assert.equal(result.ingredient.COMP.links.length,1);
 assert.ok(result.ingredient.POP.links.some(v=>v.status==="MODELED"));
 assert.equal(result.ingredient.CASH.label,"N/A");
 assert.equal(result.ingredient.MOM.label,"N/A");
 assert.equal(result.ingredient.FLOW.label,"N/A");
 assert.equal(result.group.E.label,"N/A");
 assert.equal(result.ingredient.APP.label,"N/A");
 assert.equal(result.ingredient.GRADE.label,"N/A");
 assert.equal(result.eligibleForInvestmentRanking,false);
});
test("no ticker-only match, absent sources remain unscored; no false investment rank",()=>{
 const wrong={...row,nctId:"NCT12345679"};
 const audit=auditTrialRatings(wrong,"2026-11-01",feed);
 assert.equal(audit.sourceRecordPresent,false);
 assert.equal(audit.verifiedFields,0);
 assert.equal(audit.ingredient.CL.label,"N/A");
 assert.equal(audit.ingredient.COMP.label,"N/A");
 assert.equal(audit.ingredient.VER.label,"0");
 assert.equal(audit.eligibleForInvestmentRanking,false);
 const unavail=auditTrialRatings(wrong,"2026-11-01",null,true);
 assert.equal(unavail.ingredient.VER.label,"Unavailable");
 assert.equal(unavail.ingredient.MISS.label,"Unavailable");
 assert.match(unavail.ingredient.CL.explanation,/feed unavailable/);
 assert.equal(unavail.ingredient.GRADE.label,"N/A");
});
test("missing readout or passed PDUFA cutoff must fail research-gate readiness",()=>{
 const missing={...row,timeline:{phase3DataRelease:null,pdufaTarget:null}};
 const a=auditTrialRatings(missing,"2026-11-01",feed);
 assert.equal(a.group.A.label,"Needs review");
 assert.equal(a.ingredient.FDA.label,"Date unknown");
 assert.equal(a.ingredient.CRIT.label,"1 gaps");
 assert.equal(a.ingredient.READY.label,"Not qualified");
 const cutoff={...row,timeline:{
   ...row.timeline,pdufaTarget:{...row.timeline.pdufaTarget,date:"2026-11-03"}
 }};
 const b=auditTrialRatings(cutoff,"2026-11-01",feed);
 assert.equal(b.ingredient.CRIT.label,"1 gaps");
 assert.equal(b.ingredient.READY.label,"Not qualified");
});

test("source-verified historical registry records expose measured results without inventing clinical superiority",()=>{
 const receipt={
  nctId:row.nctId,retrievedAt:"2026-11-01T17:11:01.933Z",
  sourceUpdated:"2026-10-31",resultsPosted:true,
  primaryOutcomeCount:2,measuredPrimary:true,
  secondaryOutcomeCount:1,measuredSecondary:true,
  seriousEventTerms:3,measuredSeriousEvents:true,truncated:false,
  measuredDimensions:4,dimensionsTotal:4,registryCoveragePercent:100
 };
 const audited=auditTrialRatings(row,"2026-11-01",null,false,receipt);
 assert.equal(audited.ingredient.ER.label,"100% registry");
 assert.match(audited.ingredient.ER.explanation,/NOT a clinical benefit/);
 assert.equal(audited.ingredient.CL.label,"Registry data");
 assert.equal(audited.ingredient.SAF.label,"Registry AEs");
 assert.equal(audited.ingredient.CL.kind,"coverage");
 assert.equal(audited.ingredient.CL.links.length,1);
 assert.match(audited.ingredient.CL.explanation,/NOT been clinically adjudicated/);
 assert.equal(audited.ingredient.COMP.label,"N/A");
 assert.equal(audited.group.E.label,"N/A");
 assert.equal(audited.eligibleForInvestmentRanking,false);
 assert.equal(audited.verifiedFields,0,"ClinicalTrials.gov receipts do not falsely fill benefit/superiority fields");
 const truncated=auditTrialRatings(row,"2026-11-01",null,false,{...receipt,truncated:true});
 assert.equal(truncated.ingredient.CL.label,"N/A","Truncated observations cannot count as complete input");
 assert.equal(truncated.ingredient.SAF.label,"N/A");
});

test("historical same-condition competitor leads appear in COMP as leads, never a validated comparison rating",()=>{
 const receipt={nctId:row.nctId,status:"RESEARCH_LEADS_ONLY",totalCandidates:2,
  displayed:[{nctId:"NCT12345679",therapy:"Candidate B",
   sharedConditions:["Rare Condition"],resultsPosted:true,
   sourceUrl:"https://clinicaltrials.gov/study/NCT12345679",
   retrievedAt:"2026-11-01T17:11:01.933Z"}],
  truncated:true};
 const audit=auditTrialRatings(row,"2026-11-01",null,false,null,receipt);
 assert.equal(audit.ingredient.COMP.kind,"lead");
 assert.equal(audit.ingredient.COMP.label,"2 leads");
 assert.equal(audit.ingredient.COMP.links.length,1);
 assert.equal(audit.ingredient.COMP.links[0].status,"LEAD");
 assert.equal(audit.group.B.label,"N/A","unverified lead does not count toward verified medical inputs");
 assert.equal(audit.ingredient.GRADE.label,"N/A");
 assert.equal(audit.eligibleForInvestmentRanking,false);
 assert.equal(audit.verifiedFields,0,"peer research is not a verified clinical benefit fact");
 const unrelated=auditTrialRatings({...row,nctId:"NCT12345680"},"2026-11-01",null,false,null,receipt);
 assert.equal(unrelated.ingredient.COMP.label,"N/A","cross-NCT lead data must not leak");
 const malformed={...receipt,displayed:[{...receipt.displayed[0],sourceUrl:"https://attacker.example/study/NCT12345679"}]};
 const unverified=auditTrialRatings(row,"2026-11-01",null,false,null,malformed);
 assert.equal(unverified.ingredient.COMP.label,"N/A","invalid source receipts must not be linked");
});
test("verified competitive fields remain separate from extra unverified peer suggestions",()=>{
 const receipt={nctId:row.nctId,status:"RESEARCH_LEADS_ONLY",totalCandidates:1,
  displayed:[{nctId:"NCT12345679",therapy:"Candidate B",
   sharedConditions:["Rare Condition"],resultsPosted:true,
   sourceUrl:"https://clinicaltrials.gov/study/NCT12345679",
   retrievedAt:"2026-11-01T17:11:01.933Z"}],
  truncated:false};
 const audit=auditTrialRatings(row,"2026-11-01",feed,false,null,receipt);
 assert.equal(audit.ingredient.COMP.kind,"coverage");
 assert.match(audit.ingredient.COMP.label,/verified/);
 assert.equal(audit.ingredient.COMP.links.length,2);
 assert.equal(audit.ingredient.COMP.links.filter(x=>x.status==="LEAD").length,1);
 assert.equal(audit.verifiedFields,4);
});
