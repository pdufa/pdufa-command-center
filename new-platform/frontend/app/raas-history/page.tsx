/** Historical RAAS evidence worklist. Research-only case examples are
 * deliberately excluded from the production scoring/forecast ledger.
 */
import type {Metadata} from "next";
import Link from "next/link";
import retrospectiveTopData from "../../data/raas-retrospective-top-cases.json";
import retrospectiveBottomData from "../../data/raas-retrospective-source-cases.json";
import retrospectiveAsOfData from "../../data/raas-retrospective-asof-evidence.json";
import retrospectiveFinances from "../../data/raas-historical-finance-facts.json";
import shareBridgeResearch from "../../data/raas-share-bridge-research.json";
import {parseTopRetrospective} from "../../lib/raas-top-retrospective-intake";
import {parseRetrospectiveFeed} from "../../lib/raas-retrospective-intake";
import {buildHistoricalResearchAudit,summarizeHistoricalResearch,type HistoricalAuditCase} from "../../lib/raas-history-audit";
import {parseAsOfEvidence,factsForRetrospectiveCase,measureAsOfFact} from "../../lib/raas-retrospective-asof-evidence";
import {parseHistoricalFinance,financeForCase,financeReadiness} from "../../lib/raas-finance-reconciliation";
import {parseShareBridge,bridgeForCase,bridgeSummary} from "../../lib/raas-share-bridge";
import RaasHistoricalWhatIf from "./RaasHistoricalWhatIf";
import css from "./page.module.css";

