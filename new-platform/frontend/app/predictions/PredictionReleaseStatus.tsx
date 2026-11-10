/** Release status only. Scientific grades and source audits cannot enable a forecast. */
export default function PredictionReleaseStatus() {
  return <section aria-labelledby="prediction-release-heading" style={{
    background: "#081d32", color: "#eef8fb", border: "1px solid #287a80",
    borderRadius: 12, padding: "clamp(16px,3vw,24px)", margin: "16px 0 22px", minWidth: 0,
  }}>
    <h2 id="prediction-release-heading" style={{fontSize: "clamp(17px,2.4vw,23px)", margin: "0 0 16px", lineHeight: 1.4}}>
      FINAL FDA PREDICTION | ACCURACY RATING
    </h2>
    <div style={{display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(min(100%,230px),1fr))", gap: 12}}>
      <div style={{background: "#102e45", borderRadius: 8, padding: 14, minWidth: 0}}>
        <h3 style={{fontSize: 13, color: "#8de3db", margin: "0 0 10px"}}>FINAL FDA PREDICTION</h3>
        <dl style={{margin: 0, display: "grid", gap: 8}}>
          {[["FDA APPROVAL", "ABSTAIN"], ["COMPLETE RESPONSE LETTER", "ABSTAIN"], ["REVIEW DELAY", "ABSTAIN"]].map(([outcome, status]) =>
            <div key={outcome} style={{display: "flex", flexWrap: "wrap", justifyContent: "space-between", gap: "4px 12px", fontSize: 13}}>
              <dt>{outcome}</dt><dd style={{margin: 0, fontWeight: 800, color: "#a6f0e5"}}>{status}</dd>
            </div>)}
        </dl>
      </div>
      <div style={{background: "#102e45", borderRadius: 8, padding: 14, minWidth: 0}}>
        <h3 style={{fontSize: 13, color: "#8de3db", margin: "0 0 10px"}}>ACCURACY RATING</h3>
        <p style={{fontSize: "clamp(20px,3vw,27px)", fontWeight: 800, margin: "0 0 10px", overflowWrap: "anywhere"}}>NOT CALIBRATED</p>
        <p style={{fontSize: 13, margin: 0}}>CERTAINTY: <strong>NOT VALIDATED</strong></p>
      </div>
    </div>
    <p style={{fontSize: 13, lineHeight: 1.6, margin: "14px 0 0", color: "#c1dbe5"}}>
      These are separate release gates. Source collection, an 800-method audit, or a scientific evidence-strength grade does not establish FDA outcome probability or measured forecast accuracy.
      Select an exact FOCUS trial below to inspect its live evidence and review history.
    </p>
  </section>;
}
