const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const root=path.join(__dirname,"..");
const page=fs.readFileSync(path.join(root,"app/p3-post-data/page.tsx"),"utf8");
const control=fs.readFileSync(path.join(root,"app/focus/AnalyzeNowTrial.tsx"),"utf8");
const proxy=fs.readFileSync(path.join(root,"app/api/analyze-now/route.ts"),"utf8");
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
test("clinical five-factor score remains explicitly different from full RAAS and FDA probability",()=>{
 assert.match(control,/Full RAAS \(30 metrics\)/);
 assert.match(control,/Preserved clinical research \(5 factors\)/);
 assert.match(control,/No independent scientific signoff/);
 assert.match(control,/a\.fdaPredictions\.map/);
 assert.match(control,/Not issued/);
 assert.match(control,/a\.missingEvidence\.map/);
 assert.match(control,/a\.supportingSourceUrls/);
 assert.match(control,/h\.analysis\?<Report/);
});
test("legacy optional scored archive contains the exact pilot score from real preserved history",()=>{
 const historic=JSON.parse(fs.readFileSync(path.join(root,"data/bottomOnlyScoreHistory20261107.json"),"utf8"));
 const pilot=historic.records.filter(x=>x.nctId==="NCT06081894"&&x.recordedAt==="2026-11-07");
 assert.ok(pilot.length>0);
 assert.ok(pilot.every(x=>x.clinicalFullScore===45&&x.clinicalScoredFactors===5));
 const RAAS=JSON.parse(fs.readFileSync(path.join(root,"data/raas-trial-score-history.json"),"utf8"));
 assert.ok(!RAAS.records.some(x=>x.nctId==="NCT06081894"&&typeof x.score==="number"));
});
