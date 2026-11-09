"use strict";
const test=require("node:test"),assert=require("node:assert/strict"),
      fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
for(const ext of [".ts",".tsx"])require.extensions[ext]=(mod,file)=>{
  const js=ts.transpileModule(fs.readFileSync(file,"utf8"),{compilerOptions:{
    target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,
    jsx:ts.JsxEmit.ReactJS,esModuleInterop:true}});
  mod._compile(js.outputText,file);
};
const pin=require("../data/focus-r44-original-registry-safety.json");
const {FOCUS_R44_SAFETY,validateFocusR44Safety}=require("../lib/focus-r44-registry-safety.ts");
const clone=x=>structuredClone(x);

test("real original SHA-256 receipt preserves 29/23 roster, 12 posted safety records, 28 event groups",()=>{
 const x=FOCUS_R44_SAFETY;
 assert.ok(x);
 assert.equal(x.originalResearchReceiptSha256,
  "7cf71efffaf9cc46446e75cd4a8be60c13783b5121e8d0d4650582b3d71340ab");
 assert.equal(x.items.length,12);
 assert.equal(x.absent.length,17);
 assert.equal(x.counts.trials,29);
 assert.equal(x.counts.applicationCycles,23);
 assert.equal(x.counts.seriousEventTermRows,244);
 assert.equal(x.counts.otherEventTermRows,202);
 assert.equal(x.items.reduce((n,r)=>n+r.groups.length,0),28);
 assert.equal(x.counts.independentlySignedClinicalGrades,0);
 assert.equal(x.counts.validatedApplicationFdaForecasts,0);
 assert.equal(x.counts.realHistoricalBacktests,0);
 assert.equal(x.officialFutureFdaForecast,"ABSTAIN");
 assert.equal(x.calibratedFdaAccuracy,null);
});
test("individual original arm denominators retained; no pooled safety risk estimate",()=>{
 const svra=FOCUS_R44_SAFETY.items.find(r=>r.nct==="NCT04544293");
 assert.deepEqual(svra.groups,[["Molgramostim",14,81,0,81,69,81],
                                ["Placebo",20,83,0,83,71,83]]);
 const achv=FOCUS_R44_SAFETY.items.find(r=>r.nct==="NCT05206370");
 assert.equal(achv.groups.length,3);
 assert.equal(achv.groups[2][3],3);
 assert.equal(achv.groups[2][4],260);
 assert.equal(FOCUS_R44_SAFETY.items.some(r=>r.nct==="NCT05126758"),false);
 assert.match(FOCUS_R44_SAFETY.warning,/not necessarily comparable/);
 assert.equal(FOCUS_R44_SAFETY.numericalApprovalProbability,null);
});
test("forged safety release, source hash, counts, membership or group denominator fails closed",()=>{
 const changes=[
  p=>p.originalResearchReceiptSha256="0".repeat(64),
  p=>p.sourceRunId=1,
  p=>p.counts.eventGroupRows=27,
  p=>p.counts.seriousEventTermRows=243,
  p=>p.counts.independentlySignedClinicalGrades=1,
  p=>p.counts.validatedApplicationFdaForecasts=1,
  p=>p.officialFutureFdaForecast="APPROVAL",
  p=>p.clinicalSafetyAdjudicated=true,
  p=>p.numericalApprovalProbability=.9,
  p=>p.posted[0].nct="NCT99999999",
  p=>p.posted[1].nct=p.posted[0].nct,
  p=>p.posted[0].groups[0][1]=999,
  p=>p.posted[0].groups[0][0]="",
  p=>p.posted[0].groups.pop(),
 ];
 changes.forEach((change,i)=>{
   const p=clone(pin);change(p);
   assert.equal(validateFocusR44Safety(p),null,"tamper case "+i);
 });
});
test("R44 source UI is read-only and pinned to PREDICTIONS without changing 23-app decision gates",()=>{
 const ui=fs.readFileSync(path.join(root,"app/predictions/FocusPostedSafetyR44.tsx"),"utf8");
 const page=fs.readFileSync(path.join(root,"app/predictions/page.tsx"),"utf8");
 assert.ok(page.includes("<FocusPostedSafetyR44/>"));
 assert.match(ui,/28 source-reported arms/);
 assert.match(ui,/clinical reviewer signoffs 0/);
 assert.match(ui,/not necessarily comparable|must not be pooled/);
 assert.match(ui,/sourceArtifactUrl/);
 assert.doesNotMatch(ui,/fetch\s*\(|submitClinicalGrade|updateClinical|POST\s+\/api/);
});
