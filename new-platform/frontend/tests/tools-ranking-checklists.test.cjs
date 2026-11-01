"use strict";
const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const ts=require("typescript");
for(const ext of [".ts",".tsx"])require.extensions[ext]=(mod,file)=>mod._compile(
 ts.transpileModule(fs.readFileSync(file,"utf8"),{compilerOptions:{
  module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true
 }}).outputText,file
);
const {TOOLS_RANKING_GROUPS,rankingTaxonomyAudit,selectedAssessmentIds,movePriority,
 normalizeRankingSelection}=require("../lib/tools-ranking-config.ts");
const {BENEFIT_GROUPS}=require("../lib/benefit-assessments.ts");
const source=name=>fs.readFileSync(path.join(__dirname,"../app",name),"utf8");
test("six ranking groups map each of the exact 20 original assessments once",()=>{
 const audit=rankingTaxonomyAudit();
 assert.equal(TOOLS_RANKING_GROUPS.length,6);
 assert.equal(audit.total,20);
 assert.equal(audit.originalTotal,20);
 assert.deepEqual(audit.duplicates,[]);
 assert.deepEqual(audit.missing,[]);
 assert.deepEqual(audit.unknown,[]);
 assert.equal(BENEFIT_GROUPS[5].name,"Competitive Advantage");
 assert.deepEqual(selectedAssessmentIds([1]),[2,3,4,5,8]);
});
test("each cascading level allows only verified canonical child selections",()=>{
 const raw={
  groupIds:[1,1,2,88],
  groupAssessments:[2,3,6,12,20],
  groupCriteria:{"2":["standardOfCare","standardOfCare","not-a-field"],
   "3":["clinicalBenefit","seriousAes"],
   "6":["headToHead"],"20":["shareholderRisk"]},
  priorities:[20,3,20,88],
  priorityCriteria:{"20":["shareholderRisk","clinicalBenefit"],
    "3":["magnitude","not-a-field"]}
 };
 const r=normalizeRankingSelection(raw);
 assert.deepEqual(r.groupIds,[1,2]);
 assert.deepEqual(r.groupAssessments,[2,3,6]);
 assert.deepEqual(r.groupCriteria["2"],["standardOfCare"]);
 assert.deepEqual(r.groupCriteria["3"],["clinicalBenefit"]);
 assert.deepEqual(r.groupCriteria["6"],["headToHead"]);
 assert.equal(r.groupCriteria["20"],undefined);
 assert.deepEqual(r.priorities,[20,3]);
 assert.deepEqual(r.priorityCriteria["20"],["shareholderRisk"]);
 assert.deepEqual(r.priorityCriteria["3"],["magnitude"]);
});
test("unchecking a group automatically clears its assessment and metric cascade only",()=>{
 const state=normalizeRankingSelection({
  groupIds:[1,2],groupAssessments:[3,6],
  groupCriteria:{"3":["clinicalBenefit"],"6":["headToHead"]},
  priorities:[3],priorityCriteria:{"3":["clinicalBenefit"]}
 });
 const next=normalizeRankingSelection({...state,groupIds:[2]});
 assert.deepEqual(next.groupAssessments,[6]);
 assert.deepEqual(next.groupCriteria,{"6":["headToHead"]});
 assert.deepEqual(next.priorities,[3]);
 assert.deepEqual(next.priorityCriteria,{"3":["clinicalBenefit"]});
});
test("priorities re-order uniquely without changing canonical assessment numbering",()=>{
 const current=[3,8,6];
 assert.deepEqual(movePriority(current,6,1),[6,3,8]);
 assert.deepEqual(movePriority(current,3,3),[8,6,3]);
 assert.deepEqual(movePriority(current,8,999),[3,6,8]);
 assert.deepEqual(movePriority(current,19,1),current);
 assert.deepEqual(normalizeRankingSelection(null).priorities,[]);
});
test("independent left and right cards are collapsed, side-by-side on iPhone and summary closed",()=>{
 const comp=source("ToolsRankingChecklists.tsx");
 const css=source("ToolsRankingChecklists.module.css");
 const tools=source("ToolsResultsSpreadsheet.tsx");
 assert.match(css,/grid-template-columns:repeat\(2,minmax\(0,1fr\)\)/);
 assert.match(css,/@media\(max-width:480px\)/);
 assert.equal((comp.match(/<details className=\{css.panel\}>/g)||[]).length,2);
 assert.match(comp,/<details className=\{css.results\}>/);
 assert.match(comp,/Rank Trials By/);
 assert.match(comp,/Rank 20 Assessments/);
 assert.match(comp,/Selected Ranking Criteria/);
 assert.match(comp,/priorityCriteria/);
 assert.match(comp,/window.localStorage.setItem/);
 assert.ok(tools.indexOf("<h3>Matching trial records</h3>")<
  tools.indexOf("<ToolsRankingChecklists/>"));
 assert.ok(tools.indexOf("<ToolsRankingChecklists/>")<
  tools.indexOf("Scrollable spreadsheet containing selected trial matches"));
 // The Phase/FDA source filter rows, benefits matrix, pagination and export remain.
 assert.match(tools,/ToolsBenefitMatrix/);
 assert.match(tools,/designationCoverage/);
 assert.match(tools,/Export all matches \(CSV\)/);
 assert.match(tools,/Previous 50/);
});
