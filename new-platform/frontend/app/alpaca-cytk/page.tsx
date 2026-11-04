import type { Metadata } from "next";
import Link from "next/link";
import type { FdaMilestone } from "../AlpacaStockChart";
import FdaOverlayEditor from "../FdaOverlayEditor";

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
const cytkEvents: FdaMilestone[] = [
  {
    date: "2025-12-19",
    label: "Initial FDA approval — MYQORZO (SEQUOIA-HCM)",
    chartLabel: "FDA approval 12/19",
    detail: "Prior initial approval for obstructive HCM. Separate from the MAPLE-HCM supplemental application.",
    source: "https://ir.cytokinetics.com/press-releases/press-release-details/2025/Cytokinetics-Announces-FDA-Approval-of-MYQORZO-aficamten-for-the-Treatment-of-Adults-with-Symptomatic-Obstructive-Hypertrophic-Cardiomyopathy-to-Improve-Functional-Capacity-and-Symptoms/"
  },
  {
    date: "2026-05-05",
    label: "MAPLE-HCM supplemental NDA acceptance disclosed",
    chartLabel: "FDA sNDA 5/5",
    detail: "Company's dated quarterly announcement confirmed FDA acceptance and November 14 target; the FDA's actual acceptance date was not stated here.",
    source: "https://ir.cytokinetics.com/press-releases/press-release-details/2026/Cytokinetics-Reports-First-Quarter-2026-Financial-Results-and-Provides-Business-Update/default.aspx"
  },
  {
    date: "2026-08-29",
    label: "MAPLE-HCM additional trial analysis released",
    chartLabel: "MAPLE data 8/29",
    detail: "Company disclosed additional MAPLE-HCM and ACACIA-HCM clinical data. Not a new FDA decision.",
    source: "https://ir.cytokinetics.com/press-releases/press-release-details/2026/Cytokinetics-Announces-Additional-Results-from-ACACIA-HCM-and-MAPLE-HCM-Presented-in-Late-Breaking-Clinical-Trial-Session-at-the-European-Society-of-Cardiology-ESC-Congress-2026/default.aspx"
  },
  {
    date: "2026-11-14",
    label: "MAPLE-HCM sNDA — scheduled FDA PDUFA target",
    chartLabel: "PDUFA 11/14",
    detail: "Future FDA target action date, not a guaranteed decision date or predicted approval.",
    source: "https://www.sec.gov/Archives/edgar/data/1061983/000119312526206360/cytk-ex99_1.htm",
    planned: true
  }
];

export default function CytkAlpacaPage() {
  return (
    <main className="shell" style={{maxWidth: 1200, margin: "0 auto", padding: "16px 12px 40px"}}>
      <p><Link href="/">PDUFA Dashboard / Sign in</Link></p>
      <h1>CYTK — Alpaca Stock Price Chart</h1>
      <p>Read-only, authenticated Alpaca market data. Exact registered PDUFA program: <strong>PDUFA-000069</strong>.</p>
      <FdaOverlayEditor ticker="CYTK" programId="PDUFA-000069" verifiedEvents={cytkEvents} />
      <section className="panel" style={{marginTop: 14}}>
        <h2>PDUFA milestone</h2>
        <p><strong>November 14, 2026:</strong> recorded FDA target date for the MYQORZO (aficamten) HCM application. This target is shown on the chart as an <strong>amber dashed FDA milestone</strong> when Alpaca returns the price history. Purple markers show past source-backed events. Dates and source links remain listed even if the market feed is unavailable.</p>
        <p>If the chart says <code>ALPACA_AUTH_FAILED</code>, Alpaca rejected the backend credentials or selected data feed. If it says HTTP 401, sign in on the dashboard and revisit this page.</p>
        <p>Historical research only. The chart makes no trade recommendations and cannot place orders.</p>
      </section>
    </main>
  );
}
