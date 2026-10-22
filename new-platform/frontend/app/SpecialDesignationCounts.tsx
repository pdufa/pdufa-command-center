"use client";

import { useMemo } from "react";
import type { Candidate } from "./Workspace";
import {
  SPECIAL_DESIGNATION_CATEGORIES, resolveTrialDesignations,
  type DesignationEvidence, type DesignationIndex, type DesignationKey,
} from "../lib/trial-designations";
import { trialId } from "../lib/pipeline-data";

type Match = { row: Candidate; evidence: DesignationEvidence };
type Counts = Record<DesignationKey, Match[]>;

export default function SpecialDesignationCounts({
  rows, asOf, selected, onChange, index, loading, error, onRetry,
}: {
  rows: Candidate[]; asOf: string; selected: DesignationKey[];
  onChange: (selected: DesignationKey[]) => void;
  index: DesignationIndex | null; loading: boolean; error: string; onRetry: () => void;
}) {
  const matches = useMemo<Counts>(() => {
    const byKey = Object.fromEntries(SPECIAL_DESIGNATION_CATEGORIES.map(({ key }) => [key, [] as Match[]])) as Counts;
    if (!index) return byKey;
    for (const row of rows) {
      const designations = resolveTrialDesignations(row, index);
      for (const { key } of SPECIAL_DESIGNATION_CATEGORIES) {
        const evidence = designations[key];
        // Exact-linked positive records only; no invented designation or zero from missing evidence.
        if (evidence.status === "GRANTED" && evidence.verification !== "UNVERIFIED" && evidence.source) {
          byKey[key].push({ row, evidence });
        }
      }
    }
    return byKey;
  }, [rows, index]);
  const priorityEvidence = rows.some(row => row.priorityReview?.status === "FDA_VERIFIED");
  const availableKeys = SPECIAL_DESIGNATION_CATEGORIES
    .filter(({ key }) => !!index && (!!index.availableKeys?.[key] || (key === "priority_review" && priorityEvidence)))
    .map(({ key }) => key);
  const allSelected = availableKeys.length > 0 && availableKeys.every(key => selected.includes(key));

  return <fieldset className="filter-count-group special-designation-counts" aria-label="FDA special designations and pathways in Pipeline">
    <legend>FDA SPECIAL DESIGNATIONS / PATHWAYS · 13</legend>
    <div className="filter-group-total">
      <span>PIPELINE SOURCE TOTAL</span>
      <strong>{rows.length.toLocaleString("en-US")}</strong>
    </div>
    <p className="special-designation-hint">
      Select any designations to narrow Pipeline. Multiple selections match ANY checked designation;
      other Pipeline criteria still apply. Counts show source-linked grants or approvals.
    </p>
    {error && <p role="status" className="special-designation-error">{error} <button type="button" className="secondary" onClick={onRetry}>Retry</button></p>}
    <div className="special-designation-list">
      {SPECIAL_DESIGNATION_CATEGORIES.map(({ key, label }) => {
        const tracked = !!index && availableKeys.includes(key);
        const hits = matches[key];
        const checked = selected.includes(key);
        return <div key={key} className={"special-designation-item" + (checked ? " special-designation-selected" : "")}>
          <label className="special-designation-option">
            <input type="checkbox" checked={checked} disabled={!tracked}
              onChange={() => onChange(checked ? selected.filter(item => item !== key) : [...selected, key])}
              aria-label={label} />
            <span className="special-designation-name">{label}</span>
            <strong className="special-designation-total"
              title={tracked ? "Source-linked positive Pipeline records" : "No verified count available"}>
              {loading && !index ? "…" : tracked ? hits.length.toLocaleString("en-US") : "—"}
            </strong>
            <span className="filter-mini-track" aria-hidden="true"><span style={{ width: tracked
              ? (hits.length / Math.max(1, ...SPECIAL_DESIGNATION_CATEGORIES.map(item => matches[item.key].length)) * 100) + "%" : "0%" }} /></span>
          </label>
          <details className="special-designation-drilldown">
            <summary>VIEW DATA ▾</summary>
            <div className="special-designation-detail">
              {!index ? <p>{loading ? "Loading saved FDA evidence…" : "Designation source unavailable; no count inferred."}</p>
                : !tracked ? <p>Not yet tracked in the saved designation source. No reliable count available.</p>
                : hits.length === 0 ? <p>No positive, source-linked match in these Pipeline records. This does not mean the designation was denied.</p>
                : <>
                  <p>{hits.length.toLocaleString("en-US")} source-recorded Pipeline {hits.length === 1 ? "record" : "records"}. Showing up to 50 linked records.</p>
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
                  {hits.length > 50 && <p>More records exist beyond this compact list.</p>}
                </>}
            </div>
          </details>
        </div>;
      })}
    </div>
    <button type="button" className="secondary pipeline-group-select-toggle" disabled={!availableKeys.length}
      aria-pressed={allSelected}
      onClick={() => onChange(allSelected ? [] : availableKeys)}>
      {allSelected ? "NONE" : "ALL"}
    </button>
    <p className="special-designation-footnote">
      {selected.length} checked · — means no saved source field or unavailable data, not zero.
      Untracked options cannot be selected. FDA regulatory pathways and vouchers are included alongside designations.
      {asOf ? " · Published: " + asOf : ""}
    </p>
  </fieldset>;
}
