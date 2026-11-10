"use client";
import {useMemo,useState} from "react";
import Link from "next/link";
import {FOCUS_R62_APPLICATION_SOURCE_REVIEW} from "../../lib/focus-r62-application-source-review";
import styles from "./FocusOriginalSourceChallengeR60.module.css";

/** Display only; never reads live source or accepts reviewer grades. */
export default function FocusApplicationSourceReviewR62(){
  const report=FOCUS_R62_APPLICATION_SOURCE_REVIEW;
  const [search,setSearch]=useState("");
  const [coverage,setCoverage]=useState("ALL");
  const term=search.trim().toLowerCase();
  const rows=report?.rows??[];
  const visible=useMemo(()=>rows.filter(x=>{
    const text=[x.ticker,x.id,x.drug,x.indication,
      ...x.linkedTrials.map(t=>t.nct)].join(" ").toLowerCase();
    const matched=!term||text.includes(term);
    const filter=coverage==="ALL"||
      coverage==="POSTED"&&x.currentPrimaryTrialCount>0||
      coverage==="RECOVERY"&&x.currentPrimaryTrialCount<x.linkedNctCount||
      coverage==="EXCEPTIONS"&&x.originalSourceExceptionCount>0;
    return matched&&filter;
  }),[rows,term,coverage]);

  if(!report)return <section className={styles.panel}
    aria-label="R62 application research evidence">
    <h2>Application-level evidence review</h2>
    <p role="alert">Exact NCT/application source membership has not passed verification;
      application findings are withheld.</p>
  </section>;

  return <section className={styles.panel} aria-label="R62 provisional application source review">
    <div className={styles.eyebrow}>MAIN · REVISION 62 · PHASE-FIRST RESEARCH · READ-ONLY</div>
    <h2>Application scientific evidence · 23 provisional FDA cycles</h2>
    <p>Each application expands horizontally across its linked exact-NCT trials and
      shows original posted-efficacy and safety coverage. A trial can support two
      separate applications without being counted as two independent studies.
      These are source-availability findings, <strong>not clinical grades, approval
      probabilities, FDA decisions, or verified regulatory submission statuses</strong>.</p>
    <div className={styles.stats}>
      <div className={styles.stat}><div>Application groups</div><strong>{report.provisionalApplicationGroups}</strong></div>
      <div className={styles.stat}><div>Unique source trials</div><strong>{report.uniqueTrials}</strong></div>
      <div className={styles.stat}><div>Independent clinical signoffs</div><strong>{report.qualifiedClinicalReviews}</strong></div>
      <div className={styles.stat}><div>Validated FDA forecasts</div><strong>{report.independentlyValidatedFdaForecasts}</strong></div>
    </div>
    <p className={styles.note}>Official future approval/CRL and review-delay forecasts:
      <strong> ABSTAIN</strong>. Predictive accuracy: <strong>NOT VALIDATED</strong>.
      An application marked previously approved in the preliminary roster requires
      historical action verification and is not a prospective prediction.</p>
    <div className={styles.controls}>
      <label>Find ticker, application, drug, indication or NCT
        <input aria-label="Find application source evidence" type="search" value={search}
          placeholder="e.g. SVRA or NCT04544293" onChange={e=>setSearch(e.target.value)}/>
      </label>
      <label>Source coverage
        <select aria-label="Filter application source evidence" value={coverage}
          onChange={e=>setCoverage(e.target.value)}>
          <option value="ALL">All application groups</option>
          <option value="POSTED">Current primary result available</option>
          <option value="RECOVERY">At least one primary source recovery task</option>
          <option value="EXCEPTIONS">Original-source review exceptions</option>
        </select>
      </label>
    </div>
    <div className={styles.rows}>
      {visible.map(x=><details className={styles.trial} key={x.id}>
        <summary>
          <strong>{x.ticker} · {x.drug}</strong>
          <span className={styles.countLine}>{x.linkedNctCount} NCT{ x.linkedNctCount===1?"":"s" }
            {" · "}{x.currentPrimaryTrialCount} with posted primary
            {" · "}{x.currentSafetyTrialCount} with safety arms</span>
          <span className={styles.status}>Source review · {x.id}</span>
        </summary>
        <div className={styles.details}>
          <p><strong>Indication:</strong> {x.indication}</p>
          <p className={styles.note}><strong>Provisional application stage:</strong>{" "}
            {x.sponsorReportedStageUnverified.replaceAll("_"," ").toLowerCase()}.
            The original FDA decision/review-cycle identity is not independently certified.</p>
          <h3>Linked trial evidence and original source gaps</h3>
          <div className={styles.innerList}>
            {x.linkedTrials.map(t=><div key={t.nct}>
              <strong>{t.nct}</strong>
              <p>Posted primary outcome tables: {t.currentPrimaryTables}.
                {" "}Source-reported statistical comparisons: {t.sourceReportedComparisons}.
                {" "}Current safety-arm rows: {t.currentSafetyArms}.</p>
              {t.evidenceExceptions.length?
                <p className={styles.note}>Open source checks: {t.evidenceExceptions.join(", ").replaceAll("_"," ").toLowerCase()}.
                  The absence of registry data is not a negative trial finding.</p>:
                <p className={styles.note}>No mechanical source exception. Independent
                  efficacy, safety and protocol/SAP adjudication is still pending.</p>}
              <div className={styles.links}>
                <a href={t.registryUrl} target="_blank" rel="noopener noreferrer">Original trial record</a>
                <Link href={"/predictions/assessment?nct="+t.nct+"&cycle="+x.id}>
                  Scientific assessment</Link>
              </div>
            </div>)}
          </div>
          <h3>Required reviews before any validated FDA forecast</h3>
          <ul>{x.reviewNextSteps.map((task,i)=><li key={i}>{task}</li>)}</ul>
          <p className={styles.note}>This view performs no source fetching,
            source-status modification, clinical scoring, model training, or reviewer signoff.</p>
        </div>
      </details>)}
    </div>
    {visible.length===0?<p role="status">No application group matches this search and filter.</p>:null}
    <p className={styles.footer}>Exact-NCT underlying research:{" "}
      <a href={report.sourceArchiveUrl} target="_blank" rel="noopener noreferrer">
        immutable original R60 artifact</a>.
      {" "}Application sources are provisional; all original FDA outcomes and
      qualified clinical reviews require separate verification.</p>
  </section>;
}
