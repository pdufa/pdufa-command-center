const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const vm=require("node:vm");
const path=require("node:path");
const ts=require("typescript");
function load(name, deps={}){
 const file=fs.readFileSync(path.join(__dirname,"../lib/"+name+".ts"),"utf8");
 const js=ts.transpileModule(file,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
 const m={exports:{}};
 vm.runInNewContext(js,{module:m,exports:m.exports,require:(name)=> {
  if(!Object.hasOwn(deps,name))throw Error("Unexpected dependency "+name);
  return deps[name];
 }});
 return m.exports;
}
const ranks=load("medical-intelligence-assessment-rankings");
const {DEEP_ASSESSMENTS}=load("medical-intelligence-master-depth");
const {assessLatestPhaseActivity,PHASE_RISK_WATCHLIST}=load("medical-intelligence-phase-snapshot",{
 "./medical-intelligence-assessment-rankings":ranks,
});
const NCT="NCT06081894", phase="PHASE3", asOf="2026-11-08";
const url="https://clinicaltrials.gov/study/"+NCT;
function event(id,kind,occurredOn,publishedOn=occurredOn,verified=true){
 return {id,nct:NCT,phase,kind,occurredOn,publishedOn,title:"Source-dated and clinically verifiable event",verified,sourceUrls:[url]};
}
function review(milestoneId,domain="EXECUTION",grade=4){
 return {milestoneId,domain,nct:NCT,phase,assessmentId:"4.1",level:1,
  disposition:"SCORED",grade,evidenceUrls:[url],
  rationale:"Direct original source evaluated against the selected current-phase milestone",
  sourcePublishedOn:"2026-11-06",recordedAt:"2026-11-08"};
}
function risk(milestoneId,level="HIGH",state="OPEN"){
 return {milestoneId,nct:NCT,phase,domain:"TRIAL_EXECUTION",level,state,
  finding:"Source-verified enrollment delays and remaining site-activation limitations",
  evidenceUrls:[url]};
}
test("current phase without a verified event has unanswered grade and phase risks to monitor, not invented observed risks",()=>{
 const r=assessLatestPhaseActivity(DEEP_ASSESSMENTS,NCT,phase,asOf,[],[],[]);
 assert.equal(r.latestVerifiedMilestone,null);
 assert.equal(r.currentScores.length,40);
 assert.ok(r.currentScores.every(row=>row.score===null&&row.rank===null));
 assert.equal(r.activeRisks.length,0);
 assert.ok(r.watchlist.some(x=>x.domain==="STATISTICS"));
});
test("latest enrolled patients update grades execution only and highlights actual open risks",()=>{
 const older=event("first","PRIMARY_READOUT","2026-11-01");
 const latest=event("second","ENROLLMENT_UPDATE","2026-11-06");
 const grades=[{...review("first","EFFICACY",5),sourcePublishedOn:"2026-11-01"},
  review("second","EXECUTION",2)];
 const r=assessLatestPhaseActivity(DEEP_ASSESSMENTS,NCT,phase,asOf,[older,latest],grades,[risk("second","HIGH")]);
 assert.equal(r.latestVerifiedMilestone.id,"second");
 const row=r.currentScores.find(x=>x.id==="4.1");
 assert.equal(row.score,40);
 assert.equal(row.scoredTests,1);
 assert.equal(row.status,"PROVISIONAL");
 assert.equal(r.activeRisks[0].level,"HIGH");
 assert.equal(r.activeRisks[0].state,"OPEN");
});
test("future, unverified, mismatched, and unsupported event types never create scientific grades",()=>{
 const update=event("new","ENROLLMENT_UPDATE","2026-11-06");
 assert.throws(()=>assessLatestPhaseActivity(DEEP_ASSESSMENTS,NCT,phase,asOf,[update],[review("new","EFFICACY",5)],[]),/outside its observed test domain/);
 assert.throws(()=>assessLatestPhaseActivity(DEEP_ASSESSMENTS,NCT,phase,asOf,[{...update,verified:false}],[review("new")],[]),/verified dated source/);
 assert.throws(()=>assessLatestPhaseActivity(DEEP_ASSESSMENTS,NCT,phase,asOf,[{...update,occurredOn:"2026-11-09",publishedOn:"2026-11-09"}],[],[]),/not future/);
 assert.throws(()=>assessLatestPhaseActivity(DEEP_ASSESSMENTS,NCT,phase,asOf,[{...update,phase:"PHASE2"}],[],[]),/exact NCT/);
 const other=event("complete","PHASE_COMPLETION","2026-11-07");
 assert.throws(()=>assessLatestPhaseActivity(DEEP_ASSESSMENTS,NCT,phase,asOf,[other],[{...review("complete"),sourcePublishedOn:"2026-11-07"}],[]),/outside its observed test domain/);
});
test("later unverified item does not replace verified activity or become a scientific risk finding",()=>{
 const established=event("prior","ENROLLMENT_UPDATE","2026-11-06");
 const unverified=event("rumor","PRIMARY_READOUT","2026-11-07",undefined,false);
 const r=assessLatestPhaseActivity(DEEP_ASSESSMENTS,NCT,phase,asOf,[unverified,established],[review("prior")],[]);
 assert.equal(r.latestVerifiedMilestone.id,"prior");
 assert.equal(r.unverifiedEventCount,1);
 assert.throws(()=>assessLatestPhaseActivity(DEEP_ASSESSMENTS,NCT,phase,asOf,[unverified,established],[],[risk("rumor")]),/verified current-phase evidence/);
});
test("completed safety readout can yield an unfavorable risk and independent test grade",()=>{
 const ev=event("safety","SAFETY_READOUT","2026-11-06");
 const r=assessLatestPhaseActivity(DEEP_ASSESSMENTS,NCT,phase,asOf,[ev],[review("safety","SAFETY",1)],[risk("safety","CRITICAL")]);
 assert.equal(r.currentScores.find(x=>x.id==="4.1").score,20);
 assert.equal(r.activeRisks[0].level,"CRITICAL");
 assert.equal(PHASE_RISK_WATCHLIST.PHASE1.some(x=>x.domain==="DOSE_EXPOSURE"),true);
});
