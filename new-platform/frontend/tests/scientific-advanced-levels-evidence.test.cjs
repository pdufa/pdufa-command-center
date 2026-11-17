const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const ts=require("typescript");
const React=require("react");
const {renderToStaticMarkup}=require("react-dom/server");
require.extensions[".tsx"]=(mod,file)=>mod._compile(ts.transpileModule(fs.readFileSync(file,"utf8"),{
 compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,
 jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}
}).outputText,file);
const {default:Advanced,validAdvancedScientificLevels}=require("../app/ScientificAdvancedLevelsEvidence.tsx");

function levels(){
 const data={};
 for(let i=9;i<=20;i++)data[String(i)]={
  level:i,name:"Synthetic "+i,status:"AWAITING_REVIEW",
  methodStatus:"PARTIAL_SOURCE_METHOD_NOT_VALIDATED",
  criteria:{sourceEvidence:"NOT_ASSESSED"},score:null,
  scientificValidation:"NOT_VERIFIED",fdaPrediction:"ABSTAIN",reviewedCount:0};
 return data;
}
test("all twelve numbered partial source contracts are visible with warnings",()=>{
 const value=levels();
 const html=renderToStaticMarkup(React.createElement(Advanced,{value}));
 assert.equal(validAdvancedScientificLevels(value),true);
 for(let n=9;n<=20;n++)assert.match(html,new RegExp("Level "+n+":"));
 assert.match(html,/NOT_VALIDATED/);
 assert.match(html,/FDA predictions ABSTAIN/);
 assert.match(html,/Freeze digests are not proof/);
 assert.match(html,/Official postdecision outcomes must remain separate/);
});
test("only explicitly unvalidated method status can be rendered",()=>{
 const value=levels();value["13"].filingContext={
  score:null,scientificValidation:"NOT_VERIFIED",fdaPrediction:"ABSTAIN",
  status:"DATED_FILING_RECORDS_RECONCILED_NOT_AGENCY_CERTIFICATION"};
 const html=renderToStaticMarkup(React.createElement(Advanced,{value}));
 assert.match(html,/DATED_FILING_RECORDS_RECONCILED_NOT_AGENCY_CERTIFICATION/);
 value["13"].filingContext.fdaPrediction="APPROVED";
 assert.doesNotMatch(renderToStaticMarkup(React.createElement(Advanced,{value})),
 /DATED_FILING_RECORDS_RECONCILED_NOT_AGENCY_CERTIFICATION/);
});
test("nonabstaining score or forged activation fails closed for entire panel",()=>{
 for(const mutate of [
   d=>{d["10"].score=100;},
   d=>{d["11"].fdaPrediction="APPROVED";},
   d=>{d["12"].methodStatus="SCIENTIFICALLY_VALIDATED";},
   d=>{d["13"].scientificValidation="VERIFIED";},
   d=>{delete d["20"];},
   d=>{d["19"].criteria={targetOutcome:{untrusted:"YES"}};},
 ]){
  const value=levels();mutate(value);
  assert.equal(validAdvancedScientificLevels(value),false);
  const html=renderToStaticMarkup(React.createElement(Advanced,{value}));
  assert.match(html,/source-review contracts unavailable or unverified/);
  assert.doesNotMatch(html,/Level 9:/);
 }
});
test("exact-trial loader provides the same read-only panel to POOL, FOCUS and PAST",()=>{
 const loader=fs.readFileSync(require("node:path").join(__dirname,"../app/ExactTrialScientificIntake.tsx"),"utf8");
 assert.match(loader,/ScientificAdvancedLevelsEvidence/);
 assert.match(loader,/ScientificAdvancedLevelsEvidence value=\{extensions\}/);
 assert.match(loader,/type Cohort="POOL"\|"FOCUS"\|"PAST"/);
});
