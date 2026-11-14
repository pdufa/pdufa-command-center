const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const ts=require("typescript");

const root=path.resolve(__dirname,"..");
require.extensions[".ts"]=(module,filename)=>module._compile(ts.transpileModule(
  fs.readFileSync(filename,"utf8"),{compilerOptions:{
    module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,esModuleInterop:true
  }}
).outputText,filename);
const {FOCUS_SPECIALTY_ASSESSMENT_QUEUE:queue,FOCUS_SPECIALTY_SUMMARY:summary}=
  require("../lib/focus-specialty-assessment.ts");
const canonical=require("../data/p3PostDataActive.json");

test("all canonical FOCUS NCTs are queued without merging indications or inventing conclusions",()=>{
  assert.equal(queue.length,canonical.records.length);
  assert.equal(summary.ncts,29);
  assert.equal(summary.tickers,20);
  assert.equal(summary.mappedApplicationCycles,23);
  assert.equal(summary.partialClinicalDimensions,161);
  assert.equal(summary.mappedNcts,29);
  assert.deepEqual(queue.map(r=>r.nct),canonical.records.map(r=>r.nct));
  assert.equal(new Set(queue.map(r=>r.nct)).size,queue.length);
  assert.equal(new Set(queue.flatMap(r=>r.applications.map(a=>a.cycleId))).size,23);
  for(const r of queue){
    assert.equal(r.phaseVerified,false);
    assert.equal(r.scientificAssessment,"INSUFFICIENT_VERIFIED_EVIDENCE");
    assert.equal(r.prediction,"ABSTAIN");
    assert.equal(r.certainty,"NOT_VALIDATED");
    assert.equal(r.independentlyVerifiedGates,0);
    assert.equal(r.externalReviewerRequired,false);
    assert.equal(r.ownerReviewStatus,"OWNER_NOT_REVIEWED");
    assert.ok(r.registryUrl.endsWith("/"+r.nct));
    assert.ok(r.applications.length>0,r.nct+" not application mapped");
    for(const c of r.applications){
      assert.ok(c.specialty,c.cycleId+" missing specialty");
      assert.equal(c.researchQuestions,10);
      assert.equal(c.partialCaseDimensions,7);
      assert.equal(c.specialistSignoff,false);
      assert.equal(c.clinicalAdjudicationComplete,false);
      assert.equal(c.externalReviewerRequired,false);
      assert.equal(c.ownerReviewStatus,"OWNER_NOT_REVIEWED");
      assert.ok(c.sourceLinkedDimensions<=c.partialCaseDimensions);
      assert.ok(c.sourceUrl.startsWith("https://"));
    }
  }
});

test("assessment page exposes all-trial queue, exact NCT links and evidence gaps",()=>{
  const page=fs.readFileSync(path.join(root,"app/predictions/assessment/page.tsx"),"utf8");
  const home=fs.readFileSync(path.join(root,"app/predictions/page.tsx"),"utf8");
  const navigator=fs.readFileSync(path.join(root,"app/predictions/FocusPredictionNavigator.tsx"),"utf8");
  const route=fs.readFileSync(path.join(root,"app/api/focus-assessment-intake/route.ts"),"utf8");
  assert.match(page,/FOCUS_SPECIALTY_ASSESSMENT_QUEUE\.map/);
  assert.match(page,/getFullSpecialistCase/);
  assert.match(page,/sourceDate/);
  assert.match(page,/INSUFFICIENT VERIFIED EVIDENCE/);
  assert.match(page,/OWNER NOT REVIEWED/);
  assert.match(page,/OWNER-ONLY ASSESSMENTS/);
  assert.match(page,/No outside clinician, statistician/);
  assert.doesNotMatch(page,/Independent source and current-cycle reconciliation remains required/);
  assert.match(page,/ABSTAIN/);
  assert.match(page,/clinical phase|current trial phase|PHASE \/ STATUS/i);
  assert.match(home,/href="\/predictions\/assessment"/);
  assert.match(navigator,/\/predictions\/assessment\?nct=/);
  assert.match(route,/FOCUS_SCIENTIFIC_RESEARCH_INTAKE_NOT_COMPLETED_ASSESSMENTS/);
  assert.match(route,/Cache-Control/);
  assert.doesNotMatch(route,/POST\(|PUT\(|DELETE\(/);
});
