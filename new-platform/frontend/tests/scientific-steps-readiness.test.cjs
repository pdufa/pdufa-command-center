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
