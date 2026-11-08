const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const vm=require("node:vm");
const path=require("node:path");
const ts=require("typescript");

function load(name){
 const file=fs.readFileSync(path.join(__dirname,"../lib/"+name+".ts"),"utf8");
 const compiled=ts.transpileModule(file,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
 const m={exports:{}};
 vm.runInNewContext(compiled,{module:m,exports:m.exports});
 return m.exports;
}
const {rankTrialAssessments,rankAtLastCompletedPhase,TEST_GRADE_RUBRIC,PHASE_REVIEW_STANDARD}=load("medical-intelligence-assessment-rankings");
const {DEEP_ASSESSMENTS}=load("medical-intelligence-master-depth");
const NCT="NCT06081894";
const phase="PHASE1";
function scored(assessmentId,level,grade){
 return {nct:NCT,phase,assessmentId,level,disposition:"SCORED",grade,
  evidenceUrls:["https://clinicaltrials.gov/study/"+NCT],
  rationale:"Exact trial original-source method evaluation and documented limitations",
  recordedAt:"2026-11-08"};
}
function na(assessmentId,level){
 return {nct:NCT,phase,assessmentId,level,disposition:"NOT_APPLICABLE",
  evidenceUrls:[],rationale:"This method requires data not applicable to the current verified Phase 1 design",
  recordedAt:"2026-11-08"};
}
test("all 40 assessments exist and remain unrated without actual independent test reviews",()=>{
 const rows=rankTrialAssessments(DEEP_ASSESSMENTS,NCT,phase,[]);
 assert.equal(rows.length,40);
 assert.ok(rows.every(r=>r.score===null&&r.rank===null&&r.status==="NOT_REVIEWED"));
 assert.ok(rows.every(r=>r.unreviewedTests===20));
 assert.match(PHASE_REVIEW_STANDARD.PHASE1,/no pivotal-efficacy requirement/);
 assert.equal(TEST_GRADE_RUBRIC.length,6);
});
test("original-source ranked test gets a 0-100 provisional assessment score with denominator",()=>{
 const rows=rankTrialAssessments(DEEP_ASSESSMENTS,NCT,phase,[scored("1.1",1,4),scored("1.1",2,2),na("1.1",20)]);
 const first=rows.find(r=>r.id==="1.1");
 assert.equal(first.score,60);
 assert.equal(first.status,"PROVISIONAL");
 assert.equal(first.scoredTests,2);
 assert.equal(first.excludedTests,1);
 assert.equal(first.applicableTests,19);
 assert.equal(first.unreviewedTests,17);
 assert.equal(first.rank,null);
});
test("only complete applicable tests can enter scientifically comparable assessment ranking",()=>{
 const reviews=[
  ...Array.from({length:20},(_,i)=>scored("1.1",i+1,4)),
  ...Array.from({length:19},(_,i)=>scored("1.2",i+1,5)),
  na("1.2",20),
  scored("1.3",1,5)
 ];
 const rows=rankTrialAssessments(DEEP_ASSESSMENTS,NCT,phase,reviews);
 assert.equal(rows.find(r=>r.id==="1.1").rank,2);
 assert.equal(rows.find(r=>r.id==="1.1").score,80);
 assert.equal(rows.find(r=>r.id==="1.2").rank,1);
 assert.equal(rows.find(r=>r.id==="1.2").score,100);
 assert.equal(rows.find(r=>r.id==="1.3").status,"PROVISIONAL");
 assert.equal(rows.find(r=>r.id==="1.3").rank,null);
});
test("grade input validation rejects unverified phase, duplicate marks, invalid grade and missing sources",()=>{
 assert.throws(()=>rankTrialAssessments(DEEP_ASSESSMENTS,NCT,"UNKNOWN",[{...scored("1.1",1,5),phase:"UNKNOWN"}]),/Verify the registry phase/);
 assert.throws(()=>rankTrialAssessments(DEEP_ASSESSMENTS,NCT,phase,[scored("1.1",1,3),scored("1.1",1,4)]),/Duplicate scientific/);
 assert.throws(()=>rankTrialAssessments(DEEP_ASSESSMENTS,NCT,phase,[{...scored("1.1",1,5),grade:7}]),/integer from 0 to 5/);
 assert.throws(()=>rankTrialAssessments(DEEP_ASSESSMENTS,NCT,phase,[{...scored("1.1",1,5),evidenceUrls:[]}]),/original-source/);
 assert.throws(()=>rankTrialAssessments(DEEP_ASSESSMENTS,NCT,phase,[{...scored("1.1",1,5),phase:"PHASE3"}]),/exact NCT and verified phase/);
});

const past={
 sourceNct:"NCT05507203",
 completedPhase:"PHASE2",
 phaseCompletedOn:"2025-02-01",
 readoutDate:"2025-03-05",
 sourceUrls:["https://clinicaltrials.gov/study/NCT05507203"],
 exactDrugAndIndicationMatchVerified:true,
 finalOrPrimaryPhaseResultsVerified:true,
};
const current={nct:NCT,phase:"PHASE3",status:"ONGOING"};
const priorReview=(level,grade)=>({
 nct:past.sourceNct,phase:past.completedPhase,assessmentId:"1.1",level,
 disposition:"SCORED",grade,evidenceUrls:past.sourceUrls,
 rationale:"Original completed phase outcome, full source and patient endpoint audit",
 recordedAt:"2026-11-08",sourcePublishedOn:"2025-03-05",phaseEndResultVerified:true
});
test("a Phase 3 trial is based on its verified Phase 2 end results, not current Phase 3",()=>{
 const r=rankAtLastCompletedPhase(DEEP_ASSESSMENTS,current,past,[priorReview(1,4),priorReview(2,3)]);
 assert.equal(r.basis,"LAST_COMPLETED_PHASE");
 assert.equal(r.completedPhase,"PHASE2");
 assert.equal(r.completedPhaseNct,past.sourceNct);
 const first=r.assessments.find(x=>x.id==="1.1");
 assert.equal(first.scoredTests,2);
 assert.equal(first.score,70);
 assert.equal(first.status,"PROVISIONAL");
 assert.equal(first.rank,null);
});
test("missing last-phase completion stays pending without a fabricated zero or rank",()=>{
 const r=rankAtLastCompletedPhase(DEEP_ASSESSMENTS,current,null,[]);
 assert.equal(r.basis,"NO_VERIFIED_PHASE_END");
 assert.equal(r.assessments.length,40);
 assert.ok(r.assessments.every(x=>x.score===null && x.rank===null));
 assert.throws(()=>rankAtLastCompletedPhase(DEEP_ASSESSMENTS,current,null,[priorReview(1,3)]),/Cannot grade/);
});
test("prevent cross-program mixing, phase future leakage and scoring unsupported signals",()=>{
 assert.throws(()=>rankAtLastCompletedPhase(DEEP_ASSESSMENTS,current,{...past,exactDrugAndIndicationMatchVerified:false},[]),/drug, indication/);
 assert.throws(()=>rankAtLastCompletedPhase(DEEP_ASSESSMENTS,current,{...past,completedPhase:"PHASE4"},[]),/later phase/);
 assert.throws(()=>rankAtLastCompletedPhase(DEEP_ASSESSMENTS,current,{...past,completedPhase:"PHASE3"},[]),/unfinished current/);
 assert.throws(()=>rankAtLastCompletedPhase(DEEP_ASSESSMENTS,current,past,[{...priorReview(1,4),nct:NCT}]),/exact completed-phase/);
 assert.throws(()=>rankAtLastCompletedPhase(DEEP_ASSESSMENTS,current,past,[{...priorReview(1,4),phaseEndResultVerified:false}]),/speculative signal/);
 assert.throws(()=>rankAtLastCompletedPhase(DEEP_ASSESSMENTS,current,past,[{...priorReview(1,4),sourcePublishedOn:"2027-01-01"}]),/dated phase-end source/);
});
test("completed Phase 3 can be the last completed phase if a new phase has not begun",()=>{
 const r=rankAtLastCompletedPhase(DEEP_ASSESSMENTS,
   {nct:NCT,phase:"PHASE3",status:"COMPLETED"},
   {...past,sourceNct:NCT,completedPhase:"PHASE3"},[]);
 assert.equal(r.completedPhase,"PHASE3");
});
