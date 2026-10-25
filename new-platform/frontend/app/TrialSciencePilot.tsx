"use client";

import { useEffect, useRef, useState } from "react";
import {
  PILOT_NCT,
  SCIENCE_DOMAIN_LABELS,
  pilotDomainStatus,
  pilotEffectSummary,
  validTrialSciencePilot,
  type StudySnapshot,
  type TrialEffect,
  type TrialSciencePilot,
} from "../lib/trial-science-pilot";
import styles from "./TrialSciencePilot.module.css";

const PILOT_PATH = "/api/scientific-assessment/pilot/keynote024";
const DOMAIN_KEYS = Object.keys(SCIENCE_DOMAIN_LABELS) as (keyof typeof SCIENCE_DOMAIN_LABELS)[];

function compareArms(effect: TrialEffect, outcomeName: string): string {
  if (typeof effect.pembrolizumab !== "number" || typeof effect.chemotherapy !== "number") return "Not extracted";
  const suffix = outcomeName === "quality_of_life_week15_change" ? " points" :
    effect.metric === "median_months" ? " months" :
    effect.metric === "percent" ? "%" : " units";
  return `${effect.pembrolizumab} vs ${effect.chemotherapy}${suffix}`;
}

function prettyField(name: string): string {
  const names: Record<string, string> = {
    progression_free_survival: "Progression-free survival",
    overall_survival: "Overall survival",
    objective_response_rate: "Objective response rate",
    quality_of_life_week15_change: "Quality-of-life change, week 15",
  };
  return names[name] ?? name.replaceAll("_", " ");
}

function Snapshot({ source }: { source: StudySnapshot }) {
  const reported = [...Object.entries(source.effects ?? {}), ...Object.entries(source.outcomes ?? {})];
  const treatmentSafety = source.safety?.treatment_related_adverse_events_grade_3_to_5_percent;
  const safety = treatmentSafety && typeof treatmentSafety === "object"
    ? treatmentSafety as Record<string, unknown> : null;
  return <article className={styles.snapshot}>
    <div className={styles.snapshotHead}>
      <div>
        <h4>{source.report_type.replaceAll("_", " ")}</h4>
        <p className={styles.metadata}>Published {source.publication_date} · PMID {source.source_id}{source.data_cutoff_date ? ` · data cutoff ${source.data_cutoff_date}` : ""}</p>
      </div>
      <a href={source.source_url} target="_blank" rel="noopener noreferrer">Original publication</a>
    </div>
    <div className={styles.scroll}>
      <table className={styles.resultTable}>
        <thead><tr><th scope="col">Reported outcome</th><th scope="col">Treatment comparison</th><th scope="col">Other result</th></tr></thead>
        <tbody>
          {reported.map(([name, effect]) =>
            <tr key={name}>
              <th scope="row">{prettyField(name)}</th>
              <td>{compareArms(effect, name)}</td>
              <td>{pilotEffectSummary(effect)}
                {effect.analysis_role ? <small> · {effect.analysis_role.replaceAll("_", " ")}</small> : null}
                {effect.nominal_p_value ? <small> · nominal p={effect.nominal_p_value}</small> : null}
                {effect.p_value ? <small> · p={effect.p_value}</small> : null}
                {effect.five_year_kaplan_meier_survival_percent ?
                  <small> · 5-year KM OS: {effect.five_year_kaplan_meier_survival_percent.pembrolizumab}% vs {effect.five_year_kaplan_meier_survival_percent.chemotherapy}%</small> : null}
              </td>
            </tr>)}
          {typeof safety?.pembrolizumab === "number" && typeof safety?.chemotherapy === "number" ?
            <tr><th scope="row">Grade 3–5 treatment-related adverse events</th>
              <td>{safety.pembrolizumab}% vs {safety.chemotherapy}%</td>
              <td>Reported in this analysis; not all-cause events</td></tr> : null}
        </tbody>
      </table>
    </div>
    {typeof source.effective_crossover_percent_from_chemotherapy === "number" ?
      <p className={styles.caution}>Effective crossover from chemotherapy: {source.effective_crossover_percent_from_chemotherapy}%</p> : null}
    <details className={styles.caveats}><summary>Interpretation limitations ({source.methodological_caveats.length})</summary>
      <ul>{source.methodological_caveats.map((caveat, i) => <li key={i}>{caveat}</li>)}</ul>
    </details>
    <p className={styles.metadata}>Source-reported findings · independent statistical appraisal remains incomplete</p>
  </article>;
}

