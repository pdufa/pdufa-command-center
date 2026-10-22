"use client";

import { useMemo } from "react";
import type { Candidate } from "./Workspace";
import { trialId } from "../lib/pipeline-data";
import {
  SPECIAL_DESIGNATION_CATEGORIES, resolveTrialDesignations,
  type DesignationEvidence, type DesignationIndex, type DesignationKey,
} from "../lib/trial-designations";

type Matched = { row: Candidate; evidence: DesignationEvidence };
type Counts = Record<DesignationKey, Matched[]>;

type Props = {
  rows: Candidate[];
  asOf: string;
  selected?: DesignationKey[];
  onChange?: (next: DesignationKey[]) => void;
  index?: DesignationIndex | null;
  loading?: boolean;
  error?: string;
  onRetry?: () => void;
};

export default function SpecialDesignationCounts({
  rows, asOf, selected = [], onChange = () => {}, index = null, loading = false, error = "", onRetry = () => {},
}: Props) {
  const matches = useMemo<Counts>(() => {
    const result = {} as Counts;
    for (const item of SPECIAL_DESIGNATION_CATEGORIES) result[item.key] = [];
    if (!index) return result;
    for (const row of rows) {
      const evidence = resolveTrialDesignations(row, index);
      for (const item of SPECIAL_DESIGNATION_CATEGORIES) {
        const value = evidence[item.key];
        if (value.status === "GRANTED" && value.verification !== "UNVERIFIED" && value.source) {
          result[item.key].push({ row, evidence: value });
        }
      }
    }
    return result;
  }, [rows, index]);

  const priorityRecordExists = rows.some(row => row.priorityReview?.status === "FDA_VERIFIED");
  const available: DesignationKey[] = [];
  for (const item of SPECIAL_DESIGNATION_CATEGORIES) {
    if (index && (index.availableKeys?.[item.key] || (item.key === "priority_review" && priorityRecordExists))) {
      available.push(item.key);
    }
  }
  const allSelected = available.length > 0 && available.every(key => selected.includes(key));
  const maxCount = Math.max(1, ...SPECIAL_DESIGNATION_CATEGORIES.map(item => matches[item.key].length));

  return <fieldset className="filter-count-group special-designation-counts">
    <legend>FDA SPECIAL DESIGNATIONS / PATHWAYS · 13</legend>
    <div className="filter-group-total"><span>PIPELINE SOURCE TOTAL</span><strong>{rows.length.toLocaleString("en-US")}</strong></div>
    <p className="special-designation-hint">Check one or more designations to filter Pipeline.
      Multiple checked categories match ANY selected category. An unknown designation is never treated as a grant.</p>
    {error && <p role="status" className="special-designation-error">{error} <button type="button" className="secondary" onClick={onRetry}>Retry</button></p>}
    <div className="special-designation-list">
      {SPECIAL_DESIGNATION_CATEGORIES.map(item => {
        const key = item.key;
        const checked = selected.includes(key);
        const enabled = available.includes(key);
        const records = matches[key];
        return <div className={"special-designation-item" + (checked ? " special-designation-selected" : "")} key={key}>
          <label className="special-designation-option">
            <input type="checkbox" aria-label={item.label} checked={checked} disabled={!enabled}
              onChange={() => onChange(checked ? selected.filter(value => value !== key) : [...selected, key])} />
            <span className="special-designation-name">{item.label}</span>
            <strong className="special-designation-total" title="Source-linked Pipeline matches">
              {loading && !index ? "…" : enabled ? records.length.toLocaleString("en-US") : "—"}
            </strong>
            <span className="filter-mini-track" aria-hidden="true">
              <span style={{ width: enabled ? (records.length / maxCount * 100) + "%" : "0%" }} />
            </span>
          </label>
          <details className="special-designation-drilldown">
            <summary>VIEW DATA ▾</summary>
            <div className="special-designation-detail">
              {!index ? <p>{loading ? "Loading saved evidence…" : "Designation data unavailable."}</p> :
                !enabled ? <p>Not tracked by the saved source. No reliable count.</p> :
                records.length === 0 ? <p>No source-linked positive record; this does not mean designation was denied.</p> :
                <ol className="special-designation-records">
                  {records.slice(0, 50).map(({ row, evidence }) => {
                    const id = trialId(row);
                    return <li key={row.id}>
                      <strong>{row.ticker || "Unknown ticker"}</strong> · {row.drug || row.indication || row.programId || row.id}
                      {id && <a href={"/trial/" + encodeURIComponent(id)} target="_blank" rel="noopener noreferrer">Full trial ↗</a>}
                      <a href={evidence.source} target="_blank" rel="noopener noreferrer">Evidence ↗</a>
                      <small>{evidence.designationDate ? "Date: " + evidence.designationDate + " · " : ""}{evidence.verification === "FDA_VERIFIED" ? "FDA verified" : "Source recorded"}</small>
                    </li>;
                  })}
                </ol>}
              {records.length > 50 && <p>Only the first 50 records are shown here.</p>}
            </div>
          </details>
        </div>;
      })}
    </div>
    <button type="button" className="secondary pipeline-group-select-toggle" disabled={available.length===0}
      aria-pressed={allSelected} onClick={() => onChange(allSelected ? [] : available)}>
      {allSelected ? "NONE" : "ALL"}
    </button>
    <p className="special-designation-footnote">{selected.length} checked · — means unavailable, not zero.
      Only source-linked granted designations and reported approvals qualify. Other rules remain separate.
      {asOf ? " · Published: " + asOf : ""}</p>
  </fieldset>;
}
