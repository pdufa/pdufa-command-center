"use strict";
const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const ts=require("typescript");
for(const ext of [".ts",".tsx"])require.extensions[ext]=(mod,file)=>mod._compile(
  ts.transpileModule(fs.readFileSync(file,"utf8"),{
    compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}
  }).outputText,file
);
const {BENEFIT_GROUPS,parseBenefitFeed,benefitForTrial,rankAdvantages}=require("../lib/benefit-assessments.ts");
const nctId="NCT12345678",identity={nctId,ticker:"EXAM",drug:"Therapy A",indication:"Disease A"};
const fact={value:100,status:"VERIFIED",sourceUrl:"https://example.org/primary",sourceDate:"2026-10-20",method:"Primary-source eligibility matching",confidence:"MODERATE"};
const advantage=(id,assessment,rank)=>({
  id,assessment,rank,title:"Better endpoint",comparator:"Standard drug",comparison:"Absolute difference 5 pp",
  sourceUrl:"https://example.org/study",sourceDate:"2026-10-20",method:"Direct endpoint comparison",confidence:"MODERATE",status:"VERIFIED"
});
const good=()=>({schemaVersion:1,sourceAsOf:"2026-10-20",records:[{...identity,facts:{eligibleUsPatients:{...fact}},advantages:[advantage("a",1,1),advantage("b",1,2)],overallAdvantages:[advantage("b",1,1),advantage("a",1,2)]}]});
test("canonical 20 headings map original assessment source fields, without duplicate groups",()=>{
  const other=require("../lib/pipeline-benefit-assessments.ts").RANKED_BENEFIT_ASSESSMENTS;
  assert.equal(BENEFIT_GROUPS.length,20);
  assert.deepEqual(BENEFIT_GROUPS.map(g=>g.name),other.map(g=>g.title));
  assert.deepEqual(BENEFIT_GROUPS.map(g=>g.fields.map(f=>f.id)),other.map(g=>g.fields));
  assert.ok(BENEFIT_GROUPS.every(g=>g.fields.length>0));
});
test("missing research is an empty feed, not a false zero benefit",()=>{
  const blank=parseBenefitFeed({schemaVersion:1,sourceAsOf:null,records:[]});
  assert.deepEqual(blank.records,[]);
  assert.equal(benefitForTrial(blank,identity),null);
  assert.deepEqual(rankAdvantages(null,1),[]);
});
test("exact NCT, ticker, drug and indication required; ticker alone cannot join benefits",()=>{
  const feed=parseBenefitFeed(good());
  assert.ok(benefitForTrial(feed,identity));
  assert.equal(benefitForTrial(feed,{...identity,nctId:"NCT87654321"}),null);
  assert.equal(benefitForTrial(feed,{...identity,drug:"Therapy B"}),null);
  assert.equal(benefitForTrial(feed,{...identity,indication:"Other disease"}),null);
  assert.equal(benefitForTrial(feed,{...identity,ticker:"OTHER"}),null);
  assert.equal(benefitForTrial(feed,{...identity,drug:""}),null);
});
test("assessment rankings and independently reviewed overall rankings remain separate",()=>{
  const record=parseBenefitFeed(good()).records[0];
  assert.deepEqual(rankAdvantages(record,1).map(x=>x.id),["a","b"]);
  assert.deepEqual(rankAdvantages(record).map(x=>x.id),["b","a"]);
});
test("unverified or malformed source input cannot become a clinical or competitive claim",()=>{
  const badDate=good();badDate.records[0].facts.eligibleUsPatients.sourceDate="2026-99-99";
  assert.throws(()=>parseBenefitFeed(badDate),/BENEFIT_FACT_INVALID/);
  const badSource=good();badSource.records[0].advantages[0].sourceUrl="http://insecure.org";
  assert.throws(()=>parseBenefitFeed(badSource),/BENEFIT_ADVANTAGE_INVALID/);
  const duplicate=good();duplicate.records[0].advantages[1].rank=1;
  assert.throws(()=>parseBenefitFeed(duplicate),/BENEFIT_RANK_DUPLICATED/);
  const wrongOverall=good();wrongOverall.records[0].overallAdvantages[0].id="foreign";
  assert.throws(()=>parseBenefitFeed(wrongOverall),/BENEFIT_OVERALL_RANK_INVALID/);
});
test("Step 4 mounts all twenty linked assessment choices directly above Step 5; detailed audit remains optional",()=>{
  const page=fs.readFileSync(path.join(__dirname,"../app/PoolStageExplorer.tsx"),"utf8");
  const section=fs.readFileSync(path.join(__dirname,"../app/ToolsAssessmentSection.tsx"),"utf8");
  const matrix=fs.readFileSync(path.join(__dirname,"../app/ToolsBenefitMatrix.tsx"),"utf8");
  const css=fs.readFileSync(path.join(__dirname,"../app/ToolsBenefitMatrix.module.css"),"utf8");
  assert.ok(page.indexOf("<ToolsAssessmentSection")<page.indexOf('id="tools-final-trial-spreadsheet"'));
  assert.ok(page.indexOf('id="tools-final-trial-spreadsheet"')<page.indexOf("<ToolsResultsSpreadsheet"));
  assert.match(section,/<ToolsBenefitMatrix/);
  assert.doesNotMatch(fs.readFileSync(path.join(__dirname,"../app/ToolsResultsSpreadsheet.tsx"),"utf8"),/<ToolsBenefitMatrix/);
  assert.match(matrix,/BENEFIT_GROUPS\.map/);
  assert.match(matrix,/aria-label="Step 4 five assessment groups"/);
  assert.match(matrix,/aria-label="Step 4 assessment 4a1 through 4a20"/);
  assert.match(matrix,/STEP4_SECTIONS\.map/);
  assert.match(matrix,/BENEFIT_GROUPS\.filter/);
  assert.match(matrix,/aria-label="Step 4 organization mode"/);
  assert.match(matrix,/const PRIORITY_RESEARCH=\[3,6,8,1,2,12,15,19,20\]/);
  assert.match(matrix,/PRIORITY_RESEARCH\.map\(n=>BENEFIT_GROUPS\[n-1\]\)/);
  assert.match(matrix,/mode==="clinical"\?BENEFIT_GROUPS\.filter/);
  assert.match(matrix,/modeChoices\.map/);
  assert.match(matrix,/sourceVerified=current\.fields\.filter/);
  assert.match(matrix,/scenarioModeled=current\.fields\.filter/);
  assert.match(css,/\.modeBar\{display:flex/);
  assert.match(css,/\.evidenceSummary\{/);
  assert.match(matrix,/<details className=\{css\.fullAssessmentList\} id="tools-step4-all20">/);
  assert.match(matrix,/aria-label="Complete separate Step 4 assessment list 1 through 20"/);
  assert.match(matrix,/\{"Assessment "\+g\.number\+" of 20 — "\+g\.name\}/);
  assert.match(matrix,/setActive\(g\.number\);setMode\("all"\);event\.currentTarget\.closest\("details"\)\?\.removeAttribute\("open"\)/);
  assert.match(css,/\.fullAssessmentGrid\{display:grid/);
  assert.match(matrix,/onClick=\{\(\)=>\{setMode\("category"\);setActive\(section\.start\);\}\}/);
  assert.match(matrix,/<details className=\{css\.researchDisclosure\} id="tools-step4-analysis">/);
  assert.match(css,/\.step4GroupButtons\{display:grid/);
  assert.match(css,/grid-template-columns:repeat\(5,minmax\(0,1fr\)\)/);
  assert.match(css,/\.step4GroupButtons\{grid-template-columns:repeat\(2,minmax\(0,1fr\)\)/);
  assert.match(matrix,/<div className=\{css\.step4CategoryPanel\}>/);
  assert.doesNotMatch(matrix,/mode==="category"&&<div className=\{css\.step4CategoryPanel\}>/);
  assert.match(matrix,/aria-pressed=\{mode==="category"&&selectedSection\.code===section\.code\}/);
  assert.match(css,/\.step4MetricPicker/);
  assert.match(matrix,/colSpan=\{active===g\.number\?g\.fields\.length\+2:1\}/);
  assert.match(matrix,/id="benefit-group-picker"/);
  assert.match(matrix,/id="benefit-trial-picker"/);
  assert.match(matrix,/rankAdvantages\(evidence,active\)/);
  assert.match(css,/@media\(max-width:800px\)/);
  assert.match(css,/\.mobile\{display:none\}/);
  assert.match(css,/\.mobile\{display:block\}/);
});
