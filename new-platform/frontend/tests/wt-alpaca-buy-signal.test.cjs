"use strict";
const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const ts=require("typescript");
require.extensions[".ts"]=(loaded,file)=>{
  const compiled=ts.transpileModule(fs.readFileSync(file,"utf8"),{
    compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,esModuleInterop:true},
  }).outputText;
  loaded._compile(compiled,file);
};
const {evaluateWtAlpacaTechnicalSignal}=require("../lib/wt-alpaca-buy-signal.ts");
const {WT_ETRADE_CANDIDATES,prepareWtEtradeDraft}=require("../lib/wt-etrade-order-draft.ts");
const now=Date.parse("2026-11-11T16:00:00Z");
const cases=WT_ETRADE_CANDIDATES;
const focus=(candidate,date="2026-11-22")=>({
  ticker:candidate.ticker,nct:candidate.nct,recordedPdufaDate:date,
});
function validBars(){
  const sessions=[];
  for(let time=Date.parse("2026-11-10T00:00:00Z");sessions.length<91;time-=86400000){
    const d=new Date(time),dow=d.getUTCDay();
    if(dow!==0&&dow!==6)sessions.push(d.toISOString().slice(0,10));
  }
  sessions.reverse();
  const base=[10.0,10.12,9.94,10.12,9.96,10.04,9.95,10.13,10.0,10.08];
  const prices=[
    ...Array.from({length:80},(_,i)=>9.1+0.011*i+(i%2?0.06:0)),
    ...base,10.35,
  ];
  return sessions.map((date,i)=>({
    date,open:prices[i],high:prices[i]+0.1,low:prices[i]-0.1,
    close:prices[i],volume:i===90?600000:250000,
  }));
}
function market(candidate=cases[0]){
  const bars=validBars();
  return {programId:candidate.programId,ticker:candidate.ticker,provider:"ALPACA",
    status:"OK",feed:"IEX",adjustment:"raw",asOf:bars.at(-1).date,bars};
}
test("Eight distinct Alpaca technical metrics independently yield BUY_SETUP for a valid latest complete session",()=>{
  for(const candidate of cases){
    const x=evaluateWtAlpacaTechnicalSignal(candidate,focus(candidate),market(candidate),now);
    assert.equal(x.status,"BUY_SETUP");
    assert.equal(x.passed,8);assert.equal(x.total,8);
    assert.equal(new Set(x.checks.map(c=>c.key)).size,8);
    assert.ok(x.checks.every(c=>c.passed),JSON.stringify(x.checks));
    assert.equal(x.asOf,"2026-11-10");assert.equal(x.feed,"IEX");
    assert.ok(x.triggerReference>0&&x.riskStopReference>0);
    assert.equal(x.pdufaDays,11);
    assert.equal(x.pdufaGate,"PRE_PDUFA_BLACKOUT");
    assert.equal(x.orderEligible,false);assert.equal(x.brokerOrderEnabled,false);
    assert.match(x.reason,/14-day pre-PDUFA/);
    // A technical BUY_SETUP cannot feed through the existing strict E*TRADE
    // authorization chain: no calculated live limit price, no broker order.
    const order=prepareWtEtradeDraft(candidate,focus(candidate),null,now);
    assert.equal(order.status,"PDUFA_EXIT_WINDOW");
    assert.equal(order.limitPrice,null);
    assert.equal(order.isApproved,false);
    assert.equal(order.isSubmitted,false);
  }
});
test("Missing, stale, wrong program, source and malformed bars all fail closed",()=>{
  const c=cases[0];
  const base=market(c);
  const casesInvalid=[
    null,
    {...base,programId:"PDUFA-999999"},
    {...base,ticker:"CAPR"},
    {...base,provider:"YAHOO"},
    {...base,status:"ERROR"},
    {...base,feed:"UNKNOWN"},
    {...base,adjustment:"split"},
    {...base,bars:base.bars.slice(-50)},
    {...base,asOf:"2026-11-09"},
    {...base,bars:base.bars.map((v,i)=>i===50?{...v,volume:NaN}:v)},
    {...base,bars:base.bars.map((v,i)=>i===50?{...v,date:base.bars[49].date}:v)},
  ];
  for(const wrong of casesInvalid){
    const x=evaluateWtAlpacaTechnicalSignal(c,focus(c),wrong,now);
    assert.equal(x.status,"UNAVAILABLE",wrong?.status||"null");
    assert.equal(x.orderEligible,false);
    assert.equal(x.checks.length,0);
  }
  assert.equal(evaluateWtAlpacaTechnicalSignal(c,
    {...focus(c),nct:"NCT00000000"},base,now).status,"UNAVAILABLE");
  assert.equal(evaluateWtAlpacaTechnicalSignal(c,focus(c),base,Date.parse("2026-11-19T16:00:00Z")).status,"UNAVAILABLE");
});
test("A genuine failing check reports WAIT with transparent measured metric",()=>{
  const c=cases[0],raw=market(c);
  raw.bars.at(-1).volume=50000;
  const x=evaluateWtAlpacaTechnicalSignal(c,focus(c),raw,now);
  assert.equal(x.status,"WAIT");
  assert.ok(x.passed<8);
  const relative=x.checks.find(k=>k.key==="volume");
  assert.equal(relative.passed,false);
  assert.match(relative.required,/1\.50/);
  assert.match(x.reason,/Technical buy setup not confirmed/);
});
test("PDUFA timing is separately recorded and never turns a BUY_SETUP into order permission",()=>{
  const c=cases[0],bars=market(c);
  const outside=evaluateWtAlpacaTechnicalSignal(c,focus(c,"2027-01-14"),bars,now);
  assert.equal(outside.status,"BUY_SETUP");assert.equal(outside.pdufaGate,"OUTSIDE_BLACKOUT");
  assert.equal(outside.orderEligible,false);
  const past=evaluateWtAlpacaTechnicalSignal(c,focus(c,"2026-11-10"),bars,now);
  assert.equal(past.status,"BUY_SETUP");assert.equal(past.pdufaGate,"PAST_TARGET");
  assert.equal(past.orderEligible,false);
  const missing=evaluateWtAlpacaTechnicalSignal(c,focus(c,null),bars,now);
  assert.equal(missing.status,"BUY_SETUP");assert.equal(missing.pdufaGate,"NO_VERIFIED_DATE");
  assert.equal(missing.orderEligible,false);
});
test("WT UI presents technical signal independently from E*TRADE research drafts with no order execution",()=>{
  const ui=fs.readFileSync(path.join(__dirname,"../app/WtEtradeOrderPrep.tsx"),"utf8");
  const view=fs.readFileSync(path.join(__dirname,"../app/WtAlpacaBuySignal.tsx"),"utf8");
  assert.match(ui,/evaluateWtAlpacaTechnicalSignal/);
  assert.match(ui,/WtAlpacaBuySignal signal=\{technicalSignal\}/);
  assert.match(view,/BUY SETUP — TECHNICAL ONLY/);
  assert.match(view,/WAIT — TECHNICAL CHECKS NOT MET/);
  assert.match(view,/data-wt-alpaca-technical-signal="read-only"/);
  assert.match(view,/Show all eight Alpaca technical checks and thresholds/);
  assert.match(view,/PDUFA ENTRY HOLD/);
  assert.doesNotMatch(view,/\/orders\/(?:place|preview)/);
  assert.doesNotMatch(view,/fetch\(/);
});
