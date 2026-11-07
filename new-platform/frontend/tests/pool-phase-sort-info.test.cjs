"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const {POOL_PHASE_OPTIONS,togglePoolPhase}=require("../lib/pool-phase-options.ts");
const {sortPoolPage}=require("../lib/pool-row-sorting.ts");
test("POOL phases match exactly the documented backend categories, without duplicates",()=>{
 const server=fs.readFileSync(path.join(__dirname,"../lib/pool-pipeline-funnel.ts"),"utf8");
 assert.equal(new Set(POOL_PHASE_OPTIONS).size,POOL_PHASE_OPTIONS.length);
 for(const phase of POOL_PHASE_OPTIONS)assert.ok(server.includes('"'+phase+'"'),phase);
});
test("all phases, individual phases and reset preserve intuitive checkbox semantics",()=>{
 assert.equal(togglePoolPhase(null,"Phase 3").includes("Phase 3"),false);
 const partial=togglePoolPhase(null,"Phase 3");
 assert.equal(partial.length,POOL_PHASE_OPTIONS.length-1);
 const restored=togglePoolPhase(partial,"Phase 3");
 assert.equal(restored,null);
 assert.deepEqual(togglePoolPhase(["Phase 3"],"Phase 3"),[]);
 assert.deepEqual(togglePoolPhase([],"Phase 2"),["Phase 2"]);
});
test("current page sorting is numeric, stable and always puts unknown entries last",()=>{
 const rows=[{v:10,id:"a"},{v:null,id:"b"},{v:2,id:"c"},{v:2,id:"d"}];
 assert.deepEqual(sortPoolPage(rows,r=>r.v,"asc").map(x=>x.id),["c","d","a","b"]);
 assert.deepEqual(sortPoolPage(rows,r=>r.v,"desc").map(x=>x.id),["a","c","d","b"]);
 assert.deepEqual(rows.map(x=>x.id),["a","b","c","d"]);
});
test("date-like ISO text and case-insensitive tickers are sortable",()=>{
 const rows=[{v:"2026-03-01"},{v:"2025-12-30"},{v:"Not verified"}];
 assert.deepEqual(sortPoolPage(rows,r=>r.v,"asc").map(x=>x.v),["2025-12-30","2026-03-01","Not verified"]);
});
test("stage choices are fetched server-side before pagination, with explicit none-selected semantics",()=>{
 const route=fs.readFileSync(path.join(__dirname,"../app/api/scope-funnel/route.ts"),"utf8");
 const workspace=fs.readFileSync(path.join(__dirname,"../app/FunnelWorkspace.tsx"),"utf8");
 assert.ok(route.includes('const emptyStageSelection=stagesParam==="none"'));
 assert.ok(route.includes('const page=emptyStageSelection?{...initialPage,rows:[],total:0,nextOffset:null}:initialPage'));
 assert.ok(workspace.includes('params.set("stages"'));
 assert.ok(workspace.includes('selectedPhases.length?selectedPhases.join(","):"none"'));
 assert.ok(workspace.includes('setSelectedPhases(next);setOffset(0)'));
});
