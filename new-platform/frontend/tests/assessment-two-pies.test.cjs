const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const ts=require("typescript");
const React=require("react");
const {renderToStaticMarkup}=require("react-dom/server");
const root=path.resolve(__dirname,"..");

for(const ext of [".ts",".tsx"]){
  require.extensions[ext]=(module,filename)=>module._compile(
    ts.transpileModule(fs.readFileSync(filename,"utf8"),{
      compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,
        jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}
    }).outputText,filename
  );
}

const {getAssessmentPieData,findLatestReleasedTrial}=require("../lib/focus-assessment-chart.ts");
const {FOCUS_FINAL_TRIAL_AUDIT}=require("../lib/focus-final-gate-checks.ts");
const Pies=require("../app/AssessmentStatusPies.tsx").default;

test("total pie reconciles exact FOCUS evidence checks without claiming clinical completion",()=>{
  const model=getAssessmentPieData();
  assert.equal(model.totalTrials,FOCUS_FINAL_TRIAL_AUDIT.trialCount);
  assert.equal(model.totalChecks,model.totalTrials*7);
  assert.equal(model.totalChecks,203);
  assert.equal(model.overall.reduce((total,slice)=>total+slice.value,0),model.totalChecks);
  assert.equal(model.overall.find(slice=>slice.key==="verified").value,0);
  assert.equal(model.overall.find(slice=>slice.key==="review").value,FOCUS_FINAL_TRIAL_AUDIT.review);
  assert.equal(model.overall.find(slice=>slice.key==="missing").value,FOCUS_FINAL_TRIAL_AUDIT.missing);
  assert.equal(model.latest,null,"Research-only intake must never invent a released prediction");
});

test("latest pie requires explicit release status, timestamp and a matched exact NCT",()=>{
  const row=FOCUS_FINAL_TRIAL_AUDIT.rows[0];
  const next=FOCUS_FINAL_TRIAL_AUDIT.rows[1];
  const make=(overrides={})=>({
    nct:row.nct,ticker:row.ticker,prediction:"APPROVAL",
    certainty:"VALIDATED",releaseStatus:"PUBLISHED",
    releasedAt:"2026-11-09T18:00:00Z",...overrides
  });
  assert.equal(findLatestReleasedTrial([make({prediction:"ABSTAIN"})]),null);
  assert.equal(findLatestReleasedTrial([make({certainty:"NOT_VALIDATED"})]),null);
  assert.equal(findLatestReleasedTrial([make({releaseStatus:"DRAFT"})]),null);
  assert.equal(findLatestReleasedTrial([make({releasedAt:null})]),null);
  assert.equal(findLatestReleasedTrial([make({releasedAt:"invalid"})]),null);
  assert.equal(findLatestReleasedTrial([make({nct:"NCT99999999"})]),null);
  const result=findLatestReleasedTrial([
    make(),
    make({nct:next.nct,ticker:next.ticker,decision:"CRL",prediction:"CRL",releasedAt:"2026-11-10T18:00:00Z"})
  ]);
  assert.equal(result.nct,next.nct);
  assert.equal(result.decision,"CRL");
  assert.equal(result.counts.review,next.review);
  assert.equal(result.counts.missing,next.missing);
});

test("assessments page has two pie panels, one honest unavailable-prediction empty state",()=>{
  const model=getAssessmentPieData();
  const html=renderToStaticMarkup(React.createElement(Pies,model));
  assert.match(html,/data-testid="total-assessments-pie"/);
  assert.match(html,/data-testid="latest-prediction-pie"/);
  assert.equal((html.match(/role="img"/g)||[]).length,2);
  assert.match(html,/203 evidence checks/);
  assert.match(html,/NO PREDICTION RELEASED/);
  assert.match(html,/ABSTAIN \/ NOT VALIDATED/);
  assert.doesNotMatch(html,/FDA approval probability:\s*\d+%/);
  const page=fs.readFileSync(path.join(root,"app/predictions/assessment/page.tsx"),"utf8");
  assert.match(page,/<AssessmentStatusPies \{\.\.\.pies\}\/>/);
});
