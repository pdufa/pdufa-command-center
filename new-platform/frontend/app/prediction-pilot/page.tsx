import type { Metadata } from "next";
import {PREDICTION_METRICS,SECONDARY_PREDICTION_GROUPS,proposedMetricValue} from "../../lib/prediction-priority-metrics";
import {
  PEAK_PILOT,PEAK_SOURCES,PEAK_PILOT_METRICS,
  PEAK_HISTORICAL_PRECEDENTS,PEAK_SOURCE_COVERAGE,validatePeakPilot
} from "../../lib/peak-prediction-pilot";

export const metadata: Metadata = {
  title: "COGT PEAK · Real-trial Prediction Research Pilot | PDUFA",
  description: "Read-only real clinical trial evidence and historical comparable preview, frozen October 26 2026; no validated FDA probability.",
};
export const dynamic = "force-static";
validatePeakPilot();

const card = {border:"1px solid #b7c9d3",borderRadius:12,padding:"14px",background:"#fff"} as const;
const gap = {display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(min(100%,190px),1fr))",gap:10} as const;
const subtle = {color:"#475569",fontSize:13,lineHeight:1.5} as const;
const table = {width:"100%",fontVariantNumeric:"tabular-nums",borderCollapse:"collapse" as const};
const th = {textAlign:"left" as const,padding:"8px",borderBottom:"1px solid #b7c9d3"};
const td = {padding:"9px 8px",borderBottom:"1px solid #e2e8f0",verticalAlign:"top" as const};
const pill = {border:"1px solid #94a3b8",borderRadius:999,padding:"4px 10px",whiteSpace:"nowrap" as const,fontSize:12} as const;

function Source({item}:{item:keyof typeof PEAK_SOURCES}) {
  const ref=PEAK_SOURCES[item];
  return <a href={ref.url} target="_blank" rel="noopener noreferrer">{ref.name}</a>;
}

function FactCard({label,value,detail}:{label:string;value:string;detail:string}) {
  return <div style={card}><div style={subtle}>{label}</div>
    <strong style={{display:"block",fontSize:25,fontVariantNumeric:"tabular-nums",margin:"7px 0"}}>{value}</strong>
    <small style={subtle}>{detail}</small>
  </div>;
}

