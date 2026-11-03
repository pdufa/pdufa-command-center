/** Read-only 60-metric validation worklist; never use evidence coverage as an
 * investment rating. This route is linked from both Phase 3 spreadsheets.
 */
import type {Metadata} from "next";
import Link from "next/link";
import {buildRaasMetricValidationWorklist,raasDocumentedTrialOptions,type RaasWorklistTrial} from "../../lib/raas-metric-validation-worklist";
import {activePdufaGoalAsOfAudit} from "../../lib/raas-pdufa-goal-asof-metric-audit";
import {activeSECAsOfEntryShares} from "../../lib/raas-historical-sec-entry-bridge";
import {raasFull903Overview} from "../../lib/raas-full-90-3-window-policy";
import expansionSource from "../../data/raas-2024-2025-expanded-candidate-source-leads.json";
import type {RaasStage} from "../../lib/raas-metric-specs";
import css from "./page.module.css";

export const metadata:Metadata={
 title:"RAAS TOP/BOTTOM · 60 Metric Validation Worklist | PDUFA",
 description:"All 60 risk-adjusted appreciation assessment metrics, exact-trial source evidence and unapproved calibration gaps."
};
type Params={stage?:string|string[];nctId?:string|string[];ticker?:string|string[];
 drug?:string|string[];indication?:string|string[]};
const first=(x:string|string[]|undefined)=>typeof x==="string"?x:"";
const safe=(x:string)=>x.length<=200?x:"";
function hrefForTrial(t:RaasWorklistTrial|null,stage:RaasStage):string{
 const args=new URLSearchParams({stage});
 if(t){
  args.set("nctId",t.nctId);args.set("ticker",t.ticker);
  if(t.drug)args.set("drug",t.drug);
  if(t.indication)args.set("indication",t.indication);
 }
 return "/raas-worklist?"+args.toString()+"#raas-"+(stage==="pre"?"top":"bottom")+"-worklist";
}
/** Historical examples, not exact-trial evidence for a selected current program.
 * FDA outcomes are intentionally absent; dated target versions are the only
 * inputs being evaluated for the two FDA and timing source gates.
 */
