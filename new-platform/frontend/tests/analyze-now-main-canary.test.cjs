const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const root=path.resolve(__dirname,"../../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const records=JSON.parse(read("new-platform/frontend/data/p3PostDataActive.json")).records;
const app=read("new-platform/frontend/app/analyze-now/page.tsx");
const proxy=read("new-platform/frontend/app/api/analyze-now/route.ts");
const backend=read("new-platform/backend/app/main.py");
const source=read("new-platform/backend/app/medical_on_demand.py");
const snapshot=JSON.parse(read("new-platform/backend/app/data/focus_snapshot.json")).records;

test("Analyze Now is keyed to exact current FOCUS identities",()=>{
  assert.equal(records.length,32);
  assert.deepEqual(snapshot.map(x=>x.nct),records.map(x=>x.nct));
  assert.ok(records.some(x=>x.nct==="NCT06081894"));
  assert.match(app,/focus\.records\.some\(record=>record\.nct===nct\)/);
  assert.match(app,/canary\|\|rollout/);
  assert.match(app,/historyOnly=\{!canStart\}/);
});

test("Analyze Now starts only by authenticated same-origin canary request",()=>{
  assert.match(proxy,/hasSession/);
  assert.match(proxy,/req\.headers\.get\("origin"\)!==req\.nextUrl\.origin/);
  assert.match(proxy,/UUID\.test\(requestKey\)/);
  assert.match(proxy,/pilotAllowed\(nct\)/);
  assert.match(proxy,/nct==\=\(process\.env\.PDUFA_ANALYZE_NOW_CANARY_NCT/);
  assert.match(app,/never an FDA forecast/);
});

test("Backend and stage worker fail closed until explicit isolated PostgreSQL opt-in",()=>{
  assert.match(backend,/PDUFA_MEDICAL_PREVIEW_ENABLED/);
  assert.ok(backend.includes('DATABASE_URL.startswith("postgresql+psycopg://")'));
  assert.match(backend,/medical_canary_preflight/);
  assert.match(backend,/def require_medical_pilot_storage\(\)/);
  assert.match(backend,/REQUIRE_POSTGRES and DATABASE_URL\.startswith/);
  assert.match(backend,/getattr\(app\.state, "medical_canary_initialized", False\)/);
  assert.match(backend,/install_analyze_now_routes\(app, lambda: ENGINE, require_medical_internal_key, require_medical_pilot_storage\)/);
  assert.match(backend,/install_medical_continuous_routes\(app, lambda: ENGINE, require_medical_internal_key, require_medical_pilot_storage\)/);
  assert.match(source,/core\.create\(engine,nct,request_key,submit=False\)/);
  assert.match(source,/"APPROVAL","CRL","REVIEW_DELAY"/);
  assert.match(source,/"ABSTAIN"/);
  assert.match(source,/"NOT_VALIDATED"/);
});

test("No retired scoring history becomes a source for new analysis",()=>{
  assert.doesNotMatch(source,/focus_legacy_score_snapshot|raasOverall|scientificFiveFactorScore/i);
  assert.doesNotMatch(app,/p3-post-data\//);
});
