import type { Metadata } from "next";
import Link from "next/link";
import AlpacaStockChart from "../AlpacaStockChart";

export const metadata: Metadata = {
  title: "CYTK — Alpaca Chart | PDUFA Command Center",
  description: "Read-only Alpaca daily stock price chart for CYTK, linked to its verified permanent PDUFA program identity."
};

/**
 * Dedicated Safari-friendly chart link for the exact CYTK aficamten
 * MYQORZO November 14, 2026 application record. Registry mapping verified:
 * program_identity.id = 69, source_key =
 * APPLICATION|CYTK|MYQORZO_HCM_20261114.
 * No keys, unauthenticated proxy, simulated bars, or trading endpoints.
 */
export default function CytkAlpacaPage() {
  return (
    <main className="shell" style={{maxWidth: 1200, margin: "0 auto", padding: "16px 12px 40px"}}>
      <p><Link href="/">PDUFA Dashboard / Sign in</Link></p>
      <h1>CYTK — Alpaca Stock Price Chart</h1>
      <p>Read-only, authenticated Alpaca market data. Exact registered PDUFA program: <strong>PDUFA-000069</strong>.</p>
      <AlpacaStockChart ticker="CYTK" programId="PDUFA-000069" />
      <section className="panel" style={{marginTop: 14}}>
        <h2>PDUFA milestone</h2>
        <p><strong>November 14, 2026:</strong> recorded FDA target date for the MYQORZO (aficamten) HCM application. This target is listed separately; it is <strong>not yet overlaid on the price plot</strong>.</p>
        <p>If the chart says <code>ALPACA_AUTH_FAILED</code>, Alpaca rejected the backend credentials or selected data feed. If it says HTTP 401, sign in on the dashboard and revisit this page.</p>
        <p>Historical research only. The chart makes no trade recommendations and cannot place orders.</p>
      </section>
    </main>
  );
}
