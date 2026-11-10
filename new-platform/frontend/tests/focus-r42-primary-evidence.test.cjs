"use strict";
const test=require("node:test"),assert=require("node:assert/strict"),
      fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
for(const ext of [".ts",".tsx"])require.extensions[ext]=(mod,file)=>{
 const out=ts.transpileModule(fs.readFileSync(file,"utf8"),{
   compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,
      jsx:ts.JsxEmit.ReactJS,esModuleInterop:true}});
 mod._compile(out.outputText,file);
};
const data=require("../data/focus-r42-primary-result-fields.json");
const {buildFocusR42PrimarySourceView}=require("../lib/focus-r42-primary-research.ts");
const clone=x=>structuredClone(x);

test("live-sourced 29 trial roster retains 12 posted results / 16 tables and 17 source-absent cases",()=>{
  const x=buildFocusR42PrimarySourceView();
  assert.ok(x);
  assert.equal(x.trialRows.length,29);
  assert.equal(x.trialRows.filter(z=>z.primary).length,12);
  assert.equal(x.trialRows.filter(z=>!z.primary).length,17);
  assert.equal(x.trialRows.flatMap(z=>z.primary?.endpoints||[]).length,16);
  assert.equal(x.counts.applications,23);
  assert.equal(x.sha256,"9ebfac62e6d99e105d63c107bc0aa9a52803293eba915ba4a43be3fba93f15cf");
  assert.equal(x.independentlyReviewedMethods,0);
  assert.equal(x.validatedFDAForecasts,0);
  assert.equal(x.validatedHistoricalBacktests,0);
  assert.equal(x.fdaProbability,null);
  assert.ok(x.trialRows.every(z=>z.reviewerGrade===null&&z.FDAForecast==="ABSTAIN"));
});
test("reported endpoint values and p-value strings are ungraded source inputs",()=>{
  const x=buildFocusR42PrimarySourceView();
  const achv=x.trialRows.find(z=>z.nct==="NCT04576949");
  assert.equal(achv.primary.endpoints.length,2);
  assert.ok(achv.primary.endpoints[0].pValuesAsReported.includes("< 0.0001"));
  const cort=x.trialRows.find(z=>z.nct==="NCT04308590");
  assert.ok(cort.primary.endpoints[0].pValuesAsReported.includes("0.4160"));
  const acacia=x.trialRows.find(z=>z.nct==="NCT06081894");
  assert.equal(acacia.primary,null);
  assert.match(x.sourceLimits,/No results section does not mean/);
});
test("receipt tampering, new trial source membership or forged scientific release fails closed",()=>{
  const changes=[
    v=>v.sourceReceiptSha256="a".repeat(64),
    v=>v.sourceRunId=1,
    v=>v.counts.primaryOutcomeTables=15,
    v=>v.counts.authorizedScientificGrades=1,
    v=>v.officialFutureFdaForecast="APPROVAL",
    v=>v.accuracy="100%",
    v=>v.clinicalReviewerSigned=true,
    v=>v.trialPrimaryResults[0].nct="NCT99999999",
    v=>v.trialPrimaryResults[0].endpoints=[],
    v=>v.trialPrimaryResults.push(structuredClone(v.trialPrimaryResults[0])),
  ];
  for(let i=0;i<changes.length;i++){
    const q=clone(data);changes[i](q);
    assert.equal(buildFocusR42PrimarySourceView(q),null,"tamper "+i);
  }
});
test("source-only R42 visual renders both populated and absent-registry cases",()=>{
  const page=fs.readFileSync(path.join(root,"app/predictions/page.tsx"),"utf8");
  const ui=fs.readFileSync(path.join(root,"app/predictions/FocusRegistryPrimaryEvidenceR42.tsx"),"utf8");
  assert.ok(page.includes("<FocusRegistryPrimaryEvidenceR42/>"));
  assert.match(ui,/16 source-reported endpoints/);
  assert.match(ui,/No p-value field/);
  assert.match(ui,/not a negative finding/);
  assert.match(ui,/NOT CALIBRATED/);
  assert.doesNotMatch(ui,/submitClinicalGrade|fetch\(|POST\s+\/api\/reviews/);
});