function Evidence({ pilot }: { pilot: TrialSciencePilot }) {
  const { dossier, publishedResults, pilot: study } = pilot;
  return <div className={styles.evidence}>
    <div className={styles.summary}>
      <div><span className={styles.label}>Historical Phase 3 trial</span>
        <h3>{study.trial_name}</h3>
        <p>{study.program}</p>
        <p>{study.condition}</p>
        <p><strong>Trial:</strong> {study.nct_id} · <strong>Enrolled:</strong> {study.enrollment} · <strong>Analysis:</strong> Published-source review</p>
      </div>
      <a href={dossier.source_url} target="_blank" rel="noopener noreferrer">ClinicalTrials.gov source</a>
    </div>
    <p className={styles.caution} role="status">
      No independently validated eight-domain score or FDA approval probability exists for this pilot.
      Historical efficacy results do not constitute a current regulatory forecast.
    </p>
    {pilot.scientificReadiness ? <section aria-label="Scientific input readiness and reluctance grades">
      <h3>Scientific analysis readiness — two independent grades</h3>
      <p className={styles.metadata}>These grades measure evidence completeness and uncertainty, not clinical-trial success or FDA approval probability.</p>
      <div className={styles.domains}>
        <div className={styles.domain}>
          <strong>Input readiness</strong>
          <span>{pilot.scientificReadiness.inputReadiness.grade} · {pilot.scientificReadiness.inputReadiness.status.replaceAll("_", " ")}</span>
          <small>{pilot.scientificReadiness.inputReadiness.sourceSupported} of {pilot.scientificReadiness.inputReadiness.criteriaTotal} source checks documented · {pilot.scientificReadiness.inputReadiness.unresolved} unresolved</small>
        </div>
        <div className={styles.domain}>
          <strong>Reluctance to conclude</strong>
          <span>{pilot.scientificReadiness.reluctance.grade} · {pilot.scientificReadiness.reluctance.status.replaceAll("_", " ")}</span>
          <small>{pilot.scientificReadiness.reluctance.criticalBlockedIds.length} critical blocked inputs · {pilot.scientificReadiness.reluctance.criticalReviewIds.length} critical reviews pending</small>
        </div>
      </div>
      <p className={styles.caution}>
        The publicly linked protocol/SAP is amendment {pilot.scientificReadiness.protocol.amendment},
        dated {pilot.scientificReadiness.protocol.documentDate}, after the
        {pilot.scientificReadiness.protocol.interimDataCutoff} original data cutoff.
        It is labeled {pilot.scientificReadiness.protocol.regionalScope}; it cannot establish the original analysis plan.
        {" "}<a href={pilot.scientificReadiness.protocol.url} target="_blank" rel="noopener noreferrer">Inspect protocol/SAP</a>.
      </p>
      <details className={styles.caveats}>
        <summary>Open input-readiness checklist ({pilot.scientificReadiness.checks.length})</summary>
        <div>
          {pilot.scientificReadiness.checks.map(check => <article key={check.id}>
            <h4>{check.title} · {check.status.replaceAll("_", " ")}</h4>
            <p>{check.finding}</p>
            <p><strong>Next:</strong> {check.next_action}</p>
            <ul>{check.sources.map((ref, i) => <li key={i}>
              <a href={ref.url} target="_blank" rel="noopener noreferrer">{ref.locator}</a>
            </li>)}</ul>
          </article>)}
        </div>
      </details>
    </section> : null}
    {pilot.sourceEvidenceAudit ? <section aria-label="Historical design chronology and registry safety audit">
      <h3>Trial evidence timeline · 2015 to 2021</h3>
      <p className={styles.metadata}>
        A May 2015 trial-in-progress abstract describes the primary progression-free
        survival endpoint before the May 2016 interim data cutoff. It does not
        supply a signed pre-interim statistical analysis plan or confirm multiplicity boundaries.
      </p>
      <p className={styles.caution}>
        Pre-interim original protocol/SAP still unverified; the original 2016 NEJM
        protocol supplement is listed, not independently reviewed. The registry-linked
        December 2017 Japan-only amendment remains later than the 2016 data cutoff.
        Input readiness and reluctance grades have not changed.
      </p>
      <details className={styles.caveats}>
        <summary>View dated evidence and source references ({pilot.sourceEvidenceAudit.timeline.length})</summary>
        <ol>
          {pilot.sourceEvidenceAudit.timeline.map(item => <li key={item.id}>
            <strong>{item.date} · {item.title}</strong>
            <p>{item.finding}</p>
            <p><a href={item.sourceUrl} target="_blank" rel="noopener noreferrer">
              {item.sourceLocator}</a></p>
            <small>Evidence: {item.evidenceStatus.replaceAll("_", " ")}.
              {" "}{item.limitation}</small>
          </li>)}
        </ol>
      </details>
      <h3>Registry adverse-event denominators · no pooling</h3>
      <p className={styles.metadata}>
        This view preserves each ClinicalTrials.gov adverse-event treatment-course
        group separately. The counts are aggregate registry reports, not
        confirmed treatment-related AE rates or randomized efficacy statistics.
      </p>
      {pilot.sourceEvidenceAudit.registrySafety.groups.length ? <details className={styles.caveats}>
        <summary>Inspect {pilot.sourceEvidenceAudit.registrySafety.groupCount} registry safety groups</summary>
        <div className={styles.scroll}>
          <table className={styles.resultTable}>
            <thead><tr><th scope="col">Registry group</th>
              <th scope="col">Serious AE affected / at risk</th>
              <th scope="col">Other AE affected / at risk</th>
              <th scope="col">Deaths affected / at risk</th>
            </tr></thead>
            <tbody>
              {pilot.sourceEvidenceAudit.registrySafety.groups.map(group => <tr key={group.groupId}>
                <th scope="row">{group.title}</th>
                {(["seriousEvents", "otherEvents", "deaths"] as const).map(category => {
                  const counts = group.counts[category];
                  return <td key={category}>
                    {counts.numAffected === null || counts.numAtRisk === null
                      ? "Not reported"
                      : `${counts.numAffected} / ${counts.numAtRisk}`}
                  </td>;
                })}
              </tr>)}
            </tbody>
          </table>
        </div>
        <p className={styles.metadata}>
          <a href={pilot.sourceEvidenceAudit.registrySafety.sourceUrl}
            target="_blank" rel="noopener noreferrer">Inspect the source registry record</a>.
          Switching treatment groups and first-course groups are distinct
          and must not be pooled or converted to all-cause / treatment-related percentages.
        </p>
      </details> : <p className={styles.caution}>
        No event-group counts were documented in this archived snapshot.
        This does not mean that there were zero adverse events.
      </p>}
      <p className={styles.metadata}>
        The safety audit does not change the trial efficacy estimates,
        the two readiness grades, or any GEM/WT/PIPELINE decision.
      </p>
    </section> : null}
    <h3>Eight scientific research domains</h3>
    <div className={styles.domains}>
      {DOMAIN_KEYS.map(domain => {
        const item = dossier.domains[domain];
        const registryClaims = item.claims.length;
        return <div className={styles.domain} key={domain}>
          <strong>{SCIENCE_DOMAIN_LABELS[domain]}</strong>
          <span>{pilotDomainStatus(study.domains[domain].status)}</span>
          <small>{registryClaims} source-record field{registryClaims === 1 ? "" : "s"} · scientific score not assigned</small>
        </div>;
      })}
    </div>
    <h3>Published analyses — shown separately</h3>
    <p className={styles.metadata}>Source-reported measurements are attributed to their original analysis date; they are not recomputed from patient data.</p>
    <div className={styles.snapshots}>
      {publishedResults.analysis_snapshots.map(snapshot => <Snapshot source={snapshot} key={snapshot.analysis_id} />)}
    </div>
    <h3>Additional corroborating sources</h3>
    <div className={styles.references}>
      {publishedResults.corroborating_sources.map((source, i) =>
        <div key={i}>
          <a href={source.source_url} target="_blank" rel="noopener noreferrer">{source.source_type.replaceAll("_", " ")}</a>
          <p>{source.supported_observation}</p>
          <small>{source.scope_note}</small>
        </div>)}
    </div>
    <details className={styles.caveats}><summary>Open evidence questions ({publishedResults.unresolved_tasks.length})</summary>
      <ul>{publishedResults.unresolved_tasks.map((item, i) => <li key={i}>{item}</li>)}</ul>
    </details>
    <p className={styles.metadata}>Read-only pilot · original PIPELINE / GEM JR / GEM qualification and FS/FA memberships unchanged · archived source checksum: {dossier.source_sha256.slice(0, 12)}…</p>
  </div>;
}

