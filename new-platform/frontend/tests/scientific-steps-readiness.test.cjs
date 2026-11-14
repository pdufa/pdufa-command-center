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
