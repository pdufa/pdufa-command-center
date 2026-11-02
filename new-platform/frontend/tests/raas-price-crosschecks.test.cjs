"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
require.extensions[".ts"]=(m,file)=>m._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,compilerOptions:{
 module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,file);
const moduleUnderTest=require("../lib/raas-price-crosschecks.ts");
const pre=require("../lib/raas-top-retrospective-intake.ts").parseTopRetrospective(
 require("../data/raas-retrospective-top-cases.json"));
const post=require("../lib/raas-retrospective-intake.ts").parseRetrospectiveFeed(
 require("../data/raas-retrospective-source-cases.json"));
const raw=require("../data/raas-price-crosschecks.json");
test("four exact-date closes agree across separate display vendors; only one complete trade window",()=>{
 const feed=moduleUnderTest.parsePriceCrosschecks(raw,pre,post);
 const s=moduleUnderTest.priceAuditSummary(feed,pre,post);
 assert.equal(s.caseCount,8);
 assert.equal(s.quotedPoints,16);
 assert.equal(s.secondaryPointsRecorded,4);
 assert.equal(s.matchedPoints,4);
 assert.equal(s.mismatchedPoints,0);
 assert.equal(s.bothClosesMatchedCases,1);
 assert.equal(s.adjustedTotalReturnsVerified,0);
 assert.equal(s.qualifiedHistoricalPredictions,0);
 const vrna=moduleUnderTest.priceAuditForCase(feed,pre,post,"vrna-ensifentrine-copd-2024-illustrative");
 assert.equal(vrna.entry.originalClose,14.85);
 assert.equal(vrna.exit.secondaryClose,15);
 assert.equal(vrna.entry.status,"PROVIDER_PRICE_MATCH");
 assert.equal(vrna.exit.status,"PROVIDER_PRICE_MATCH");
 assert.equal(vrna.bothClosesAgree,true);
 assert.equal(vrna.vendorPricesIndependentlyAudited,false);
 assert.equal(vrna.eligibleForValidatedRAAS,false);
 const urgn=moduleUnderTest.priceAuditForCase(feed,pre,post,"urgn-ugn102-nmibc-2025-illustrative");
 assert.equal(urgn.entry.status,"SECOND_SOURCE_MISSING");
 assert.equal(urgn.exit.status,"PROVIDER_PRICE_MATCH");
 assert.equal(urgn.bothClosesAgree,false);
 const mdgl=moduleUnderTest.priceAuditForCase(feed,pre,post,"mdgl-resmetirom-maestro-nash-pre2022-illustrative");
 assert.equal(mdgl.entry.status,"SECOND_SOURCE_MISSING");
 assert.equal(mdgl.exit.secondaryClose,63.8);
});
test("wrong date, unknown case, missing original independence, invalid quote reject",()=>{
 const mutate=(change)=>({...raw,observations:raw.observations.map((v,i)=>i===0?{...v,...change}:v)});
 assert.throws(()=>moduleUnderTest.parsePriceCrosschecks(mutate({caseId:"not-a-real-case"}),pre,post),/OBSERVATION_INVALID/);
 assert.throws(()=>moduleUnderTest.parsePriceCrosschecks(mutate({date:"2024-05-09"}),pre,post),/NOT_INDEPENDENT_DATE_OR_SOURCE/);
 assert.throws(()=>moduleUnderTest.parsePriceCrosschecks(mutate({secondaryClose:-12}),pre,post),/OBSERVATION_INVALID/);
 const first=pre.records[0];
 const source=post.records.find(x=>x.id===raw.observations[0].caseId).entry.sourceUrl;
 assert.throws(()=>moduleUnderTest.parsePriceCrosschecks(mutate({sourceUrl:source}),pre,post),/NOT_INDEPENDENT_DATE_OR_SOURCE/);
 assert.ok(first);
});
test("mismatches are displayed and never silently treated as audited prices",()=>{
 const broken={...raw,observations:raw.observations.map((v,i)=>i===0?{...v,secondaryClose:14.5}:v)};
 const feed=moduleUnderTest.parsePriceCrosschecks(broken,pre,post);
 const v=moduleUnderTest.priceAuditForCase(feed,pre,post,"vrna-ensifentrine-copd-2024-illustrative");
 assert.equal(v.entry.status,"PROVIDER_PRICE_MISMATCH");
 assert.equal(v.bothClosesAgree,false);
 assert.equal(v.eligibleForValidatedRAAS,false);
 assert.equal(moduleUnderTest.priceAuditSummary(feed,pre,post).mismatchedPoints,1);
});
test("a second-provider match cannot generate a validated price or fictitious RAAS score",()=>{
 const feed=moduleUnderTest.parsePriceCrosschecks(raw,pre,post);
 for(const c of [...pre.records,...post.records]){
  const state=moduleUnderTest.priceAuditForCase(feed,pre,post,c.id);
  assert.equal(state.eligibleForValidatedRAAS,false);
  assert.equal(state.vendorPricesIndependentlyAudited,false);
  assert.equal(state.adjustmentStatus,"CORPORATE_ACTION_RECONCILIATION_PENDING");
  assert.ok(state.blockingIssues.length>=3);
 }
 assert.equal(require("../data/raas-historical-cases.json").cases.length,0);
 assert.equal(require("../data/raas-approved-calibrations.json").entries.length,0);
});
test("TypeScript and audit page transpile without TS/TSX parse errors",()=>{
 for(const name of ["lib/raas-price-crosschecks.ts","app/raas-history/page.tsx"]){
  const code=fs.readFileSync(path.join(__dirname,"..",name),"utf8");
  const out=ts.transpileModule(code,{fileName:name,reportDiagnostics:true,
  compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX}});
  assert.deepEqual((out.diagnostics||[]).filter(x=>x.category===ts.DiagnosticCategory.Error)
   .map(x=>ts.flattenDiagnosticMessageText(x.messageText," ")),[],name);
 }
});
