const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path");
const root=path.resolve(__dirname,"..");
const scientific=fs.readFileSync(path.join(root,"app/predictions/assessment/ScientificMethodMatrix.tsx"),"utf8");
const monitor=fs.readFileSync(path.join(root,"app/predictions/assessment/LivePredictionMonitor.tsx"),"utf8");
const snapshot=fs.readFileSync(path.join(root,"app/predictions/assessment/PilotPredictionWorkup.tsx"),"utf8");
const route=fs.readFileSync(path.join(root,"app/api/predictions/medical-matrix/route.ts"),"utf8");

test("LIVE uses actual authenticated isolated ledger with bounded poll and no worker fiction",()=>{
  assert.match(scientific,/fetch\("\/api\/predictions\/medical-matrix\?nct="/);
  assert.match(scientific,/window\.setInterval\(\(\) =>/);
  assert.match(scientific,/document\.visibilityState === "visible"/);
  assert.match(scientific,/15000\)/);
  assert.match(scientific,/document\.addEventListener\("visibilitychange"/);
  assert.match(scientific,/document\.removeEventListener\("visibilitychange"/);
  assert.match(scientific,/window\.clearInterval\(interval\)/);
  assert.match(scientific,/abort\.abort\(\)/);
  assert.match(scientific,/if \(inFlight \|\| disposed \|\| abort\.signal\.aborted\) return/);
  assert.match(route,/hasSession/);
  assert.match(route,/isolatedMedicalBackend/);
  assert.match(route,/validateReviewMatrix/);
  assert.match(route,/assertMatrixPhaseSnapshot/);
  assert.match(route,/cache: "no-store"/);
});
test("run status refuses to claim activity or prediction without a backend event stream",()=>{
  assert.match(monitor,/CURRENT PREDICTION RUN/);
  assert.match(monitor,/NOT OBSERVABLE/);
  assert.match(monitor,/The backend has no prediction-run activity feed/);
  assert.match(monitor,/FDA PREDICTION/);
  assert.match(monitor,/ABSTAIN/);
  assert.match(monitor,/ACCURACY RATING/);
  assert.match(monitor,/NOT CALIBRATED/);
  assert.match(monitor,/not reported by the existing backend/);
  assert.match(monitor,/Source research worker · 12 stages/);
  assert.match(monitor,/This is a real <strong>source collection<\/strong> job/);
  assert.doesNotMatch(monitor,/>RUNNING</);
  assert.doesNotMatch(monitor,/>100%</);
});
test("live progress only counts independently recorded reviewed/excluded methods, not fetched rows",()=>{
  assert.match(monitor,/review\?\.counts\.SCORED/);
  assert.match(monitor,/review\?\.counts\.NOT_APPLICABLE/);
  assert.match(monitor,/800-graded-excluded/);
  assert.match(monitor,/Progress withheld until the isolated ledger can be read and validated/);
  assert.match(monitor,/refreshing\|\|loading/);
  assert.match(monitor,/onClick=\{\(\)=>\{refresh\(\);sourcePollRef\.current\?\.\(\);\}\}/);
  assert.match(monitor,/href="#live-scientific-review-ledger"/);
  assert.match(scientific,/<div id="live-scientific-review-ledger">/);
  assert.match(scientific,/setLastCheckedAt\(new Date\(\)\.toISOString\(\)\)/);
  assert.match(scientific,/setError\(""\)/);
  assert.match(scientific,/cached results are withheld until a successful refresh/);
  assert.match(scientific,/\{review && catalog && !error \? <div id=/);
});
test("stale method detail responses are checked against latest poll, not old render",()=>{
  assert.match(scientific,/const current = lastSnapshotRef\.current/);
  assert.match(scientific,/data\.review\?\.phaseEventId !== current\.phaseEventId/);
  assert.match(scientific,/data\.review\?\.historicalReviewEvents !== current\.historicalReviewEvents/);
  assert.match(scientific,/setDetails\(\{\}\); setErrors\(\{\}\); setShowAllScores\(false\)/);
});
test("the monitor is the single headline and installed before research snapshot and method ledger",()=>{
  const live=scientific.indexOf("<LivePredictionMonitor nct={nct}");
  const research=scientific.indexOf("<PilotPredictionWorkup nct={nct}");
  const installation=scientific.indexOf("<ScientificInstallationStatus />");
  assert.ok(live>0 && research>live && installation>research);
  assert.doesNotMatch(snapshot,/FINAL FDA PREDICTION/);
  assert.match(snapshot,/Historical evidence snapshot/);
});
