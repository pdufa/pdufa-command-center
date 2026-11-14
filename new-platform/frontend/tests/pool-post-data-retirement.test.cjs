"use strict";
const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const root=path.join(__dirname,"..");
const source=p=>fs.readFileSync(path.join(root,p),"utf8");

test("active site navigation preserves POOL and FOCUS populations with prediction status",()=>{
 const nav=source("app/GlobalNavigation.tsx");
 const home=source("app/page.tsx");
 const tools=source("app/tools/page.tsx");
 const links=[...nav.matchAll(/\{label:"([^"]+)",href:"([^"]+)"\}/g)].map(m=>[m[1],m[2]]);
 assert.deepEqual(links,[["POOL","/pool"],["INDICATIONS","/indications"],["FOCUS","/focus"],["WT","/wt"],["CAL","/cal"],["COMPANY","/company"],["NEWS","/news"],["PREDICTIONS","/predictions"],["ASSESMENTS","/predictions/assessment"],["TOOLS","/tools"],["INSTALLATION","/installation-audit"]]);
 assert.match(home,/href:"\/pool"/);
 assert.match(home,/href:"\/focus"/);
 assert.match(home,/\/api\/auth/);
 assert.doesNotMatch(home,/href:"\/(?:raas-762|raas-top-bottom|scans|pipeline|gem)/);
 assert.match(tools,/PoolStageExplorer/);
 assert.match(tools,/href="\/focus"/);
});

test("FOCUS allows any positive number of unique qualified NCT records with source links",()=>{
 const page=source("app/focus/page.tsx");
 const snapshot=JSON.parse(source("data/p3PostDataActive.json"));
 assert.equal(snapshot.schemaVersion,1);
 const records=snapshot.records;
 assert.match(page,/import snapshot from/);
 assert.ok(records.length>0);
 assert.equal(new Set(records.map(t=>t.nct)).size,records.length);
 for(const t of records){
  assert.match(t.nct,/^NCT\d{8}$/);
  assert.ok(Number.isFinite(t.marketCap) && t.marketCap>=300_000_000 && t.marketCap<=10_000_000_000,t.nct);
  assert.match(t.resultsUrl,/^https:\/\//);
  assert.match(t.regulatoryUrl,/^https:\/\//);
 }
});

test("preserved POOL source API, sign-in and original NCT inventory",()=>{
 const api=source("app/api/scope-funnel/route.ts");
 const auth=source("app/api/auth/route.ts");
 const pool=source("app/pool/page.tsx");
 assert.match(api,/authConfigured\(\)/);
 assert.match(api,/reconcilePoolPipeline/);
 assert.match(api,/fetchReadOnlyWithWarmRetry/);
 assert.match(auth,/hasSession/);
 assert.match(pool,/FunnelWorkspace section="pool"/);
});

test("retired TOP, BOTTOM 23 and 762-only API routes do not exist",()=>{
 for(const route of [
  "app/api/top-only-completion/route.ts",
  "app/api/bottom-only-completion/route.ts",
  "app/api/phase3-active-cohorts/route.ts",
  "app/api/phase3-active-190-coverage/route.ts",
  "app/api/phase3-unified-190-columns/route.ts",
  "app/api/raas-762-review-queue/route.ts"
 ])assert.equal(fs.existsSync(path.join(root,route)),false,route);
});