/** Search specification only: research outputs remain provisional until validated. */
function FullRange903History(){
 const x=raasFull903Overview();
 return <section id="raas-full-t90-t3-study" className={css.context}
  data-raas-full-window-study="T90-to-T3-all-combinations">
  <h2>Full entry / exit study · anywhere from T−90 to T−3</h2>
  <p><strong>Any entry and exit combination is allowed</strong> when the entry occurs before the exit. Neither T−79 nor T−14 is a benchmark or required date.</p>
  <div className={css.stats}>
   <div><strong>{x.availablePairs.toLocaleString("en-US")}</strong><span>Entry/exit combinations per PDUFA goal version</span></div>
   <div><strong>{x.sampleCaseCount}</strong><span>2024–2025 historical source-traced trial cases (not full FDA census)</span></div>
   <div><strong>{x.historicalGoalVersionCaseSets}</strong><span>Goal-version case sets (including two revisions)</span></div>
   <div><strong>{x.scenarioEvaluations.toLocaleString("en-US")}</strong><span>Total case-window comparisons in research scan</span></div>
  </div>
  <div className={css.reviewGrid}>
   <div><span>Entry day range</span><strong>{x.entryRange}</strong></div>
   <div><span>Exit day range</span><strong>{x.exitRange}</strong></div>
   <div><span>Calendar and price alignment</span><strong>Next actual session at entry / preceding actual session at exit, at most 4 calendar days</strong></div>
   <div><span>Minimum source-quality safeguards</span><strong>Point-in-time FDA target and Phase 3 date, SEC cover-share publication, and early FDA-action censoring</strong></div>
   <div><span>2024 vs 2025</span><strong>Separate exploratory training and descriptive holdout; no pooling into a claimed optimal result</strong></div>
   <div><span>Approved best entry / exit</span><strong>None — historical evidence not yet independently validated</strong></div>
  </div>
  <p className={css.notice}>Full pairwise research is generated in the 2024–2025 historical source workflow as JSON/CSV; the displayed counts represent configured comparisons, <strong>not verified profitable trades</strong>. Results use separate raw Alpaca prices for provisional $300 million–$10 billion capitalization and adjusted bars for provisional returns. Independent prices, stock split/share-continuity checks, the full FDA event census, trading costs, and out-of-sample replication remain required. <a href="https://github.com/pdufa/pdufa-command-center/actions/workflows/raas-active-2024-2025-original-source-research.yml" target="_blank" rel="noopener noreferrer">View historical comparison scan and artifacts</a>.</p>
  <p className={css.muted}>The T−79 to T−14 source-date entries further down this page are older single-window audit examples only. The full research configuration does not privilege or optimize around them.</p>
 </section>;
}
/** Dated source research queue: neither counts as an approved stock backtest. */
function ExpandedHistoricalCandidates(){
 const x=expansionSource;
 return <section id="raas-historical-expansion-candidates" className={css.context}
  data-raas-expanded-candidates="source-leads-only">
  <h2>Expand the historical 2024–2025 research sample</h2>
  <p><strong>{x.records.length} additional Phase 3-linked FDA case leads</strong> are now recorded for independent eligibility review. They do not increase the nine-stock research results, the validated-trade count or the RAAS score.</p>
  <div className={css.stats}>
   <div><strong>{x.records.length}</strong><span>New dated FDA and Phase 3 case leads</span></div>
   <div><strong>{x.approvedAdditionsTo2024To2025Backtest}</strong><span>Eligible cases added to the approved return sample</span></div>
  </div>
  {x.records.map(c=><details key={c.caseId} className={css.detail}>
   <summary><strong>{c.ticker} · {c.drug}</strong> · {c.pdufaTargetDate} FDA target · source review only</summary>
   <p>{c.indication}. Review type: {c.reviewCycleType}; trial {c.nctIds.join(", ")}.</p>
   <p>Phase 3 source date: <strong>{c.phase3EvidenceDate}</strong> · PDUFA target publicly announced <strong>{c.targetAnnouncementDate}</strong> · recorded retrospective FDA action <strong>{c.actualFDAActionDate}</strong> ({c.actualFDAOutcome}).</p>
   <p><a href={c.phase3EvidenceSourceUrl} target="_blank" rel="noopener noreferrer">Phase 3 readout source</a> · <a href={c.targetAnnouncementSourceUrl} target="_blank" rel="noopener noreferrer">Published PDUFA target</a> · <a href={c.outcomeSourceUrl} target="_blank" rel="noopener noreferrer">FDA outcome source</a>.</p>
   <p className={css.notice}>Not yet approved for the $300M–$10B study. Missing: {c.missingChecks.join("; ")}. No adjusted price return or validated historical market cap has been computed for this candidate.</p>
  </details>)}
 </section>;
}
function GoalAsOfHistory(){
 const audit=activePdufaGoalAsOfAudit();
 return <section id="raas-pdufa-asof-history" className={css.context}
   data-raas-pdufa-asof-metric-research="research-only">
  <h2>Legacy T−79/T−14 date-source example · 2024–2025 (not preferred)</h2>
  <p><strong>{audit.sourceCases} source-traced cases</strong> · <strong>{audit.revisedGoalCases} formal goal revisions</strong> · <strong>{audit.finalGoalPublishedBeforeFinalEntryCases}/{audit.sourceCases}</strong> target sources published by the provisional T−79 entry · <strong>{audit.stageMetricHistoricalApprovedCases}</strong> approved historical RAAS metric grades.</p>
  <p>For <strong>post-3-5</strong> (PDUFA date and review risks), <strong>post-6-1</strong> (exact-program target) and <strong>post-6-2</strong> (tradable exit calendar). These are historical examples only, <strong>not</strong> source evidence or scores transferred to the selected trial. No FDA outcomes or post-decision facts are used as entry features.</p>
  <div className={css.stats}>
   <div><strong>{audit.reviewYears[2024]}</strong><span>2024 FDA target-year selected cases</span></div>
   <div><strong>{audit.reviewYears[2025]}</strong><span>2025 FDA target-year selected cases</span></div>
   <div><strong>{audit.calendarWeekendEntryCases}</strong><span>Calendar T−79 entries falling on weekends</span></div>
   <div><strong>{audit.calendarWeekendExitCases}</strong><span>Calendar T−14 exits falling on weekends</span></div>
  </div>
  <p className={css.notice}>Calendar offsets and proposed next-entry / prior-exit Nasdaq sessions are not executable trading sessions, verified prices, or independent historical returns. Market closures include the exceptional January 9, 2025 shutdown; <a href="https://classic.nasdaqtrader.com/TraderNews.aspx?id=ETA2025-1" target="_blank" rel="noopener noreferrer">Nasdaq closure notice</a>. Issuer announcements do not independently validate FDA chronology or capitalization. No 0–100 RAAS grade is approved. SLNO's separately saved original announcement URL remains missing.</p>
  {audit.cases.map(c=><details key={c.caseId} className={css.group}
    data-raas-goal-asof-case={c.ticker}>
    <summary><strong>{c.ticker} · {c.application}</strong>
     <span>{c.revised?"Revised FDA target":"Original FDA target"} · {c.eventTargetDate} · T−79 {c.current.calendarEntryDate} · {c.finalTargetKnownAtFinalT79Entry?"dated source exists":"entry blocked"}</span>
     <i aria-hidden="true">▸</i>
    </summary>
    <div className={css.metricBody}>
     <div className={css.reviewGrid}>
      <div><span>Original publicly stated goal</span>
       <strong>{c.initialGoalDate} · first dated announcement {c.initialGoalAnnouncementDate}</strong></div>
      <div><span>Original T−79 → T−14 calendar window</span>
       <strong>{c.initial.calendarEntryDate} → {c.initial.calendarExitDate}</strong></div>
      <div><span>{c.revised?"Revised":"Current saved"} goal and announced-on date</span>
       <strong>{c.eventTargetDate} · {c.revised?c.revisedGoalAnnouncementDate:c.initialGoalAnnouncementDate}</strong></div>
      <div><span>Current T−79 → T−14 calendar window</span>
       <strong>{c.current.calendarEntryDate} → {c.current.calendarExitDate}</strong></div>
      <div><span>Indicative Nasdaq regular sessions · enter next / exit prior</span>
       <strong>{c.current.indicativeEntrySessionDate} → {c.current.indicativeExitSessionDate}</strong></div>
      <div><span>Calendar-to-session adjustment</span>
       <strong>Entry +{c.current.entrySessionShiftCalendarDays} days · exit {c.current.exitSessionShiftCalendarDays} days</strong></div>
      <div><span>Abbreviated session close flags</span>
       <strong>Entry {c.current.entrySessionIsEarlyClose?"early close":"normal calendar"} · exit {c.current.exitSessionIsEarlyClose?"early close":"normal calendar"}</strong></div>
      <div><span>FDA goal revision, calendar day shift</span>
       <strong>{c.sourceShiftCalendarDays} days</strong></div>
      <div><span>Pre-entry source gate for post-3-5 / post-6-1</span>
       <strong>{c.reviewState==="POINT_IN_TIME_SOURCE_LEAD_ONLY"?"Issuer source known; not graded":"BLOCKED — announcement/evidence not known at entry"}</strong></div>
     </div>
     <p className={css.muted}><strong>Original source:</strong> {c.initialGoalSourceUrl?
      <a href={c.initialGoalSourceUrl} target="_blank" rel="noopener noreferrer">Open dated original announcement</a>:
      "No separate original announcement URL retained; historical attribution not independently verified."}</p>
     {c.revised&&c.revisedGoalSourceUrl&&<p className={css.muted}><strong>Target revision:</strong> <a href={c.revisedGoalSourceUrl} target="_blank" rel="noopener noreferrer">Open dated revised target source</a> · originally announced target moved {c.sourceShiftCalendarDays} calendar days.</p>}
     <p className={css.muted}><strong>Phase 3 public-result source listed:</strong> {c.phase3ReadoutListedDate} · <a href={c.phase3ReadoutSourceUrl} target="_blank" rel="noopener noreferrer">Original clinical source</a>. Independently audited source publication chronology: <strong>not complete</strong>.</p>
     {(c.current.entryIsWeekend||c.current.exitIsWeekend)&&<p className={css.notice}>At least one proposed T−79/T−14 date is a weekend. Exact trading-session normalization, real price verification and slippage are required before any return claim.</p>}
     <p className={css.muted}><strong>Market-session limitations:</strong> Session dates are calendar proposals, not proof of ticker-level open trading, independent daily bars, adjusted prices, slippage, financing or market cap. Verify actual Alpaca/independent price data before any return comparison.</p>
     <p className={css.muted}><strong>Metric-grade status:</strong> —/100 for post-3-5 and post-6-1. Post-6-2 cannot be graded using calendar dates alone. Historical outcome decisions have not been used in this source-time calculation.</p>
    </div>
  </details>)}
 </section>;
}
/** Historical SEC shares only, never an approved 2024/25 PDUFA capitalization score. */
function SECAsOfHistory(){
 const audit=activeSECAsOfEntryShares();
 return <section id="raas-sec-entry-asof" className={css.context}
  data-raas-sec-entry-asof="research-only">
  <h2>Legacy single-window SEC share-source example · proposed T−79 (not preferred)</h2>
  <p><strong>{audit.coverFactsPublicAtProposedEntry}/{audit.caseCount}</strong> cases have a dated, pre-entry SEC share-count source lead. <strong>{audit.laterSnapshotsUnavailableAtEntry}</strong> later cover filings cannot be used at their proposed entry. <strong>0</strong> independently verified entry market caps; <strong>0</strong> independently verified adjusted entry/exit price pairs.</p>
  <p className={css.notice}>A historical cover-page share count is a dated disclosure, not a continuous or fully diluted day-of-trade share count. The $300 million–$10 billion market-cap restriction is still <strong>unverified</strong> for every case. Revised targets and proposed Nasdaq sessions are handled by the separate goal-date audit above.</p>
  {audit.rows.map(x=><details key={x.caseId} className={css.group} data-raas-sec-entry-case={x.ticker}>
   <summary><strong>{x.ticker} · {x.application}</strong>
    <span>Proposed entry {x.proposedEntrySession} · {x.currentSECShares===null?"SEC source missing":x.currentSECShares.toLocaleString("en-US")+" dated SEC shares (not verified cap)"}</span>
    <i aria-hidden="true">▸</i>
   </summary>
   <div className={css.metricBody}>
    <div className={css.reviewGrid}>
     <div><span>Proposed entry → exit regular sessions</span>
      <strong>{x.proposedEntrySession} → {x.proposedExitSession}</strong></div>
     <div><span>Cover-page outstanding common shares available at entry</span>
      <strong>{x.currentSECShares?.toLocaleString("en-US")??"No eligible pre-entry SEC source"}</strong></div>
     <div><span>Share-count observation date → conservative first public use</span>
      <strong>{x.currentSECSharesMeasurementDate??"—"} → {x.currentSECFirstConservativeUse??"—"}</strong></div>
     <div><span>Share measurement age at proposed entry</span>
      <strong>{x.currentSECDisclosureAgeDays===null?"—":x.currentSECDisclosureAgeDays+" calendar days"}</strong></div>
     <div><span>Earlier / later saved SEC share observations</span>
      <strong>{x.earlierCoverShares.toLocaleString("en-US")} / {x.laterCoverShares.toLocaleString("en-US")}</strong></div>
     <div><span>Later SEC source usable at original entry?</span>
      <strong>{x.laterCoverAvailableAtEntry?"Yes, conservative as-of date passed":"No — later filing excluded from entry source"}</strong></div>
     <div><span>Same-day market cap eligibility</span><strong>Unverified · no USD calculation promoted</strong></div>
     <div><span>Independent adjusted entry/exit prices</span><strong>Not verified · return and RAAS score withheld</strong></div>
    </div>
    <p className={css.muted}>Earlier cover shares <a href={x.earlierSECUrl} target="_blank" rel="noopener noreferrer">SEC filing</a> · Later cover shares <a href={x.laterSECUrl} target="_blank" rel="noopener noreferrer">SEC filing</a>{x.currentSECSourceUrl?<> · <a href={x.currentSECSourceUrl} target="_blank" rel="noopener noreferrer">Source eligible at proposed entry</a></>:""}</p>
    <p className={css.notice}>Source review still required: exact-day common share continuity, splits and financing, independent adjusted vendor closes and full FDA event census. Later cover difference: {x.shareSnapshotDifference.toLocaleString("en-US")} shares; this is not a proven change on the entry day.</p>
   </div>
  </details>)}
 </section>;
}
export default async function RaasWorklistPage({searchParams}:{searchParams:Promise<Params>}){
 const q=await searchParams;
 const anchorStage:RaasStage=first(q.stage)==="post"?"post":"pre";
 const rawNct=first(q.nctId),rawTicker=first(q.ticker);
 const trial= /^NCT\d{8}$/.test(rawNct)&&/^[A-Z0-9.\-]{1,12}$/.test(rawTicker)?
  {nctId:rawNct,ticker:rawTicker,drug:safe(first(q.drug)),indication:safe(first(q.indication))}:null;
 const invalidContext=!!(rawNct||rawTicker)&&trial===null;
 const data=buildRaasMetricValidationWorklist(trial);
 const available=raasDocumentedTrialOptions();
 return <main className={css.root} data-raas-validation-worklist={data.scope}>
  <header className={css.header}>
   <Link href="/tools" className={css.back}>← TOP / BOTTOM spreadsheets</Link>
   <h1>RAAS · 60-metric validation worklist</h1>
   <p>Thirty TOP pre-readout metrics and thirty BOTTOM post-readout metrics, each with its required source, current evidence leads, missing verification and calibration status.</p>
  </header>
  <div className={css.stats}>
   <div><strong>60 / 60</strong><span>Metric requirements inventoried</span></div>
   <div><strong>{data.approvedCalibrations} / 60</strong><span>Independently approved calibrations</span></div>
   <div><strong>{data.sourceMappedMetrics} / 60</strong><span>{trial?"Source-mapped metric areas for the selected trial across both stages":"Source-mapped areas in saved research across both stages"}</span></div>
   <div><strong>— / 100</strong><span>Overall RAAS remains unapproved</span></div>
  </div>
  <p className={css.notice}><strong>Research worklist, not a trading score.</strong> A single source lead does not establish a verified metric assessment, FDA approval probability, or expected stock appreciation. Missing evidence receives no 0/100 grade. Snapshot: {data.sourceAsOf}; all 60 metrics remain subject to historical holdout and source-time checks.</p>
  <nav className={css.stageNav} aria-label="Jump to TOP or BOTTOM RAAS metrics">
   <Link href={hrefForTrial(trial,"pre")} aria-current={anchorStage==="pre"?"location":undefined}>TOP · 30 metrics</Link>
   <Link href={hrefForTrial(trial,"post")} aria-current={anchorStage==="post"?"location":undefined}>BOTTOM · 30 metrics</Link>
   <Link href="/raas-scan">Full 60-metric readiness scan</Link>
  </nav>
  <FullRange903History/>
  <ExpandedHistoricalCandidates/>
  <GoalAsOfHistory/>
  <SECAsOfHistory/>
  <section className={css.context} aria-label="Trial source filter">
   <h2>Evidence context</h2>
   {invalidContext&&<p className={css.notice}>Invalid trial identity in the URL. Showing global source examples; no trial-specific score is inferred.</p>}
   <p>{trial?
    <>Exact trial <strong>{trial.ticker} · {trial.nctId}</strong>{trial.drug?" · "+trial.drug:""}{trial.indication?" · "+trial.indication:""}. Sources are matched by NCT, issuer, stage and supplied therapy identity.</>:
    <>All saved example programs. A source attached to another trial is never an approved grade or a source for the trial you are researching.</>}</p>
   <div className={css.trials}>
    <Link href="/raas-worklist" className={!trial?css.selected:undefined}>All source examples</Link>
    {available.map(t=><Link key={(t.stage||"")+"|"+t.nctId+"|"+t.ticker}
      href={hrefForTrial(t,t.stage||"pre")}
      className={trial?.nctId===t.nctId&&trial.ticker===t.ticker?css.selected:undefined}>
      {t.stage==="pre"?"TOP":"BOTTOM"} · {t.ticker} · {t.nctId}
     </Link>)}
   </div>
  </section>
  {(["pre","post"] as const).map(stage=>{
   const stageItems=data.items.filter(x=>x.stage===stage);
   const stats=data.byStage[stage];
   const groups=[...new Map(stageItems.map(x=>[x.groupId,{id:x.groupId,name:x.group,weight:x.groupWeight}])).values()];
   return <section id={"raas-"+(stage==="pre"?"top":"bottom")+"-worklist"} className={css.stage} key={stage}
    data-raas-worklist-stage={stage}>
    <div className={css.stageTitle}>
     <div><span className={css.eyebrow}>{stage==="pre"?"TOP · BEFORE PHASE 3 RESULTS":"BOTTOM · AFTER PHASE 3 RESULTS"}</span>
      <h2>{stage==="pre"?"TOP-RAAS":"BOTTOM-RAAS"} · all 30 metrics</h2></div>
     <strong>{stats.mapped}/30 linked to source examples · {stats.calibrated}/30 calibrated</strong>
    </div>
    <p className={css.muted}>Six scored categories, each with five metric requirements. Expand any category and then any metric to inspect source evidence, blockers and the exact requirements for approval.</p>
    {groups.map(group=>{
     const g=stageItems.filter(x=>x.groupId===group.id);
     const linked=g.filter(x=>x.sourceCount>0).length;
     return <details key={group.id} className={css.group} data-raas-validation-group={stage+"|"+group.id}>
      <summary><strong>{group.name}</strong><span>{linked}/5 source-linked · {group.weight}% category weight · 0 approved trial grades</span><i aria-hidden="true">▸</i></summary>
      <div className={css.groupBody}>
       {g.map(metric=><details key={metric.id} className={css.metric}
         data-raas-validation-metric={metric.id}>
        <summary>
         <span className={css.metricName}><small>{metric.id}</small><strong>{metric.name}</strong></span>
         <span className={metric.sourceCount?css.sourceLinked:css.sourceMissing}>{metric.sourceCount?metric.sourceCount+" source lead(s)":"No mapped sources"}</span>
         <span className={css.unapproved}>Grade pending</span>
         <i aria-hidden="true">▸</i>
        </summary>
        <div className={css.metricBody}>
         <div className={css.infoRow}><strong>Required evidence</strong><p>{metric.requiredEvidence}</p></div>
         <div className={css.infoRow}><strong>Proposed scoring interpretation (not calibrated)</strong><p>{metric.scoreRule}</p></div>
         <div className={css.infoRow}><strong>Critical risk to investigate</strong><p>{metric.criticalRisk}</p></div>
         <div className={css.infoRow}><strong>Preliminary assessment</strong><p>{metric.sourceCount?"Dated research leads identified; effect, quality, uncertainty and rating still unreviewed.":"No metric-specific lead in the selected saved source context. Nothing has been graded."}</p></div>
         <div className={css.reviewGrid}>
          <div><span>Validated metric score</span><strong>— / 100 · pending</strong></div>
          <div><span>Calibration approval</span><strong>{metric.calibrationApproved?"Approved, trial assessment still pending":"Not approved"}</strong></div>
          <div><span>Issuer-disjoint train / holdout</span><strong>{metric.historicalTrainIssuers} / 30 · {metric.historicalHoldoutIssuers} / 30</strong></div>
          <div><span>Held-out high / low groups</span><strong>{metric.historicalHighHoldoutIssuers} / 5 · {metric.historicalLowHoldoutIssuers} / 5</strong></div>
         </div>
         {["post-3-5","post-6-1","post-6-2"].includes(metric.id)&&<p><a href="#raas-pdufa-asof-history">Review 2024–2025 original vs revised PDUFA goal dates, evidence known at entry and trading-session gaps (historical research only)</a></p>}
         <h4>Recorded metric-specific sources · {metric.sourceCount}</h4>
         {metric.sourceLeads.length===0?<p className={css.muted}>No dated source linked to this metric for the selected context. Other trials' evidence is not substituted.</p>:
          <ul className={css.evidenceList}>{metric.sourceLeads.map(source=>
           <li key={source.origin+"|"+source.nctId+"|"+source.id}>
            <strong>{source.ticker} · {source.nctId} · {source.title}</strong>
            <span>{source.date} · {source.origin==="PROSPECTIVE"?"Recorded prospective source lead":"Historical pilot observation"}</span>
            <p>{source.note}</p>
            <a href={source.sourceUrl} target="_blank" rel="noopener noreferrer">Open dated source</a>
           </li>)}</ul>}
         <h4>What is missing before an approved grade?</h4>
         <ol className={css.missingList}>{metric.missingRequirements.map((s,i)=><li key={i}>{s}</li>)}</ol>
         <p className={css.muted}><strong>Historical audit:</strong> {metric.readinessReason}</p>
        </div>
       </details>)}
      </div>
     </details>;
    })}
   </section>;
  })}
  <footer className={css.footer}>
   <strong>Release gate: not passed</strong>
   <p>Historical FDA target-year census, same-issuer share continuity, independent price confirmation, predeclared metric thresholds, 30/30 disjoint holdout and exact trial reviews are still required. This page is generated from the dated, committed RAAS research feeds; it does not claim live FDA or brokerage market updates.</p>
   <Link href="/tools#tools-phase3-release-sheets">Return to TOP and BOTTOM spreadsheets</Link>
  </footer>
 </main>;
}
