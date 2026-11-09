"use client";
import {useMemo,useState} from "react";
import Link from "next/link";
import {FOCUS_R60_ORIGINAL_TRIAL_REVIEW} from "../../lib/focus-r60-original-trial-research";
import styles from "./FocusOriginalSourceChallengeR60.module.css";

const EXCEPTIONS:Record<string,string>={
  NO_CURRENT_POSTED_PRIMARY_TABLE_CHECK_OTHER_ORIGINALS:
    "Primary result table not in the current registry copy; seek sponsor, journal or FDA originals",
  NO_CURRENT_POSTED_SAFETY_ARM_TABLE_CHECK_OTHER_ORIGINALS:
    "Safety-arm table not in the current registry copy; seek other original reports",
  POSTED_PRIMARY_WITHOUT_STATISTICAL_COMPARISON:
    "A posted primary table has no statistical comparison entry",
  CURRENT_REGISTRATION_AND_POSTED_PRIMARY_TITLE_OR_TIME_DIFFER:
    "Current registered and posted primary title or time frame differ",
  STATISTICAL_COMPARISON_WITHOUT_REPORTED_P_VALUE:
    "A statistical comparison lacks a posted p-value field",
  INCOMPLETE_POSTED_SAFETY_ARM_DENOMINATOR:
    "A safety-arm affected/at-risk denominator is incomplete"
};

