"use client";

import { useEffect, useState } from "react";
import { SCIENCE_ASSESSMENT_COUNT, SCIENCE_LAYERS, SCIENCE_DEPTH_LEVELS, SCIENCE_SCHEMA_VERSION, assessScienceReadiness, type ScienceDossier, type ScienceList } from "../lib/science-evidence";

/** Read-only scientific dossier. An absent record is not a zero or a failed trial. */
export default function ScienceEvidencePanel({ programId, list }: { programId: string; list: ScienceList }) {
  const [dossier, setDossier] = useState<ScienceDossier | null>(null);
  const [state, setState] = useState<"loading" | "missing" | "error" | "loaded">("loading");
  useEffect(() => {
    const controller = new AbortController();
    setDossier(null); setState("loading");
    fetch("/api/science/dossier?programId=" + encodeURIComponent(programId) + "&list=" + encodeURIComponent(list),
      { signal: controller.signal, cache: "no-store" })
      .then(async response => {
        if (response.status === 404 || response.status === 501) { setState("missing"); return; }
        if (!response.ok) throw new Error("Scientific evidence unavailable");
        const value: unknown = await response.json();
        if (!value || typeof value !== "object") throw new Error("Invalid scientific dossier");
        const candidate = value as ScienceDossier;
        if (candidate.schemaVersion !== SCIENCE_SCHEMA_VERSION || candidate.programId !== programId || candidate.list !== list ||
          !Array.isArray(candidate.assessments)) throw new Error("Mismatched scientific dossier");
        setDossier(candidate); setState("loaded");
      }).catch(() => { if (!controller.signal.aborted) setState("error"); });
    return () => controller.abort();
  }, [programId, list]);
  const result = dossier ? assessScienceReadiness(dossier) : null;
  return <section aria-label="SCIENCE scientific investigation" style={{ marginTop: 12, padding: 12, border: "1px solid #888", borderRadius: 8 }}>
    <strong>SCIENCE · independent scientific investigation</strong>
    <p>8 layers · {SCIENCE_ASSESSMENT_COUNT} required assessments · depth 1–{SCIENCE_DEPTH_LEVELS}. Separate from existing GEM scoring.</p>
    {state === "loading" && <p role="status">Checking scientific dossier…</p>}
    {state === "missing" && <p role="status">NOT READY — no published scientific dossier endpoint or record. No score inferred.</p>}
    {state === "error" && <p role="alert">NOT READY — scientific dossier could not be verified.</p>}
    {result && <div role="status">
      <strong>{result.status === "READY_FOR_ANALYSIS" ? "READY FOR ANALYSIS" : "RELUCTANT — EVIDENCE INCOMPLETE"}</strong>
      <p>Verified assessments: {result.verifiedAssessments}/{result.totalAssessments}. FDA approval probability: Not calculated.</p>
      <details><summary>Evidence gaps ({result.missing.length})</summary>
        {result.missing.length ? <ul>{result.missing.map((gap, index) => <li key={index}>{gap}</li>)}</ul> : <p>No gaps recorded in this dossier.</p>}
      </details>
      <details><summary>Eight scientific layers</summary><ol>{SCIENCE_LAYERS.map(layer => <li key={layer}>{layer}</li>)}</ol></details>
    </div>}
  </section>;
}
