"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const ts=require("typescript");
const root=path.resolve(__dirname,"..");
for(const ext of [".ts",".tsx"])require.extensions[ext]=(mod,file)=>{
  const source=ts.transpileModule(fs.readFileSync(file,"utf8"),{
    compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,
      jsx:ts.JsxEmit.ReactJS,esModuleInterop:true}
  });
  mod._compile(source.outputText,file);
};
const {buildR62ApplicationSourceReview,FOCUS_R62_APPLICATION_SOURCE_REVIEW}=
  require("../lib/focus-r62-application-source-review.ts");
const {FOCUS_R60_ORIGINAL_TRIAL_REVIEW}=
  require("../lib/focus-r60-original-trial-research.ts");
const {FOCUS_PRELIMINARY_R39}=
  require("../lib/focus-preliminary-application-research.ts");

test("23 original applications link exactly 29 unique trials without making predictions",()=>{
  const r=FOCUS_R62_APPLICATION_SOURCE_REVIEW;
  assert.ok(r);
  assert.equal(r.provisionalApplicationGroups,23);
  assert.equal(r.uniqueTrials,29);
  assert.equal(r.rows.length,23);
  assert.equal(r.qualifiedClinicalReviews,0);
  assert.equal(r.independentlyValidatedFdaForecasts,0);
  assert.equal(r.historicalMeasuredAccuracy,null);
  assert.equal(r.allFutureApprovalCrlAndTimingForecasts,"ABSTAIN");
  assert.equal(r.noProductionOrClinicalWrites,true);
  const unique=new Set(r.rows.flatMap(a=>a.linkedTrials.map(t=>t.nct)));
  assert.equal(unique.size,29);
  assert.ok(r.rows.every(a=>a.signedScientificReview===false&&
    a.calibratedProbability===null&&a.officialFutureFdaOutcome==="ABSTAIN"&&
    a.officialFutureTiming==="ABSTAIN"&&
    a.linkedTrials.length===a.linkedNctCount));
  assert.equal(r.originalR60Run,42709199117);
  assert.equal(r.originalR60Artifact,13715890359);
});

test("Savara original registry research remains source-reported, not clinical-grade",()=>{
  const s=FOCUS_R62_APPLICATION_SOURCE_REVIEW.rows.find(a=>a.id==="svra-molgramostim");
  assert.ok(s);
  assert.equal(s.ticker,"SVRA");
  assert.deepEqual(s.linkedTrials.map(t=>t.nct),["NCT04544293"]);
  assert.equal(s.currentPrimaryTrialCount,1);
  assert.equal(s.sourceReportedStatisticalComparisons,1);
  assert.equal(s.currentSafetyTrialCount,1);
  assert.equal(s.officialFutureFdaOutcome,"ABSTAIN");
  assert.equal(s.signedScientificReview,false);
});

test("17 trials with absent posted results remain original-evidence recovery tasks, never failure",()=>{
  const rows=FOCUS_R62_APPLICATION_SOURCE_REVIEW.rows;
  const capr=rows.find(x=>x.id==="capr-deramiocel");
  assert.equal(capr.currentPrimaryTrialCount,0);
  assert.equal(capr.linkedTrials[0].currentPrimaryTables,0);
  assert.ok(capr.linkedTrials[0].evidenceExceptions.some(x=>x.startsWith("NO_CURRENT_POSTED")));
  assert.equal(capr.officialFutureFdaOutcome,"ABSTAIN");
});

test("The same pivotal trial may support both Sarepta application cycles but has one source identity",()=>{
  const rows=FOCUS_R62_APPLICATION_SOURCE_REVIEW.rows;
  const nct="NCT02500381";
  assert.equal(rows.filter(a=>a.linkedTrials.some(t=>t.nct===nct)).length,2);
  assert.equal(FOCUS_R60_ORIGINAL_TRIAL_REVIEW.trials.filter(t=>t.nct===nct).length,1);
});

test("Source roster tampering, forged reviewer status and altered app memberships fail closed",()=>{
  const cases=[
    ()=>[null,FOCUS_PRELIMINARY_R39.applications],
    ()=>{
      const data=structuredClone(FOCUS_R60_ORIGINAL_TRIAL_REVIEW);
      data.trials[0].cycles=[];
      return [data,FOCUS_PRELIMINARY_R39.applications];
    },
    ()=>{
      const apps=structuredClone(FOCUS_PRELIMINARY_R39.applications);
      apps.pop();
      return [FOCUS_R60_ORIGINAL_TRIAL_REVIEW,apps];
    },
    ()=>{
      const apps=structuredClone(FOCUS_PRELIMINARY_R39.applications);
      apps[0].ncts=["NCT99999999"];
      return [FOCUS_R60_ORIGINAL_TRIAL_REVIEW,apps];
    },
    ()=>{
      const apps=structuredClone(FOCUS_PRELIMINARY_R39.applications);
      apps[0].qualifiedReviewerSignoff=true;
      return [FOCUS_R60_ORIGINAL_TRIAL_REVIEW,apps];
    },
    ()=>{
      const data=structuredClone(FOCUS_R60_ORIGINAL_TRIAL_REVIEW);
      data.trials[0].officialApprovalOrCrlForecast="APPROVAL";
      return [data,FOCUS_PRELIMINARY_R39.applications];
    },
  ];
  for(const [i,fn] of cases.entries()){
    const [source,apps]=fn();
    assert.equal(buildR62ApplicationSourceReview(source,apps),null,"forged scenario "+i);
  }
});

test("Prediction dashboard has expandable, filterable, read-only application source findings",()=>{
  const page=fs.readFileSync(path.join(root,"app/predictions/page.tsx"),"utf8");
  const ui=fs.readFileSync(path.join(root,"app/predictions/FocusApplicationSourceReviewR62.tsx"),"utf8");
  assert.match(page,/import FocusApplicationSourceReviewR62/);
  assert.ok(page.includes("<FocusApplicationSourceReviewR62/>"));
  assert.match(ui,/23 provisional FDA cycles/);
  assert.match(ui,/Find application source evidence/);
  assert.match(ui,/Filter application source evidence/);
  assert.match(ui,/<details/);
  assert.match(ui,/original R60 artifact/);
  assert.doesNotMatch(ui,/\bfetch\(|submitClinicalGrade|POST\s*\/api|setReviewerSignoff/);
});
