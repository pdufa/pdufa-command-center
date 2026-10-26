import {
  PRIMARY_PREDICTION_METRICS,
  SECONDARY_PREDICTION_GROUPS,
  PREDICTION_METRICS,
  proposedMetricValue,
  type PredictionMetricSpec,
} from "../lib/prediction-priority-metrics";

function RankedRows({rows}: {rows: ReadonlyArray<PredictionMetricSpec>}) {
  return <tbody>{rows.map(metric=><tr key={metric.rank}>
    <th scope="row" style={{whiteSpace:"nowrap",textAlign:"left"}}>#{metric.rank}</th>
    <td>{metric.label}</td>
    <td style={{whiteSpace:"nowrap",fontVariantNumeric:"tabular-nums"}}>
      <strong>{proposedMetricValue(metric)}</strong>
    </td>
    <td>Not independently scored</td>
  </tr>)}</tbody>;
}

function RankedTable({rows}: {rows: ReadonlyArray<PredictionMetricSpec>}) {
  return <div className="table-scroll">
    <table style={{width:"100%"}}>
      <thead><tr>
        <th scope="col">Priority</th>
        <th scope="col">Prediction factor</th>
        <th scope="col">Numerical result</th>
        <th scope="col">Verification</th>
      </tr></thead>
      <RankedRows rows={rows}/>
    </table>
  </div>;
}

/**
 * Planned ranked metrics are presentation-only; they must never turn the
 * 7-category heuristic into a 60-factor or FDA probability score.
 */
export default function PredictionPriorityMetrics() {
  return <section aria-label="Prediction metric priority ranking" style={{margin:"18px 0"}}>
    <h4 style={{marginBottom:5}}>Important prediction metrics — first 12 / 60</h4>
    <p className="subtle" style={{margin:"4px 0 12px"}}>
      Highest-priority decision factors remain on screen. These 60 planned
      investigation and quality measurements are <strong>not yet independently scored</strong>.
      The recorded seven-category research scores are displayed separately below.
      Priority order is a proposed review sequence, not a statistically fitted importance weight.
    </p>
    <RankedTable rows={PRIMARY_PREDICTION_METRICS}/>
    <h4 style={{margin:"18px 0 8px"}}>Secondary prediction metrics — 48 / 60, hidden by default</h4>
    <div aria-label="Collapsible secondary prediction metrics">
      {SECONDARY_PREDICTION_GROUPS.map(group=><details key={group.start} style={{
        border:"1px solid #cbd5e1",borderRadius:9,padding:"9px 12px",margin:"8px 0",
      }}>
        <summary style={{cursor:"pointer",fontWeight:700}}>
          {group.title} · #{group.start}–{group.end} · {group.end-group.start+1} metrics
        </summary>
        <p className="subtle" style={{fontSize:12,margin:"8px 0"}}>
          Proposed numerical ratings, with verified evidence to be added. Empty results
          remain unscored rather than treated as zero or a prediction.
        </p>
        <RankedTable rows={PREDICTION_METRICS.slice(group.start-1,group.end)}/>
      </details>)}
    </div>
  </section>;
}
