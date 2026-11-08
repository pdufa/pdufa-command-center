const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const root=path.resolve(__dirname,"../../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
test("Monitor is on MAIN and a standalone active route",()=>{
 const main=read("new-platform/frontend/app/main/page.tsx");
 const standalone=read("new-platform/frontend/app/precision-monitor/page.tsx");
 const nav=read("new-platform/frontend/app/GlobalNavigation.tsx");
 const ui=read("new-platform/frontend/app/main/InstallationProgressDashboard.tsx");
 assert.match(main,/<InstallationProgressDashboard\s*\/>/);
 assert.match(standalone,/Precision Monitoring Dashboard/);
 assert.match(nav,/href="\/precision-monitor"/);
 assert.match(ui,/45000/);
 assert.match(ui,/<TrialEvidenceExplorer\s*\/>/);
 assert.match(ui,/data\.signals\.alerts/);
});
test("Read-only monitor and history endpoints require session and use secret backend proxy",()=>{
 for(const path of ["new-platform/frontend/app/api/main/installation-progress/route.ts",
 "new-platform/frontend/app/api/main/installation-trial/route.ts"]){
  const code=read(path);
  assert.match(code,/hasSession/);
  assert.match(code,/authConfigured/);
  assert.match(code,/X-Pdufa-Internal-Key/);
  assert.doesNotMatch(code,/export async function POST|sendMessage|placeOrder|startScan/);
 }
 const history=read("new-platform/frontend/app/api/main/installation-trial/route.ts");
 assert.match(history,/nctRx\.test\(nct\)/);
 assert.match(history,/raw\.nct!==nct/);
 assert.match(history,/\.slice\(0,100\)/);
});
test("Installation scoring is based only on evidence, never retired grades",()=>{
 const p=read("new-platform/frontend/lib/main-install-progress.ts");
 const l=read("new-platform/frontend/lib/precision-monitor-levels.ts");
 assert.match(p,/precision-monitor-levels/);
 assert.doesNotMatch(p,/from ".\/medical-intelligence-advanced"|raasOverall|focus_legacy_score_snapshot/);
 assert.equal((l.match(/requiredEvidence:/g)||[]).length,12);
 assert.match(p,/from\("medical\.code","Independent research framework","PENDING"/);
});
test("Trial detail keeps all unvalidated outcomes abstaining",()=>{
 const t=read("new-platform/frontend/app/main/TrialEvidenceExplorer.tsx");
 assert.match(t,/ABSTAIN \(approval \/ CRL \/ delay\)/);
 assert.match(t,/NOT VALIDATED/);
 assert.match(t,/focus\.records/);
 assert.match(t,/saved revision history/);
});
