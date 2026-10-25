"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import type { PublishedCoverage, StageCoverage } from "../../../lib/scientific-cohort-coverage";

/** No automatic trial download or scoring. One explicit read-only audit click. */
export default function ScientificListCoveragePage() {
  const [data, setData] = useState<PublishedCoverage | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const aborter = useRef<AbortController | null>(null);
  useEffect(() => () => aborter.current?.abort(), []);

  async function audit() {
    aborter.current?.abort();
    const controller = new AbortController();
    aborter.current = controller;
    setLoading(true);
    setError("");
    setData(null);
    try {
      const response = await fetch("/api/scientific-cohort/coverage", {
        cache: "no-store",
        signal: controller.signal,
      });
      if (!response.ok) throw new Error(
        response.status === 401 ? "Sign in to the dashboard to verify published list coverage."
          : "Published trial membership could not be verified (" + response.status + ")."
      );
      const json: unknown = await response.json();
      if (!json || typeof json !== "object" || Array.isArray(json)) {
        throw new Error("Coverage report format is invalid.");
      }
      const value = json as Partial<PublishedCoverage>;
      if (!Array.isArray(value.stages) || value.stages.length !== 3
          || value.importsPerformed !== false || value.approvalProbability !== null
          || value.archivedScientificRecordsVerified !== null
          || value.scientificFindingsVerified !== null
          || value.qualificationPresetsChanged !== false
          || typeof value.asOf !== "string"
          || value.stages.some(s => !s || !["GEM JR", "GEM", "WT"].includes(s.list)
            || !Number.isSafeInteger(s.uniquePrograms)
            || !Number.isSafeInteger(s.exactNctPrograms)
            || s.exactNctPrograms > s.uniquePrograms
            || !Array.isArray(s.sampleExactNct)
            || s.sampleExactNct.length > 12
            || s.sampleExactNct.some(sample =>
              !/^PDUFA-[0-9]{6,}$/.test(sample.programId)
              || !/^NCT[0-9]{8}$/.test(sample.nctId)))) {
        throw new Error("Unverified or inconsistent science coverage report.");
      }
      if (!controller.signal.aborted) setData(value as PublishedCoverage);
    } catch (cause) {
      if (!controller.signal.aborted) {
        setError(cause instanceof Error ? cause.message : "Coverage audit unavailable.");
      }
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }

  return <main className="site">
    <section className="panel">
      <div className="sectionhead">
        <div>
          <h1>Scientific trial coverage — GEM JR / GEM / WT</h1>
          <p className="subtle">Exact published program-to-NCT identity review, not a clinical scoring run.</p>
        </div>
        <Link className="streamlit-fallback" href="/">← PDUFA dashboard</Link>
      </div>
      <p>Review whether saved members of each list link directly to a registry trial.
        An application-only record is not a verified NCT link. All grades and FDA
        approval probabilities remain unassigned.</p>
      <button type="button" onClick={() => void audit()} disabled={loading}>
        {loading ? "Checking published source identities…" : "Check current list coverage"}
      </button>
      {error && <p role="alert">{error}</p>}
      {!data && !error && <p className="subtle">No sources are fetched until you select the check above. No trial imports are initiated.</p>}
    </section>

    {data && <section className="panel" aria-label="Published scientific cohort coverage report">
      <div className="sectionhead">
        <div>
          <h2>List-to-trial identity audit</h2>
          <p className="subtle">Published snapshot: {data.asOf} · Source: {data.sourceMode} · Health: {data.sourceHealthState}</p>
        </div>
      </div>
      {data.status === "SOURCE_NOT_FRESHLY_VERIFIED" && <p role="alert">
        Source health is stale or unavailable; treat the numbers as an unverified snapshot, not current membership.
      </p>}
      <p><strong>{data.pipelineRows.toLocaleString("en-US")}</strong> published Pipeline rows were used only as an identity cross-reference.</p>
      <div style={{overflowX:"auto"}}>
        <table>
          <thead><tr>
            <th>List</th><th>Exact programs</th><th>Direct NCT links</th>
            <th>Unlinked programs</th><th>Conflicting identity</th><th>Missing from current source</th>
          </tr></thead>
          <tbody>{data.stages.map((stage: StageCoverage) => <tr key={stage.list}>
            <th scope="row">{stage.list}</th>
            <td>{stage.uniquePrograms}</td>
            <td>{stage.exactNctPrograms}</td>
            <td>{stage.unlinkedPrograms}</td>
            <td>{stage.conflictingIdentityPrograms}</td>
            <td>{stage.sourceMissingPrograms}</td>
          </tr>)}</tbody>
        </table>
      </div>
      {data.stages.map(stage => <details key={stage.list}>
        <summary><strong>{stage.list} — exact-source examples and manual crosswalk needs</strong></summary>
        {stage.rowsWithoutPermanentId > 0 && <p>{stage.rowsWithoutPermanentId} row(s) lack a valid permanent Program ID and were not counted as exact programs.</p>}
        {stage.sampleExactNct.length ? <>
          <h3>Direct trial source keys — sample (maximum 12)</h3>
          <ul>{stage.sampleExactNct.map(item =>
            <li key={item.programId}>
              {item.programId} · <Link href={"/trial/"+item.nctId}>{item.nctId} — review trial dossier</Link>
            </li>
          )}</ul>
        </> : <p>No directly linked NCT source key was verified for this list's current records.</p>}
        {stage.sampleUnlinkedPrograms.length ? <>
          <h3>Manual trial crosswalk required — sample (maximum 12)</h3>
          <ul>{stage.sampleUnlinkedPrograms.map(item =>
            <li key={item.programId}>{item.programId} · {item.sourceType.replaceAll("_", " ")} · no trial assigned</li>
          )}</ul>
        </> : null}
      </details>)}
      <p role="status"><strong>No scientific records imported. No readiness grade or approval probability assigned.</strong></p>
      <p className="subtle">{data.reason}</p>
      <small>This check does not change GEM JR, GEM or WT membership, FS/FA presets,
        scanner schedules, trading orders, scientific records or trial scores.</small>
    </section>}
  </main>;
}
