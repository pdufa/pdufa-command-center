"use strict";
const fs=require("node:fs"),path=require("node:path"),test=require("node:test"),
 assert=require("node:assert/strict"),ts=require("typescript");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,
 compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,
 esModuleInterop:true,jsx:ts.JsxEmit.ReactJSX}}).outputText,file);
const {raasFull903CalendarPairs,raasFull903Overview}=
 require("../lib/raas-full-90-3-window-policy.ts");
test("All possible ordered T-90..T-3 calendar pairs are allowed, no 79/14 default",()=>{
 const p=raasFull903CalendarPairs(),o=raasFull903Overview();
 assert.equal(p.length,3828);
 assert.deepEqual(p[0],{entryLeadCalendarDays:90,exitLeadCalendarDays:3});
 assert.deepEqual(p.at(-1),{entryLeadCalendarDays:4,exitLeadCalendarDays:3});
 assert.equal(new Set(p.map(x=>x.entryLeadCalendarDays+"|"+x.exitLeadCalendarDays)).size,3828);
 assert.ok(p.some(x=>x.entryLeadCalendarDays===79&&x.exitLeadCalendarDays===14));
 assert.equal(o.explicitBenchmarkWindow,null);
 assert.equal(o.approvedOptimalWindow,null);
 assert.equal(o.scenarioEvaluations,42108);
 assert.equal(o.independentlyVerifiedTrades,0);
});
test("Mobile RAAS page visibly promotes full search range above the old 79/14 research example",()=>{
 const file=fs.readFileSync(path.join(__dirname,"../app/raas-worklist/page.tsx"),"utf8");
 assert.match(file,/FullRange903History/);
 assert.match(file,/raas-full-t90-t3-study/);
 assert.ok(file.indexOf("<FullRange903History/>")<file.indexOf("<GoalAsOfHistory/>"));
 assert.match(file,/T−90 to T−3/);
 assert.match(file,/None — historical evidence not yet independently validated/);
 const compiled=ts.transpileModule(file,{fileName:"page.tsx",reportDiagnostics:true,
  compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX}});
 assert.deepEqual((compiled.diagnostics||[]).filter(x=>x.category===ts.DiagnosticCategory.Error)
 .map(x=>ts.flattenDiagnosticMessageText(x.messageText," ")),[]);
});
