const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs"),path=require("node:path"),vm=require("node:vm");
const ts=require("typescript");
const root=path.resolve(__dirname,"..");
const source=fs.readFileSync(path.join(root,"lib/medical-review-register.ts"),"utf8");
const generated=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020}}).outputText;
const mod={exports:{}};
vm.runInNewContext(generated,{module:mod,exports:mod.exports});
const {buildClinicalReviewRegisterCsv}=mod.exports;
const nct="NCT06081894";
function fixture(scored=false){
  const assessments=[], summaries=[], details={};
  for(let a=1;a<=40;a++){
    const methods=[],current=[];
    for(let m=1;m<=20;m++){
      methods.push({methodIndex:m,method:a===1&&m===2?"=DANGEROUS()":"Method "+m,
        methodDescription:"Science and evidence",priorityTier:"Critical",priorityRank:a*20+m,
        phaseApplicability:"PHASE3",requiredSources:"Original protocol"});
      const marked=scored&&a===1&&m===1;
      current.push({methodIndex:m,status:marked?"SCORED":scored?"UNREVIEWED":"VERIFY_PHASE",
        grade:marked?0:null,reviewEventId:marked?"review-1":null,revision:marked?1:null,
        reviewedAt:marked?"2026-11-08":null,reviewerId:marked?"authorized@example.org":null,
        rationale:marked?"Source examined":null,
        sourceEvidence:marked?[{sourceUrl:"https://clinicaltrials.gov/study/NCT06081894"}]:[],
        history:[],evidenceGaps:[]});
    }
    assessments.push({assessmentIndex:a,assessmentId:"A"+a,layerId:"L1",
      label:"Assessment "+a,methods});
    const summary={assessmentIndex:a,status:scored?(a===1?"PROVISIONAL":"NOT_REVIEWED"):"VERIFY_PHASE",
      reviewedMethods:scored&&a===1?1:0,excludedMethods:0,pendingMethods:scored&&a===1?19:20,
      applicableMethods:20,scoreOutOf100:scored&&a===1?0:null};
    summaries.push(summary);details[a]={...summary,methods:current};
  }
  return {catalog:{nct,assessments},review:{nct,totalPositions:800,
    verifiedPhase:scored?"PHASE3":null,phaseEventId:scored?"phase-1":null,
    counts:{SCORED:scored?1:0,NOT_APPLICABLE:0},assessments:summaries},details};
}
test("all 800 positions are exported, with blank unreviewed values never treated as grade zero",()=>{
  const f=fixture(),csv=buildClinicalReviewRegisterCsv(f.catalog,f.review,f.details);
  assert.equal(csv.trim().split("\r\n").length,801);
  assert.match(csv,/"VERIFY_PHASE",""/);
  assert.match(csv,/"'=DANGEROUS\(\)"/);
  assert.match(csv,/clinical_grade_0_to_5/);
  assert.doesNotMatch(csv,/"VERIFY_PHASE","0"/);
});
test("a genuine independently reviewed zero grade is retained rather than hidden or invented",()=>{
  const f=fixture(true),csv=buildClinicalReviewRegisterCsv(f.catalog,f.review,f.details);
  assert.match(csv,/"SCORED","0","review-1"/);
  assert.equal(csv.trim().split("\r\n").length,801);
});
test("fail closed on partial, mismatched or unsupported records",()=>{
  const f=fixture();delete f.details[40];
  assert.throws(()=>buildClinicalReviewRegisterCsv(f.catalog,f.review,f.details),/ALL_800/);
  const g=fixture(true);g.details[1].methods[0].grade=null;
  assert.throws(()=>buildClinicalReviewRegisterCsv(g.catalog,g.review,g.details),/UNVERIFIED_GRADE/);
  const h=fixture();h.catalog.nct="NCT00000001";
  assert.throws(()=>buildClinicalReviewRegisterCsv(h.catalog,h.review,h.details),/INVALID_SNAPSHOT/);
});
test("interface only enables export after all 40 authenticated method groups loaded",()=>{
  const component=fs.readFileSync(path.join(root,"app/predictions/assessment/ScientificMethodMatrix.tsx"),"utf8");
  assert.match(component,/buildClinicalReviewRegisterCsv\(catalog,review,details\)/);
  assert.match(component,/Object\.keys\(details\)\.length!==40/);
  assert.match(component,/Object\.values\(errors\)\.some\(Boolean\)/);
  assert.match(component,/blank grades remain blank/);
});
