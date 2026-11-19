const protocol = "CANONICAL_HISTORICAL_FDA_DIRECTION_V1";
const ruleSet = "SCIENTIFIC_L01_L06_HISTORICAL_DIRECTION_V1";
const levels = ["L01", "L02", "L03", "L04", "L05", "L06"] as const;
const levelNames = [
  "Trial identity", "Study design", "Statistics and efficacy", "Safety",
  "Indication-specific relevance", "Regulatory readiness",
];

type SummaryRow = {
  level: (typeof levels)[number];
  events: number;
  predicted: number;
  abstained: number;
  correct: number;
  incorrect: number;
  coverage: number;
  accuracy: number | null;
  accuracy_ci95_wilson_low: number | null;
  accuracy_ci95_wilson_high: number | null;
  protocol: string;
  rule_set: string;
  lock_sha256: string;
};

type VerifiedEvaluation = {
  /** Vetted cohort label, e.g. "Verified subset, January to November 2026". */
  cohortLabel: string;
  eligibleEvents: number;
  /** Read from the independently retained prediction receipt. */
  lockSha256: string;
  /** Aggregate post-lock score report. Keep case data in outcome quarantine. */
  summary: unknown;
};

const integer = (value: unknown): value is number =>
  typeof value === "number" && Number.isSafeInteger(value) && value >= 0;
const proportion = (value: unknown): value is number =>
  typeof value === "number" && Number.isFinite(value) && value >= 0 && value <= 1;
const percent = (value: number) => `${(100 * value).toFixed(1)}%`;

function reportRows(evaluation: VerifiedEvaluation): SummaryRow[] | null {
  const {cohortLabel, eligibleEvents, lockSha256, summary} = evaluation;
  if (!cohortLabel.trim() || !integer(eligibleEvents) || eligibleEvents === 0 ||
      !/^[0-9a-f]{64}$/.test(lockSha256) || !Array.isArray(summary) ||
      summary.length !== levels.length) return null;

  const rows = [];
  for (const level of levels) {
    const row = summary.find(item => item && typeof item === "object" && item.level === level);
    if (!row || row.protocol !== protocol || row.rule_set !== ruleSet ||
        row.lock_sha256 !== lockSha256 || row.events !== eligibleEvents) return null;

    const {predicted, abstained, correct, incorrect, coverage, accuracy} = row;
    const low = row.accuracy_ci95_wilson_low, high = row.accuracy_ci95_wilson_high;
    if (!integer(predicted) || !integer(abstained) || !integer(correct) ||
        !integer(incorrect) || predicted + abstained !== eligibleEvents ||
        correct + incorrect !== predicted || coverage !== predicted / eligibleEvents) return null;
    if (predicted === 0) {
      if (accuracy !== null || low !== null || high !== null) return null;
    } else if (!proportion(accuracy) || accuracy !== correct / predicted ||
               !proportion(low) || !proportion(high) || low > accuracy || high < accuracy) {
      return null;
    }
    rows.push(row as SummaryRow);
  }
  return rows;
}

export default function HistoricalScientificBacktest({
  surface,
  evaluation,
}: {
  surface: "POOL" | "FOCUS" | "PAST" | "ASSESSMENTS";
  evaluation?: VerifiedEvaluation;
}) {
  const rows = evaluation ? reportRows(evaluation) : null;
  return <section className="panel" id="historical-fda-backtest" aria-labelledby="historical-fda-backtest-title">
    <h2 id="historical-fda-backtest-title">2026 historical FDA backtest</h2>
    {rows && evaluation
      ? <p>{evaluation.cohortLabel} · {evaluation.eligibleEvents} eligible FDA {evaluation.eligibleEvents === 1 ? "action" : "actions"}</p>
      : <p>Verified historical accuracy is unavailable.</p>}
    {(surface === "POOL" || surface === "FOCUS") && <p><a href="/past#historical-fda-backtest">View historical cohort on PAST</a></p>}
    {surface === "PAST" && rows && <p><a href="/assessments#historical-fda-backtest">View level results on ASSESSMENTS</a></p>}
    {surface === "ASSESSMENTS" && rows && <div style={{overflowX:"auto"}}>
      <table>
        <caption>FDA direction by scientific level · {ruleSet}</caption>
        <thead><tr>
          <th scope="col">Scientific level</th><th scope="col">Answered</th>
          <th scope="col">Correct</th><th scope="col">Incorrect</th>
          <th scope="col">Abstained</th><th scope="col">Coverage</th>
          <th scope="col">Accuracy</th><th scope="col">95% Wilson interval</th>
        </tr></thead>
        <tbody>{rows.map((row, index) => <tr key={row.level}>
          <th scope="row">{row.level} · {levelNames[index]}</th>
          <td>{row.predicted} / {row.events}</td><td>{row.correct}</td>
          <td>{row.incorrect}</td><td>{row.abstained}</td><td>{percent(row.coverage)}</td>
          <td>{row.accuracy === null ? "Unavailable" : percent(row.accuracy)}</td>
          <td>{row.accuracy_ci95_wilson_low === null || row.accuracy_ci95_wilson_high === null
            ? "Unavailable"
            : `${percent(row.accuracy_ci95_wilson_low)}–${percent(row.accuracy_ci95_wilson_high)}`}</td>
        </tr>)}</tbody>
      </table>
    </div>}
  </section>;
}
