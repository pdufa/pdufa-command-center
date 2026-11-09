"use strict";
const test=require("node:test"),assert=require("node:assert/strict"),
  fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
for(const ext of [".ts",".tsx"])require.extensions[ext]=(mod,file)=>{
 const out=ts.transpileModule(fs.readFileSync(file,"utf8"),{compilerOptions:{
  target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,
  jsx:ts.JsxEmit.ReactJS,esModuleInterop:true}});
 mod._compile(out.outputText,file);
};
const pin=require("../data/focus-r45-primary-text-concordance.json");
const {FOCUS_R45_CURRENT_TEXT,validateR45CurrentEndpointText}=require("../lib/focus-r45-current-primary-text.ts");
const clone=x=>structuredClone(x);

test("29 exact NCT current registry primary text 45/16/16 remains ungraded",()=>{
 const r=FOCUS_R45_CURRENT_TEXT;
 assert.ok(r);
 assert.equal(r.items.length,29);
 assert.equal(r.items.reduce((n,x)=>n+x.currentRegisteredPrimaryCount,0),45);
 assert.equal(r.items.reduce((n,x)=>n+x.postedPrimaryCount,0),16);
 assert.equal(r.items.reduce((n,x)=>n+x.exactCurrentTitleTimeframeMatchCount,0),16);
 assert.equal(r.items.filter(x=>x.postedPrimaryCount>0).length,12);
 assert.equal(r.items.filter(x=>x.postedPrimaryCount===0).length,17);
 assert.equal(r.counts.applicationGroups,23);
 assert.equal(r.counts.qualifiedClinicalReviews,0);
 assert.equal(r.counts.validatedFDAForecasts,0);
 assert.equal(r.counts.independentHistoricalBacktests,0);
 assert.equal(r.officialFdaPrediction,"ABSTAIN");
 assert.equal(r.numericProbability,null);
 assert.ok(r.items.every(x=>x.originalPrespecificationVerified===false && x.clinicalGrade===null));
});
test("source comparisons do not mean original locked SAP or positive FDA outcome",()=>{
 const r=FOCUS_R45_CURRENT_TEXT;
 assert.equal(r.lockedSapAndMultiplicityVerified,false);
 assert.equal(r.originalPreReadoutRegistryVersionVerified,false);
 assert.match(r.caution,/does not prove prespecification/);
 const cogt=r.items.find(x=>x.nct==="NCT05208047");
 assert.equal(cogt.currentRegisteredPrimaryCount,8);
 assert.equal(cogt.postedPrimaryCount,0);
 assert.equal(cogt.FDAForecast,"ABSTAIN");
});
test("forged trial NCT, count, receipt, clinical signoff or FDA probability fails closed",()=>{
 const mutations=[
  v=>v.sourceReceiptSha256="0".repeat(64),
  v=>v.sourceArtifactId=1,
  v=>v.counts.currentRegisteredPrimaryTitles=44,
  v=>v.counts.exactCurrentTitleTimeframeMatches=15,
  v=>v.originalPreReadoutRegistryVersionVerified=true,
  v=>v.lockedSapAndMultiplicityVerified=true,
  v=>v.scientificScoresWritten=1,
  v=>v.counts.validatedFDAForecasts=1,
  v=>v.numericProbability=.95,
  v=>v.officialFdaPrediction="APPROVAL",
  v=>v.rows[0][0]="NCT99999999",
  v=>v.rows[1][0]=v.rows[0][0],
  v=>v.rows[0][3]=2,
  v=>v.rows[0].push("extra")
 ];
 mutations.forEach((change,i)=>{const v=clone(pin);change(v);
   assert.equal(validateR45CurrentEndpointText(v),null,"tamper "+i);});
});
test("R45 research-only panel is on predictions and does not write clinical scores",()=>{
 const page=fs.readFileSync(path.join(root,"app/predictions/page.tsx"),"utf8");
 const ui=fs.readFileSync(path.join(root,"app/predictions/FocusCurrentEndpointConcordanceR45.tsx"),"utf8");
 assert.ok(page.includes("<FocusCurrentEndpointConcordanceR45/>"));
 assert.match(ui,/all 29 trial-level/);
 assert.match(ui,/Not a locked SAP validation/);
 assert.match(ui,/validated FDA forecasts/);
 assert.doesNotMatch(ui,/fetch\(|submitGrade|POST\s*\/api/);
});
