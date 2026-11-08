const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const root=path.join(__dirname,"..");
const page=fs.readFileSync(path.join(root,"app/p3-post-data/page.tsx"),"utf8");
const control=fs.readFileSync(path.join(root,"app/focus/AnalyzeNowTrial.tsx"),"utf8");
const proxy=fs.readFileSync(path.join(root,"app/api/analyze-now/route.ts"),"utf8");
const historyPage=fs.readFileSync(path.join(root,"app/analyze-now/history/page.tsx"),"utf8");
const canonicalHistoryPage=fs.readFileSync(path.join(root,"app/analyze-now/page.tsx"),"utf8");
const focus=JSON.parse(fs.readFileSync(path.join(root,"data/p3PostDataActive.json"),"utf8"));
test("every exact eligible FOCUS row has Analyze Now plus history control",()=>{
 assert.equal(focus.records.length,29);
 assert.equal(new Set(focus.records.map(r=>r.nct)).size,29);
 assert.match(page,/trials\.map\(\(t,i\)=>/);
 assert.match(page,/<AnalyzeNowTrial nct=\{t\.nct\}/);
 assert.match(page,/Analyze Now · history/);
 assert.match(control,/>\s*Analyze Now\s*</);
 assert.match(control,/History/);
 assert.match(control,/nct,requestKey:crypto\.randomUUID\(\)/);
 assert.match(control,/run\?\.status==="PENDING"\|\|run\?\.status==="RUNNING"/);
 assert.match(control,/3500/);
});
test("one-trial canary is gated until verified live pilot, including on server",()=>{
 assert.match(page,/analyzeAllEnabled=process\.env\.PDUFA_ANALYZE_NOW_ALL_ENABLED==="true"/);
 assert.match(page,/NCT06081894/);
 assert.match(proxy,/PDUFA_ANALYZE_NOW_ALL_ENABLED==="true"/);
 assert.match(proxy,/pilotAllowed\(nct\)/);
 assert.match(proxy,/limited to the canary trial/);
});
test("analysis endpoint requires an operator session, same origin and eligible NCT",()=>{
 assert.match(proxy,/hasSession/);
 assert.match(proxy,/req\.headers\.get\("origin"\)!==req\.nextUrl\.origin/);
 assert.match(proxy,/focus\.records\.some\(r=>r\.nct===nct\)/);
 assert.match(proxy,/UUID\.test\(requestKey\)/);
 assert.match(proxy,/GET\(req:NextRequest\)/);
 assert.match(proxy,/history==="1"/);
 assert.match(proxy,/POST\(req:NextRequest\)/);
 assert.match(proxy,/PDUFA_INTERNAL_API_KEY/);
 assert.match(proxy,/private, no-store/);
});
test("Analyze Now displays only independent source investigations and abstaining FDA outcomes",()=>{
 assert.match(control,/Scientific source checks/);
 assert.match(control,/Independent signoff:/);
 assert.match(control,/a\.fdaPredictions\.map/);
 assert.match(control,/Not validated/);
 assert.match(control,/a\.missingEvidence\.map/);
 assert.match(control,/a\.supportingSourceUrls/);
 assert.match(control,/h\.analysis\?<Report/);
 assert.doesNotMatch(control,/raas|Full RAAS|scientificFiveFactorScore/i);
});

test("retired scores remain in read-only evidence files, never loaded by Analyze Now",()=>{
 const historic=JSON.parse(fs.readFileSync(path.join(root,"data/bottomOnlyScoreHistory20261107.json"),"utf8"));
 const pilot=historic.records.filter(x=>x.nctId==="NCT06081894"&&x.recordedAt==="2026-11-07");
 assert.ok(pilot.length>0);
 assert.ok(pilot.every(x=>x.clinicalFullScore===45&&x.clinicalScoredFactors===5));
 const RAAS=JSON.parse(fs.readFileSync(path.join(root,"data/raas-trial-score-history.json"),"utf8"));
 assert.ok(!RAAS.records.some(x=>x.nctId==="NCT06081894"&&typeof x.score==="number"));
 const active=fs.readFileSync(path.join(root,"../backend/app/medical_on_demand.py"),"utf8");
 assert.doesNotMatch(active,/optional_legacy|focus_legacy_score_snapshot|raasOverall|raasScoreKind/i);
});

test("archived exact-NCT history remains reachable without active FOCUS membership",()=>{
 assert.match(page,/href="\/analyze-now\/history"/);
 assert.match(historyPage,/redirect\(nct\?/);
 assert.match(historyPage,/\/analyze-now\?nct=/);
 assert.match(canonicalHistoryPage,/historyOnly/);
 assert.match(canonicalHistoryPage,/pattern="NCT\[0-9\]\{8\}"/);
 assert.match(canonicalHistoryPage,/AnalyzeNowTrial nct=\{nct\} enabled=\{false\}/);
 assert.match(canonicalHistoryPage,/read-only and never starts a new analysis/);
 assert.match(proxy,/Historical exact NCTs remain accessible after the trial leaves FOCUS/);
});