export const metadata:Metadata={
 title:"RAAS Historical Evidence Audit | PDUFA",
 description:"Phase-separated, point-in-time RAAS historical source and validation readiness."
};
const pre=parseTopRetrospective(retrospectiveTopData);
const post=parseRetrospectiveFeed(retrospectiveBottomData);
const audits=buildHistoricalResearchAudit(pre,post);
const summary=summarizeHistoricalResearch(audits);
const datedFacts=parseAsOfEvidence(retrospectiveAsOfData,post);
const observedFactCount=datedFacts.records.reduce((sum,r)=>sum+r.facts.length,0);
const financialResearch=parseHistoricalFinance(retrospectiveFinances,pre,post);
const financeCount=financialResearch.records.reduce((sum,r)=>sum+r.facts.length,0);
const shareResearch=parseShareBridge(shareBridgeResearch,pre,post);
const sharesSummary=bridgeSummary(shareResearch,pre,post);
const scenarioInputs=[
 ...pre.records.map(x=>({id:x.id,ticker:x.ticker,stage:"pre" as const,entryPrice:x.entry.close,exitPrice:x.exit.close})),
 ...post.records.map(x=>({id:x.id,ticker:x.ticker,stage:"post" as const,entryPrice:x.entry.close,exitPrice:x.exit.close}))
];
const dateFormat=(s:string)=>s;
function CaseRow({entry}:{entry:HistoricalAuditCase}){
 const sign=entry.grossPercent>0?"+":"";
 const priorFacts=entry.stage==="post"?factsForRetrospectiveCase(datedFacts,entry.id):[];
 const finances=financeForCase(financialResearch,entry.id);
 const financeQuality=financeReadiness(financialResearch,entry.id,entry.stage);
 const capBridge=bridgeForCase(shareResearch,pre,post,entry.id);
 return <details className={css.case} data-history-case={entry.id}>
   <summary className={css.caseHead}>
     <span className={css.identity}>
       <strong>{entry.ticker}</strong><span>{entry.drug}</span>
       <small>{entry.indication}</small>
     </span>
     <span className={css.numbers}>
       <strong>{sign}{entry.grossPercent.toFixed(2)}%</strong>
       <small>Observed gross, not forecast</small>
     </span>
     <span className={css.window}>
       <strong>{dateFormat(entry.entryDate)} → {dateFormat(entry.exitDate)}</strong>
       <small>{entry.stage==="pre"?"Phase 3 pre-readout":"Post-Phase 3 / pre-FDA"}</small>
     </span>
     <span className={css.review}>
       <strong>{entry.outstandingCount} review gaps</strong>
       <small>{entry.criticalOutstandingCount} high priority</small>
     </span>
     <span className={css.arrow} aria-hidden="true">▸</span>
   </summary>
   <div className={css.details}>
     <p className={css.notice}><strong>Research example, not a trade recommendation.</strong> The dates were selected retrospectively. A published price change cannot validate a forecast that did not exist at entry. No RAAS score is assigned.</p>
     <div className={css.facts}>
       <div><span>Historical market capitalization</span><strong>${entry.marketCapUsdMillions.toLocaleString("en-US")}M, vendor reported</strong></div>
       <div><span>Registered trial count</span><strong>{entry.nctCount} — one therapy opportunity</strong></div>
       <div><span>{entry.stage==="pre"?"Actual Phase 3 readout":"Verified-target claim"}</span><strong>{entry.eventDate}</strong></div>
       <div><span>Historic RAAS validation</span><strong>Ineligible · no original forecast</strong></div>
     </div>
     {priorFacts.length>0&&<details className={css.check} data-preentry-facts={entry.id}>
       <summary><span className={css.indicator}>◌</span><strong>{priorFacts.length} historical clinical and financial observations available before entry</strong><span className={css.status}>Not RAAS scores</span></summary>
       <div className={css.checkBody}>
         {priorFacts.map(fact=>{const calc=measureAsOfFact(fact);return <div key={fact.id} className={css.sourceFact}>
           <strong>{fact.title}</strong>
           <p>{calc.label}: <strong>{calc.value.toLocaleString("en-US",{maximumFractionDigits:2})} {calc.unit}</strong></p>
           {fact.kind==="RANDOMIZED_RESPONSE"&&<p>Reported active arm {fact.activePercent}% versus comparator {fact.comparatorPercent}%.</p>}
           <p>Source published {fact.sourcePublishedAt}. {fact.measurementAsOf?"Measurement as of "+fact.measurementAsOf+". ":""}{fact.context}</p>
           <p className={css.factCaution}>{calc.interpretation}</p>
           <a href={fact.sourceUrl} target="_blank" rel="noopener noreferrer">Inspect contemporaneous evidence</a>
         </div>;})}
       </div>
     </details>}
     <details className={css.check} data-historical-financing={entry.id}>
       <summary><span className={css.indicator}>◌</span><strong>{financeQuality.financeFactCount} dated SEC/issuer financial facts · unresolved valuation checks</strong><span className={css.status}>Not cash runway</span></summary>
       <div className={css.checkBody}>
         {finances?<>
           <p>Financial observation as of {finances.asOf}, published {finances.publishedAt}, before the selected historical entry. Values in USD millions.</p>
           {finances.facts.map(fact=><div key={fact.type} className={css.sourceFact}>
             <strong>{fact.type.replaceAll("_"," ")}</strong>
             <p>Reported amount: <strong>${fact.valueUsdMillions.toLocaleString("en-US",{maximumFractionDigits:3})}M</strong></p>
             <p>{fact.method}</p><p className={css.factCaution}>{fact.caveat}</p>
             <a href={finances.sourceUrl} target="_blank" rel="noopener noreferrer">Check original financial disclosure</a>
           </div>)}
         </>:<p>No timely issuer/SEC financial source imported for this example.</p>}
         <p><strong>Still blocked:</strong> {financeQuality.issues.join("; ")}.</p>
       </div>
     </details>
     <details className={css.check} data-share-reconciliation={entry.id}>
       <summary><span className={css.indicator}>{capBridge?"◌":"!"}</span>
         <strong>Historical share count, share class and capitalization arithmetic</strong>
         <span className={css.status}>{capBridge?(capBridge.capComparisonBasis==="SAME_SHARES_RECONSTRUCTION"?"Share-based cap reconstruction":capBridge.status==="ARITHMETIC_MATCH_REQUIRES_PRICE_AUDIT"?"Vendor cap arithmetic matches · price unverified":"Vendor cap discrepancy"):"SEC share count missing"}</span>
       </summary>
       <div className={css.checkBody}>
         {capBridge?<>
           <p>Historical source price ${capBridge.observedEntryPrice.toFixed(2)} × SEC ordinary/common shares converted to quoted security units. SEC shares observed {capBridge.shareCountAsOf}, published {capBridge.sharePublishedAt}; no later SEC filing is used.</p>
           <div className={css.sourceFact}>
             <strong>Quoted-security share equivalent: {capBridge.quotedSharesEquivalent.toLocaleString("en-US",{maximumFractionDigits:2})}</strong>
             <p>Arithmetic capitalization: <strong>${capBridge.reconstructedEquityCapUsdMillions.toLocaleString("en-US",{maximumFractionDigits:2})}M</strong></p>
             <p>Vendor capitalization: ${capBridge.vendorCapUsdMillions.toLocaleString("en-US",{maximumFractionDigits:2})}M; difference <strong>{capBridge.relativeDifferencePercent.toFixed(2)}%</strong>.</p>
             <p className={css.factCaution}>{capBridge.capComparisonBasis==="SAME_SHARES_RECONSTRUCTION"?"This market-cap figure was derived from these same shares and price; matching it is circular, not an independent vendor confirmation.":"The stated market capitalization is a separate vendor estimate, but agreeing on multiplication does not independently verify the historical price."} Fully diluted shares, corporate actions and executable transactions remain unverified. Never approve RAAS from arithmetic alone.</p>
           </div>
           <a href={capBridge.shareSourceUrl} target="_blank" rel="noopener noreferrer">SEC cover share-count filing</a>
           <a href={capBridge.priceSourceUrl} target="_blank" rel="noopener noreferrer">Historical vendor price series</a>
           <a href={capBridge.vendorCapSourceUrl} target="_blank" rel="noopener noreferrer">Historical vendor equity-cap estimate</a>
         </>:<p>No pre-entry SEC share-count bridge has yet been recorded for this case. Vendor market cap is not independently reconciled. Leave security-share verification and full dilution unresolved.</p>}
       </div>
     </details>
     <h3>Point-in-time evidence and audit worklist</h3>
     <div className={css.checks}>
       {entry.items.map(item=><details key={item.id} className={css.check} data-check={item.id}>
         <summary>
           <span className={css.indicator}>{item.status==="RECORDED_NOT_INDEPENDENTLY_VERIFIED"?"◌":"!"}</span>
           <strong>{item.label}</strong>
           <span className={css.status}>{item.status==="RECORDED_NOT_INDEPENDENTLY_VERIFIED"?"Dated claim recorded":
             item.status==="NOT_AVAILABLE"?"No original record":"Requires audit"}</span>
         </summary>
         <div className={css.checkBody}>
           <p>{item.detail}</p>
           {item.sourceUrl&&<a href={item.sourceUrl} target="_blank" rel="noopener noreferrer">Inspect recorded source</a>}
           {item.priority===1&&<small>High-priority prerequisite</small>}
         </div>
       </details>)}
     </div>
     <p className={css.foot}>Next: audit the source material and historical market data. Do not promote this example to the original-prediction ledger or replace missing scientific metrics with zeros.</p>
   </div>
 </details>;
}
export default function RaasHistoricalAuditPage(){
 const top=audits.filter(a=>a.stage==="pre");
 const bottom=audits.filter(a=>a.stage==="post");
 return <main className={css.root}>
   <header className={css.header}>
     <Link className={css.back} href="/tools">← Back to Tools</Link>
     <h1>RAAS · Historical Evidence Audit</h1>
     <p>One place to inspect historic research windows, verify their sources, and identify why they cannot yet support qualified TOP or BOTTOM investment scores.</p>
   </header>
   <div className={css.stats}>
     <div><strong>{summary.topExamples}</strong><span>TOP research windows</span></div>
     <div><strong>{summary.bottomExamples}</strong><span>BOTTOM research windows</span></div>
     <div><strong>{summary.openReviews}</strong><span>Outstanding source/market reviews</span></div>
     <div><strong>{sharesSummary.separatelyReportedCapMatches}/{sharesSummary.caseCount}</strong><span>Vendor cap cross-checks match · prices unverified</span></div>
   </div>
   <p className={css.disclaimer}>All examples were selected after their historical outcomes and report gross vendor close-to-close price changes, excluding trading costs. {observedFactCount} dated clinical observations, {financeCount} sourced financing figures and {sharesSummary.withSecShareCount} SEC share-count cross-checks are available for research, but none is a RAAS grade or independently verified full valuation. Published links require independent audit. No retrospective simulation is an authentic prior prediction. As-of snapshot: {pre.sourceAsOf}.</p>
   <section className={css.section} aria-labelledby="raas-history-top">
     <div className={css.sectionTitle}><h2 id="raas-history-top">TOP · 3 — before public Phase 3 results</h2><span>{top.length} examples · not validated</span></div>
     <div className={css.cases}>{top.map(x=><CaseRow key={x.id} entry={x}/>)}</div>
   </section>
   <section className={css.section} aria-labelledby="raas-history-bottom">
     <div className={css.sectionTitle}><h2 id="raas-history-bottom">BOTTOM · P — after Phase 3, before FDA action</h2><span>{bottom.length} examples · not validated</span></div>
     <div className={css.cases}>{bottom.map(x=><CaseRow key={x.id} entry={x}/>)}</div>
   </section>
   <RaasHistoricalWhatIf cases={scenarioInputs}/>
   <footer className={css.footer}>
     <strong>Score readiness</strong>
     <p>To qualify a score: collect dated pre-entry sources, reconstruct fully diluted valuation, reconcile split-adjusted prices, model execution and tail losses, and validate metric thresholds on independent walk-forward holdouts. Historic replay must remain labeled as a simulation; only subsequently recorded forecasts can establish forward predictive performance.</p>
   </footer>
 </main>;
}
