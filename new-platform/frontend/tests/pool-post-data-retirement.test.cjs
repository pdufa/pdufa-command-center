"use strict";
const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const root=path.join(__dirname,"..");
const source=p=>fs.readFileSync(path.join(root,p),"utf8");

test("active site navigation lists only POOL, P3 POST-DATA and POOL tools",()=>{
 const nav=source("app/GlobalNavigation.tsx");
 const home=source("app/page.tsx");
 const tools=source("app/tools/page.tsx");
 const links=[...nav.matchAll(/\{label:"([^"]+)",href:"([^"]+)"\}/g)].map(m=>[m[1],m[2]]);
 assert.deepEqual(links,[["POOL","/pool"],["P3 POST-DATA","/p3-post-data"],["TOOLS","/tools"]]);
 assert.match(home,/href:"\/pool"/);
 assert.match(home,/href:"\/p3-post-data"/);
 assert.match(home,/\/api\/auth/);
 assert.doesNotMatch(home,/href:"\/(?:raas-762|raas-top-bottom|scans|pipeline|gem)/);
 assert.match(tools,/PoolStageExplorer/);
 assert.match(tools,/href="\/p3-post-data"/);
});

test("P3 POST-DATA static screenshot snapshot has 25 unique in-range NCT records with source links",()=>{
 const page=source("app/p3-post-data/page.tsx");
 const snapshot=JSON.parse(source("data/p3PostDataActive.json"));
 assert.equal(snapshot.schemaVersion,1);
 const records=snapshot.records;
 assert.match(page,/import snapshot from/);
 assert.equal(records.length,25);
 assert.equal(new Set(records.map(t=>t.nct)).size,25);
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
