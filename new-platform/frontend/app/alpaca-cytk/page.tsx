import type { Metadata } from "next";
import Link from "next/link";
import {cytkEvents} from "../../lib/cytk-fda-overlay";
import FdaOverlayEditor from "../FdaOverlayEditor";
import fdaAutoEvents from "./fda-auto-events.json";

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
      <FdaOverlayEditor
        ticker="CYTK"
        programId="PDUFA-000069"
        verifiedEvents={cytkEvents}
        categories={fdaAutoEvents.categories}
      />
      <section className="panel" style={{marginTop:12,padding:14}}>
        <h2>Automatic FDA milestone watcher</h2>
        <p><strong>Nightly check enabled</strong> for the exact FDA application NDA 219083.
          Only action records with verified FDA status, an actual dated submission, and an exact application match
          are automatically added. No event is plotted because a PDUFA target day arrived.</p>
        <p><strong>Official source:</strong> <a href="https://open.fda.gov/apis/drug/drugsfda/" target="_blank" rel="noopener noreferrer">
          Drugs@FDA submission actions</a> ·
          <strong> Last successful published check:</strong> {fdaAutoEvents.checkedAt?new Date(fdaAutoEvents.checkedAt).toLocaleString("en-US",{timeZone:"America/Los_Angeles",dateStyle:"medium",timeStyle:"short"}):"Awaiting first scheduled source check"} ·
          <strong> Automatic markers:</strong> {fdaAutoEvents.eventCount}</p>
        <details>
          <summary style={{cursor:"pointer",fontWeight:700}}>
            Trackable FDA event categories ({fdaAutoEvents.categories.length})
          </summary>
          <div style={{marginTop:8,fontSize:13}}>
            <p><strong>Automatically plotted now:</strong> Approved or tentative Drugs@FDA
            supplemental submission actions on this exact NDA.</p>
            <p><strong>Registered, but awaiting a separate official-source connection:</strong>
            CRLs, AdComs, manufacturing inspections, FDA correspondence, PDUFA date changes,
            designations, label/REMS changes and resubmissions. These cannot safely appear on the chart
            until evidence with a matching application, an actual date and a source document becomes available.</p>
            <ul style={{paddingLeft:20}}>
              {fdaAutoEvents.categories.map(item=><li key={item.id}>
                {item.title} — {item.mode==="official_drugsfda"?"Official Drugs@FDA feed":"Separate source required"}
              </li>)}
            </ul>
          </div>
        </details>
        <p style={{fontSize:12,color:"#546477"}}>An FDA source may update after the underlying action date. This feed
          does not cover all submissions or complete response letters; supplement status alone does not establish
          that the MAPLE-HCM label expansion was decided. Source corrections require review rather than silently
          changing historical chart markers.</p>
      </section>
      <section className="panel" style={{marginTop: 14}}>
        <h2>PDUFA milestone</h2>
        <p><strong>November 14, 2026:</strong> recorded FDA target date for the MYQORZO (aficamten) HCM application. This target is shown on the chart as an <strong>amber dashed FDA milestone</strong> when Alpaca returns the price history. Purple markers show past source-backed events. Dates and source links remain listed even if the market feed is unavailable.</p>
        <p>If the chart says <code>ALPACA_AUTH_FAILED</code>, Alpaca rejected the backend credentials or selected data feed. If it says HTTP 401, sign in on the dashboard and revisit this page.</p>
        <p>Historical research only. The chart makes no trade recommendations and cannot place orders.</p>
      </section>
    </main>
  );
}
