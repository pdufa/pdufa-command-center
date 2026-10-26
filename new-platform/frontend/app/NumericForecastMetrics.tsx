"use client";

import type { AssessmentDetail, AssessmentStage } from "../lib/candidate-assessments";
import type { CSSProperties } from "react";
import type { NumericForecastDisplay } from "../lib/numeric-forecast-metrics";
import { stageLabel } from "../lib/candidate-assessments";
import { createNumericForecastDisplay, HISTORICAL_SIMILARITY_DIMENSIONS } from "../lib/numeric-forecast-metrics";
import PredictionPriorityMetrics from "./PredictionPriorityMetrics";

const fmt = (n:number) => Number(n.toFixed(1)).toLocaleString("en-US");
const fraction = (n:number | null, denominator:number) => (n === null ? "—" : fmt(n)) + " / " + fmt(denominator);
const numericCard: CSSProperties = {
  minWidth:0, padding:"12px 14px", border:"1px solid #cbd5e1", borderRadius:10, background:"#fff",
};
const muted: CSSProperties = {fontSize:12,color:"#475569",lineHeight:1.5};

export default function NumericForecastMetrics({detail,stage}: {detail:AssessmentDetail;stage:AssessmentStage}) {
  let current: NumericForecastDisplay;
  try {
    current = createNumericForecastDisplay(detail,stage);
  } catch {
    return <section className="panel" role="status" aria-label="Numerical trial forecast metrics">
      <h3>Numerical trial research ratings</h3>
      <p>Exact-trial metric totals cannot be reconciled. Ratings have been withheld rather than guessed.</p>
    </section>;
  }
  const cards = [
    {label:"Recorded research model score",value:fraction(current.researchModelScore,100),note:"Only when all 7/7 categories are completely scored"},
    {label:"Observed points (partial research)",value:fraction(current.observedResearchPoints,100),note:"Not a complete score or FDA approval probability"},
    {label:"Evidence coverage",value:fraction(current.evidenceCoverageOutOf100,100),note:"Points of evidence assessed, not predicted success"},
    {label:"Fully rated research metrics",value:current.completeCategories+" / "+current.categoryTotal,note:"A zero score counts only when evidence was actually reviewed"},
    {label:"Historical comparable trials",value:"— / —",note:"Exact, independently matched comparison cohort not established"},
    {label:"SCIENCE-40 investigations",value:fraction(current.scientificAssessmentCount,current.scientificAssessmentDenominator),note:"Separate from the existing seven-category scoring model"},
    {label:"Readiness numerical grade",value:fraction(current.readinessGradeOutOf100,100),note:"Awaiting defensible source-backed grading criteria"},
    {label:"Reluctance numerical grade",value:fraction(current.reluctanceGradeOutOf100,100),note:"Unresolved-risk grade not yet independently derived"},
  ];
  const primaryCards = cards.slice(0,4);
  const secondaryCards = cards.slice(4);
  return <section className="panel" aria-label="Numerical trial forecast metrics" style={{margin:"14px 0",border:"1px solid #94a3b8",borderRadius:12}}>
    <div className="sectionhead">
      <div>
        <h3 style={{marginBottom:4}}>Numerical trial ratings — preliminary research</h3>
        <p style={{margin:0}}><strong>{stageLabel(stage)}</strong> · source model {current.modelVersion} · assessed {current.asOf} · exact trial {detail.nctId || detail.id}</p>
      </div>
    </div>
    <p style={{margin:"10px 0",fontSize:13}}>
      <strong>Historical-comparable forecast: NOT YET SCORED.</strong> These are existing numerical research measurements, not a modeled chance of FDA approval. Unknown values appear as <strong>—</strong>; observed zero is displayed as <strong>0</strong>.
    </p>
    <p role="status" style={{marginTop:10,padding:11,border:"1px solid #cbd5e1",borderRadius:8,background:"#f8fafc"}}>
      <strong>FDA approval probability: — / 100% (not validated).</strong> Historical FDA review-cycle adjudication and predictive calibration remain incomplete. No trading or FS/FA changes are authorized.
    </p>
    <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(min(100%,200px),1fr))",gap:10,margin:"14px 0"}}>
      {primaryCards.map(c=><div key={c.label} style={numericCard}>
        <div style={muted}>{c.label}</div>
        <strong style={{fontSize:22,fontVariantNumeric:"tabular-nums",display:"block",margin:"7px 0"}}>{c.value}</strong>
        <small style={muted}>{c.note}</small>
      </div>)}
    </div>
    <PredictionPriorityMetrics/>
    <details style={{marginTop:15,border:"1px solid #cbd5e1",borderRadius:9,padding:"9px 12px"}}>
      <summary style={{cursor:"pointer",fontWeight:700}}>Existing research scores — 7 metrics · {current.completeCategories} / {current.categoryTotal} fully rated</summary>
      <h4>Underlying metric ratings — 0 to 100 scale</h4>
    <div className="table-scroll">
      <table style={{width:"100%",fontVariantNumeric:"tabular-nums"}}>
        <thead><tr>
          <th scope="col">Research metric</th>
          <th scope="col">Numerical rating</th>
          <th scope="col">Earned / available points</th>
          <th scope="col">Evidence assessed / required</th>
          <th scope="col">Measurements assessed / total</th>
          <th scope="col">State</th>
        </tr></thead>
        <tbody>{current.metrics.map(metric=><tr key={metric.id}>
          <th scope="row" style={{textAlign:"left",maxWidth:220}}>{metric.id} · {metric.label}</th>
          <td><strong>{fraction(metric.ratingOutOf100,100)}</strong></td>
          <td>{fraction(metric.points,metric.maximum)}</td>
          <td>{fraction(metric.evidencePoints,metric.maximum)}</td>
          <td>{metric.reviewedMeasurements} / {metric.totalMeasurements}</td>
          <td>{metric.complete?"Complete research metric":"Incomplete · "+metric.status}</td>
        </tr>)}</tbody>
      </table>
    </div>
    <p style={{...muted,marginTop:8}}>
      Numerical rating = recorded complete category points ÷ category maximum × 100. If its evidence is incomplete, the rating is withheld even when observed partial points are nonzero.
      The original evidence, rules, source dates and per-measurement scores remain in the expandable assessment tables below.
    </p>
    </details>
    <details style={{marginTop:15,border:"1px solid #cbd5e1",borderRadius:9,padding:"9px 12px"}}>
      <summary style={{cursor:"pointer",fontWeight:700}}>Additional research and readiness metrics — 4 items</summary>
      <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(min(100%,200px),1fr))",gap:10,margin:"14px 0"}}>
        {secondaryCards.map(c=><div key={c.label} style={numericCard}>
          <div style={muted}>{c.label}</div>
          <strong style={{fontSize:22,fontVariantNumeric:"tabular-nums",display:"block",margin:"7px 0"}}>{c.value}</strong>
          <small style={muted}>{c.note}</small>
        </div>)}
      </div>
    </details>
    <details style={{marginTop:15,border:"1px solid #cbd5e1",borderRadius:9,padding:"9px 12px"}}>
      <summary style={{cursor:"pointer",fontWeight:700}}>Historical comparable scoring — {HISTORICAL_SIMILARITY_DIMENSIONS.length} dimensions, awaiting verified trial matches</summary>
      <p style={muted}>The eventual historical comparison must match on exact disease, mechanism, population, design, endpoints, clinical results, safety and FDA precedent. No historical trial similarity rating is assigned without reviewed comparator evidence and a documented scoring method.</p>
      <div className="table-scroll"><table>
        <thead><tr><th>Historical similarity metric</th><th>Numerical rating</th><th>Verified comparisons</th></tr></thead>
        <tbody>{HISTORICAL_SIMILARITY_DIMENSIONS.map((label,i)=><tr key={label}><td>{i+1}/8 · {label}</td><td><strong>— / 100</strong></td><td>— / —</td></tr>)}</tbody>
      </table></div>
    </details>

  </section>;
}
