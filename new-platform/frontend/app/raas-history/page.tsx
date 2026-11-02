/** Historical RAAS evidence worklist. Research-only case examples are
 * deliberately excluded from the production scoring/forecast ledger.
 */
import type {Metadata} from "next";
import Link from "next/link";
import retrospectiveTopData from "../../data/raas-retrospective-top-cases.json";
import retrospectiveBottomData from "../../data/raas-retrospective-source-cases.json";
import {parseTopRetrospective} from "../../lib/raas-top-retrospective-intake";
import {parseRetrospectiveFeed} from "../../lib/raas-retrospective-intake";
import {buildHistoricalResearchAudit,summarizeHistoricalResearch,type HistoricalAuditCase} from "../../lib/raas-history-audit";
import css from "./page.module.css";

export const metadata:Metadata={
 title:"RAAS Historical Evidence Audit | PDUFA",
 description:"Phase-separated, point-in-time RAAS historical source and validation readiness."
};
const pre=parseTopRetrospective(retrospectiveTopData);
const post=parseRetrospectiveFeed(retrospectiveBottomData);
const audits=buildHistoricalResearchAudit(pre,post);
const summary=summarizeHistoricalResearch(audits);
const dateFormat=(s:string)=>s;
function CaseRow({entry}:{entry:HistoricalAuditCase}){
 const sign=entry.grossPercent>0?"+":"";
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
     <div><strong>{summary.eligiblePredictions}</strong><span>Verified original RAAS forecasts</span></div>
   </div>
   <p className={css.disclaimer}>All examples were selected after their historical outcomes and report gross vendor close-to-close price changes, excluding trading costs. Published source links are recorded, not independently audited. This research screen never creates or certifies a RAAS investment score. As-of snapshot: {pre.sourceAsOf}.</p>
   <section className={css.section} aria-labelledby="raas-history-top">
     <div className={css.sectionTitle}><h2 id="raas-history-top">TOP · 3 — before public Phase 3 results</h2><span>{top.length} examples · not validated</span></div>
     <div className={css.cases}>{top.map(x=><CaseRow key={x.id} entry={x}/>)}</div>
   </section>
   <section className={css.section} aria-labelledby="raas-history-bottom">
     <div className={css.sectionTitle}><h2 id="raas-history-bottom">BOTTOM · P — after Phase 3, before FDA action</h2><span>{bottom.length} examples · not validated</span></div>
     <div className={css.cases}>{bottom.map(x=><CaseRow key={x.id} entry={x}/>)}</div>
   </section>
   <footer className={css.footer}>
     <strong>Score readiness</strong>
     <p>To qualify a score: collect dated pre-entry sources, reconstruct fully diluted valuation, reconcile split-adjusted prices, model execution and tail losses, and validate metric thresholds on independent walk-forward holdouts. Historic replay must remain labeled as a simulation; only subsequently recorded forecasts can establish forward predictive performance.</p>
   </footer>
 </main>;
}
