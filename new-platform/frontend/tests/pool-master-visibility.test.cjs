"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const root=path.join(__dirname,"..");
const workspace=fs.readFileSync(path.join(root,"app/FunnelWorkspace.tsx"),"utf8");
const grid=fs.readFileSync(path.join(root,"app/PoolMasterSpreadsheet.tsx"),"utf8");
test("POOL master controls render before source results and overview sections",()=>{
 assert.match(workspace,/section==="pool"&&<section id="pool-master"/);
 assert.ok(workspace.indexOf('id="pool-master"')<workspace.indexOf('qualification rules:'.toUpperCase())||workspace.indexOf('id="pool-master"')<workspace.indexOf('Qualification rules:'));
 assert.match(workspace,/rows=\{page\?\.rows\.filter/);
 assert.match(workspace,/loading=\{loading\} error=\{error\}/);
});
test("POOL displays unfiltered clinical trial records from all phases",()=>{
 assert.match(workspace,/recordKind:"trials"/);
 assert.match(workspace,/All recorded phases are included/);
 assert.match(workspace,/page\.nextOffset/);
});
test("POOL never shows an invisible empty table on fetch or sign-in failure",()=>{
 assert.match(grid,/sortedRows\.length===0&&<tr>/);
 assert.match(grid,/Loading clinical POOL records/);
 assert.match(grid,/No clinical records loaded/);
 assert.match(workspace,/Return to the dashboard to sign in/);
});
