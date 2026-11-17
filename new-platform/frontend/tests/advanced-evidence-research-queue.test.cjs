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
const {default:Queue,validAdvancedResearchQueue}=require("../app/AdvancedEvidenceResearchQueue.tsx");
const NCT="NCT00000001";
function good(){
 return {methodVersion:"scientific-advanced-research-queue-v1",nctId:NCT,
  asOf:"2026-02-01",status:"RESEARCH_QUEUE_READY",score:null,
  scientificValidation:"NOT_VERIFIED",fdaPrediction:"ABSTAIN",
  reviewedCriteria:0,unresolvedCriteria:1,deferred:[],
  tasks:[{id:NCT+":L09:benefitEvidence",level:9,criterion:"benefitEvidence",
   state:"NOT_ASSESSED",action:"COLLECT_AND_REVIEW_SOURCE",
   priorityOrder:1,reason:"Find dated source evidence",rejectionReason:null}]};
}
test("exact NCT displays stable priority without scientific rating",()=>{
 const value=good();
 assert.equal(validAdvancedResearchQueue(value,NCT),true);
 const html=renderToStaticMarkup(React.createElement(Queue,{value,nctId:NCT}));
 assert.match(html,/L09/);assert.match(html,/benefitEvidence/);
 assert.match(html,/Workflow order does not represent scientific importance/);
 assert.doesNotMatch(html,/FDA probability: [0-9]/);
});
test("wrong NCT and forged scientific output are not rendered",()=>{
 for(const mutate of [
  d=>{d.nctId="NCT00000002";},
  d=>{d.tasks[0].id="NCT00000002:L09:benefitEvidence";},
  d=>{d.tasks[0].priorityOrder=99;},
  d=>{d.fdaPrediction="APPROVAL";},
  d=>{d.score=100;},
  d=>{d.scientificValidation="VERIFIED";},
  d=>{d.tasks[0].action="AUTO_APPROVE";},
  d=>{d.unresolvedCriteria=0;},
 ]){
  const data=good();mutate(data);
  assert.equal(validAdvancedResearchQueue(data,NCT),false);
  const html=renderToStaticMarkup(React.createElement(Queue,{value:data,nctId:NCT}));
  assert.match(html,/queue unavailable or unverified/);
  assert.doesNotMatch(html,/#1/);
 }
});
test("early-phase future criteria show deferred not adverse",()=>{
 const data=good();
 data.deferred=[{id:NCT+":L13:acceptedFiling",level:13,
  criterion:"acceptedFiling",state:"NOT_YET_EXPECTED",reason:"Not due"}];
 const html=renderToStaticMarkup(React.createElement(Queue,{value:data,nctId:NCT}));
 assert.match(html,/1 criteria not yet expected/);
 assert.match(html,/NOT_YET_EXPECTED/);
});
test("blocked or no tasks cannot imply completion",()=>{
 const value=good();
 value.status="BLOCKED_UNVERIFIED_INTAKE";value.tasks=[];value.unresolvedCriteria=0;
 let html=renderToStaticMarkup(React.createElement(Queue,{value,nctId:NCT}));
 assert.match(html,/Verified trial phase and source cutoff are required/);
 value.status="NO_ACTIVE_GAPS_NOT_SCIENTIFIC_VALIDATION";
 html=renderToStaticMarkup(React.createElement(Queue,{value,nctId:NCT}));
 assert.match(html,/does not mean any scientific level is validated/);
});
test("exact program loader includes read-only research queue",()=>{
 const source=fs.readFileSync(require("node:path").join(__dirname,"../app/ExactTrialScientificIntake.tsx"),"utf8");
 assert.match(source,/AdvancedEvidenceResearchQueue/);
 assert.match(source,/advancedEvidenceQueue/);
 assert.match(source,/nctId=\{nctId\}/);
});
