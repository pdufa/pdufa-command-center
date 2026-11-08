"use strict";
const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const read=name=>fs.readFileSync(path.join(__dirname,"../app",name),"utf8");

test("production home only surfaces the POOL and FOCUS trial lists",()=>{
 const home=read("page.tsx");
 const nav=read("GlobalNavigation.tsx");
 assert.match(home,/href:"\/pool"/);
 assert.match(home,/href:"\/focus"/);
 assert.match(home,/\/api\/auth/);
 assert.match(nav,/label:"POOL",href:"\/pool"/);
 assert.match(nav,/label:"FOCUS",href:"\/focus"/);
 assert.match(nav,/label:"TOOLS",href:"\/tools"/);
 assert.doesNotMatch(nav,/label:"(?:PIPELINE|SCAN|RESULTS|GOAL|GEM|TOP|BOTTOM|PREDICTIONS)"/);
 assert.doesNotMatch(home,/streamlit\.app|GemQualificationChecklist|href:"\/raas-/);
});

test("both active trial populations and their POOL controls have native routes",()=>{
 for(const file of ["pool/page.tsx","focus/page.tsx","tools/page.tsx",
    "api/scope-funnel/route.ts","api/auth/route.ts"]){
  assert.ok(read(file).length>0,file);
 }
 const pool=read("pool/page.tsx"),tools=read("tools/page.tsx");
 assert.match(pool,/FunnelWorkspace section="pool"/);
 assert.match(tools,/PoolStageExplorer/);
 assert.doesNotMatch(tools,/Phase3SourceOnlySheets|Phase3ReadoutSheets/);
});

test("FOCUS has verified candidate snapshot data and evidence",()=>{
 const sheet=JSON.parse(fs.readFileSync(path.join(__dirname,"../data/p3PostDataActive.json"),"utf8"));
 const page=read("focus/page.tsx");
 assert.equal(sheet.schemaVersion,1);
 assert.ok(sheet.records.length>0);
 assert.equal(new Set(sheet.records.map(r=>r.nct)).size,sheet.records.length);
 assert.ok(sheet.records.every(r=>r.marketCap>=300e6&&r.marketCap<=10e9&&
  /^https:\/\//.test(r.resultsUrl)&&/^https:\/\//.test(r.regulatoryUrl)));
 assert.match(page,/import snapshot from/);
});
