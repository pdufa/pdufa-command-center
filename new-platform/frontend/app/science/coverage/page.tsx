"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import type { PublishedCoverage, StageCoverage } from "../../../lib/scientific-cohort-coverage";

/** No automatic trial downloads, probes or scoring. Checks require explicit clicks. */
const PILOT_EXACT_ID = "TRIAL|NCT02142738";
export default function ScientificListCoveragePage() {
  const [data, setData] = useState<PublishedCoverage | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [connectionLoading, setConnectionLoading] = useState(false);
  const [connectionResult, setConnectionResult] = useState("");
  const [connectionSucceeded, setConnectionSucceeded] = useState(false);
  const aborter = useRef<AbortController | null>(null);
  const connectionAborter = useRef<AbortController | null>(null);
  useEffect(() => () => {
    aborter.current?.abort();
    connectionAborter.current?.abort();
  }, []);

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

  /** A signed-in live read of one archived pilot, not scientific adjudication. */
  async function checkScientificConnection() {
    connectionAborter.current?.abort();
    const controller = new AbortController();
    connectionAborter.current = controller;
    setConnectionLoading(true);
    setConnectionSucceeded(false);
    setConnectionResult("");
    try {
      const response = await fetch(
        "/api/scientific-assessment/connection?exact_id=" + encodeURIComponent(PILOT_EXACT_ID),
        { cache: "no-store", signal: controller.signal },
      );
      if (response.status === 401) throw new Error(
        "Dashboard sign-in required. Sign in to the preview, then try again."
      );
      if (response.status === 502) throw new Error(
        "The isolated scientific service rejected the preview access key. Connection is NOT verified."
      );
      if (!response.ok) throw new Error(
        "Live scientific service connection NOT verified (HTTP " + response.status + ")."
      );
      const body: unknown = await response.json();
      if (!body || typeof body !== "object" || Array.isArray(body)) {
        throw new Error("Scientific connection response is invalid.");
      }
      const result = body as Record<string, unknown>;
      if (result.connection !== "connected"
          || result.exactTrialIdentityMatched !== true
          || typeof result.archivedRecordPresent !== "boolean"
          || result.independentScientificReview !== "not_certified_by_connection_test"
          || result.approvalProbability !== null
          || result.scoresAssignedByConnectionTest !== false) {
        throw new Error("Scientific connection response failed validation.");
      }
      if (!controller.signal.aborted) {
        setConnectionSucceeded(true);
        setConnectionResult(
          "CONNECTED: preview authenticated to isolated scientific service for "
          + "KEYNOTE-024 (NCT02142738). Exact trial identity matched. "
          + (result.archivedRecordPresent
            ? "Archived registry record present. "
            : "Archived registry record not loaded. ")
          + "Independent scientific evidence and FDA outcome prediction remain UNVERIFIED."
        );
      }
    } catch (cause) {
      if (!controller.signal.aborted) {
        setConnectionResult(cause instanceof Error ? cause.message :
          "Scientific service connection could not be verified.");
      }
    } finally {
      if (!controller.signal.aborted) setConnectionLoading(false);
    }
  }

  // The two checks reflect only explicit successful requests in this browser session.
  // They are not source adjudication or a software release authorization.
  const currentPublishedSourceVerified = data?.status === "PUBLISHED_SNAPSHOT_AUDIT";
  const sessionChecksVerified = Number(currentPublishedSourceVerified) + Number(connectionSucceeded);

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

    <section className="panel" aria-label="Isolated scientific service connection">
      <h2>Verify live scientific service connection</h2>
      <p className="subtle">Signed-in, read-only pilot test for KEYNOTE-024
        (NCT02142738): Vercel preview to the isolated Render scientific API.
        This does not import trials, certify evidence, assign grades or predict FDA decisions.</p>
      <button type="button" onClick={() => void checkScientificConnection()}
        disabled={connectionLoading}>
        {connectionLoading
          ? "Checking isolated scientific service…"
          : "Verify isolated scientific API (pilot)"}
      </button>
      {connectionResult && <p role={connectionSucceeded ? "status" : "alert"}>
        {connectionResult}
      </p>}
      {!connectionResult && <p className="subtle">No connection test runs automatically.
        A successful test verifies credentials and one exact trial response only.</p>}
    </section>

    <section className="panel" aria-label="Scientific release readiness checklist">
      <details>
        <summary><strong>Scientific release checklist — {sessionChecksVerified} of 2 session checks verified; 5 independent requirements</strong></summary>
        <p className="subtle">The session checks require the buttons above. They reset on refresh
          and do not establish a completed live scan, original-document authenticity,
          independent clinical assessment, or production release approval.</p>
        <h3>Read-only session checks</h3>
        <ol>
          <li><strong>Current published GEM JR / GEM / WT program identity:</strong>{" "}
            {currentPublishedSourceVerified
              ? "Published source health and exact-NCT identity checked in this session."
              : "Not freshly verified in this session. Run Check current list coverage."}
          </li>
          <li><strong>Authenticated isolated scientific API transport:</strong>{" "}
            {connectionSucceeded
              ? "Pilot exact-NCT connection checked in this session."
              : "Not verified in this session. Run Verify isolated scientific API (pilot)."}
          </li>
        </ol>
        <h3>Independent release requirements — not certified by these checks</h3>
        <ol>
          <li>Authenticated primary-source origin, original PDF bytes, dates and content verification.</li>
          <li>Original protocol/SAP, endpoint estimates, safety denominators and contradictory findings adjudicated.</li>
          <li>Two independently authenticated, appropriately qualified reviewers and signed evidence decisions.</li>
          <li>Validated, held-out FDA outcome calibration before any numeric regulatory prediction.</li>
          <li>Production credential isolation, rollback rehearsal, current FS/FA parity and explicit release authorization.</li>
        </ol>
        <p><strong>Scientific release: HOLD.</strong> No independent scientific
          conclusions, FDA approval probabilities, trial imports or clinical scores
          are authorized by this checklist.</p>
      </details>
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
