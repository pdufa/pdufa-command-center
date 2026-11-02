"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const ts=require("typescript");
const root=path.resolve(__dirname,"..");
const source=fs.readFileSync(path.join(root,"app/PoolStageExplorer.tsx"),"utf8");
const styles=fs.readFileSync(path.join(root,"app/FunnelWorkspace.module.css"),"utf8");
const page=fs.readFileSync(path.join(root,"app/tools/page.tsx"),"utf8");
test("POOL five segments have independent native disclosures and start closed",()=>{
 const keys=[...source.matchAll(/data-pool-segment="([^"]+)"/g)].map(x=>x[1]);
 assert.deepEqual(keys,["funnel","selectors","assessments","live-trials","advanced"]);
 assert.equal((source.match(/className=\{styles\.poolSegment\}/g)||[]).length,5);
 assert.equal((source.match(/className=\{styles\.poolSegmentSummary\}/g)||[]).length,5);
 assert.doesNotMatch(source,/<details[^>]*\sopen(?:\s|=|>)/);
 assert.match(page,/<details data-tools-segment="pool"/);
 assert.ok(styles.includes(".poolSegmentSummary{"));
 assert.ok(styles.includes(".poolSegment[open]>.poolSegmentSummary"));
});
test("POOL sections stay visible without selections; research inputs remain gated",()=>{
 assert.doesNotMatch(source,/\{hasSelections&&<>\s*<details/);
 assert.match(source,/hasSelections\?<ToolsAssessmentSection/);
 assert.match(source,/hasSelections\?<div className=\{styles\.toolsFinalSpreadsheet\}/);
 assert.match(source,/hasSelections&&<ToolsResultsSpreadsheet/);
 assert.match(source,/Select a Phase or FDA designation in section 2/);
});
test("POOL disclosure changes do not clear saved Phase/FDA selections or search",()=>{
 assert.match(source,/setSelectedStages\(saved\.selectedStages\)/);
 assert.match(source,/setSelectedDesignations\(saved\.selectedDesignations\)/);
 assert.match(source,/setQuery\(saved\.query\)/);
 assert.match(source,/setActiveFilter\(null\)/);
 assert.match(source,/clearAllToolsSelections/);
 assert.match(source,/downloadUrl=\{downloadUrl\}/);
});
test("POOL JSX and CSS parse without TypeScript syntax errors",()=>{
 const file=ts.createSourceFile("PoolStageExplorer.tsx",source,
  ts.ScriptTarget.Latest,true,ts.ScriptKind.TSX);
 const errors=file.parseDiagnostics;
 assert.deepEqual(errors.map(e=>ts.flattenDiagnosticMessageText(e.messageText,"; ")),[]);
});