export default function FocusOriginalSourceChallengeR60(){
  const review=FOCUS_R60_ORIGINAL_TRIAL_REVIEW;
  const [query,setQuery]=useState("");
  const [kind,setKind]=useState("ALL");
  const [expanded,setExpanded]=useState(false);
  const normalized=query.trim().toLowerCase();
  const trials=review?.trials??[];
  const matching=useMemo(()=>trials.filter(row=>{
    const byQuery=!normalized||[row.nct,row.ticker,...row.cycles].join(" ").toLowerCase().includes(normalized);
    const byKind=kind==="ALL"?true:
      kind==="POSTED"?row.primaryTables>0:
      kind==="RECOVERY"?row.primaryTables===0:
      kind==="EXCEPTION"?row.reviewExceptions.length>0:false;
    return byQuery&&byKind;
  }),[trials,normalized,kind]);
  if(!review)return <section className={styles.panel} aria-label="R60 original scientific source audit">
    <h2>Original source investigation</h2>
    <p role="alert">The pinned source snapshot or exact 29-trial/23-application identity was not verified.
      Trial findings are withheld rather than displaying untrusted claims.</p>
  </section>;
  return <section aria-label="R60 source-verified trial findings" className={styles.panel}>
    <div className={styles.eyebrow}>MAIN · REVISION 60 ORIGINAL EVIDENCE · READ-ONLY DEVELOPMENT VIEW</div>
    <h2>Expandable scientific source findings · 29 FOCUS trials</h2>
    <p>
      Inspect original registry endpoint tables, as-reported numerical statistics,
      serious adverse-event participant denominators and missing-evidence flags.
      These are <strong>source observations, not independent statistical or safety adjudications</strong>.
      Missing current registry results do not establish that a trial failed or has no sponsor-reported data.
    </p>
    <div className={styles.stats} aria-label="Research source coverage">
      {([
        ["Unique trials",review.counts.uniqueNcts],
        ["Application cycles",review.counts.applicationGroups],
        ["Posted primary tables",review.counts.postedPrimaryTables],
        ["Statistical entries",review.counts.reportedStatisticalComparisons],
        ["Clinical signoffs",0],
        ["Validated forecasts",review.counts.independentlyValidatedFdaForecasts]
      ] as const).map(([title,val])=><div key={title} className={styles.stat}>
          <div>{title}</div><strong>{val}</strong>
        </div>)}
    </div>
    <p className={styles.note}>
      The archive also contains <strong>{review.counts.sourceReportedSeriousAeTermRows}</strong> serious-AE
      term rows and <strong>{review.counts.sourceReportedOtherAeTermRows}</strong> other-AE term rows;
      those are <em>terms, not patient counts</em>. Historical accuracy: <strong>NOT CALIBRATED</strong>.
      FDA approval/CRL and review-timing outputs: <strong>ABSTAIN</strong>.
    </p>
    <div className={styles.controls}>
      <label>Find ticker, application or exact NCT
        <input aria-label="Search original source trial findings" type="search" value={query}
          onChange={event=>setQuery(event.target.value)} placeholder="SVRA, ACHV, NCT..." />
      </label>
      <label>Source status
        <select aria-label="Filter original source findings" value={kind}
          onChange={event=>setKind(event.target.value)}>
          <option value="ALL">All 29 trials</option>
          <option value="POSTED">Current posted primary table</option>
          <option value="RECOVERY">Primary evidence recovery required</option>
          <option value="EXCEPTION">Review exception recorded</option>
        </select>
      </label>
      <button type="button" className={styles.toggle} onClick={()=>setExpanded(x=>!x)}>
        {expanded?"Collapse all findings":"Expand all findings"}
      </button>
    </div>
    <div className={styles.rows}>
      {matching.map(t=><details key={t.nct} open={expanded||undefined} className={styles.trial}>
        <summary>
          <strong>{t.ticker} · {t.nct}</strong>
          <span className={styles.countLine}>
            {t.primaryTables} primary table{t.primaryTables===1?"":"s"} · {t.reportedAnalyses} analyses · {t.safetyArms} safety arms
          </span>
          <span className={styles.status}>
            {t.primaryTables?"Reported registry data":"Other original evidence needed"}
          </span>
        </summary>
        <div className={styles.details}>
          <p><strong>Provisional application link(s):</strong> {t.cycles.join(", ")}</p>
          <h3>Original posted primary endpoint fields</h3>
          {t.endpoints.length===0?
            <p>No primary outcome result table in this archived current registry copy.
              Check original Phase 3 sponsor, journal and regulatory records.</p>:
            <div className={styles.innerList}>
              {t.endpoints.map(([title,analyses],i)=><div key={i}>
                <strong>{title}</strong>
                {analyses.length?<ul>
                  {analyses.map(([p,estimate],j)=><li key={j}>
                    Source-reported p-value: {p??"not reported"} · estimate: {estimate??"not reported"}
                  </li>)}
                </ul>:<p>No deposited statistical comparison in this primary table.</p>}
              </div>)}
            </div>}
          <h3>Original reported serious adverse-event participants</h3>
          {t.seriousAeArmAffectedAtRisk.length===0?<p>Current registry safety-arm data unavailable;
            no negative safety conclusion can be drawn.</p>:
            <ul>{t.seriousAeArmAffectedAtRisk.map(([name,counts],i)=>
              <li key={i}>{name}: <strong>{counts[0]}/{counts[1]}</strong> affected / at risk</li>)}</ul>}
          <h3>Unresolved original-evidence checks</h3>
          {t.reviewExceptions.length===0?
            <p>No mechanical source-extraction exceptions flagged. Qualified scientific review is still pending.</p>:
            <ul>{t.reviewExceptions.map((e,i)=>
              <li key={i}>{EXCEPTIONS[e]??"Unresolved original source review"}</li>)}</ul>}
          <p className={styles.note}><strong>Original JSON SHA-256:</strong> <code>{t.originalRegistrySha256}</code></p>
          <p className={styles.links}>
            <a href={t.originalRegistryUrl} target="_blank" rel="noopener noreferrer">
              Original ClinicalTrials.gov record
            </a>
            <Link href={"/predictions/assessment?nct="+t.nct}>Scientific method matrix</Link>
          </p>
          <p className={styles.note}>No patient-level recalculation, verified pre-unblinding
            protocol/SAP, CMC assessment, clinical reviewer signoff, or FDA outcome prediction is claimed.</p>
        </div>
      </details>)}
    </div>
    {matching.length===0?<p role="status">No matching trial. Change the source filters.</p>:null}
    <p className={styles.footer}>
      Original source archive recorded {review.observedAtUtc.replace("T"," ").replace("+00:00"," UTC")}.
      Read-only research snapshot from a verified development workflow.
      {" "}<a target="_blank" rel="noopener noreferrer" href={review.sourceArchiveUrl}>
        Inspect original R60 research artifact
      </a>. Not live clinical data or released forecasts.
    </p>
  </section>;
}
