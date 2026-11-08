import Link from "next/link";
export const metadata={title:"Retired analysis · PDUFA"};
/** Permanently retired. Historical records are available only in the read-only archive. */
export default function RetiredAnalysisPage(){
 return <main style={{maxWidth:900,margin:"32px auto",padding:20}} data-analysis-retired="permanent">
  <h1>This analysis workspace is permanently retired</h1>
  <p>Historical records are preserved read-only. This route cannot calculate ratings, run scans, validate predictions, or feed active analysis.</p>
  <p><Link href="/archive/raas">Read-only historical archive</Link>{" · "}<Link href="/focus">FOCUS</Link>{" · "}<Link href="/pool">POOL</Link></p>
 </main>;
}
