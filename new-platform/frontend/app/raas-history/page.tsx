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
import priceCrosscheckResearch from "../../data/raas-price-crosschecks.json";
import corporateActionResearch from "../../data/raas-corporate-actions-research.json";
import fdaPrimaryOutcomeData from "../../data/raas-fda-primary-outcomes.json";
import prospectiveSourceData from "../../data/raas-prospective-source-baselines.json";
import {parseTopRetrospective} from "../../lib/raas-top-retrospective-intake";
import {parseRetrospectiveFeed} from "../../lib/raas-retrospective-intake";
import {buildHistoricalResearchAudit,summarizeHistoricalResearch,type HistoricalAuditCase} from "../../lib/raas-history-audit";
import {parseAsOfEvidence,factsForRetrospectiveCase,measureAsOfFact} from "../../lib/raas-retrospective-asof-evidence";
import {parseHistoricalFinance,financeForCase,financeReadiness} from "../../lib/raas-finance-reconciliation";
import {parseShareBridge,bridgeForCase,bridgeSummary} from "../../lib/raas-share-bridge";
import {parsePriceCrosschecks,priceAuditForCase,priceAuditSummary} from "../../lib/raas-price-crosschecks";
import {parseCorporateActions,corporateActionsForCase,corporateActionSummary} from "../../lib/raas-corporate-action-audit";
import {parseFdaPrimaryOutcomes,fdaPrimaryOutcomeForCase,fdaPrimaryOutcomeSummary} from "../../lib/raas-fda-primary-outcomes";
import {parseProspectiveSourceBaselines,prospectiveSourceSummary} from "../../lib/raas-prospective-source-baselines";
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
const priceResearch=parsePriceCrosschecks(priceCrosscheckResearch,pre,post);
const priceSummary=priceAuditSummary(priceResearch,pre,post);
const actionFeed=parseCorporateActions(corporateActionResearch);
const actionSummary=corporateActionSummary(actionFeed,pre,post);
const fdaPrimary=parseFdaPrimaryOutcomes(fdaPrimaryOutcomeData,post);
const fdaPrimarySummary=fdaPrimaryOutcomeSummary(fdaPrimary,post);
const prospective=parseProspectiveSourceBaselines(prospectiveSourceData);
const prospectiveSummary=prospectiveSourceSummary(prospective);
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
 const closeAudit=priceAuditForCase(priceResearch,pre,post,entry.id)!;
 const actionAudit=corporateActionsForCase(actionFeed,pre,post,entry.id)!;
 const fdaDecision=entry.stage==="post"?fdaPrimaryOutcomeForCase(fdaPrimary,entry.id):null;
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
     {entry.stage==="post"&&<details className={css.check} data-fda-primary-outcome={entry.id}>
       <summary>
         <span className={css.indicator}>{fdaDecision?"◌":"!"}</span>
         <strong>Primary FDA action source · historical outcome only</strong>
         <span className={css.status}>{fdaDecision?"FDA approval independently cross-checked":"FDA primary source not reconciled"}</span>
       </summary>
       <div className={css.checkBody}>
         {fdaDecision?<div className={css.sourceFact}>
           <strong>{fdaDecision.product} · FDA {fdaDecision.decision.toLowerCase()} · {fdaDecision.decisionDate}</strong>
           <p>Drug and indication matched to this BOTTOM historical example. FDA publication was reviewed {fdaDecision.reviewedAt}. The FDA action occurred <strong>after</strong> the selected historical exit ({entry.exitDate}).</p>
           <a href={fdaDecision.fdaUrl} target="_blank" rel="noopener noreferrer">{fdaDecision.sourceTitle}</a>
         </div>:<p>FDA action date and product have not been independently reconciled to a primary FDA page for this case.</p>}
         <p className={css.factCaution}>Outcome-only verification. This later regulatory decision did not exist at the selected historical entry or exit and cannot qualify a contemporaneous stock prediction, independently establish every associated NCT, validate adjusted market prices or produce a RAAS grade.</p>
       </div>
     </details>}
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
           {finances.riskDisclosure&&<div className={css.sourceFact} data-historical-preentry-risk={entry.id}>
             <strong>Pre-entry SEC financing risk · going-concern substantial doubt</strong>
             <p>Risk reported as of {finances.riskDisclosure.asOf} in an SEC filing published {finances.riskDisclosure.publishedAt}, before the selected research entry.</p>
             <p>{finances.riskDisclosure.summary}</p>
             <p className={css.factCaution}>{finances.riskDisclosure.caveat} This is entry-time adverse evidence, not a retrospective RAAS score.</p>
             <a href={finances.riskDisclosure.sourceUrl} target="_blank" rel="noopener noreferrer">Read SEC going-concern disclosure</a>
           </div>}
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
     <details className={css.check} data-price-reconciliation={entry.id}>
       <summary><span className={css.indicator}>{closeAudit.bothClosesAgree?"◌":"!"}</span>
         <strong>Independent-provider historical closing price checks</strong>
         <span className={css.status}>{closeAudit.secondProviderPoints}/2 dates cross-checked · adjusted prices NOT verified</span>
       </summary>
       <div className={css.checkBody}>
         {([closeAudit.entry,closeAudit.exit] as const).map(point=><div key={point.side} className={css.sourceFact}>
           <strong>{point.side} · {point.date} · {point.status==="PROVIDER_PRICE_MATCH"?"Two displayed closing prices agree":point.status==="PROVIDER_PRICE_MISMATCH"?"Price discrepancy":"No independent second close yet"}</strong>
           <p>Original price: <strong>${point.originalClose.toFixed(2)}</strong>; second source: {point.secondaryClose===null?"Not available":"$"+point.secondaryClose.toFixed(2)}{point.secondaryProvider?" ("+point.secondaryProvider+")":""}. {point.quoteGranularity==="WEEKLY_FRIDAY_CLOSE"?"Secondary is a Friday-ending weekly close; source methodology needs review.":point.quoteGranularity==="DAILY_SESSION_CLOSE"?"Secondary source shows a dated daily trading session.":""}</p>
           {point.differenceUsd!==null&&<p>Difference: ${point.differenceUsd.toFixed(4)} ({point.differencePercent?.toFixed(2)}%).</p>}
           {point.postExitDisclosure&&<p className={css.factCaution}>This corroborating document was first published {point.sourceFirstPublishedAt}, after the selected historical exit. It confirms a past quote only and cannot be used as a contemporaneous RAAS signal.</p>}
           <a href={point.originalUrl} target="_blank" rel="noopener noreferrer">Original vendor price</a>
           {point.secondaryUrl&&<a href={point.secondaryUrl} target="_blank" rel="noopener noreferrer">Second provider's dated history</a>}
         </div>)}
         <p><strong>Still blocked:</strong> {closeAudit.blockingIssues.join("; ")}.</p>
         <p className={css.factCaution}>Matching two displayed nominal closes is useful price corroboration, but does NOT establish split- or dividend-adjusted total returns or independent exchange-tape verification. Neither price nor historical RAAS prediction is approved by this comparison.</p>
       </div>
     </details>
     <details className={css.check} data-corporate-actions={entry.id}>
       <summary><span className={css.indicator}>!</span>
         <strong>Corporate actions, distributions and ADS ratio review</strong>
         <span className={css.status}>{actionAudit.listedEvents.length} historical events recorded · full adjustment audit pending</span>
       </summary>
       <div className={css.checkBody}>
         <p>Security class: {actionAudit.securityClass??"Not reconciled"}{actionAudit.adsOrdinaryShares?" · "+actionAudit.adsOrdinaryShares+" ordinary shares per quoted ADS":""}. This is a partial event history; absence of a listed event does not prove none occurred during this trade window.</p>
         {actionAudit.listedEvents.length===0?<p>No supporting corporate-action event source has been recorded for this ticker.</p>:
           actionAudit.listedEvents.map(({event,placement})=><div className={css.sourceFact} key={event.id}>
             <strong>{event.date} · {event.type.replaceAll("_"," ")} · {placement.replaceAll("_"," ").toLowerCase()}</strong>
             {event.factorNumerator&&event.factorDenominator&&<p>Reported factor: {event.factorNumerator}:{event.factorDenominator}. Factor is not applied to these historic returns.</p>}
             {event.cashPerQuotedSecurityUsd&&<p>Reported later cash consideration: ${event.cashPerQuotedSecurityUsd.toFixed(2)} per quoted security; not used as an earlier trade forecast.</p>}
             <p>{event.notes}</p>
             <a href={event.sourceUrl} target="_blank" rel="noopener noreferrer">Review corporate-action evidence</a>
           </div>)}
         <p><strong>Open blockers:</strong> {actionAudit.blockers.join("; ")}.</p>
         <p className={css.factCaution}>Verified split/dividend-adjusted total returns: NO. Approved investment predictions: NO. Events after the selected exit are not treated as knowledge available at entry.</p>
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
      <p><Link href="/raas-scan">Open executed RAAS 60-metric readiness scan and unresolved requirements</Link></p>
     <h1>RAAS · Historical Evidence Audit</h1>
     <p>Inspect pre-readout evidence captured prospectively, historical research windows, and why neither yet supports approved TOP or BOTTOM investment scores.</p>
   </header>
   <div className={css.stats}>
     <div><strong>{prospectiveSummary.baselines}</strong><span>Pre-readout source baselines recorded · not numerical ratings</span></div>
     <div><strong>{summary.topExamples}</strong><span>TOP research windows</span></div>
     <div><strong>{summary.bottomExamples}</strong><span>BOTTOM research windows</span></div>
     <div><strong>{summary.eligiblePredictions}</strong><span>Eligible original predictions · unvalidated historical cases excluded</span></div>
     <div><strong>{fdaPrimarySummary.crosschecked}/{fdaPrimarySummary.total}</strong><span>BOTTOM FDA actions matched to primary FDA pages · outcome only</span></div>
     <div><strong>{priceSummary.matchedPoints}/{priceSummary.quotedPoints}</strong><span>Second-source closing-price matches · adjustment pending</span></div>
     <div><strong>{sharesSummary.separatelyReportedCapMatches}/{sharesSummary.caseCount}</strong><span>Vendor cap checks match; {sharesSummary.mismatchedVendorCaps} discrepancies remain · prices unverified</span></div>
   </div>
   <p className={css.disclaimer}>Five historical FDA actions are now separately cross-checked against primary FDA sources. These occurred after the selected historical exits and do not increase the count of valid backtested RAAS predictions. Corporate actions: {actionSummary.withPartialActionHistory} of {actionSummary.cases} study windows have some historical event evidence, but 0 have a completed corporate-action adjustment audit. Independent-provider research: {priceSummary.matchedPoints} of {priceSummary.quotedPoints} exact-date displayed historical closes agree; {priceSummary.bothClosesMatchedCases} of {priceSummary.caseCount} trade windows have both dates matched. Adjusted-return audits and approved predictions remain at zero. All examples were selected after their historical outcomes and report gross vendor close-to-close price changes, excluding trading costs. {observedFactCount} dated clinical observations, {financeCount} sourced financing figures and {sharesSummary.withSecShareCount} SEC share-count cross-checks are available for research ({sharesSummary.mismatchedVendorCaps} mismatches requiring issuer/vendor denominator review), but none is a RAAS grade or independently verified full valuation. Published links require independent audit. No retrospective simulation is an authentic prior prediction. As-of snapshot: {pre.sourceAsOf}.</p>
   <section className={css.section} aria-labelledby="raas-prospective-sources">
     <div className={css.sectionTitle}>
       <h2 id="raas-prospective-sources">Prospective TOP · pre-readout evidence captured</h2>
       <span>{prospectiveSummary.baselines} source baselines · {prospectiveSummary.distinctIssuers} issuers · {prospectiveSummary.distinctPrograms} therapy programs · {prospectiveSummary.recordedSourceFacts} dated source facts · 0 predictions</span>
     </div>
     <p className={css.disclaimer}>These source observations were recorded on {prospective.sourceAsOf} while the corresponding pivotal readout was still expected in the future. Git commit history provides an inspectable capture trail, not cryptographic timestamp notarization. No original 0–100 RAAS grade, entry execution price or expected return has been recorded. Source facts here cannot be backfilled as historic investment forecasts.</p>
     <div className={css.cases}>
       {prospective.records.map(record=><details className={css.case} data-prospective-baseline={record.id} key={record.id}>
         <summary className={css.caseHead}>
           <span className={css.identity}><strong>{record.ticker} · {record.drug}</strong><span>{record.indication}</span><small>{record.nctId} · Phase 3 before readout</small></span>
           <span className={css.numbers}><strong>{record.observations.length} sourced facts</strong><small>Not graded</small></span>
           <span className={css.window}><strong>Recorded {record.capturedOn}</strong><small>Outcome still pending at capture</small></span>
           <span className={css.review}><strong>RAAS — / 100</strong><small>No archived score or trade</small></span>
           <span className={css.arrow} aria-hidden="true">▸</span>
         </summary>
         <div className={css.details}>
           <p className={css.notice}><strong>Prospective research record, not a trading signal.</strong> The issuer and trial identity can be checked against <a href={"https://clinicaltrials.gov/study/"+record.nctId} target="_blank" rel="noopener noreferrer">ClinicalTrials.gov</a>. The planned readout has not been recorded as completed. Recorded source evidence does not yet meet the 60 historically validated metric-calibration requirements.</p>
           <div className={css.facts}>
             <div><span>Historical price-filter reference</span><strong>${record.marketCap.usdMillions.toLocaleString("en-US")}M market cap · {record.marketCap.observedAsOf}</strong></div>
             <div><span>Market capitalization verification</span><strong>Vendor reported · fully diluted share/corporate-action audit incomplete</strong></div>
             <div><span>Original RAAS forecast</span><strong>None · no precommitted numeric score or return</strong></div>
             <div><span>Stage</span><strong>TOP · Phase 3 before results</strong></div>
           </div>
           <p className={css.foot}><a href={record.marketCap.sourceUrl} target="_blank" rel="noopener noreferrer">Review dated market-cap reference</a> — {record.marketCap.note}</p>
           <details className={css.check} data-prospective-facts={record.id}>
             <summary><span className={css.indicator}>◌</span><strong>{record.observations.length} point-in-time clinical and financial source facts</strong><span className={css.status}>Expand sources · no ratings assigned</span></summary>
             <div className={css.checkBody}>
               {record.observations.map(fact=><div key={fact.id} className={css.sourceFact}>
                 <strong>{fact.kind.replaceAll("_"," ")} · {fact.observedAsOf}</strong>
                 <p>{fact.valueText}</p>
                 <p>Source first published {fact.sourcePublishedAt}; candidate RAAS metric(s): {fact.metricIds.join(", ")}.</p>
                 <p className={css.factCaution}>{fact.limitation}</p>
                 <a href={fact.sourceUrl} target="_blank" rel="noopener noreferrer">Read contemporaneous issuer source</a>
               </div>)}
             </div>
           </details>
           <p className={css.foot}>Inspect the <a href="https://github.com/pdufa/pdufa-command-center/commits/main/new-platform/frontend/data/raas-prospective-source-baselines.json" target="_blank" rel="noopener noreferrer">repository record and commit history</a>. Neither independent scientific grading nor the 30/30 holdout validation is complete.</p>
         </div>
       </details>)}
     </div>
   </section>
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
