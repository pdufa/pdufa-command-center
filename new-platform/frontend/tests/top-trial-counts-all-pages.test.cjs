const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const read=name=>fs.readFileSync(path.join(__dirname,"../app",name),"utf8");
test("production home uses native active POOL and Pipeline without legacy workbench",()=>{
 const home=read("page.tsx");
 const nav=read("GlobalNavigation.tsx");
 assert.doesNotMatch(home,/from "\.\/Workspace"|\bGemQualificationChecklist\b|streamlit\.app/i);
 assert.match(home,/href:"\/pool"/);
 assert.match(home,/href:"\/pipeline"/);
 assert.match(nav,/label:"TOOLS",href:"\\/tools"/);
 assert.match(nav,/label:"SCAN",href:"\\/scans"/);
 for(const retired of ["POOL","RESULTS","GOAL","RESTRICTIONS"])
  assert.ok(!nav.includes('label:"'+retired+'"'),retired+" should not be a top navigation link");
 assert.doesNotMatch(nav,/\bGEM[_ ]JR\b|\bGEM\b|streamlit/i);
});
test("every active site section has a native page",()=>{
 for(const file of ["pool/page.tsx","pipeline/page.tsx","tools/page.tsx","scans/page.tsx",
    "results/page.tsx","goal/page.tsx","restrictions/page.tsx",
    "predictions/page.tsx","patient-population/page.tsx"]){
  assert.ok(read(file).length>0,file);
 }
});
test("standalone trial sheets show the Pipeline source total only",()=>{
 const page=read("trial/[nctId]/page.tsx");
 const trial=read("TrialWorkflowCounts.tsx");
 assert.match(page,/<TrialWorkflowCounts \/>/);
 assert.match(trial,/fetch\("\/api\/workspace\/summary"/);
 assert.match(trial,/href="\/pipeline"/);
 assert.doesNotMatch(trial,/fetch\("\/api\/program-watch-trade"/);
});
