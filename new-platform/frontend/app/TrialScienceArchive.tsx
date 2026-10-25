"use client";

import { useEffect, useRef, useState } from "react";
import {
  ARCHIVE_DOMAIN_NAMES,
  ARCHIVE_DOMAINS,
  ARCHIVE_NCT_PATTERN,
  formatArchivedField,
  isExactArchivedDossier,
  summarizeArchivedValue,
  type ArchivedScienceDossier,
} from "../lib/archived-science-dossier";
import styles from "./TrialSciencePilot.module.css";

/**
 * All eight source-only research domains for one exact, already-archived NCT.
 * Unlike the historical KEYNOTE-024 publication pilot, this general view
 * deliberately makes no external literature or FDA-results claims.
 */
export default function TrialScienceArchive({ nctId }: { nctId: string }) {
  const [dossier, setDossier] = useState<ArchivedScienceDossier | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const inflight = useRef<AbortController | null>(null);
  const valid = ARCHIVE_NCT_PATTERN.test(nctId);

  useEffect(() => {
    // Switching selected trials may never retain the previous trial's claims.
    inflight.current?.abort();
    setDossier(null);
    setError("");
    setLoading(false);
    return () => { inflight.current?.abort(); };
  }, [nctId]);

  async function load() {
    if (!valid) return;
    inflight.current?.abort();
    const controller = new AbortController();
    inflight.current = controller;
    setLoading(true);
    setDossier(null);
    setError("");
    try {
      const result = await fetch(
        "/api/scientific-assessment/archived/" + encodeURIComponent(nctId),
        { cache: "no-store", signal: controller.signal },
      );
      if (!result.ok) {
        throw new Error(result.status === 404
          ? "This exact trial has not been imported into the scientific archive. No evidence or score has been inferred."
          : "The archived scientific record could not be verified (" + result.status + ").");
      }
      const body: unknown = await result.json();
      if (!isExactArchivedDossier(body, nctId)) {
        throw new Error("Trial identity or source provenance failed validation. Nothing has been scored.");
      }
      if (!controller.signal.aborted) setDossier(body);
    } catch (err) {
      if (!controller.signal.aborted) {
        setError(err instanceof Error ? err.message : "Scientific archive unavailable.");
      }
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }

  return <details id={"archived-trial-science-" + nctId} className={`panel ${styles.root}`}>
    <summary className={styles.heading}>
      <strong>TRIAL SCIENCE · Eight-domain source dossier</strong>
      <span>{nctId} · archived evidence only</span>
    </summary>
    <div className={styles.body}>
      <p className={styles.metadata}>
        Examines one stored ClinicalTrials.gov record. Registry statements are not
        independent scientific verification, FDA approval forecasts, or trading signals.
      </p>
      <button type="button" disabled={loading || !valid} onClick={() => void load()}>
        {loading ? "Verifying archived trial…" : dossier ? "Refresh verified archive" : "Load selected trial archive"}
      </button>
      {error ? <p role="alert" className={styles.error}>{error}</p> : null}
      {dossier ? <>
        <p role="status" className={styles.caution}>
          Scientific assessment incomplete. All eight domain scores and the FDA
          approval probability are intentionally unavailable pending independent review.
        </p>
        <div className={styles.summary}>
          <p className={styles.metadata}>
            Exact trial: <strong>{dossier.nct_id}</strong>
            {dossier.source_fetched_at ? <> · Archived: {dossier.source_fetched_at}</> : null}
            {" · "}Record SHA-256: {dossier.source_sha256.slice(0, 16)}…
          </p>
          <a href={dossier.source_url} target="_blank" rel="noopener noreferrer">
            Open original registry record
          </a>
        </div>
        <h3>Eight source-level research domains</h3>
        <div className={styles.domains}>
          {ARCHIVE_DOMAINS.map((name) => {
            const part = dossier.domains[name];
            return <div className={styles.domain} key={name}>
              <strong>{ARCHIVE_DOMAIN_NAMES[name]}</strong>
              <span>{part.status === "source_record_only"
                ? "Registry metadata identified · not independently assessed"
                : "Not assessed"}</span>
              <small>{part.claims.length} source field{part.claims.length === 1 ? "" : "s"} · score not assigned</small>
            </div>;
          })}
        </div>
        <h3>Registered trial-design information</h3>
        {dossier.domains.clinical_design.claims.length > 0
          ? <div className={styles.references}>
              {dossier.domains.clinical_design.claims.map((claim) =>
                <div key={claim.field}>
                  <strong>{formatArchivedField(claim.field)}</strong>
                  <p className={styles.metadata} style={{ overflowWrap: "anywhere", whiteSpace: "pre-wrap" }}>
                    {summarizeArchivedValue(claim.reported_value)}
                  </p>
                  <small>Source field: {claim.source_locator} · source-record only</small>
                </div>)}
            </div>
          : <p className={styles.metadata}>No supported trial-design fields in this archived registry snapshot.</p>}
        <p className={styles.metadata}>
          This record has not been checked against full publications, the trial protocol,
          FDA application materials, or competing studies. No PIPELINE, GEM JR, GEM,
          WT, FS/FA presets, or trading actions are changed.
        </p>
      </> : null}
    </div>
  </details>;
}
