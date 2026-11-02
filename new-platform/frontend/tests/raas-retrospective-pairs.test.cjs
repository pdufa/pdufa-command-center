"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs"),ts=require("typescript"),path=require("node:path");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(fs.readFileSync(file,"utf8"),{
 fileName:file,compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}
}).outputText,file);
const top=require("../lib/raas-top-retrospective-intake.ts");
const post=require("../lib/raas-retrospective-intake.ts");
const joined=require("../lib/raas-retrospective-pairs.ts");
const topFeed=top.parseTopRetrospective(require("../data/raas-retrospective-top-cases.json"));
const postFeed=post.parseRetrospectiveFeed(require("../data/raas-retrospective-source-cases.json"));
test("three historically paired issuer+drug+NCT groups retain independent TOP and BOTTOM returns",()=>{
 const pairs=joined.pairRetrospectivePrograms(topFeed,top.topRetrospectiveResults(topFeed),
  postFeed,post.retrospectiveResults(postFeed));
 assert.equal(pairs.length,3);
 const byTicker=Object.fromEntries(pairs.map(p=>[p.ticker,p]));
 assert.equal(byTicker.BBIO.pre.grossPercent,24.74);
 assert.equal(byTicker.BBIO.post.grossPercent,-18.49);
 assert.equal(byTicker.MDGL.pre.grossPercent,-12.36);
 assert.equal(byTicker.MDGL.post.grossPercent,73.82);
 assert.equal(byTicker.GERN.pre.grossPercent,7.08);
 assert.equal(byTicker.GERN.post.grossPercent,-9.67);
 assert.ok(pairs.every(p=>p.combinedReturn===null&&p.status==="RETROSPECTIVE_RESEARCH_ONLY"));
 assert.ok(pairs.every(p=>p.pre.exitDate<p.post.entryDate));
});
test("another NCT of same ticker does not produce a false same-drug opportunity match",()=>{
 const copied=JSON.parse(JSON.stringify(postFeed));
 const bbio=copied.records.find(r=>r.ticker==="BBIO");
 bbio.nctIds=["NCT00000009"];
 const pairs=joined.pairRetrospectivePrograms(topFeed,top.topRetrospectiveResults(topFeed),
  copied,post.retrospectiveResults(copied));
 assert.equal(pairs.length,2);
 assert.ok(!pairs.some(p=>p.ticker==="BBIO"));
});
test("different therapy from same issuer cannot be paired by ticker alone",()=>{
 const copied=JSON.parse(JSON.stringify(postFeed));
 copied.records.find(r=>r.ticker==="BBIO").drug="other therapy";
 const pairs=joined.pairRetrospectivePrograms(topFeed,top.topRetrospectiveResults(topFeed),
  copied,post.retrospectiveResults(copied));
 assert.equal(pairs.length,2);
});
test("retrospective comparison code and UI parse without diagnostics",()=>{
 for(const f of ["lib/raas-retrospective-pairs.ts","app/TrialRaasDisclosure.tsx"]){
  const result=ts.transpileModule(fs.readFileSync(path.join(__dirname,"..",f),"utf8"),{
   fileName:f,reportDiagnostics:true,compilerOptions:{jsx:ts.JsxEmit.ReactJSX,module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}
  });
  assert.equal((result.diagnostics||[]).filter(d=>d.category===ts.DiagnosticCategory.Error).length,0,f);
 }
});
