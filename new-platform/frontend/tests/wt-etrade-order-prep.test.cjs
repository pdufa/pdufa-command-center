"use strict";
const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const ts=require("typescript");
require.extensions[".ts"]=(mod,filename)=>{
  const compiled=ts.transpileModule(fs.readFileSync(filename,"utf8"),{
    compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,esModuleInterop:true}
  }).outputText;
  mod._compile(compiled,filename);
};

const {WT_ETRADE_CANDIDATES,daysUntilPdufa,prepareWtEtradeDraft,formatWtEtradeDraft}
  =require("../lib/wt-etrade-order-draft.ts");
const now=Date.parse("2026-11-11T16:00:00.000Z");
const candidate=WT_ETRADE_CANDIDATES[0];
const focus=(date="2027-01-14")=>({ticker:candidate.ticker,nct:candidate.nct,recordedPdufaDate:date});
const green=()=>({
  provider:"ALPACA",ticker:candidate.ticker,programId:candidate.programId,
  model:"BASE_BREAKOUT_V1_UNVALIDATED",status:"BUY",green:true,
  orderExecutionEnabled:false,
  calculatedAt:new Date(now-1000).toISOString(),entryOpen:"2026-11-11T14:30:00Z",
  entryClose:"2026-11-11T21:00:00Z",entryTrigger:5.10,maximumEntry:5.35,
  checks:[{pass:true},{pass:true}],quote:{bid:5.15,ask:5.16,
    feed:"IEX",asOf:new Date(now-2000).toISOString()}
});

test("SVRA and CAPR are exact current-Focus NCTs with permanent distinct programs",()=>{
  const json=JSON.parse(fs.readFileSync(path.join(__dirname,"../data/p3PostDataActive.json"),"utf8"));
  assert.equal(WT_ETRADE_CANDIDATES.length,2);
  for(const candidate of WT_ETRADE_CANDIDATES){
    const row=json.records.find(x=>x.nct===candidate.nct);
    assert.equal(row.ticker,candidate.ticker);
    assert.match(candidate.programId,/^PDUFA-\d{6,}$/);
    assert.equal(row.recordedPdufaDate,"2026-11-22");
  }
  assert.equal(new Set(WT_ETRADE_CANDIDATES.map(x=>x.programId)).size,2);
});
test("both actual FOCUS candidates are blocked by the 14-day PDUFA entry policy",()=>{
  for(const item of WT_ETRADE_CANDIDATES){
    const draft=prepareWtEtradeDraft(item,
      {ticker:item.ticker,nct:item.nct,recordedPdufaDate:"2026-11-22"},
      {...green(),ticker:item.ticker,programId:item.programId},now);
    assert.equal(draft.status,"PDUFA_EXIT_WINDOW");
    assert.equal(draft.limitPrice,null);
    assert.equal(draft.quantity,1);
    assert.equal(draft.isSubmitted,false);
    assert.equal(draft.isApproved,false);
  }
  assert.equal(daysUntilPdufa("2026-11-22",now),11);
});
test("a qualifying future-program signal gives a research-only limit, never a broker preview",()=>{
  const d=prepareWtEtradeDraft(candidate,focus(),green(),now);
  assert.equal(d.status,"PRICE_SUGGESTED_REVIEW_ONLY");
  assert.equal(d.limitPrice,5.16);
  assert.equal(d.action,"BUY");
  assert.equal(d.quantity,1);
  assert.equal(d.priceType,"LIMIT");
  assert.equal(d.orderTerm,"GOOD_FOR_DAY");
  assert.equal(d.isApproved,false);
  assert.equal(d.isBrokerPreview,false);
  assert.equal(d.isSubmitted,false);
  const summary=formatWtEtradeDraft(d,"2027-01-14");
  assert.match(summary,/NOT AN E\*TRADE ORDER/);
  assert.match(summary,/Order submission: DISABLED/);
  assert.match(summary,/User approval: NOT GIVEN/);
});
test("wrong program, ticker, provider, model, or execution contract never yields a limit",()=>{
  for(const mutated of [
    {programId:"PDUFA-000999"},
    {ticker:"CAPR"},{provider:"YAHOO"},{model:"UNKNOWN"},
    {orderExecutionEnabled:true},{orderExecutionEnabled:undefined},
  ]){
    const d=prepareWtEtradeDraft(candidate,focus(),{...green(),...mutated},now);
    assert.equal(d.limitPrice,null);
    assert.equal(d.status,"NO_FRESH_ENTRY");
  }
});
test("stale quote, incomplete checks, stale signal, missing green, or closed market blocks",()=>{
  for(const mutated of [
    {calculatedAt:new Date(now-65000).toISOString()},
    {quote:{...green().quote,asOf:new Date(now-65000).toISOString()}},
    {checks:[{pass:true},{pass:false}]},{checks:[]},
    {status:"WAIT"},{green:false},
    {entryClose:"2026-11-11T15:00:00Z"},
    {quote:{...green().quote,feed:"UNKNOWN"}},
    {quote:{...green().quote,bid:5.40}},
    {quote:{...green().quote,ask:5.40}},
    {quote:{...green().quote,ask:5.161}},
  ]){
    const d=prepareWtEtradeDraft(candidate,focus(),{...green(),...mutated},now);
    assert.equal(d.limitPrice,null,JSON.stringify(mutated));
  }
});
test("unknown date, passed decision, or cross-trial identity cannot generate a price",()=>{
  const cases=[
    {row:focus(null),status:"SOURCE_NOT_VERIFIED"},
    {row:focus("2026-11-10"),status:"PDUFA_DATE_PASSED"},
    {row:{...focus(),nct:"NCT00000000"},status:"SOURCE_NOT_VERIFIED"},
    {row:focus("2026-02-30"),status:"SOURCE_NOT_VERIFIED"},
  ];
  for(const x of cases){
    const d=prepareWtEtradeDraft(candidate,x.row,green(),now);
    assert.equal(d.status,x.status);assert.equal(d.limitPrice,null);
  }
});
test("WT order-prep UI has no E*TRADE order route or automatic approval",()=>{
  const src=fs.readFileSync(path.join(__dirname,"../app/WtEtradeOrderPrep.tsx"),"utf8");
  const route=fs.readFileSync(path.join(__dirname,"../app/wt/page.tsx"),"utf8");
  assert.match(route,/WtEtradeOrderPrep/);
  assert.match(src,/data-wt-etrade-prep="read-only"/);
  assert.match(src,/One|whole share|one whole share/i);
  assert.doesNotMatch(src,/\/orders\/(?:place|preview)/);
  assert.doesNotMatch(src,/fetch\([^\)]*,\s*\{\s*method:\s*["']POST/);
  assert.doesNotMatch(src,/oauth_token|oauth_consumer_secret|ALPACA_SECRET_KEY/);
  assert.match(src,/No order can be placed or approved through this page/);
});
