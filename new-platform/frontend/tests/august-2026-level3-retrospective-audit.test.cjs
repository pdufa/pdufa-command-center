const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const ts=require("typescript");
const React=require("react");
const {renderToStaticMarkup}=require("react-dom/server");
require.extensions[".tsx"]=(module,filename)=>module._compile(
  ts.transpileModule(fs.readFileSync(filename,"utf8"),{
    compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,
      jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}
  }).outputText,filename
);
const data=require("../data/august2026Level3HistoricalResearch.json");
const Panel=require("../app/August2026HistoricalAuditPanel.tsx").default;

test("August historical audit preserves twelve source-backed predecision-dated Level 3 research calls",()=>{
  assert.equal(data.rows.length,12);
  const seen=new Set();
  for(const x of data.rows){
    assert.equal(seen.has(x.id),false,"duplicate action");
    seen.add(x.id);
    assert.match(x.date,/^2026-08-/);
    assert.equal(x.datedPublicEvidence.sourceDate<x.date,true);
    assert.ok(x.datedPublicEvidence.url.startsWith("https://"));
    assert.ok(x.datedPublicEvidence.clinical);
    assert.ok(x.datedPublicEvidence.benefitRisk);
    assert.ok(x.datedPublicEvidence.regulatory);
    assert.ok(x.datedPublicEvidence.unresolved);
    assert.equal(x.actualFdaDisposition,"APPROVAL");
    assert.equal(x.outcomeKnownToResearcher,true);
    assert.equal(x.evidenceFrozenBeforeResearch,false);
    assert.equal(x.independentPublicationClockVerified,false);
    assert.equal(x.formalScientificGrade,null);
    assert.equal(x.retrospectiveDirectionMatch,x.level3ResearchCall==="APPROVAL");
  }
  assert.equal(data.summary.sourceListedApprovals,12);
  assert.equal(data.summary.level3ResearchReviews,12);
  assert.equal(data.summary.retrospectiveMatches,11);
  assert.equal(data.summary.retrospectiveMisses,1);
  assert.equal(data.summary.alwaysApproveBaseline,12);
  assert.equal(data.summary.validBlindForecasts,0);
  assert.equal(data.summary.validatedAccuracy,null);
  assert.equal(data.warnings.sampleSelectionLeakage,true);
  const missed=data.rows.filter(x=>x.retrospectiveDirectionMatch===false);
  assert.equal(missed.length,1);
  assert.equal(missed[0].ticker,"REPL");
});
test("August isolated chart shows research-only 91.7%, eleven/twelve matches and always-approval baseline",()=>{
  const html=renderToStaticMarkup(React.createElement(Panel));
  assert.match(html,/data-testid="august-2026-historical-audit"/);
  assert.match(html,/data-testid="august-2026-historical-chart"/);
  assert.match(html,/data-testid="august-2026-historical-table"/);
  assert.match(html,/91\.7%/);
  assert.match(html,/11 matched/);
  assert.match(html,/12\/12 = 100%/);
  assert.match(html,/NOT VALIDATED/);
  assert.match(html,/TUDRIQEV/);
  assert.match(html,/MIMRYLO/);
});
