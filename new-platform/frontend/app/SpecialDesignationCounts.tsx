"use client";

import { useMemo } from "react";
import type { Candidate } from "./Workspace";
import { useTrialDesignations } from "./TrialDesignations";
import {
  SPECIAL_DESIGNATION_CATEGORIES, resolveTrialDesignations,
  type DesignationEvidence, type DesignationKey,
} from "../lib/trial-designations";
import { trialId } from "../lib/pipeline-data";

type Match = { row: Candidate; evidence: DesignationEvidence };
type Counts = Record<DesignationKey, Match[]>;

/** Informational counts only. This control never changes Pipeline, GEM JR, GEM or FS/FA restrictions. */
export default function SpecialDesignationCounts({ rows, asOf }: { rows: Candidate[]; asOf: string }) {
  const { index, loading, error, retry } = useTrialDesignations();
  const matches = useMemo<Counts>(() => {
    const byKey = Object.fromEntries(SPECIAL_DESIGNATION_CATEGORIES.map(({ key }) => [key, [] as Match[]])) as Counts;
    if (!index) return byKey;
    for (const row of rows) {
      const designations = resolveTrialDesignations(row, index);
      for (const { key } of SPECIAL_DESIGNATION_CATEGORIES) {
        const evidence = designations[key];
        // Report only exact-linked, positively sourced grants/approvals; never infer one from missing fields.
        if (evidence.status === "GRANTED" && evidence.verification !== "UNVERIFIED" && evidence.source) {
          byKey[key].push({ row, evidence });
        }
      }
    }
    return byKey;
  }, [rows, index]);
  const priorityEvidence = rows.some(row => row.priorityReview?.status === "FDA_VERIFIED");

  return <fieldset className="filter-count-group special-designation-counts" aria-label="FDA special designations and pathways in Pipeline">
    <legend>FDA SPECIAL DESIGNATIONS / PATHWAYS · 13</legend>
    <div className="filter-group-total">
      <span>Source-recorded matches · PIPELINE</span>
      <strong>{rows.length.toLocaleString("en-US")}</strong>
    </div>
    <p className="special-designation-hint">
      Matching Pipeline records for the current search, market-cap and trial filters, using exact trial/application links.
      A missing designation is unknown, not a denial. Categories can overlap.
    </p>
    {error && <p role="status" className="special-designation-error">{error} <button type="button" className="secondary" onClick={retry}>Retry</button></p>}
    <div className="special-designation-list">
      {SPECIAL_DESIGNATION_CATEGORIES.map(({ key, label }) => {
        const tracked = !!index?.availableKeys?.[key] || (key === "priority_review" && priorityEvidence);
        const known = !!index && tracked;
        const hits = matches[key];
        return <details key={key} className="special-designation-item">
          <summary>
            <span className="special-designation-name">{label}</span>
            <strong className="special-designation-total"
              title={known ? "Exact-linked, sourced positive records; not all real-world designations" : "No count can be verified from the current source"}>
              {loading && !index ? "…" : known ? hits.length.toLocaleString("en-US") : "—"}
            </strong>
            <span className="special-designation-view">VIEW DATA ▾</span>
          </summary>
          <div className="special-designation-detail">
            {!index ? <p>{loading ? "Loading saved FDA evidence…" : "Designation source currently unavailable. No counts inferred."}</p>
              : !tracked ? <p>Not yet tracked in the saved designation source. No reliable count available.</p>
              : hits.length === 0 ? <p>No source-recorded positive match in these Pipeline records. This does not establish that no designation exists.</p>
              : <>
                <p>{hits.length.toLocaleString("en-US")} source-recorded positive Pipeline {hits.length === 1 ? "record" : "records"}. Showing up to 50 linked records.</p>
                <ol className="special-designation-records">
                  {hits.slice(0, 50).map(({ row, evidence }) => {
                    const nct = trialId(row);
                    return <li key={row.id}>
                      <strong>{row.ticker || "Unknown ticker"}</strong> · {row.drug || row.indication || row.programId || row.id}
                      {nct && <a href={"/trial/" + encodeURIComponent(nct)} target="_blank" rel="noopener noreferrer">Full trial ↗</a>}
                      <a href={evidence.source} target="_blank" rel="noopener noreferrer">Evidence ↗</a>
                      <small>{evidence.designationDate ? "Date: " + evidence.designationDate + " · " : ""}{evidence.verification === "FDA_VERIFIED" ? "FDA verified" : "Source recorded"}</small>
                    </li>;
                  })}
                </ol>
                {hits.length > 50 && <p>Additional records are not shown in this compact view.</p>}
              </>}
          </div>
        </details>;
      })}
    </div>
    <p className="special-designation-footnote">
      — = not yet tracked or unavailable; 0 = no positive evidence currently linked (not proof of absence).
      PRV programs, LPAD and the Animal Rule are regulatory mechanisms, not ordinary FDA designations.
      {asOf ? " · Pipeline source published: " + asOf : ""}
    </p>
  </fieldset>;
}
