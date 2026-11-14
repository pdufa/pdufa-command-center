const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");

const app=path.join(__dirname,"..","app");
const component=fs.readFileSync(path.join(app,"ScientificStepsReadiness.tsx"),"utf8");

test("shared readiness explicitly avoids claiming scientific activation",()=>{
 assert.match(component,/Integration pending/);
 assert.match(component,/Not live/);
 assert.match(component,/No score or FDA prediction is implied/);
});
for(const [name,cohort] of [["pool","POOL"],["focus","FOCUS"],["past","PAST"]]){
 test(name+" includes Steps 1-3 readiness with correct cohort",()=>{
  const source=fs.readFileSync(path.join(app,name,"page.tsx"),"utf8");
  assert.match(source,/ScientificStepsReadiness/);
  assert.ok(source.includes('cohort="'+cohort+'"'));
 });
}

test("exact trial guard matches NCT followed by eight digits and rejects mismatched identities",()=>{
 assert.ok(component.includes(String.raw`/^NCT\d{8}$/`));
 assert.match(component,/trial\.nctId===trial\.assessmentNctId/);
 assert.match(component,/const intake=exactTrial\?trial\?\.intake:undefined/);
});

test("FOCUS links each exact NCT to saved research without claiming an assessment",()=>{
 const source=fs.readFileSync(path.join(app,"focus","page.tsx"),"utf8");
 assert.ok(source.includes('href={"/analyze-now?nct="+encodeURIComponent(t.nct)}'));
 assert.match(source,/View exact-trial research history/);
});
test("scientific panel fails closed when FDA prediction is not ABSTAIN",()=>{
 assert.match(component,/intake\?\.fdaPrediction==="ABSTAIN"/);
 assert.match(component,/scientificScoreStatus==="NOT_VALIDATED"/);
 assert.match(component,/Array\.isArray\(intake\.missingEvidence\)/);
});

test("exact-program loader uses authenticated assessments and fails closed on identity mismatch",()=>{
 const source=fs.readFileSync(path.join(app,"ExactTrialScientificIntake.tsx"),"utf8");
 assert.match(source,/\/api\/assessments\?identity=/);
 assert.match(source,/record\.id!==programIdentity\|\|record\.nctId!==nctId/);
 assert.match(source,/!validIntake\(record\.levelOneIntake\)/);
 assert.match(source,/scientificValidation==="NOT_VERIFIED"/);
 assert.match(source,/scientificScoreStatus==="NOT_VALIDATED"/);
});

test("FOCUS trial rows expose explicit exact-program intake selector without auto-mapping",()=>{
 const source=fs.readFileSync(path.join(app,"focus","page.tsx"),"utf8");
 const loader=fs.readFileSync(path.join(app,"ExactTrialScientificIntake.tsx"),"utf8");
 assert.match(source,/<ExactTrialIntakeSelector cohort="FOCUS" nctId=\{t\.nct\}\/>/);
 assert.match(loader,/Program identity must be verified separately/);
 assert.match(loader,/programIdentity=\{selected\}/);
});

test("POOL exact-NCT review rows provide a guarded intake selector",()=>{
 const source=fs.readFileSync(path.join(app,"FunnelWorkspace.tsx"),"utf8");
 assert.match(source,/<ExactTrialIntakeSelector cohort="POOL" nctId=\{r\.nctId\}\/>/);
 assert.match(source,/section==="pool"/);
});

test("PAST requires explicit NCT and exact program before intake lookup",()=>{
 const source=fs.readFileSync(path.join(app,"past","page.tsx"),"utf8");
 assert.match(source,/Historical event-to-NCT linkage remains unverified/);
 assert.match(source,/<ExactTrialIntakeSelector cohort="PAST" nctId=\{verifiedNctByEvent\[r\.eventKey\]\}\/>/);
 assert.ok(source.includes(String.raw`/^NCT\\d{8}$/`), "PAST must validate the exact NCT format");
});
