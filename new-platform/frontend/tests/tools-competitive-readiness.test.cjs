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
const {competitiveReadiness,scanCompetitivePopulation}=require("../lib/tools-competitive-readiness.ts");
const {parseBenefitFeed}=require("../lib/benefit-assessments.ts");
const today="2026-11-01";
const readout={date:"2026-10-15",sourceUrl:"https://clinicaltrials.gov/study/NCT12345678",status:"VERIFIED"};
const target={date:"2026-11-28",sourceUrl:"https://www.fda.gov/example",status:"VERIFIED"};
const row=(nctId="NCT12345678",timeline={phase3DataRelease:readout,pdufaTarget:target})=>({
 nctId,ticker:"EXAM",drug:"Examumab",indication:"Example disease",stage:"Phase 3 Results",timeline
});
const savedFact=(value)=>({value,status:"VERIFIED",sourceUrl:"https://clinicaltrials.gov/study/NCT12345678",
  sourceDate:"2026-10-15",method:"Source comparison reviewed for this exact trial",confidence:"HIGH"});
const record=(nctId,fields)=>({nctId,ticker:"EXAM",drug:"Examumab",indication:"Example disease",
  facts:fields,advantages:[]});
test("source-verified public Phase 3 release and PDUFA dates determine the research gate",()=>{
 const a=competitiveReadiness(row(),today);
 assert.equal(a.status,"RESEARCH_WINDOW_OPEN");
 assert.equal(a.daysSinceReadout,17);
 assert.equal(a.daysToPdufa,27);
 assert.equal(a.readyToRank,false);
 assert.equal(a.evidence,"NOT_ASSESSED");
 assert.equal(competitiveReadiness(row("NCT12345679",{phase3DataRelease:readout,pdufaTarget:null}),today).status,
  "PDUFA_DATE_UNVERIFIED");
 assert.equal(competitiveReadiness(row("NCT12345680",{phase3DataRelease:null,pdufaTarget:target}),today).status,
  "NO_VERIFIED_PUBLIC_READOUT");
 assert.equal(competitiveReadiness(row("NCT12345681",{
   phase3DataRelease:readout,pdufaTarget:{...target,date:"2026-11-03"}}),today).status,
  "PDUFA_CUTOFF_REACHED");
 assert.equal(competitiveReadiness(row("NCT12345682",{
   phase3DataRelease:{...readout,date:"2026-11-04"},pdufaTarget:target
 }),today).status,"NO_VERIFIED_PUBLIC_READOUT","A future readout cannot qualify as released data");
});
test("all restricted POOL trials are scanned; totals partition exact research gates",()=>{
 const rows=[row(),row("NCT12345679",{phase3DataRelease:readout,pdufaTarget:null}),
  row("NCT12345680",{phase3DataRelease:null,pdufaTarget:null}),
  row("NCT12345681",{phase3DataRelease:readout,pdufaTarget:{...target,date:"2026-11-03"}})];
 const s=scanCompetitivePopulation(rows,today,"2026-10-26");
 assert.equal(s.populationCount,4);
 assert.equal(s.verifiedPublicReadouts,3);
 assert.equal(s.withoutVerifiedReadout,1);
 assert.equal(s.openResearchWindow,1);
 assert.equal(s.unknownPdufa,1);
 assert.equal(s.pastResearchCutoff,1);
 assert.equal(s.qualification,"NOT_VERIFIED");
 assert.equal(s.evidenceCoverage,"NOT_COMPUTED_FOR_FULL_POOL");
 assert.throws(()=>scanCompetitivePopulation([...rows,row()],today,"2026-10-26"),
  /DUPLICATED_COMPETITIVE_TRIAL_ID/);
});
test("six topics use only exact identity/source-checked facts; coverage never creates stock rank",()=>{
 const fields={closestCompetitor:savedFact("Comparator A"),clinicalBenefit:savedFact("Endpoint result"),
  competitivePipelineThreat:savedFact("Competitor trial source"),
  payerAccess:savedFact("Payer coverage assumption"),
  exclusivity:savedFact("Patent date"),valuationImpact:savedFact("Valuation scenario")};
 const feed=parseBenefitFeed({schemaVersion:1,sourceAsOf:"2026-10-15",records:[record("NCT12345678",fields)]});
 const full=competitiveReadiness(row(),today,feed);
 assert.equal(full.verifiedTopics,6);
 assert.equal(full.evidence,"EVIDENCE_REVIEW_READY");
 assert.equal(full.readyToRank,false,"Six sourced categories never establish comparative winner");
 assert.equal(full.topics.find(t=>t.key==="MED").verified,1);
 assert.ok(full.topics.every(t=>t.sources.every(x=>x.sourceUrl.startsWith("https://"))));
 const mismatched=competitiveReadiness(row("NCT12345679",{phase3DataRelease:readout,pdufaTarget:target}),today,feed);
 assert.equal(mismatched.verifiedTopics,0);
 assert.equal(mismatched.evidence,"NOT_ASSESSED","Never match by ticker alone");
 const noRelease=competitiveReadiness(row("NCT12345678",{phase3DataRelease:null,pdufaTarget:target}),today,feed);
 assert.equal(noRelease.verifiedTopics,0,"No proven released results: do not claim topic evidence");
});
test("full-screened-window audit reports exact-NCT verified, modeled and missing CS inputs",()=>{
 const fields={
  closestCompetitor:savedFact("Comparator A"),
  clinicalBenefit:savedFact("Endpoint source"),
  competitivePipelineThreat:savedFact("Rival trial"),
  payerAccess:savedFact("Coverage source"),
  exclusivity:savedFact("Patent citation"),
  valuationImpact:savedFact("Scenario citation")
 };
 const feed=parseBenefitFeed({schemaVersion:1,sourceAsOf:"2026-10-15",
  records:[record("NCT12345678",fields)]});
 const eligible=[row(),row("NCT12345679"),row("NCT12345680",{
   phase3DataRelease:null,pdufaTarget:target
 })];
 const result=scanCompetitivePopulation(eligible,today,"2026-10-26",feed);
 assert.equal(result.populationCount,3);
 assert.equal(result.openResearchWindow,2);
 assert.equal(result.evidenceCoverage,"SOURCE_INPUT_AUDIT_IN_WINDOW");
 assert.deepEqual(result.topicSourceAudit,{
  eligibleTrials:2,topicSlots:12,verifiedSlots:6,modeledOnlySlots:0,
  missingSlots:6,verifiedPercent:50,trialsWithSixVerifiedTopics:1,
  sourceFeedAsOf:"2026-10-15"
 });
 assert.equal(result.qualification,"NOT_VERIFIED");
 const noFacts=scanCompetitivePopulation(eligible,today,"2026-10-26",
  parseBenefitFeed({schemaVersion:1,sourceAsOf:null,records:[]}));
 assert.equal(noFacts.topicSourceAudit.verifiedSlots,0);
 assert.equal(noFacts.topicSourceAudit.missingSlots,12);
 assert.equal(noFacts.topicSourceAudit.verifiedPercent,0);
 const noEligible=scanCompetitivePopulation([eligible[2]],today,"2026-10-26",feed);
 assert.equal(noEligible.topicSourceAudit.verifiedPercent,null);
 assert.equal(noEligible.topicSourceAudit.topicSlots,0);
 const notLoaded=scanCompetitivePopulation(eligible,today,"2026-10-26");
 assert.equal(notLoaded.topicSourceAudit,null);
 assert.equal(notLoaded.evidenceCoverage,"NOT_COMPUTED_FOR_FULL_POOL");
});
test("Step 5 wires full-population scan and per-row disclosures without overwriting CS ranking",()=>{
 const root=path.join(__dirname,"..");
 const api=fs.readFileSync(path.join(root,"app/api/scope-funnel/route.ts"),"utf8");
 const pool=fs.readFileSync(path.join(root,"app/PoolStageExplorer.tsx"),"utf8");
 const ui=fs.readFileSync(path.join(root,"app/ToolsOpeningTrialGrid.tsx"),"utf8");
 assert.match(api,/competitionPopulation=inventory\.poolRows\.filter\(isPoolTrial\)/);
 assert.match(api,/scanCompetitivePopulation\(/);
 assert.match(api,/parseBenefitFeed\(JSON\.parse\(content\)\)/);
 assert.match(ui,/topicSourceAudit\.verifiedSlots/);
 assert.match(ui,/topicSourceAudit\.missingSlots/);
 assert.match(api,/competitiveScan,designationTotals/);
 assert.match(pool,/competitiveScan=\{page\?\.competitiveScan\?\?null\}/);
 assert.match(ui,/CS Research Readiness Scan/);
 assert.match(ui,/competitiveReadiness\(row,today,competitionEvidence\)/);
 assert.match(ui,/Not ranked/);
 assert.match(ui,/Not assessed/);
});
