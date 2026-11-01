"use strict";
const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const ts=require("typescript");
for(const ext of [".ts",".tsx"])require.extensions[ext]=(mod,file)=>mod._compile(
 ts.transpileModule(fs.readFileSync(file,"utf8"),{compilerOptions:{
 module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true
 }}).outputText,file);
const {competitiveEdge}=require("../lib/competitive-edge.ts");
const candidate=(v={})=>({
 nctId:"NCT12345678",ticker:"AAA",drug:"Therapy A",indication:"Disease Z",...v
});
const peer=(v={})=>candidate({nctId:"NCT23456789",ticker:"BBB",drug:"Therapy B",...v});
const advantage=(v={})=>({
 id:"e-1",assessment:6,rank:1,title:"Observed benefit",comparator:"Therapy B",
 comparison:"Directly reviewed endpoint improvement against Therapy B in the specified population.",
 sourceUrl:"https://example.org/review",sourceDate:"2026-10-20",
 method:"Reviewed exact-drug clinical comparison",confidence:"HIGH",status:"VERIFIED",...v
});
const feed=(items)=>({schemaVersion:1,sourceAsOf:"2026-10-30",records:[{
 nctId:"NCT12345678",ticker:"AAA",drug:"Therapy A",indication:"Disease Z",
 facts:{},advantages:items,overallAdvantages:[]
}]});
test("no evidence or no peer: gold factor is not an invented superiority verdict",()=>{
 const e=competitiveEdge(candidate(),null,[peer()]);
 assert.equal(e.status,"NOT_ESTABLISHED");
 assert.equal(e.overallWinner,false);
 assert.match(e.reason,/No verified/);
});
test("different indication or missing exact identity always abstains",()=>{
 assert.equal(competitiveEdge(candidate(),null,[peer({indication:"Disease Q"})]).status,"NOT_COMPARABLE");
 assert.equal(competitiveEdge(candidate({drug:null}),null,[peer()]).status,"NOT_ESTABLISHED");
});
test("modeled findings, low confidence, and wrong peer are never shown as advantages",()=>{
 assert.equal(competitiveEdge(candidate(),feed([advantage({status:"MODELED"})]),[peer()]).status,"NOT_ESTABLISHED");
 assert.equal(competitiveEdge(candidate(),feed([advantage({confidence:"LOW"})]),[peer()]).status,"NOT_ESTABLISHED");
 assert.equal(competitiveEdge(candidate(),feed([advantage()]),[peer({drug:"Therapy C"})]).status,"NOT_ESTABLISHED");
 assert.equal(competitiveEdge(candidate({ticker:"OTHER"}),feed([advantage()]),[peer()]).status,"NOT_ESTABLISHED");
});
test("verified assessment #6 record gives sourced reason, never overall superiority",()=>{
 const e=competitiveEdge(candidate(),feed([advantage()]),[peer()]);
 assert.equal(e.status,"SOURCED_FACTOR");
 assert.equal(e.assessment,6);
 assert.equal(e.assessmentTitle,"Competitive Advantage");
 assert.equal(e.comparator,"Therapy B");
 assert.equal(e.sourceUrl,"https://example.org/review");
 assert.match(e.reason,/endpoint improvement/);
 assert.equal(e.overallWinner,false);
});
test("explicit reviewed top factor can originate in any of the 20 assessments",()=>{
 const a=advantage({id:"qol-5",assessment:5,title:"Better daily function"});
 const other=advantage({id:"cost-9",assessment:9,rank:1,title:"Cost saving"});
 const data=feed([a,other]);
 data.records[0].overallAdvantages=[{...a,rank:1},{...other,rank:2}];
 const e=competitiveEdge(candidate(),data,[peer()]);
 assert.equal(e.assessment,5);
 assert.equal(e.label,"Top reviewed competitive factor");
 assert.equal(e.overallWinner,false);
});
test("source-verified direct peer comparison requires exact NCT, treatment line, population, endpoint and follow-up",()=>{
 const e={
  programNctId:"NCT12345678",programTicker:"AAA",indication:"Disease Z",programTherapy:"Therapy A",
  verificationStatus:"VERIFIED",lastVerified:"2026-10-30",
  id:"study-c",kind:"PIPELINE",therapy:"Therapy B",manufacturer:"Company B",
  regulatorOrTrialId:"NCT23456789",approvalOrPhase:"Phase 3",lineOfTherapy:"Second-line",
  patientPopulation:"Biomarker-positive adults",sourceUrl:"https://example.org/study",
  sourceDate:"2026-10-20",sourceType:"PUBLICATION",outcome:"Response at 24 weeks",
  effectSize:"Absolute difference 12 percentage points",duration:"24 weeks",safety:"",
  convenience:"",firstYearPrice:"",payerAccess:"",comparisonBasis:"DIRECT_HEAD_TO_HEAD",
  finding:"BETTER",reason:"Favorable response observed",confidence:"HIGH",
  comparisonEvidence:{parentTherapy:"Therapy A",lineOfTherapy:"Second-line",patientPopulation:"Biomarker-positive adults",
   endpoint:"Response at 24 weeks",effectEstimate:0.12,lower95:0.04,upper95:0.20,
   denominator:240,comparatorDenominator:220,followUpMonths:6,
   sourceUrl:"https://example.org/study",verifiedAt:"2026-10-30"}
 };
 const scope={status:"VERIFIED",lineOfTherapy:"Second-line",patientPopulation:"Biomarker-positive adults",
  endpoint:"Response at 24 weeks",followUpMonths:6,sourceUrl:"https://example.org/study",verifiedAt:"2026-10-30"};
 const trial=candidate({competitorEvidence:[e],comparisonScope:scope});
 const supported=competitiveEdge(trial,null,[peer()]);
 assert.equal(supported.status,"SOURCED_FACTOR");
 assert.equal(supported.label,"Reported head-to-head advantage");
 assert.equal(supported.assessment,6);
 assert.equal(supported.overallWinner,false);
 assert.equal(competitiveEdge(trial,null,[peer({nctId:"NCT34567890"})]).status,"NOT_ESTABLISHED");
 assert.equal(competitiveEdge(candidate({...trial,comparisonScope:{...scope,patientPopulation:"Unmatched adults"}}),null,[peer()]).status,"NOT_ESTABLISHED");
 assert.equal(competitiveEdge(candidate({...trial,competitorEvidence:[{...e,comparisonBasis:"INDIRECT"}]}),null,[peer()]).status,"NOT_ESTABLISHED");
});
test("gold bordered reason appears directly AFTER both green A and P cards in shared component",()=>{
 const summary=fs.readFileSync(path.join(__dirname,"../app/TrialTimelineSummary.tsx"),"utf8");
 assert.match(summary,/border:"3px solid #b8860b"/);
 assert.ok(summary.indexOf('aria-label="A: days since Phase 3 readout"')<
  summary.indexOf('aria-label="P: days to PDUFA"'));
 assert.ok(summary.indexOf('aria-label="P: days to PDUFA"')<
  summary.indexOf('aria-label="Gold competitive advantage evidence"'));
 assert.ok(summary.indexOf("{edge.reason}</p>")>summary.indexOf('aria-label="Gold competitive advantage evidence"'));
 assert.ok(summary.indexOf("{edge.reason}</p>")<summary.indexOf("Why? · Evidence and limitations"));
 assert.match(summary,/Why\? · Evidence and limitations/);
 assert.match(summary,/overall clinical superiority/);
});
