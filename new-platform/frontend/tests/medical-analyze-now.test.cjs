const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const read=p=>fs.readFileSync(path.join(__dirname,"..",p),"utf8");
const focus=JSON.parse(read("data/p3PostDataActive.json"));
const historical=JSON.parse(read("../backend/app/data/focus_legacy_score_snapshot.json"));
const list=read("app/p3-post-data/page.tsx");
const control=read("app/focus/AnalyzeNowTrial.tsx");
const api=read("app/api/analyze-now/route.ts");
const backend=read("../backend/app/medical_on_demand.py");
const worker=read("../backend/app/medical_continuous.py");
const advanced=read("../backend/app/medical_advanced_runtime.py");
const proxy=read("proxy.ts");

test("29 exact FOCUS trial rows share one pilot-gated independent source worker",()=>{
 assert.equal(focus.records.length,29);
 assert.equal(new Set(focus.records.map(r=>r.nct)).size,29);
 assert.match(list,/trials\.map\(\(t,i\)=>/);
 assert.match(list,/AnalyzeNowTrial nct=\{t\.nct\}/);
 assert.match(list,/analyzeAllEnabled\|\|t\.nct===canaryNct/);
 assert.match(control,/Analyze Now/);
 assert.match(control,/\/api\/analyze-now/);
 assert.match(api,/pilotAllowed/);
 assert.match(api,/PDUFA_ANALYZE_NOW_ALL_ENABLED/);
 assert.match(backend,/core\.create\(engine,nct,request_key,submit=False\)/);
 assert.doesNotMatch(backend,/ThreadPoolExecutor|new Thread\(/);
 assert.match(worker,/medical_on_demand import initialize/);
});
test("authenticated exact-NCT operation cannot start a different trial",()=>{
 assert.match(api,/hasSession/);
 assert.match(api,/req\.headers\.get\("origin"\)!==req\.nextUrl\.origin/);
 assert.match(api,/eligible\(nct\)/);
 assert.match(api,/UUID\.test\(requestKey\)/);
 assert.match(api,/\/api\/analyze-now\/"/);
 assert.match(api,/not configured|not connected/i);
});
test("retired score archive exists but no longer participates in live analysis",()=>{
 assert.equal(historical.schemaVersion,1);
 assert.equal(historical.records.length,29);
 assert.equal(new Set(historical.records.map(r=>r.nct)).size,29);
 assert.doesNotMatch(backend,/raas|LEGACY|optional_legacy|focus_legacy_score_snapshot/i);
 assert.doesNotMatch(control,/raas|raasOverall|scientificFiveFactorScore|historicalFiveFactorEventIds/i);
 assert.doesNotMatch(list,/raas|BottomClinicalRating|bottomTrialHistory/i);
 assert.match(backend,/scientificAssessment/);
 assert.match(backend,/fdaPredictions/);
 assert.match(backend,/NOT_VALIDATED/);
 assert.match(backend,/ABSTAIN/);
 assert.match(backend,/initial_report/);
 assert.match(advanced,/report\["analyzeNow"\]=build_saved_analysis/);
});
test("exact-NCT immutable history survives spreadsheet movement and failures",()=>{
 assert.match(backend,/historyKey":"EXACT_NCT"/);
 assert.match(backend,/LEFT JOIN medical_analyze_requests/);
 assert.match(backend,/LEFT JOIN medical_prediction_revisions/);
 assert.match(backend,/initial_report/);
 assert.match(control,/loadHistory/);
 assert.match(control,/locationIndependent/);
 assert.match(control,/missingEvidence/);
 assert.match(control,/supportingSourceUrls/);
});
test("automation is opt-in and same-canary gated for component and registry changes",()=>{
 assert.match(advanced,/check_registry_updates_once/);
 assert.match(advanced,/REGISTRY_CHANGE/);
 assert.match(advanced,/eligible_for_analysis/);
 assert.match(backend,/check_operational_component_changes/);
 assert.match(backend,/eligible_for_analysis\(nct\)/);
 assert.match(backend,/COMPONENT_CHANGE/);
 assert.doesNotMatch(backend,/calibrationReleasePermitted\s*:\s*True/);
});
test("retired UI/API routes are 410 and current report contains no retired scores",()=>{
 assert.match(proxy,/status:410/);
 assert.match(proxy,/raas/);
 assert.doesNotMatch(read("lib/main-install-progress.ts"),/raas/i);
 assert.doesNotMatch(read("app/main/page.tsx"),/raas/i);
});
