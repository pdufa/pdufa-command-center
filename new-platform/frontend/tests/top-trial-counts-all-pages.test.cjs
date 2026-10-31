const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const read=(name)=>fs.readFileSync(path.join(__dirname,"../app",name),"utf8");

test("Four colored stage cards render on every main tab including Calendar",()=>{
  const ws=read("Workspace.tsx");
  assert.match(ws,/<div className="nav-wrapper">/);
  assert.match(ws,/<div className="workflow-counts" role="group"/);
  assert.doesNotMatch(ws,/top==="PDUFA" && <div className="workflow-counts"/);
  assert.doesNotMatch(ws,/top==="PDUFA" && <div className="nav-wrapper"/);
  assert.match(ws,/onClick=\{\(\)=>\{setTop\("PDUFA"\);setNav\(item\.id\)/);
  assert.match(ws,/top==="CALENDAR" && <section className="panel"/);
});

test("Top cards are above research body and use real corresponding page totals",()=>{
 const ws=read("Workspace.tsx");
 const nav=ws.indexOf('id="pdufa-section-navigation"');
 const row=ws.indexOf('className="workflow-counts"');
 const body=ws.indexOf('className="workspace-update-row"');
 assert.ok(nav>=0 && row>nav && body>row);
 for(const [field,source] of [["PIPELINE","designationQualified.length"]]) {
   assert.ok(ws.includes(field+": "+source),field+" total must match its page");
 }
 assert.match(ws,/localStorage\.setItem\("pdufa_stage_totals_v1"/);
 assert.doesNotMatch(ws,/id:"GEM_JR" as Nav, label:"GEM JR"/);
 assert.doesNotMatch(ws,/id:"GEM" as Nav, label:"GEM"/);
});

test("Standalone trial sheets use Pipeline-only source count and navigation",()=>{
 const page=read("trial/[nctId]/page.tsx");
 const trial=read("TrialWorkflowCounts.tsx");
 assert.match(page,/<TrialWorkflowCounts \/>/);
 assert.match(trial,/className="workflow-counts"/);
 assert.match(trial,/import WorkflowStageIcon/);
 assert.match(trial,/fetch\("\/api\/workspace\/summary"/);
 assert.match(trial,/saved\?\.asOf===data\.asOf/);
 assert.match(trial,/href="\/pipeline"/);
 assert.doesNotMatch(trial,/label:"GEM JR"|label:"GEM"|label:"WT"/);
 assert.doesNotMatch(trial,/fetch\("\/api\/program-watch-trade"/);
 assert.match(read("Workspace.tsx"),/new URLSearchParams\(window\.location\.search\)\.get\("section"\)/);
});

test("Production home places section header directly ahead of stage bar without obsolete migration banner",()=>{
 const home=read("page.tsx");
 const css=read("globals.css");
 assert.match(home,/<Workspace onInspect=\{inspectProgram\} \/>/);
 assert.doesNotMatch(home,/<div className="banner"><strong>Streamlit is preserved/);
 assert.match(css,/\.migration-workspace \.workflow-count--pipeline/);
 assert.match(css,/\.migration-workspace \.workflow-count--gem_jr/);
 assert.match(css,/\.migration-workspace \.workflow-count--gem \{/);
 assert.match(css,/\.migration-workspace \.workflow-count--wt/);
});
