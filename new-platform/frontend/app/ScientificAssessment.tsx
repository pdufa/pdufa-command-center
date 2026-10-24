"use client";

import { useState } from "react";

type Domain = { score: number | null; verified: boolean; verified_fields: number; required_fields: number; missing_fields: string[] };
type Assessment = { exactId: string; sourceStatus: string; assessment: { overall_score: number | null; status: string; domains: Record<string, Domain> } };

export default function ScientificAssessment({ exactId }: { exactId: string }) {
  const [result, setResult] = useState<Assessment | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function load() {
    if (!exactId) return;
    setLoading(true);
    setError("");
    try {
      const response = await fetch("/api/scientific-assessment?exact_id=" + encodeURIComponent(exactId), { cache: "no-store" });
      if (!response.ok) throw new Error("Scientific assessment unavailable (" + response.status + ")");
      setResult(await response.json() as Assessment);
    } catch (e) { setError(String(e)); }
    finally { setLoading(false); }
  }

  return <section aria-label="Scientific Assessment">
    <button type="button" disabled={!exactId || loading} onClick={load}>{loading ? "Loading…" : "Scientific Assessment"}</button>
    {error && <p role="alert">{error}</p>}
    {result && <div>
      <p>Trial: {result.exactId}</p>
      <p>{result.assessment.overall_score === null ? "Insufficient verified evidence — no overall score" : "Scientific score: " + result.assessment.overall_score}</p>
      {Object.entries(result.assessment.domains).map(([name, domain]) =>
        <details key={name}><summary>{name.replaceAll("_", " ")} · {domain.verified_fields}/{domain.required_fields} verified</summary>
          <p>{domain.score === null ? "Score unavailable" : "Score: " + domain.score}</p>
          <p>Missing evidence: {domain.missing_fields.join(", ") || "None"}</p>
        </details>)}
      <small>Scientific evidence is separate from PIPELINE, GEM JR and GEM qualification presets.</small>
    </div>}
  </section>;
}
