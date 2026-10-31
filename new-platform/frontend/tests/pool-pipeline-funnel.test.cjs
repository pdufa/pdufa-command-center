"use strict";
const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const ts=require("typescript");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}
).outputText,file);
const {parsePhase3CensusCsv}=require("../lib/phase3-census-rows.ts");
const {parsePhase3CensusSourceDirectory}=require("../lib/phase3-census-sources.ts");
const {reconcilePoolPipeline,funnelPage}=require("../lib/pool-pipeline-funnel.ts");
const publicDir=path.join(__dirname,"../public");
const csv=fs.readFileSync(path.join(publicDir,"phase3-census-2026-10-26.csv"),"utf8");
const sources=JSON.parse(fs.readFileSync(path.join(publicDir,"phase3-census-sources-2026-10-26.json"),"utf8"));
const census=parsePhase3CensusCsv(csv);
parsePhase3CensusSourceDirectory(sources,census);
function source(rows){
 return {
   asOf:"2026-10-31T07:00:00Z",pipeline:rows,
   sourceHealth:{state:"PARTIAL",clinicalRows:rows.length,regulatoryRows:0,
     pipelineSourceParity:{exactPrograms:rows.length}},
 };
}
const input=census.rows.map(t=>({id:"TRIAL|"+t.nctId,ticker:t.ticker,
 company:t.company,drug:"Unverified drug",indication:"Unverified indication"}));
test("full historical exact-ID source is reconciled conservatively",()=>{
 const result=reconcilePoolPipeline(source(input),csv,sources);
 assert.equal(result.poolRows.length,741);
 assert.equal(result.overview.poolRecords,741);
 assert.equal(result.overview.matchedPhase3Records,741);
 assert.equal(result.overview.matchedCompletedRecords,375);
 assert.equal(result.overview.noncompletedReadoutReview,366);
 assert.equal(result.overview.qualifiedPrograms,null);
 assert.equal(funnelPage(result,"pool",0,50,"").total,741);
 assert.equal(funnelPage(result,"pipeline",0,50,"").total,375);
 assert.equal(funnelPage(result,"readout-review",0,50,"").total,366);
 assert.equal(funnelPage(result,"pipeline",0,50,"").rows.length,50);
 assert.equal(funnelPage(result,"pipeline",50,50,"").nextOffset,100);
 assert.ok(result.reviewRows.every(x=>x.qualification==="NEEDS_REVIEW" && x.capUsd>=300_000_000
 && x.capUsd<=10_000_000_000 && x.reasons.length>=3));
});
test("missing, misassigned or changed issuer records never promote to Pipeline",()=>{
 const changed=input.map(x=>({...x}));
 const completed=census.rows.find(x=>x.status==="COMPLETED");
 const target=changed.find(x=>x.id==="TRIAL|"+completed.nctId);
 target.ticker="WRONG";
 const r=reconcilePoolPipeline(source(changed),csv,sources);
 assert.equal(r.overview.matchedCompletedRecords,374);
 assert.equal(r.overview.missingOrConflicted,1);
 assert.equal(funnelPage(r,"pipeline",0,50,"").total,374);
 assert.equal(funnelPage(r,"readout-review",0,50,"").total,367);
 assert.equal(r.reviewRows.find(x=>x.nctId===completed.nctId).poolStatus,"TICKER_CONFLICT");
 assert.equal(r.overview.qualifiedPrograms,null);
});
test("extra unqualified trial/record remains in POOL without being discarded",()=>{
 const plus=[...input,{id:"TRIAL|NCT99999999",ticker:"OTHER",stage:"Phase 1"}];
 const r=reconcilePoolPipeline(source(plus),csv,sources);
 assert.equal(r.poolRows.length,742);
 assert.equal(funnelPage(r,"pool",0,50,"").total,742);
 assert.equal(funnelPage(r,"pipeline",0,50,"").total,375);
});
test("fail-closed on incomplete, stale or duplicate source inventory",()=>{
 const duplicate=source([...input,input[0]]);
 assert.throws(()=>reconcilePoolPipeline(duplicate,csv,sources),/integrity|freshness/);
 const stale=source(input);stale.sourceHealth.state="STALE";
 assert.throws(()=>reconcilePoolPipeline(stale,csv,sources),/integrity|freshness/);
 const inconsistent=source(input);inconsistent.sourceHealth.pipelineSourceParity.exactPrograms=12;
 assert.throws(()=>reconcilePoolPipeline(inconsistent,csv,sources),/integrity|freshness/);
});

test("read-only legacy Render source-parity metadata is accepted without GEM gate membership",()=>{
 const legacy=source(input);
 legacy.sourceHealth.streamlitPipelineParity=legacy.sourceHealth.pipelineSourceParity;
 delete legacy.sourceHealth.pipelineSourceParity;
 const result=reconcilePoolPipeline(legacy,csv,sources);
 assert.equal(result.overview.poolRecords,741);
 assert.equal(result.overview.matchedCompletedRecords,375);
 assert.equal(result.overview.qualifiedPrograms,null);
 assert.ok(result.reviewRows.every(row=>row.qualification==="NEEDS_REVIEW"));
});
test("POOL retains unmatched original records with blank issuer tickers without promoting them",()=>{
 const unresolved={id:"TRIAL|NCT99999999",ticker:"",stage:"Unknown",company:"Unresolved issuer"};
 const rows=[...input,unresolved];
 const result=reconcilePoolPipeline(source(rows),csv,sources);
 assert.equal(result.overview.poolRecords,742);
 assert.equal(funnelPage(result,"pool",0,100,"").total,742);
 assert.equal(funnelPage(result,"pipeline",0,50,"").total,375);
 assert.equal(funnelPage(result,"pool",0,50,"Unresolved issuer").rows[0].ticker,"");
 assert.equal(result.overview.qualifiedPrograms,null);
});
test("mismatched legacy source parity still fails closed",()=>{
 const broken=source(input);
 delete broken.sourceHealth.pipelineSourceParity;
 broken.sourceHealth.streamlitPipelineParity={exactPrograms:12};
 assert.throws(()=>reconcilePoolPipeline(broken,csv,sources),/integrity|freshness/);
});
test("navigation links and API views remain independent of historical GEM presets",()=>{
 const read=p=>fs.readFileSync(path.join(__dirname,"../",p),"utf8");
 const nav=read("app/GlobalNavigation.tsx");
 const api=read("app/api/scope-funnel/route.ts");
 const ui=read("app/FunnelWorkspace.tsx");
 assert.match(nav,/label:"POOL",href:"\/pool"/);
 assert.match(nav,/label:"PIPELINE",href:"\/pipeline"/);
 assert.match(nav,/label:"#1",href:"\/patient-population"/);
 assert.match(api,/readFile\(join\(process.cwd\(\),"public","phase3-census-2026-10-26.csv"\)/);
 assert.match(api,/authConfigured\(\)/);
 assert.match(ui,/reviewMode/);
 assert.match(ui,/Not established/);
 assert.match(ui,/r\.qualification/);
 assert.match(read("lib/pool-pipeline-funnel.ts"),/qualification:"NEEDS_REVIEW"/);
});
