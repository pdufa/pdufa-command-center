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


test("LIVE arrow jumps immediately and refreshes in the background",()=>{
 const css=fs.readFileSync(path.join(app,"installation-audit/InstallationLiveNavigator.module.css"),"utf8");
 assert.match(ui,/<span>LOCATE LIVE<\/span> <span className=\{styles\.liveArrow\}/);
 assert.match(ui,/onClick=\{\(\)=>\{void goToLive\(\);\}\}/);
 assert.match(ui,/locateSnapshot\(audit\);\s*void fetchData\(\)\.then\(latest=>/);
 assert.ok(ui.indexOf("locateSnapshot(audit);") < ui.indexOf("void fetchData().then(latest=>"));
 assert.doesNotMatch(ui,/onClick=\{\(\)=>\{void goToLive\(\);\}\} disabled=\{busy\}/);
 assert.match(ui,/const cursor=getActiveExecution\(snapshot\)/);
 assert.match(ui,/setSection\("present"\)/);
 assert.match(ui,/setChosenTask\(destination\)/);
 assert.match(ui,/requestAnimationFrame/);
 assert.match(ui,/second=window\.requestAnimationFrame/);
 assert.match(ui,/data-installation-task-list/);
 assert.match(ui,/list\.scrollTop\+=/);
 assert.match(ui,/target\.focus\(\{preventScroll:true\}\)/);
 assert.match(ui,/document\.getElementById\(idOf\(liveJump\.taskId\)\)/);
 assert.match(ui,/document\.getElementById\("installation-active-cursor"\)/);
 assert.match(ui,/id="installation-active-cursor"/);
 assert.match(ui,/Live location not verified/);
 assert.match(ui,/getRunningGithub\(snapshot\)/);
 assert.match(ui,/installation-github-execution/);
 assert.match(ui,/No verified live location has loaded yet/);
 assert.match(ui,/90000/);
 assert.match(css,/\.liveButton/);
 assert.match(css,/\.liveArrow/);
 assert.match(css,/\.cursorTarget/);
 assert.match(css,/\.locateIcon/);
 assert.match(css,/\.checkpointMarker/);
 assert.match(ui,/const workflow=cursor\?null:getRunningGithub\(snapshot\)/);
 assert.match(ui,/aria-current=\{located\?"location":undefined\}/);
 assert.match(ui,/Exact Codex \/ scientific task identity is not verified/);
 assert.match(ui,/kind:cursor\?"live":workflow\?"workflow":"status"/);
 assert.doesNotMatch(ui,/getDocumentedCheckpoint\(snapshot\)/);
 assert.doesNotMatch(ui,/status\(row\)==="In Progress".*setLiveJump/);
});


test("installation timeline and scientific assessments collapse under independent carets",()=>{
 const css=fs.readFileSync(path.join(app,"installation-audit/InstallationLiveNavigator.module.css"),"utf8");
 assert.match(ui,/const \[installationExpanded,setInstallationExpanded\]=useState\(false\)/);
 assert.match(ui,/aria-expanded=\{installationExpanded\} aria-controls="installation-tracker-details"/);
 assert.match(ui,/onClick=\{\(\)=>setInstallationExpanded\(open=>!open\)\}/);
 assert.match(ui,/installationExpanded&&<div id="installation-tracker-details"/);
 assert.match(ui,/<details id="scientific-assessment-register"/);
 assert.match(ui,/<summary className=\{styles\.scienceSummary\}>Scientific assessments/);
 assert.match(css,/\.sectionCaret/);
 assert.match(css,/\.scienceSummary::marker/);
});

test("LOCATE LIVE still opens the caret before scrolling to the task",()=>{
 assert.match(ui,/setInstallationExpanded\(true\);/);
 assert.match(ui,/if\(!liveJump\|\|!installationExpanded\)return/);
 assert.match(ui,/\[liveJump,section,installationExpanded\]/);
 assert.match(ui,/if\(!following\|\|!installationExpanded\)return/);
 assert.match(ui,/document\.getElementById\(idOf\(liveJump\.taskId\)\)/);
 assert.match(ui,/document\.getElementById\("installation-active-cursor"\)/);
 assert.match(ui,/No active GitHub Actions workflow or task-specific live heartbeat/);
});

test("verified GitHub runs are independently observable, never certified as Codex tasks",()=>{
 const route=fs.readFileSync(path.join(app,"api/installation-audit/live-task-evidence/route.ts"),"utf8");
 assert.match(route,/hasSession\(sessionCookie\)/);
 assert.match(route,/fetchLiveGithubActions\(process\.env\.PDUFA_GITHUB_TOKEN,checkedAt\)/);
 assert.match(route,/githubActions,/);
 assert.match(ui,/GitHub Actions workflow/);
 assert.match(ui,/No in-progress GitHub Actions workflows observed/);
 assert.match(ui,/running\.map\(run=>/);
 assert.match(ui,/jobStatus/);
 assert.match(ui,/not a Codex task-level heartbeat/);
 assert.doesNotMatch(ui,/Located last documented checkpoint/);
});
