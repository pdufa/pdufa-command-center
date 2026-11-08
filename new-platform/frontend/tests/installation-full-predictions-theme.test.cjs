const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");

const dir=path.resolve(__dirname,"../app/installation-audit");
const src=(file)=>fs.readFileSync(path.join(dir,file),"utf8");
const page=src("page.tsx");
const css=src("InstallationAuditTheme.module.css");
const chart=src("InstallationProgressChart.tsx");
const master=src("MasterBuildProgress.tsx");
const daily=src("DailySystemProgress.tsx");
const science=src("ScientificOutcomeLive.tsx");
const navigator=src("InstallationLiveNavigator.tsx");
const predictions=fs.readFileSync(path.resolve(__dirname,"../app/predictions/FocusPredictionNavigator.module.css"),"utf8");

test("whole INSTALLATION page uses same PREDICTIONS navy-teal-dark palette",()=>{
 assert.match(page,/className=\{styles\.auditPage\}/);
 assert.match(page,/InstallationAuditTheme\.module\.css/);
 for(const color of ["#071824","#0b3543","#0a2c3b","#39717b","#e7f9fc","#6af8cf"]){
  assert.ok(predictions.includes(color),"PREDICTIONS palette missing "+color);
  assert.ok((page+css+chart+master+daily+science).includes(color),"INSTALLATION palette missing "+color);
 }
 assert.match(css,/\.auditPage :global\(a\)/);
 assert.match(css,/\.auditPage :global\(th\)/);
});

test("legacy audit table is not white: header, alternate rows, status tones and cards",()=>{
 assert.match(page,/background:"#123e4b"/);
 assert.match(page,/background:i%2\?"#102f3a":"#0b2a38"/);
 assert.match(page,/color:isAccepted\(item\)\?"#6af8cf":"#ffdc97"/);
 assert.match(page,/"Not verified": "#ffb4a6"/);
 assert.match(page,/"Not audited": "#c1dfe2"/);
 assert.match(page,/borderBottom:"1px solid #315f69"/);
 for(const source of [page,chart,master,daily,science]){
  assert.doesNotMatch(source,/background:(?:"white"|"#fff"|"#f8fafc"|"#f1f5f9")/);
 }
});

test("progress chart, master inventory, daily snapshots and SCIENCE panels keep dark surfaces",()=>{
 for(const source of [chart,master,daily,science]){
  assert.match(source,/background:"#0b3040"/);
 }
 assert.match(chart,/background:"#0a2c3b"/);
 assert.match(master,/background:"#0b3040"/);
 assert.match(daily,/background:"#0a2c3b"/);
 assert.match(science,/background:"#0a2c3b"/);
 assert.match(science,/background:"#0b625c"/);
 assert.match(navigator,/installationExpanded&&<div id="installation-tracker-details"/);
 assert.match(navigator,/<details id="scientific-assessment-register"/);
 assert.match(navigator,/LOCATE LIVE/);
});
