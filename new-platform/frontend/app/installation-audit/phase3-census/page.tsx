import Link from "next/link";
import Phase3CensusExplorer from "./Phase3CensusExplorer";

export const metadata = {
  title: "Phase 3 company census | PDUFA Command Center",
  description: "741 exact-lead-sponsor historical Phase 3 trial records. Not qualified Pipeline candidates.",
};

export default function Phase3CensusPage() {
  return <main style={{maxWidth:1280,margin:"0 auto",padding:"26px 18px",fontFamily:"system-ui,sans-serif",color:"#17212b"}}>
    <p><Link href="/installation-audit">← MAIN installation tracker</Link></p>
    <h1>Phase 3 market-cap census — trial-level research inventory</h1>
    <p><strong>October 26, 2026 research snapshot.</strong> 741 unique trial IDs
      from 130 exact-matched listed-company tickers in the $300M–$10B
      market-cap range, across all years. This is a conservative inventory
      with incomplete sponsor relationships and unavailable market-cap records.
      It is not a complete qualified Pipeline, and has no verified FDA PDUFA
      dates or validated prediction outputs.</p>
    <Phase3CensusExplorer/>
  </main>;
}
