"use client";

import { useEffect, useState } from "react";

type Item = {
  event_key: string; ticker: string; category: string; claim: string; verification_status: string;
  verification_required: string; expected: string; observed: string; reason: string;
  source_url: string; checked_at: string;
};
type Ledger = {
  status: string; asOf: string; total: number; counts: Record<string, number>;
  categories: Record<string, Record<string, number>>; filteredCount: number;
  page: number; pageSize: number; pages: number; items: Item[]; disclaimer: string;
};
const SOURCE_CATEGORIES = ["ALL", "FDA", "SEC", "FINANCIAL", "MARKET", "ISSUER"];
const STATES = ["REVIEW_REQUIRED", "UNAVAILABLE", "VERIFIED", "NOT_APPLICABLE", "ALL"];
const LABELS: Record<string, string> = {
  VERIFIED: "Verified", REVIEW_REQUIRED: "Needs review", UNAVAILABLE: "Unavailable",
  NOT_APPLICABLE: "Not applicable", ALL: "All statuses"
};
function number(n?: number) { return typeof n === "number" ? n.toLocaleString("en-US") : "—"; }

export default function VerificationLedgerPanel() {
  const [category, setCategory] = useState("ALL");
  const [status, setStatus] = useState("REVIEW_REQUIRED");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [version, setVersion] = useState(0);
  const [ledger, setLedger] = useState<Ledger | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    const ctrl = new AbortController();
    const url = new URLSearchParams({ category, status, search, page: String(page) });
    fetch("/api/scan-verification?" + url, { cache: "no-store", signal: ctrl.signal })
      .then(async response => {
        const result: Ledger & {error?: string} = await response.json();
        if (!response.ok) throw Error(result.error || "Verification evidence unavailable");
        return result;
      }).then(result => { if (!ctrl.signal.aborted) { setLedger(result); setError(""); } })
      .catch(err => { if (!ctrl.signal.aborted) { setError(String(err)); setLedger(null); } });
    return () => ctrl.abort();
  }, [category, status, search, page, version]);
  const changeCategory = (value: string) => { setCategory(value); setPage(1); };
  const changeStatus = (value: string) => { setStatus(value); setPage(1); };
  const changeSearch = (value: string) => { setSearch(value); setPage(1); };
  return <section className="panel" aria-label="Item-by-item evidence verification">
    <div className="sectionhead">
      <div><h3>EACH VERIFIED OR UNVERIFIED ITEM — SOURCE LEDGER</h3>
        <p className="subtle">Every saved finding has its own ticker, exact program, check, result, explanation, evidence URL and date. This is not a new independent source check.</p></div>
      <button type="button" className="secondary" onClick={() => setVersion(v => v + 1)}>REFRESH EVIDENCE ↻</button>
    </div>
    {error && <p className="risk-line" role="alert">{error}. No missing rows are treated as verified.</p>}
    {ledger && <>
      <p className="subtle"><strong>{number(ledger.total)} saved checks</strong> · Last recorded verification {ledger.asOf || "unknown"} · {ledger.disclaimer}</p>
      <div className="table-scroll">
        <table>
          <thead><tr><th>Source</th><th>Verified</th><th>Needs review</th><th>Unavailable</th><th>N/A</th><th>Total</th></tr></thead>
          <tbody>{Object.entries(ledger.categories).map(([name, counts]) => <tr key={name}>
            <td><button type="button" className="secondary" onClick={() => changeCategory(name)}>{name}</button></td>
            <td>{number(counts.VERIFIED || 0)}</td><td>{number(counts.REVIEW_REQUIRED || 0)}</td>
            <td>{number(counts.UNAVAILABLE || 0)}</td><td>{number(counts.NOT_APPLICABLE || 0)}</td>
            <td>{number(Object.values(counts).reduce((total,n)=>total+n,0))}</td>
          </tr>)}</tbody>
        </table>
      </div>
    </>}
    <div className="pipeline-row" style={{ display:"flex", flexWrap:"wrap", alignItems:"end", gap:"0.75rem" }}>
      <label>Source section
        <select value={category} onChange={e => changeCategory(e.target.value)}>
          {SOURCE_CATEGORIES.map(s => <option value={s} key={s}>{s}</option>)}
        </select>
      </label>
      <label>Verification result
        <select value={status} onChange={e => changeStatus(e.target.value)}>
          {STATES.map(s => <option value={s} key={s}>{LABELS[s]}</option>)}
        </select>
      </label>
      <label>Find ticker, program or explanation
        <input value={search} onChange={e => changeSearch(e.target.value)} placeholder="Ticker, drug or claim" maxLength={72} />
      </label>
      <button type="button" className="secondary" onClick={() => {
        setCategory("ALL");setStatus("REVIEW_REQUIRED");setSearch("");setPage(1);
      }}>SHOW ITEMS NEEDING REVIEW</button>
    </div>
    {ledger && <>
      <p className="subtle"><strong>{number(ledger.filteredCount)}</strong> matching item(s) · Page {ledger.page} / {Math.max(ledger.pages, 1)}. Select ALL STATUSES to inspect every saved finding.</p>
      <div className="table-scroll">
        <table>
          <thead><tr><th>Ticker</th><th>Program / event</th><th>Source</th><th>Check</th><th>Verification status</th><th>Details</th></tr></thead>
          <tbody>
            {ledger.items.map((item, i) => <tr key={item.event_key + "|" + item.category + "|" + item.claim + "|" + i}>
              <td><strong>{item.ticker || "—"}</strong></td>
              <td>{item.event_key || "—"}</td>
              <td>{item.category}</td><td>{item.claim}</td>
              <td><strong>{LABELS[item.verification_status] || item.verification_status}</strong></td>
              <td><details><summary>Why / source</summary>
                <p><strong>Result:</strong> {item.verification_status} · {item.verification_required === "YES" ? "Required" : "Supplemental"}</p>
                <p><strong>Reason:</strong> {item.reason || "No further explanation published"}</p>
                <p><strong>Expected:</strong> {item.expected || "—"} · <strong>Observed:</strong> {item.observed || "—"}</p>
                <p><strong>Checked:</strong> {item.checked_at || "Not reported"}</p>
                {item.source_url ? <a href={item.source_url} target="_blank" rel="noopener noreferrer">OPEN SAVED PRIMARY SOURCE ↗</a> : <p className="subtle">No cited primary-source URL in the saved record.</p>}
              </details></td>
            </tr>)}
          </tbody>
        </table>
        {!ledger.items.length && <p className="subtle">No matching saved verification rows.</p>}
      </div>
      {ledger.pages > 1 && <div className="pipeline-actions">
        <button type="button" className="secondary" disabled={page <= 1} onClick={() => setPage(p => Math.max(1,p-1))}>PREVIOUS 50</button>
        <span>Page {page} of {ledger.pages}</span>
        <button type="button" className="secondary" disabled={page >= ledger.pages} onClick={() => setPage(p => p+1)}>NEXT 50</button>
      </div>}
    </>}
  </section>;
}
