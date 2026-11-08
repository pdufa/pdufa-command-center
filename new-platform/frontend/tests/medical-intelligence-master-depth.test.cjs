const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const vm=require("node:vm");
const path=require("node:path");
const ts=require("typescript");
function load(name){
 const f=fs.readFileSync(path.join(__dirname,"../lib/"+name+".ts"),"utf8");
 const js=ts.transpileModule(f,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
 const m={exports:{}};
 vm.runInNewContext(js,{module:m,exports:m.exports});
 return m.exports;
}
const {
 SCIENTIFIC_LEVELS,SCIENTIFIC_LAYERS,DEEP_ASSESSMENTS,DEPTH_SLOT_COUNT,
 THERAPEUTIC_STRATEGY_QUESTIONS,getDepthSlot
}=load("medical-intelligence-master-depth");
const {
 MEDICAL_CASES,CAPR_FDA_PUL_SAP_COMPARISONS,caprSapComparisonSummary,
 cogtLiverSafetyDifference,caseForCycle,researchForSlot
}=load("medical-intelligence-md-casebook");
const roster=JSON.parse(fs.readFileSync(path.join(__dirname,"../data/p3PostDataActive.json"),"utf8"));
const ncts=new Set(roster.records.map(x=>x.nct));
test("Master Depth exactly matches 20 levels × 40 assessments across 8 layers",()=>{
 assert.equal(SCIENTIFIC_LEVELS.length,20);
 assert.equal(SCIENTIFIC_LAYERS.length,8);
 assert.equal(DEEP_ASSESSMENTS.length,40);
 assert.equal(DEPTH_SLOT_COUNT,800);
 const ids=new Set();
 for(const layer of SCIENTIFIC_LAYERS){
   assert.equal(layer.assessments.length,5);
   for(const a of layer.assessments){
     assert.equal(a.layerId,layer.id);
     assert.ok(a.objective.length>25);
     assert.ok(a.failureMechanism.length>20);
     for(const level of SCIENTIFIC_LEVELS){
       const slot=getDepthSlot(a.id,level.id);
       assert.ok(slot&&slot.id.endsWith(":L"+level.id));
       assert.equal(slot.status,"UNREVIEWED");
       assert.ok(slot.question.length>50);
       ids.add(slot.id);
     }
   }
 }
 assert.equal(ids.size,800);
 assert.equal(getDepthSlot("NONSENSE",1),null);
 assert.equal(getDepthSlot("1.1",21),null);
});
test("Therapeutic strategy adds 75 unique research questions with no synthetic conclusions",()=>{
 assert.equal(THERAPEUTIC_STRATEGY_QUESTIONS.length,75);
 assert.equal(new Set(THERAPEUTIC_STRATEGY_QUESTIONS.map(x=>x.id)).size,75);
 assert.equal(new Set(THERAPEUTIC_STRATEGY_QUESTIONS.map(x=>x.group)).size,5);
 assert.ok(THERAPEUTIC_STRATEGY_QUESTIONS.every(x=>x.question.includes("evidence")));
});
test("Case study MD investigations are linked to legitimate source-limited methods",()=>{
 assert.equal(MEDICAL_CASES.length,3);
 for(const program of MEDICAL_CASES){
   assert.ok(ncts.has(program.nct));
   assert.match(program.source,/^https:\/\//);
   assert.match(program.sourceDate,/^\d{4}-\d{2}-\d{2}$/);
   assert.ok(program.sourceDate<="2026-11-07");
   assert.equal(program.decision,"INDETERMINATE");
   assert.ok(program.investigations.length>0&&program.investigations.length<800);
   assert.ok(program.uncertainties.length>=3);
   assert.ok(program.strongestCounter.length>70);
   const keys=new Set();
   for(const v of program.investigations){
     assert.ok(getDepthSlot(v.assessmentId,v.level));
     assert.ok(v.sourceObservation.length>25&&v.medicalInterpretation.length>25);
     assert.ok(!keys.has(v.assessmentId+":"+v.level));
     keys.add(v.assessmentId+":"+v.level);
     assert.ok(researchForSlot(program.cycleId,v.assessmentId,v.level));
   }
   assert.equal(caseForCycle(program.cycleId).nct,program.nct);
 }
});
test("CAPR FDA 7-way analysis is source-grounded and not falsely interpreted as independent votes",()=>{
 assert.equal(CAPR_FDA_PUL_SAP_COMPARISONS.length,7);
 const s=caprSapComparisonSummary();
 assert.equal(s.reportedAnalyses,7);
 assert.equal(s.nominalBelow005,2);
 assert.equal(s.fdaOriginallySpecified.pValue,0.24);
 assert.equal(s.applicantModified.pValue,0.029);
 assert.match(s.caution,/not.*independent/i);
 for(const a of CAPR_FDA_PUL_SAP_COMPARISONS){
   assert.ok(a.upper>a.lower);
   assert.ok(a.pValue>0&&a.pValue<=1);
 }
});
test("COGT ALT/AST difference is descriptive and does not imply statistical inference",()=>{
 const l=cogtLiverSafetyDifference();
 assert.equal(l.combinationPercent,10.8);
 assert.equal(l.controlPercent,1.4);
 assert.equal(l.absoluteDifferencePercentagePoints,9.4);
 assert.match(l.caution,/no valid p-value/);
});
