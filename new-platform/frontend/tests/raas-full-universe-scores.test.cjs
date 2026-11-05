"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,
  compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,esModuleInterop:true}}
).outputText,file);
const {parsePhase3CensusCsv}=require("../lib/phase3-census-rows.ts");
const {classifyPhase3Readouts}=require("../lib/phase3-public-readout.ts");
const {parseRaasScreenedPhase3Csv,RAAS_RESTRICTED_PHASE3_CSV_QUERY}=
 require("../lib/raas-full-universe-roster.ts");
const {provisionalScoresForTrial}=require("../lib/raas-provisional-trial-scores.ts");
const real=classifyPhase3Readouts(
 JSON.parse(read("public/phase3-public-readout-evidence-2026-11-01.json")),
 parsePhase3CensusCsv(read("public/phase3-census-2026-10-26.csv")).rows
);
const all=[...real.pre,...real.post,...real.unverified];
test("all 741 research-census NCTs evaluated; five pilots are not the universe",()=>{
 assert.equal(real.total,741);
 assert.equal(new Set(all.map(x=>x.nctId)).size,741);
 assert.equal(real.pre.length,2);assert.equal(real.post.length,3);
 assert.equal(real.unverified.length,736);
 const graded=all.map(row=>{
  const stage=row.evidence?.kind==="PRE_AS_OF_CHECK"?"pre":
   row.evidence?.kind==="POST_PUBLIC_READOUT"?"post":null;
  return stage?{
   nctId:row.nctId,trial:row.ticker,
   metricGrades:provisionalScoresForTrial({
    nctId:row.nctId,ticker:row.ticker,
    drug:row.evidence?.drug,indication:row.evidence?.indication
   },stage).scoredMetrics}:null;
 }).filter(Boolean);
 assert.equal(graded.length,5);
 assert.deepEqual(graded.filter(x=>x.metricGrades.length).map(x=>[x.trial,x.nctId,x.metricGrades[0].score]),[
  ["LBRX","NCT07363577",50],["TRVI","NCT07671911",50],
  ["CLDX","NCT06445023",75],["CLDX","NCT06455202",75]
 ]);
 assert.ok(all.every(row=>row.nctId.startsWith("NCT")));
});
const headings=["NCT ID","Ticker","Company","Drug / therapy","Disease / indication",
 "Recorded development stage","Source snapshot as of",
 ...Array.from({length:13},(_,i)=>"Other "+i)];
const quoted=s=>'"'+s.replace(/"/g,'""')+'"';
const csv=(records)=>"\uFEFF"+[headings,...records].map(row=>row.map(quoted).join(",")).join("\r\n")+"\r\n";
const record=(nct,stage="Phase 3",ticker="LBRX")=>[
 nct,ticker,'Issuer, Inc.','Drug "ABC"','Illness',stage,"2026-11-04T05:10:00.000Z",...Array(13).fill("")
];
test("cap-screened source parser accepts full unpaginated CSV and keeps verified stage only",()=>{
 assert.match(RAAS_RESTRICTED_PHASE3_CSV_QUERY,/format=csv/);
 assert.match(decodeURIComponent(RAAS_RESTRICTED_PHASE3_CSV_QUERY),/Phase 3,Phase 3 Results/);
 const out=parseRaasScreenedPhase3Csv(csv([
  record("NCT07363577"),record("NCT12345678","Phase 3 Results","TEST")
 ]),real);
 assert.equal(out.rows.length,2);
 assert.equal(out.rows[0].nctId,"NCT07363577");
 assert.equal(out.rows[0].evidence?.kind,"PRE_AS_OF_CHECK");
 assert.equal(out.rows[1].evidence,null); // Registry "Results" is NOT verified public readout
 assert.equal(out.rows[1].fdaPdufaVerification,false);
 assert.equal(out.sourceAsOf,"2026-11-04T05:10:00.000Z");
});
test("wrong issuer, duplicate ID, invalid stage, stale schema, non-NCT are rejected",()=>{
 const badIssuer=parseRaasScreenedPhase3Csv(csv([record("NCT07363577","Phase 3","FAKE")]),real);
 assert.equal(badIssuer.rows[0].evidence,null);
 for(const rows of [
  [record("NCT12345678"),record("NCT12345678")],
  [record("NCT12345678","Phase 2")],
  [record("INVALID_ID")],
  [record("NCT12345678"),record("NCT12345679").map((v,i)=>i===6?"2025-01-01":v)]
 ])assert.throws(()=>parseRaasScreenedPhase3Csv(csv(rows),real),/INVALID|SHAPE/);
 assert.throws(()=>parseRaasScreenedPhase3Csv("NCT ID,Ticker\nA,B",real),/INVALID/);
 assert.throws(()=>parseRaasScreenedPhase3Csv(csv([]),real),/EMPTY/);
});
test("full trial UI does not hardcode the five pilot identities or round off missing scores",()=>{
 const page=read("app/raas-scan/page.tsx");
 const ui=read("app/RaasFullUniverseScores.tsx");
 const helper=read("lib/raas-full-universe-roster.ts");
 assert.match(page,/<RaasFullUniverseScores\/>/);
 assert.doesNotMatch(page,/provisionalTrials|data-raas-provisional-trial-scores="pilot"/);
 assert.match(ui,/data-raas-all-trials="true"/);
 assert.match(ui,/stageResearchReviewsForUnverifiedTrial/);
 assert.match(ui,/data-raas-reviewed-partial-nct/);
 assert.match(ui,/a reviewed-only mean is not a complete RAAS score/i);
 assert.match(ui,/RaasTrialHistoryButton row=\{x\.row\} bucket=\{x\.stage\}/);
 assert.match(ui,/Not scored/);
 assert.match(ui,/No missing input scored as zero/);
 assert.match(ui,/setLiveState\("unavailable"\)/);
 assert.match(ui,/PAGE_SIZE=50/);
 assert.match(ui,/raasSpreadsheetSummary/);
 assert.match(helper,/pipelineQualification:null/);
 for(const [source,name] of [[ui,"RaasFullUniverseScores.tsx"],[page,"raas-scan/page.tsx"],[helper,"raas-full-universe-roster.ts"]]){
  const out=ts.transpileModule(source,{fileName:name,reportDiagnostics:true,
   compilerOptions:{jsx:ts.JsxEmit.ReactJSX,module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}});
  assert.deepEqual((out.diagnostics||[]).filter(d=>d.category===ts.DiagnosticCategory.Error).map(d=>d.code),[]);
 }
});
