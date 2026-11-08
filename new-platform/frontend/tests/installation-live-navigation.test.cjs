const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");

const app=path.resolve(__dirname,"../app");
const nav=fs.readFileSync(path.join(app,"GlobalNavigation.tsx"),"utf8");
const page=fs.readFileSync(path.join(app,"installation-audit/page.tsx"),"utf8");
const ui=fs.readFileSync(path.join(app,"installation-audit/InstallationLiveNavigator.tsx"),"utf8");
const catalog=JSON.parse(fs.readFileSync(path.join(app,"../public/installation-audit/science-40-catalog.json"),"utf8"));

test("INSTALLATION immediately follows TOOLS on global site navigation",()=>{
 const toolsAt=nav.indexOf('label:"TOOLS",href:"/tools"');
 const installAt=nav.indexOf('label:"INSTALLATION",href:"/installation-audit"');
 assert.ok(toolsAt>=0&&installAt>toolsAt);
 assert.equal(nav.slice(toolsAt,installAt).match(/label:/g)?.length,1);
 assert.match(page,/<InstallationLiveNavigator \/>/);
 assert.match(page,/<MasterBuildProgress \/>/);
});

test("live cursor requires real fresh RUNNING task identity; no guessed movement",()=>{
 assert.match(ui,/c\.state!=="RUNNING"/);
 assert.match(ui,/!c\.taskId\|\|!c\.observedAt/);
 assert.match(ui,/90000/);
 assert.match(ui,/taskList\.some\(t=>t\.id===c\.taskId\)/);
 assert.match(ui,/scrollIntoView/);
 assert.match(ui,/No verified active installation task is currently reported/);
 assert.match(ui,/15 seconds/);
 assert.match(ui,/In Progress.*does not establish|does not establish.*Codex/s);
});

test("past, present and future are backed by accepted task evidence",()=>{
 assert.match(ui,/status\(audit\?\.tasks\[t\.id\]\)==="Verified"/);
 assert.match(ui,/status\(audit\?\.tasks\[t\.id\]\)==="In Progress"/);
 assert.match(ui,/status\(audit\?\.tasks\[t\.id\]\)!=="Verified"/);
 assert.match(ui,/acceptanceMissing/);
 assert.match(ui,/Revalidation/);
 assert.doesNotMatch(ui,/setDemo\(/);
});

test("scientific drilldown preserves the original catalog and labels 800 as a target",()=>{
 assert.equal(catalog.questionCount,40);
 assert.equal(catalog.questions.length,40);
 assert.equal(catalog.maximumInvestigationDepth,20);
 assert.equal(new Set(catalog.questions.map(x=>x.id)).size,40);
 assert.equal(new Set(catalog.questions.map(x=>x.layer)).size,8);
 assert.equal(catalog.questionCount*catalog.maximumInvestigationDepth,800);
 assert.match(ui,/not 800 installed tests/);
 assert.match(ui,/up to 50 depth levels/);
 assert.match(ui,/Unknown<\/strong><br\/><small>Executed \/ passed/);
 assert.match(ui,/Expected evidence/);
});


test("LIVE arrow refreshes the current execution position before jumping",()=>{
 const css=fs.readFileSync(path.join(app,"installation-audit/InstallationLiveNavigator.module.css"),"utf8");
 assert.match(ui,/LIVE <span className=\{styles\.liveArrow\}/);
 assert.match(ui,/onClick=\{\(\)=>\{void goToLive\(\);\}\}/);
 assert.match(ui,/const latest=await fetchData\(\)/);
 assert.match(ui,/const cursor=getActiveExecution\(latest\)/);
 assert.match(ui,/setSection\("present"\)/);
 assert.match(ui,/setChosenTask\(cursor\?\.taskId\?\?null\)/);
 assert.match(ui,/requestAnimationFrame/);
 assert.match(ui,/document\.getElementById\(idOf\(liveJump\.taskId\)\)/);
 assert.match(ui,/document\.getElementById\("installation-active-cursor"\)/);
 assert.match(ui,/id="installation-active-cursor"/);
 assert.match(ui,/Live location unavailable: no fresh, verified running task is reported/);
 assert.match(ui,/90000/);
 assert.match(css,/\.liveButton/);
 assert.match(css,/\.liveArrow/);
 assert.match(css,/\.cursorTarget/);
 assert.doesNotMatch(ui,/status\(row\)==="In Progress".*setLiveJump/);
});