export default function PeakPredictionPilot() {
  return <main className="shell" style={{maxWidth:1200,margin:"0 auto",padding:"20px clamp(12px,3vw,32px)"}}>
    <nav aria-label="Prediction pilot navigation" style={{display:"flex",flexWrap:"wrap",gap:16,margin:"5px 0 18px"}}>
      <a href="/">Dashboard</a>
      <a href="/installation-audit">Installation audit</a>
      <a href="/trial/NCT05208047">Complete clinical trial sheet</a>
    </nav>
    <header style={{marginBottom:18}}>
      <div className="topline">PDUFA COMMAND CENTER · PHASE 3 TRIAL RESEARCH PILOT</div>
      <h1>COGT · Bezuclastinib + sunitinib</h1>
      <p><strong>PEAK Phase 3 · NCT05208047</strong> · GIST after prior imatinib · PDUFA target <strong>November 30, 2026</strong></p>
      <div style={{display:"flex",gap:8,flexWrap:"wrap",margin:"12px 0"}}>
        <span style={pill}>Historical research case · Oct 25</span>
        <span style={pill}>Research cutoff · Oct 26, 2026</span>
        <span style={pill}>Real reported trial results</span>
      </div>
      <p style={subtle}>
        This is a <strong>frozen, manual, source-linked demonstration</strong>, not a live analytical job.
        Clinical data are sponsor-reported and published at ASCO; FDA review materials have not independently
        adjudicated efficacy/safety for this pilot. Prior historical classification is not an active Pipeline gate, nor proof of current trading eligibility.
      </p>
    </header>

    <section className="panel" aria-label="Pilot outcome preview" style={{marginBottom:16}}>
      <h2>Trial prediction · preliminary scientific outlook</h2>
      <div style={{...gap,gridTemplateColumns:"repeat(auto-fit,minmax(min(100%,240px),1fr))",marginBottom:12}}>
        <FactCard label="FDA approval probability" value="—%" detail="NOT VALIDATED · No independent calibrated model"/>
        <FactCard label="Observed efficacy direction" value="Favorable" detail="PFS primary endpoint positive in the published Phase 3 analysis"/>
        <FactCard label="Safety and CMC reservations" value="Open" detail="Liver-enzyme imbalance; NDA manufacturing assessment not independently reviewed"/>
      </div>
      <p role="status" style={{...subtle,border:"1px solid #cbd5e1",padding:10,borderRadius:8,background:"#f8fafc"}}>
        No certified 40-assessment dossier, numerical Readiness/Reluctance rating, or FDA approval probability
        was produced. Historical FDA context is descriptive, not a validated comparator training cohort.
        This test did not change scored trials, scanning, restrictions, FS/FA presets or trading permissions.
      </p>
    </section>

    <section className="panel" aria-label="Observed trial statistics" style={{marginBottom:16}}>
      <h2>Real published clinical numbers</h2>
      <div style={gap}>
        <FactCard label="Primary PFS hazard ratio" value="0.50" detail="95% confidence interval 0.39–0.65; p < 0.0001"/>
        <FactCard label="Median PFS improvement" value="+7.3 mo" detail="16.5 combination vs 9.2 months on sunitinib"/>
        <FactCard label="Objective response improvement" value="+20 pp" detail="46% combination vs 26% control"/>
        <FactCard label="Randomized participants" value="413" detail="204 combination; 209 control"/>
        <FactCard label="Grade 3+ ALT/AST elevations" value="10.8% / 1.4%" detail="Combination / control; important safety concern"/>
        <FactCard label="Treatment-related AE discontinuation" value="7.4% / 3.8%" detail="Combination / control; risk requiring follow-up"/>
      </div>
      <p style={{...subtle,marginTop:12}}>
        Source: <Source item="asco"/> and <Source item="company"/>. The trial was randomized and open label;
        its PFS endpoint was assessed by blinded independent central review. Overall-survival data were immature.
      </p>
    </section>

    <section className="panel" aria-label="Twelve primary prediction factors" style={{marginBottom:16}}>
      <h2>Highest priority: 12 prediction factors</h2>
      <p style={subtle}>
        <strong>{PEAK_SOURCE_COVERAGE.directlyReported}/12</strong> have published supporting observations,
        <strong> {PEAK_SOURCE_COVERAGE.partiallyReviewed}/12</strong> are partial, and
        <strong> {PEAK_SOURCE_COVERAGE.notReviewed}/12</strong> have not been independently reviewed.
        These are <strong>coverage counts, not approval odds or validated scientific grades</strong>.
      </p>
      <div className="table-scroll">
        <table style={table}>
          <thead><tr>
            <th style={th} scope="col">Rank</th>
            <th style={th} scope="col">Decision factor</th>
            <th style={th} scope="col">Observed numeric evidence</th>
            <th style={th} scope="col">Review state</th>
          </tr></thead>
          <tbody>{PEAK_PILOT_METRICS.map(row=><tr key={row.rank}>
            <td style={td}>#{row.rank}</td>
            <th style={{...td,textAlign:"left",fontWeight:600}} scope="row">{row.label}</th>
            <td style={td}>
              <strong>{row.observed}</strong>
              <small style={{...subtle,display:"block",marginTop:4}}>{row.note}</small>
              {row.source && <small style={{display:"block",marginTop:5}}><Source item={row.source}/></small>}
            </td>
            <td style={{...td,whiteSpace:"nowrap",fontSize:12}}>
              {row.status==="PUBLISHED"?"Published":row.status==="PARTIAL"?"Partial":"Not reviewed"}
            </td>
          </tr>)}</tbody>
        </table>
      </div>
      <p style={{...subtle,marginTop:10}}>The numerical 0–100 metric grades remain unscored
        until a documented weighting rubric and independent source review are complete.
        A reported effect size is not a 0–100 approval likelihood.</p>
    </section>

    <section className="panel" aria-label="Expandable secondary prediction metrics" style={{marginBottom:16}}>
      <h2>Secondary prediction metrics · 48 factors</h2>
      <p style={subtle}>Four dropdowns are collapsed initially, keeping the front page focused on the top 12.
        No unreviewed factor is assigned a fictitious 0–100 rating.</p>
      {SECONDARY_PREDICTION_GROUPS.map(group=><details key={group.start} style={{border:"1px solid #cbd5e1",borderRadius:10,padding:"12px",margin:"9px 0"}}>
        <summary style={{cursor:"pointer",fontWeight:700}}>
          {group.title} · ranks #{group.start}–#{group.end} · 12 factors
        </summary>
        <div className="table-scroll" style={{marginTop:9}}>
          <table style={table}><thead><tr><th style={th}>#</th><th style={th}>Metric</th><th style={th}>Rating</th></tr></thead>
            <tbody>{PREDICTION_METRICS.slice(group.start-1,group.end).map(m=><tr key={m.rank}>
              <td style={td}>{m.rank}</td><td style={td}>{m.label}</td>
              <td style={{...td,whiteSpace:"nowrap"}}>{proposedMetricValue(m)}</td>
            </tr>)}</tbody>
          </table>
        </div>
      </details>)}
    </section>

    <section className="panel" aria-label="Historical trial comparisons" style={{marginBottom:16}}>
      <h2>Historical GIST evidence · {PEAK_HISTORICAL_PRECEDENTS.length} researched precedents</h2>
      <p style={subtle}>
        These are <strong>three selected FDA-approved GIST precedents</strong>, not an unbiased pool
        of approval and nonapproval decisions. They cannot establish a historical approval success rate.
        <strong> Independently model-eligible comparable review cycles: {PEAK_PILOT.modelEligibleHistoricalCases}.</strong>
      </p>
      <details style={{border:"1px solid #cbd5e1",borderRadius:10,padding:12}}>
        <summary style={{cursor:"pointer",fontWeight:700}}>Show historical comparator studies and their exact outcomes</summary>
        <div className="table-scroll" style={{marginTop:10}}>
          <table style={table}><thead><tr><th style={th}>Trial</th><th style={th}>Historical decision</th><th style={th}>Clinical comparison</th><th style={th}>Limitations</th></tr></thead>
            <tbody>{PEAK_HISTORICAL_PRECEDENTS.map(item=><tr key={item.drug}>
              <td style={td}><strong>{item.drug}</strong><small style={{...subtle,display:"block"}}>{item.trial}</small></td>
              <td style={td}>{item.outcome}<small style={{...subtle,display:"block"}}>{item.treatmentLine}</small></td>
              <td style={td}>PFS: {item.medianPfs}<small style={{...subtle,display:"block"}}>HR: {item.hazardRatio}</small>
                <small style={{display:"block",marginTop:3}}><Source item={item.source}/></small></td>
              <td style={td}>{item.qualification}</td>
            </tr>)}</tbody>
          </table>
        </div>
        <p style={{...subtle,marginTop:9}}>
          Source for the 2013 regorafenib GIST FDA approval: <Source item="regorafenibFDA"/>.
          All three trials differ from PEAK in control arms and/or treatment lines.
        </p>
      </details>
    </section>

    <section className="panel" aria-label="Research provenance" style={{marginBottom:16}}>
      <h2>Evidence, limitations and next steps</h2>
      <p>The current Phase 3 efficacy evidence is favorable relative to the active second-line comparator,
        but grade 3+ liver-enzyme elevations, dose modifications, missing full CMC/inspection review,
        and immature overall survival prevent a fully adjudicated regulatory outlook.</p>
      <details style={{border:"1px solid #cbd5e1",borderRadius:10,padding:12}}>
        <summary style={{cursor:"pointer",fontWeight:700}}>View all source references · {Object.keys(PEAK_SOURCES).length} records</summary>
        <ul>{Object.entries(PEAK_SOURCES).filter(([id])=>id!=="membership").map(([id,source])=><li key={id} style={{margin:"7px 0"}}>
          <a href={source.url} target="_blank" rel="noopener noreferrer">{source.name}</a>
        </li>)}</ul>
      </details>
      <p style={subtle}>
        Frozen research cutoff: {PEAK_PILOT.snapshotDate}; saved GEM membership observed through
        {PEAK_PILOT.membershipLastSeen}. Not live-linked to candidate assessments, and not an
        independent 40-assessment dossier. Read-only: no FDA probability, orders, FS/FA changes,
        historical-cohort certification, or source-scanning writes.
      </p>
    </section>
  </main>;
}
