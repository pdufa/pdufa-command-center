"use client";

import { goalDailyHistory, type GoalDaySection } from "../lib/goal-daily-history";
import styles from "./GoalDailyHistory.module.css";

type Props = {daily:unknown;loading:boolean;error?:string};
function value(number:number|null):string {
  return number===null?"—":number.toLocaleString("en-US");
}
function stage(item:GoalDaySection):string {
  return value(item.total)+" / "+value(item.new);
}
export default function GoalDailyHistory({daily,loading,error}:Props) {
  const rows=goalDailyHistory(daily);
  return <section className={styles.history} aria-label="GOAL dated scan history">
    <details className={styles.details}>
      <summary className={styles.summary}>
        <span>Daily scan history · recorded totals</span>
        <small>{loading?"Reading ledger…":rows.length+" published day"+(rows.length===1?"":"s")} · Expand ▾</small>
      </summary>
      <div className={styles.body}>
        <p className={styles.explainer}>Counts are saved against each Pacific calendar date and its original GitHub run.
          These are historical source snapshots, not a new scan. “Total / new” in stage columns
          are historical reported inventory values, <strong>not</strong> newly qualified trials.
          Changed master records are not new trials.</p>
        {rows.length ? <div className={styles.scroll}><table>
          <thead><tr>
            <th>Date (Pacific)</th><th>Published status</th>
            <th>Tracked trials total</th><th>Tracked changed</th><th>New trials</th>
            <th>Pipeline total / new</th><th>FDA designations total / new</th>
            <th>Original run</th>
          </tr></thead>
          <tbody>{rows.map(day=><tr key={day.date}>
            <th scope="row">{day.date}{day.today?" · Today":""}</th>
            <td><span className={day.status==="PARTIAL"?styles.partial:day.status==="RUN_FAILED"?styles.failed:styles.complete}>
              {day.status==="PARTIAL"?"Partial evidence":day.status==="RUN_FAILED"?"Run failed":"Published complete"}
            </span></td>
            <td>{value(day.master.total)}</td><td>{value(day.master.updated)}</td>
            <td>{value(day.master.new)}</td>
            <td>{stage(day.pipeline)}</td><td>{stage(day.designations)}</td>
            <td><a href={day.runUrl} target="_blank" rel="noopener noreferrer">#{day.runId} ↗</a></td>
          </tr>)}</tbody>
        </table></div> :
          <p className={styles.empty}>{loading?"Checking the saved daily ledger…":
            error||"No valid dated ledger entries are available."}</p>}
        <p className={styles.note}>— means unavailable or not independently established, never zero.
          A completed GitHub run does not certify FDA, SEC, market, or financing coverage.
          Run failures withhold all numeric values. There is no trial scoring or trading action here.</p>
      </div>
    </details>
  </section>;
}
