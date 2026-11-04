"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const ledger=require("../new-platform/frontend/data/raas-active-2024-2025-independent-entry-close-leads.json");
const {auditIndependentEntryCloses:audit}=require("../scripts/raas_independent_entry_close_research.cjs");
const caseId="GERN|RYTELO_IMETELSTAT|NDA217779|2024";
const cases=()=>({
 scope:"RAAS_2024_2025_RAW_CLOSE_SEC_COVER_ENTRY_CAP_RESEARCH",
 rows:[
  {caseId,ticker:"GERN",proposedEntrySession:"2024-02-23",rawCloseAlpaca:1.96},
  {caseId:"ARQT|ZORYVE015_AD|NDA215985_S007|2024",ticker:"ARQT",
   proposedEntrySession:"2024-03-13",rawCloseAlpaca:11.06}
 ]
});
const clone=x=>structuredClone(x);
test("historical third-party GERN closing-price source corroborates only NOMINAL entry close",()=>{
 const r=audit(cases(),ledger);
 assert.equal(r.scope,"RAAS_2024_2025_INDEPENDENT_ENTRY_PRICE_NOMINAL_AUDIT");
 assert.equal(r.casesInspected,2);
 assert.equal(r.secondSourcePriceLeads,1);
 assert.equal(r.matchingIndependentNominalCloses,1);
 assert.equal(r.mismatchedIndependentNominalCloses,0);
 assert.equal(r.missingIndependentNominalCloses,1);
 assert.equal(r.independentlyVerifiedAdjustedPricePairs,0);
 assert.equal(r.verifiedCorporateActionHistories,0);
 assert.equal(r.independentlyValidatedEntryMarketCaps,0);
 assert.equal(r.approvedRaasScores,0);
 const gern=r.rows.find(x=>x.ticker==="GERN");
 assert.equal(gern.status,"INDEPENDENT_NOMINAL_CLOSE_MATCH_ADJUSTMENTS_UNAUDITED");
 assert.equal(gern.entrySession,"2024-02-23");
 assert.equal(gern.alpacaRawEntryClose,1.96);
 assert.equal(gern.independentNominalEntryClose,1.96);
 assert.equal(gern.independentProvider,"FinanceCharts");
 assert.equal(gern.differenceUsd,0);
 assert.equal(gern.independentPriceGranularity,"WEEKLY_FRIDAY_CLOSE");
 assert.equal(gern.priceAdjustmentVerified,false);
 assert.equal(gern.corporateActionVerified,false);
 assert.equal(gern.entryMarketCapVerified,false);
 assert.equal(gern.eligibleForValidatedRaasTradingCase,false);
 assert.equal(gern.approvedRaasScore,null);
});
test("a second-source disagreement is retained as mismatch not assigned success",()=>{
 const d=clone(ledger);d.observations[0].nominalCloseUsd=1.91;
 const r=audit(cases(),d);
 assert.equal(r.matchingIndependentNominalCloses,0);
 assert.equal(r.mismatchedIndependentNominalCloses,1);
 assert.equal(r.rows[0].status,"INDEPENDENT_NOMINAL_CLOSE_DISAGREEMENT");
 assert.equal(r.approvedRaasScores,0);
});
test("no raw Alpaca entry price means independent nominal quote cannot approve a match",()=>{
 const c=cases();c.rows[0].rawCloseAlpaca=null;
 const r=audit(c,ledger);
 assert.equal(r.rows[0].status,"ALPACA_RAW_PRICE_MISSING");
 assert.equal(r.matchingIndependentNominalCloses,0);
 assert.equal(r.independentlyVerifiedAdjustedPricePairs,0);
});
test("reject ticker, session, price, source, adjustment and chronology spoofing",()=>{
 const modify=[
  x=>{x.ticker="ARQT";},
  x=>{x.session="2024-02-22";},
  x=>{x.quoteGranularity="WEEKLY_FRIDAY_CLOSE";x.session="2024-02-22";},
  x=>{x.nominalCloseUsd=-1;},
  x=>{x.secondaryProvider="Alpaca second";},
  x=>{x.sourceUrl="https://data.alpaca.markets/v2/stocks/GERN/bars";},
  x=>{x.sourceUrl="https://user@evil.example/forged";},
  x=>{x.sourceInspectedDate="2023-01-01";},
  x=>{x.priceAdjustmentBasis="FULLY_AUDITED";},
  x=>{x.caseId="unknown";},
 ];
 for(const fn of modify){
  const d=clone(ledger);fn(d.observations[0]);
  assert.throws(()=>audit(cases(),d),/RAAS_SECOND_CLOSE_OBSERVATION_INVALID/);
 }
 const dup=clone(ledger);dup.observations.push(clone(dup.observations[0]));
 assert.throws(()=>audit(cases(),dup),/RAAS_SECOND_CLOSE_OBSERVATION_INVALID/);
 assert.throws(()=>audit({scope:"FAKE",rows:[]},ledger),/RAAS_SECOND_CLOSE_INPUT_INVALID/);
});
test("a missing second-provider ledger never becomes zero-pct or perfect accuracy",()=>{
 const empty=clone(ledger);empty.observations=[];
 const r=audit(cases(),empty);
 assert.equal(r.secondSourcePriceLeads,0);
 assert.equal(r.matchingIndependentNominalCloses,0);
 assert.equal(r.missingIndependentNominalCloses,2);
 assert.equal(r.independentlyVerifiedAdjustedPricePairs,0);
 assert.equal(r.approvedRaasScores,0);
});
