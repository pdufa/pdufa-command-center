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
const {createSourceTests,makeEvidenceRun,TEST_NAMES}=require("../lib/prediction-source-tests.ts");
const sourceUrl="https://clinicaltrials.gov/study/NCT05507203";
const study={
  hasResults:true,
  protocolSection:{
    identificationModule:{nctId:"NCT05507203",briefTitle:"Registry smoke-test fixture"},
    statusModule:{overallStatus:"COMPLETED",studyFirstPostDateStruct:{date:"2021-01-12"},lastUpdatePostDateStruct:{date:"2026-01-12"}},
    designModule:{phases:["PHASE3"],studyType:"INTERVENTIONAL",
      designInfo:{allocation:"RANDOMIZED",interventionModel:"PARALLEL"},
      enrollmentInfo:{count:500}},
    conditionsModule:{conditions:["Ulcerative colitis"]},
    armsInterventionsModule:{interventions:[{name:"Obefazimod"}],armGroups:[{label:"active"},{label:"control"}]},
    sponsorCollaboratorsModule:{leadSponsor:{name:"Abivax"}},
    outcomesModule:{primaryOutcomes:[{measure:"Clinical remission"}]}
  },
  resultsSection:{
    outcomeMeasuresModule:{outcomeMeasures:[{analyses:[{pValue:"0.03"}]}]},
    adverseEventsModule:{seriousEvents:[{term:"Serious event"}]},
    participantFlowModule:{periods:[{title:"Treatment"}]}
  }
};
test("one exact-NCT full source scan builds twelve separate evidence checks and never a forecast",()=>{
  const result=makeEvidenceRun(study,"NCT05507203","FULL");
  assert.equal(result.nct,"NCT05507203");
  assert.equal(result.mode,"FULL");
  assert.equal(result.executedCount,12);
  assert.deepEqual(result.tests.map(x=>x.title),[...TEST_NAMES]);
  assert.equal(result.tests[0].state,"SOURCE_FIELD_PRESENT");
  assert.equal(result.tests[1].state,"SOURCE_FIELD_PRESENT");
  assert.match(result.tests[1].summary,/PHASE3/);
  assert.match(result.tests[4].summary,/Clinical remission/);
  assert.equal(result.tests[9].state,"INDEPENDENT_REVIEW_REQUIRED");
  assert.equal(result.tests[10].state,"NOT_AUTOMATED");
  assert.equal(result.tests[11].state,"NOT_AUTOMATED");
  assert.equal(result.registrySourceUrl,sourceUrl);
  assert.equal(result.registryLastUpdate,"2026-01-12");
  assert.deepEqual(result.prediction,{approval:"ABSTAIN",crl:"ABSTAIN",reviewDelay:"ABSTAIN",certainty:"NOT_VALIDATED"});
});
test("run exactly one requested check, no synthetic completion of other checks",()=>{
  for(const index of [0,5,9,11]){
    const result=makeEvidenceRun(study,"NCT05507203","SINGLE",index);
    assert.equal(result.tests.length,1);
    assert.equal(result.tests[0].index,index);
    assert.equal(result.executedCount,1);
  }
  assert.throws(()=>makeEvidenceRun(study,"NCT05507203","SINGLE",12),/INVALID_SOURCE_TEST_INDEX/);
  assert.throws(()=>makeEvidenceRun(study,"NCT05507203","SINGLE",-1),/INVALID_SOURCE_TEST_INDEX/);
  assert.throws(()=>makeEvidenceRun(study,"NCT05507203","SINGLE",1.5),/INVALID_SOURCE_TEST_INDEX/);
});
test("reject wrong NCT and avoid claiming unposted study data as negative safety or clinical result",()=>{
  assert.throws(()=>createSourceTests(study,"NCT05507216"),/REGISTRY_NCT_ID_MISMATCH/);
  assert.throws(()=>createSourceTests(study,"NCT00000000"),/EXACT_FOCUS_NCT_REQUIRED/);
  const incomplete={protocolSection:{identificationModule:{nctId:"NCT05507203"}}};
  const tests=createSourceTests(incomplete,"NCT05507203");
  assert.equal(tests.length,12);
  assert.equal(tests[1].state,"SOURCE_FIELD_MISSING");
  assert.equal(tests[5].state,"SOURCE_FIELD_MISSING");
  assert.equal(tests[7].state,"SOURCE_FIELD_MISSING");
  assert.equal(tests[10].state,"NOT_AUTOMATED");
});
test("buttons make an explicit POST and cannot silently publish FDA odds or run on page load",()=>{
  const component=fs.readFileSync(path.join(root,"app/predictions/PredictionSourceRunControls.tsx"),"utf8");
  const nav=fs.readFileSync(path.join(root,"app/predictions/FocusPredictionNavigator.tsx"),"utf8");
  const route=fs.readFileSync(path.join(root,"app/api/predictions/source-analysis/route.ts"),"utf8");
  assert.match(component,/Start Full Analysis — 12 Checks/);
  assert.match(component,/Run One Test/);
  assert.match(component,/method:"POST"/);
  assert.match(component,/setTests/);
  assert.match(component,/Reset test sequence/);
  assert.match(nav,/PredictionSourceRunControls key={selectedTrial.nct}/);
  assert.match(route,/export async function POST/);
  assert.doesNotMatch(route,/export async function GET/);
  assert.match(route,/clinicaltrials\.gov\/api\/v2\/studies\//);
  assert.match(route,/FOCUS_SPECIALTY_ASSESSMENT_QUEUE\.some/);
  assert.match(route,/Cross-origin analysis request denied/);
  assert.doesNotMatch(route,/probability\s*:\s*(?:\d|0\.)/);
});
