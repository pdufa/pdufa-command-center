import baseline from "../data/focusScientificBaseline20261119.json";

const levels = [
  ["L01", "Trial identity"], ["L02", "Trial design"], ["L03", "Statistics and efficacy"],
  ["L04", "Safety"], ["L05", "Indication relevance"], ["L06", "Regulatory readiness"],
] as const;

const statuses: Record<string, { label: string; color: string }> = {
  INTAKE_ONLY: { label: "Registry intake", color: "#e1f0fb" },
  PARTIAL: { label: "Partial findings", color: "#e1f3e8" },
  AWAITING_REVIEW: { label: "Awaiting review", color: "#f3eee3" },
};

export default function FocusScientificCoverageChart() {
  return <figure id="focus-six-level-chart" aria-labelledby="focus-six-level-title" style={{margin:"18px 0"}}>
    <figcaption id="focus-six-level-title"><strong>FOCUS assessment chart · Levels 1–6</strong></figcaption>
    <p>{baseline.trialCount} trials · <time dateTime={baseline.assessmentDate}>{baseline.assessmentDate}</time> · Evidence review status</p>
    <div style={{overflowX:"auto"}}>
      <table style={{width:"100%",minWidth:760,borderSpacing:4}}>
        <thead><tr><th scope="col">Trial</th>{levels.map(([id,label]) =>
          <th key={id} scope="col">{id} · {label}</th>
        )}</tr></thead>
        <tbody>{baseline.trials.map(trial => <tr key={trial.nct}>
          <th scope="row" style={{textAlign:"left",whiteSpace:"nowrap"}}>{trial.ticker} · {trial.nct}</th>
          {levels.map(([id],index) => {
            const status = statuses[trial.status[index]];
            return <td key={id} style={{padding:"5px 8px",background:status?.color ?? "#f3eee3"}}>
              {status?.label ?? "Awaiting review"}
            </td>;
          })}
        </tr>)}</tbody>
      </table>
    </div>
  </figure>;
}
