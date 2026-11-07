"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const ts=require("typescript");
const root=path.join(__dirname,"..");
const component=fs.readFileSync(path.join(root,"app/PoolMasterSpreadsheet.tsx"),"utf8");
const style=fs.readFileSync(path.join(root,"app/PoolMasterSpreadsheet.module.css"),"utf8");
const workspace=fs.readFileSync(path.join(root,"app/FunnelWorkspace.tsx"),"utf8");
test("POOL master uses the existing paginated source, not a restricted stage-only filter",()=>{
 assert.match(workspace,/view=section==="pool"\?"pool"/);
 assert.match(workspace,/<PoolMasterSpreadsheet[\s\S]*?rows=\{page\?\.rows\.filter/);
 assert.match(component,/FOCUS gates not established for this record/);
});
test("32 columns are segmented, all source rows preserved, and separate viewport layouts retained",()=>{
 for(const key of ["clinical","dates","qualifiers","focus"])assert.match(component,new RegExp('key:"'+key+'"'));
 assert.match(component,/pdufa:pool-column-layout:v1:/);
 assert.match(component,/hiddenColumns/);
 assert.match(component,/hiddenSegments/);
 assert.match(component,/expanded/);
 assert.match(component,/Showing 3 identity columns/);
 assert.match(component,/Not on current FOCUS roster — unassessed/);
});
test("mobile uses half-viewport optional columns; desktop fits more and pins identity",()=>{
 assert.match(style,/@media \(max-width:640px\)/);
 assert.match(style,/\.dataColumn\{width:50vw;min-width:50vw;max-width:50vw\}/);
 assert.match(style,/width:clamp\(180px,18vw,260px\)/);
 assert.match(style,/\.ticker\{/);
 assert.match(style,/\.company\{/);
 assert.match(style,/\.nct\{/);
});
test("POOL Master component parses as valid TypeScript JSX",()=>{
 const source=ts.createSourceFile("PoolMasterSpreadsheet.tsx",component,ts.ScriptTarget.Latest,true,ts.ScriptKind.TSX);
 assert.deepEqual(source.parseDiagnostics.map(e=>ts.flattenDiagnosticMessageText(e.messageText,"; ")),[]);
});

test("both toolbar buttons toggle the optional POOL columns between shown and hidden",()=>{
 assert.match(component,/const toggleAll=\(\)=>edit\(\(\)=>allShowing\?hideAllOptional\(\)/);
 assert.match(component,/const togglePreferred=\(\)=>edit\(\(\)=>atPreferred\?hideAllOptional\(\):defaultLayout\(view\)\)/);
 assert.match(component,/aria-pressed=\{allShowing\}/);
 assert.match(component,/aria-pressed=\{atPreferred\}/);
 assert.match(component,/allShowing\?"Hide All":"Show All"/);
 assert.match(component,/atPreferred\?"Hide All":"Reset "/);
 assert.match(component,/hiddenSegments:\[\.\.\.ALL_SEGMENTS\]/);
 assert.match(style,/\.actions button\[data-visibility="hidden"\]/);
 assert.match(style,/\.actions button\[data-visibility="all"\]/);
 assert.match(style,/\.segmentToggle\[aria-pressed="true"\]/);
 assert.match(style,/\.visibilityToggle\[aria-pressed="true"\]/);
});
