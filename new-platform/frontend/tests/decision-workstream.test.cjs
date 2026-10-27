const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs"),path=require("node:path"),Module=require("node:module"),ts=require("typescript");
const root=path.resolve(__dirname,"../lib"),cache={};
function load(name){if(cache[name])return cache[name].exports;const file=path.join(root,name+".ts");const js=ts.transpileModule(fs.readFileSync(file,"utf8"),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;const m=new Module(file,module);cache[name]=m;m.filename=file;m.paths=module.paths;m.require=id=>id.startsWith("./")?load(id.slice(2)):require(id);m._compile(js,file);return m.exports;}
const {assessDecisionWorkstream}=load("decision-workstream");
const {investigation}=require("./fixtures/decision-investigation.cjs");
const asOf="2026-10-26T11:00:00Z",now=new Date("2026-10-26T12:00:00Z");
const identity={exactKey:"TRIAL|NCT12345678|TEST",programId:"PDUFA-999999",trialId:"NCT12345678",ticker:"TEST",stage:"GEM_JR"};
const stage=(result,name)=>result.stages.find(row=>row.name===name);
// These are invented contract fixtures. They verify composition, not source truth or prediction accuracy.
function evidence(){
 const record={programId:identity.programId,trialId:identity.trialId,asOf,status:"COMPLETE",sourceStatus:"VERIFIED",reviewedLevels:20,requiredLevels:20,criticalFindingsResolved:true,calibrationStatus:"VALIDATED"};
 const target={programId:identity.programId,asOf,diseaseSubtype:"A",indication:"B",mechanism:"C",primaryEndpoint:"OS"};
 const history=Array.from({length:3},(_,i)=>({programId:"PDUFA-"+(200001+i),decisionAt:"2024-01-01T00:00:00Z",diseaseSubtype:"A",indication:"B",mechanism:"C",primaryEndpoint:"OS",trialPhase:3,outcome:i?"APPROVED":"CRL",sourceUrl:"https://example.org/action",independentlyReviewed:true}));
 const chronology=Object.fromEntries(history.map(row=>[row.programId,[{sourceUrl:row.sourceUrl,publishedAt:"2024-01-02T00:00:00Z",observedAt:"2024-01-03T00:00:00Z",decisionAt:row.decisionAt,predictionCutoff:asOf,independentlyReviewed:true}]]));
 const price=(observedAt,adjustedClose)=>({programId:identity.programId,ticker:identity.ticker,observedAt,capturedAt:"2026-10-25T00:00:00Z",adjustedClose,currency:"USD",priceSource:"https://example.org/prices",adjustmentMethod:"SPLIT_AND_DIVIDEND_ADJUSTED",corporateActionsReviewed:true,verifiedBy:"synthetic-contract-reviewer"});
 const rows=(offset,year)=>Array.from({length:30},(_,i)=>({programId:"PDUFA-"+(100000+offset+i),applicationNumber:"NDA"+(100000+offset+i),predictedAt:year+"-02-01T00:00:00Z",predictionCapturedAt:year+"-02-01T00:00:00Z",decisionAt:year+"-03-01T00:00:00Z",decisionObservedAt:year+"-03-02T00:00:00Z",predictionSource:"https://example.org/forecast",decisionSource:"https://example.org/action",probability:i%2?.2:.8,approved:i%2===0,reviewStatus:"INDEPENDENTLY_VERIFIED",modelVersion:"frozen-v1",subgroup:"synthetic-contract-cohort"}));
 const training=rows(0,"2023"),holdout=rows(30,"2025");
 return {identity:{...identity},scienceDossier:investigation(identity,asOf),outcomeApplicationNumber:"NDA999999",mainCompanyCik:"0000000001",science:{...record},outcome:{...record},target,history,chronology,
  coverage:{asOf,windowStart:"2020-01-01",windowEnd:"2025-01-01",eligibleApplications:10,reviewedDecisions:10,approved:6,crl:3,withdrawn:1,unresolved:0,sourceCoverageConfirmed:true,includesNonApprovals:true},
  main:{programId:identity.programId,ticker:identity.ticker,asOf,restrictionsReviewed:true,unresolvedCriticalRisks:0,marketEntry:price("2025-01-01",10),marketExit:price("2025-02-01",12)},
  calibrationRows:structuredClone(holdout),holdout:{training,rows:holdout,plan:{modelVersion:"frozen-v1",planSource:"https://example.org/frozen-plan",frozenAt:"2025-01-01",holdoutStart:"2025-01-01",holdoutEnd:"2026-01-01",evaluatedAt:"2026-02-01",trainingProgramIds:training.map(row=>row.programId),holdoutProgramIds:holdout.map(row=>row.programId)}}};
}
function sourceAudit(){return {status:"RESEARCH_ONLY",checkedAt:asOf,publishedLetters:458,approvedApplications:29416,sourcePageReviewRows:458,independentlyVerifiedReviewCycles:0,modelEligibleReviewCycles:0,modelValidated:false,predictionAvailable:false,denominatorComplete:false,probability:null};}
function mainSource(){
 const id={programId:identity.programId,exactKey:identity.exactKey},boundary={assessmentScoreChange:false,fsFaChange:false};
 return {...id,stage:identity.stage,researchOnly:true,ordersEnabled:false,fsFaChanges:false,marketDataStatus:"OK",
  assessmentEvidence:{status:"COMPLETE",assessment_score:80,assessment_coverage:100},
  marketEvidenceReview:{...id,...boundary,qualificationChange:false,recommendation:null,status:"RESEARCH_ONLY"},
  decisionReadiness:{...id,...boundary,ordersEnabled:false,status:"READY_FOR_HUMAN_RESEARCH_REVIEW",missingRequirements:[],tradeCall:null,entryPrice:null,targetPrice:null,stopLoss:null},
  riskEvidenceReview:{...id,...boundary,stage:identity.stage,identityStatus:"EXACT_IDENTITY_MATCH",researchOnly:true,ordersEnabled:false,qualificationChange:false,catalystVerified:true,financingRiskReviewed:true,riskFlags:[],
   checks:["catalystTiming","cashRunway","dilutionRisk"].map(id=>({id,label:id,status:"REVIEWED",reason:"Synthetic contract metadata",source:"https://example.org/source",sourceDate:"2026-10-25",checkedAt:asOf}))}};
}
const assess=(manifest=evidence(),options={})=>assessDecisionWorkstream(options.identity??identity,options.detail??null,options.historicalSource??null,options.mainSource??null,manifest,now);
test("all missing evidence leaves every workstream stage NOT_READY",()=>{
 const result=assess(null);assert.equal(result.status,"NOT_READY");assert.ok(result.stages.every(row=>row.status==="NOT_READY"));
 assert.equal(result.historicalMatches,0);assert.equal(result.historicalSource,null);assert.equal(result.probability,null);assert.equal(result.modelValidated,false);assert.equal(result.tradeAuthorized,false);
});
test("a complete synthetic manifest reaches research review only, with no probability or trading permission",()=>{
 const result=assess();assert.equal(result.status,"RESEARCH_REVIEW_REQUIRED");assert.deepEqual(result.issues,[]);assert.equal(result.historicalMatches,3);
 assert.equal(result.modelValidated,false);assert.equal(result.probability,null);assert.equal(result.tradeAuthorized,false);
 assert.equal(stage(result,"Calibration").status,"RESEARCH_ONLY");
});
test("composition never changes input restrictions, scores, stage or FS/FA metadata",()=>{
 const manifest=evidence(),live=mainSource();live.preservedAssociations={WT:"existing-only",FS:"fixed-source",FA:"fixed-association"};
 const before=structuredClone({manifest,live,identity});assess(manifest,{mainSource:live});
 assert.deepEqual({manifest,live,identity},before);
});
test("cross-program, trial, ticker, exact-key or stage manifests are withheld entirely",()=>{
 for(const changed of [{programId:"PDUFA-888888"},{trialId:"NCT87654321"},{ticker:"OTHER"},{exactKey:"OTHER"},{stage:"GEM"}]){
  const manifest=evidence();Object.assign(manifest.identity,changed);const result=assess(manifest);
  assert.equal(result.status,"NOT_READY");assert.equal(result.historicalMatches,0);assert.ok(result.stages.every(row=>row.status==="NOT_READY"));
 }
});
test("reviewed target, science/outcome trial, and MAIN ticker must match the selected identity",()=>{
 for(const mutate of [m=>m.target.programId="PDUFA-888888",m=>m.science.trialId="NCT87654321",m=>m.outcome.trialId="NCT87654321",m=>m.main.ticker="OTHER"]){
  const manifest=evidence();mutate(manifest);assert.equal(assess(manifest).status,"NOT_READY");
 }
});
test("an assessment from another exact trial blocks an otherwise complete reviewed manifest",()=>{
 const result=assess(evidence(),{detail:{id:"ANOTHER_TRIAL",programId:identity.programId,nctId:identity.trialId,asOf}});
 assert.equal(result.status,"NOT_READY");assert.equal(result.historicalMatches,0);
});
test("invalid identity and unsupported assessment stages cannot produce a review-ready decision",()=>{
 for(const changed of [{programId:"invalid"},{trialId:"invalid"},{ticker:""},{exactKey:""},{stage:"WT"}])
  assert.equal(assess(evidence(),{identity:{...identity,...changed}}).status,"NOT_READY");
});
test("archive source progress is displayed separately and never supplies trial evidence",()=>{
 const result=assess(null,{historicalSource:sourceAudit(),mainSource:mainSource()});
 assert.equal(result.historicalSource.publishedLetters,458);assert.equal(result.historicalSource.modelEligibleReviewCycles,0);
 assert.equal(result.status,"NOT_READY");assert.equal(result.historicalMatches,0);assert.equal(stage(result,"Historical FDA").status,"NOT_READY");
 assert.equal(stage(result,"SCIENCE").status,"NOT_READY");assert.equal(stage(result,"OUTCOME").status,"NOT_READY");
 assert.equal(stage(result,"MAIN").status,"SOURCE_CONNECTED_REVIEW_INCOMPLETE");
});
test("malformed or predictive archive responses withhold source counts",()=>{
 for(const changed of [{modelValidated:true},{probability:.8},{modelEligibleReviewCycles:1},{publishedLetters:-1}]){
  const result=assess(null,{historicalSource:{...sourceAudit(),...changed}});
  assert.equal(result.historicalSource,null);assert.equal(result.status,"NOT_READY");assert.match(result.sourceIssues.join(" "),/could not be verified/);
 }
});
test("complete candidate scores alone cannot certify independent SCIENCE or OUTCOME",()=>{
 const detail={id:identity.exactKey,programId:identity.programId,nctId:identity.trialId,asOf,models:{PIPELINE:{score:100,coverage:100},GEM_JR:{score:100,coverage:100},GEM:{score:100,coverage:100}}};
 const result=assess(null,{detail});assert.equal(result.status,"NOT_READY");assert.equal(stage(result,"SCIENCE").status,"NOT_READY");assert.equal(stage(result,"OUTCOME").status,"NOT_READY");
});
test("each independent reviewed evidence stage is mandatory",()=>{
 for(const field of ["scienceDossier","outcome","main"]){const manifest=evidence();manifest[field]=null;const result=assess(manifest);assert.equal(result.status,"NOT_READY");}
 const manifest=evidence();manifest.science.reviewedLevels=19;assert.equal(assess(manifest).status,"NOT_READY");
});
test("source-cited investigation can derive science readiness when a redundant summary is absent",()=>{
 const manifest=evidence();manifest.science=null;assert.equal(assess(manifest).status,"RESEARCH_REVIEW_REQUIRED");
 manifest.scienceDossier.levels[0].assessments[0].uncertainty="";assert.equal(assess(manifest).status,"NOT_READY");
});
test("a 20-level summary alone cannot replace 40 source-cited assessments or eight layers",()=>{
 const manifest=evidence();delete manifest.scienceDossier;const result=assess(manifest);
 assert.equal(result.status,"NOT_READY");assert.match(stage(result,"SCIENCE").issues.join(" "),/40-assessment/);
});
test("scientific application and indication identity must be reconciled before integrated review",()=>{
 for(const changes of [{fdaApplication:null},{indication:"different indication"}]){const manifest=evidence();Object.assign(manifest.scienceDossier,changes);assert.equal(assess(manifest).status,"NOT_READY");}
});
test("OUTCOME application and MAIN company must match the scientific dossier's declared identities",()=>{
 for(const changes of [{outcomeApplicationNumber:"BLA999998"},{outcomeApplicationNumber:null},{mainCompanyCik:"0000000002"},{mainCompanyCik:null}]){const manifest=Object.assign(evidence(),changes);assert.equal(assess(manifest).status,"NOT_READY");}
});
test("historical matches require denominator and source chronology, not only close scientific similarity",()=>{
 for(const mutate of [m=>m.coverage.sourceCoverageConfirmed=false,m=>m.coverage.includesNonApprovals=false,m=>m.chronology={},m=>m.history=[]]){
  const manifest=evidence();mutate(manifest);const result=assess(manifest);assert.equal(result.status,"NOT_READY");assert.equal(stage(result,"Historical FDA").status,"NOT_READY");
 }
});
test("missing cohort calibration or frozen holdout blocks integrated research review",()=>{
 for(const mutate of [m=>m.calibrationRows=[],m=>m.holdout=null]){
  const manifest=evidence();mutate(manifest);const result=assess(manifest);assert.equal(result.status,"NOT_READY");assert.equal(stage(result,"Calibration").status,"NOT_READY");
 }
});
test("historical outcome observations after the target cutoff cannot enter integrated calibration",()=>{
 const manifest=evidence();manifest.calibrationRows[0].decisionObservedAt=asOf;
 const result=assess(manifest);assert.equal(result.status,"NOT_READY");assert.match(stage(result,"Calibration").issues.join(" "),/unavailable at target cutoff/);
});
test("holdout evaluation later than the target cutoff is blocked even if internally chronological",()=>{
 const manifest=evidence();manifest.holdout.plan.evaluatedAt="2026-10-27T00:00:00Z";
 const result=assess(manifest);assert.equal(result.status,"NOT_READY");assert.match(stage(result,"Calibration").issues.join(" "),/unavailable at the target cutoff/);
});
test("holdout model retuning, missing declared cases and training observation leakage all block review",()=>{
 for(const mutate of [m=>m.holdout.rows[0].modelVersion="retuned",m=>m.holdout.plan.holdoutProgramIds.push("PDUFA-111111"),m=>m.holdout.training[0].decisionObservedAt=m.holdout.plan.frozenAt]){
  const manifest=evidence();mutate(manifest);assert.equal(assess(manifest).status,"NOT_READY");
 }
});
test("FDA application overlap across chronological partitions blocks integrated research review",()=>{
 const manifest=evidence();manifest.holdout.rows[0].applicationNumber=manifest.holdout.training[0].applicationNumber;
 const result=assess(manifest);assert.equal(result.status,"NOT_READY");assert.match(stage(result,"Calibration").issues.join(" "),/application cannot cross/);
});
test("holdout must improve on the baseline frozen from training outcomes",()=>{
 const manifest=evidence();manifest.holdout.rows=manifest.holdout.rows.map(row=>({...row,probability:.5}));
 const result=assess(manifest);assert.equal(result.status,"NOT_READY");assert.equal(stage(result,"Calibration").status,"NOT_READY");
 assert.match(stage(result,"Calibration").issues.join(" "),/baseline/);
});
test("review and critical-findings attestations require literal true, not truthy strings",()=>{
 for(const mutate of [m=>m.main.restrictionsReviewed="true",m=>m.science.criticalFindingsResolved="true",m=>m.outcome.criticalFindingsResolved=1]){
  const manifest=evidence();mutate(manifest);assert.equal(assess(manifest).status,"NOT_READY");
 }
});
test("identity mismatch is explicitly surfaced as a separate blocked stage",()=>{
 const manifest=evidence();manifest.identity.stage="GEM";const result=assess(manifest);
 assert.equal(stage(result,"Identity").status,"NOT_READY");assert.ok(stage(result,"Identity").issues.length);
});
test("historical sources observed at or after target cutoff are unavailable",()=>{
 const manifest=evidence();manifest.chronology[manifest.history[0].programId][0].observedAt=asOf;
 const result=assess(manifest);assert.equal(result.status,"NOT_READY");assert.equal(stage(result,"Historical FDA").status,"NOT_READY");
});
test("MAIN observations and captures must both precede the target cutoff",()=>{
 for(const field of ["observedAt","capturedAt"]){
  const manifest=evidence();manifest.main.marketExit[field]=asOf;
  const result=assess(manifest);assert.equal(result.status,"NOT_READY",field);assert.equal(stage(result,"MAIN").status,"NOT_READY");
 }
});
test("MAIN restrictions, unresolved risks and adjusted source data remain mandatory",()=>{
 for(const mutate of [m=>m.main.restrictionsReviewed=false,m=>m.main.unresolvedCriticalRisks=1,m=>m.main.marketEntry.adjustmentMethod="RAW",m=>m.main.marketExit=null]){
  const manifest=evidence();mutate(manifest);const result=assess(manifest);assert.equal(result.status,"NOT_READY");assert.equal(stage(result,"MAIN").status,"NOT_READY");
 }
});
test("a live MAIN source cannot confer connection status across identity, stage or trading boundaries",()=>{
 for(const mutate of [r=>r.programId="PDUFA-888888",r=>r.stage="GEM",r=>r.ordersEnabled=true,r=>r.fsFaChanges=true,r=>r.decisionReadiness.tradeCall="BUY",r=>r.marketEvidenceReview.recommendation="BUY"]){
  const source=mainSource();mutate(source);const result=assess(null,{mainSource:source});
  assert.equal(result.status,"NOT_READY");assert.equal(stage(result,"MAIN").status,"NOT_READY");assert.match(result.sourceIssues.join(" "),/MAIN source/);
 }
});
test("PIPELINE cannot borrow a GEM JR MAIN source connection",()=>{
 const result=assess(null,{identity:{...identity,stage:"PIPELINE"},mainSource:mainSource()});
 assert.equal(result.status,"NOT_READY");assert.equal(stage(result,"MAIN").status,"NOT_READY");
});