/** Standalone opt-in display; does not start network requests until clicked. */
export default function TrialSciencePilot() {
  const [result, setResult] = useState<TrialSciencePilot | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const request = useRef<AbortController | null>(null);

  useEffect(() => () => { request.current?.abort(); }, []);

  async function load() {
    request.current?.abort();
    const controller = new AbortController();
    request.current = controller;
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const response = await fetch(PILOT_PATH, {
        cache: "no-store", signal: controller.signal,
      });
      if (!response.ok) {
        const message = response.status === 404
          ? "The pilot API has not yet been deployed on the review service."
          : "The scientific pilot is temporarily unavailable (" + response.status + ").";
        throw new Error(message);
      }
      const data: unknown = await response.json();
      if (!validTrialSciencePilot(data)) {
        throw new Error("Pilot data failed trial identity, provenance or unscored-state validation.");
      }
      if (!controller.signal.aborted) setResult(data);
    } catch (e) {
      if (!controller.signal.aborted) setError(e instanceof Error ? e.message : "Unable to load pilot.");
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }

  return <details id="trial-science-pilot" className={`panel ${styles.root}`}>
    <summary className={styles.heading}><strong>TRIAL SCIENCE · 8-domain historical pilot</strong>
      <span>KEYNOTE-024 · {PILOT_NCT} · research only</span></summary>
    <div className={styles.body}>
      <p className={styles.metadata}>Open this review to compare published outcomes, uncertainty and eight research domains. No scanning, scoring, or trading is triggered.</p>
      <button type="button" onClick={() => void load()} disabled={loading}>
        {loading ? "Loading trial evidence…" : result ? "Refresh historical evidence" : "Load historical trial evidence"}
      </button>
      {error ? <p role="alert" className={styles.error}>{error}</p> : null}
      {result ? <Evidence pilot={result} /> : null}
    </div>
  </details>;
}
