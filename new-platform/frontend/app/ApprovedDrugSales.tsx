"use client";

import { useEffect, useId, useState } from "react";
import { salesAmount, salesTicker, type CompanySales } from "../lib/approved-drug-sales";

export function SalesDisclosureView({ data }: { data: CompanySales }) {
  const [periodChoice, setPeriodChoice] = useState("");
  const selectId = useId();
  const selected = data.periods.find(period => period.period === periodChoice) || data.periods[0];
  if (!selected) return <p role="status">No approved-drug sales disclosures are saved for {data.ticker} yet. This does not establish whether the company has approved products.</p>;
  return <div>
    <div className="approved-sales-heading">
      <p>Historical disclosures for <strong>{data.company} ({data.ticker})</strong>.</p>
      <label htmlFor={selectId}>Reporting period <select id={selectId} value={selected.period} onChange={event => setPeriodChoice(event.target.value)}>
        {data.periods.map(period => <option key={period.period}>{period.period}</option>)}
      </select></label>
    </div>
    <div className="approved-sales-summary">
      <article><span>Listed products subtotal · {selected.period}</span><strong>{salesAmount(selected.listedProductsSubtotal)}</strong><small>Only the {selected.products.length} product disclosure{selected.products.length === 1 ? "" : "s"} shown below; see revenue notes.</small></article>
      <article><span>Reported company figure · {selected.period}</span><strong>{selected.companyFigure !== null ? salesAmount(selected.companyFigure) : selected.companyFigureConflict ? "Conflicting disclosures" : "Not recorded"}</strong><small>Shown once. It may include other products, royalties or license revenue; see each disclosure.</small></article>
    </div>
    <div className="approved-sales-products">{selected.products.map(product => <article className="approved-sales-product" key={product.product}>
      <header><strong>{product.product}</strong><strong>{salesAmount(product.individualSales)}</strong></header>
      <p>{product.indication}</p>
      <p className="subtle">{product.note}</p>
      {(product.partnerSales !== null || product.royalties !== null || product.combinedTotal !== null) && <p>
        {product.partnerSales !== null && <span>Partner sales: {salesAmount(product.partnerSales)}. </span>}
        {product.royalties !== null && <span>Royalties: {salesAmount(product.royalties)}. </span>}
        {product.combinedTotal !== null && <span>Disclosed combined total: {salesAmount(product.combinedTotal)}. </span>}
      </p>}
      <div className="approved-sales-evidence"><a href={product.sourceUrl} target="_blank" rel="noopener noreferrer">SEC / issuer disclosure ↗</a><span>Source checked: {product.verifiedOn}</span></div>
    </article>)}</div>
    <p className="subtle">USD millions. Each reporting period is shown separately. Historical approved-product revenue is company context for the selected trial; it is not a sales forecast for the drug under review. The sales ledger does not establish that this company has an upcoming PDUFA date. Confirm the selected program and its regulatory evidence separately.</p>
  </div>;
}

type LoadState = { ticker: string; data?: CompanySales; error?: string };
export default function ApprovedDrugSales({ ticker: value }: { ticker?: string }) {
  const ticker = salesTicker(value || "");
  const [state, setState] = useState<LoadState>({ ticker: "" });
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    if (!ticker) return;
    const controller = new AbortController();
    setState({ ticker });
    async function load() {
      try {
        const response = await fetch("/api/approved-drug-sales?ticker=" + encodeURIComponent(ticker), { cache: "no-store", signal: controller.signal });
        if (!response.ok) throw new Error("Sales disclosures are unavailable. Try again.");
        const data: CompanySales = await response.json();
        if (data.schemaVersion !== 1 || data.ticker !== ticker || !Array.isArray(data.periods) || !["available", "not-recorded"].includes(data.status)) throw new Error("Sales response could not be validated.");
        if (!controller.signal.aborted) setState({ ticker, data });
      } catch (error) {
        if (!controller.signal.aborted) setState({ ticker, error: error instanceof Error ? error.message : "Sales disclosures are unavailable." });
      }
    }
    void load();
    return () => controller.abort();
  }, [ticker, attempt]);
  const current = state.ticker === ticker ? state : { ticker };
  return <section className="approved-sales-panel" aria-label="Previously approved drug sales">
    <h4>PREVIOUSLY APPROVED DRUG SALES</h4>
    {!ticker ? <p>A company ticker is needed to match saved sales disclosures.</p> : current.data ? <SalesDisclosureView key={ticker} data={current.data} /> : current.error ? <div role="status"><p>{current.error}</p><button type="button" className="secondary" onClick={() => setAttempt(count => count + 1)}>RETRY SALES</button></div> : <p role="status">Loading sales disclosures for {ticker}…</p>}
  </section>;
}
