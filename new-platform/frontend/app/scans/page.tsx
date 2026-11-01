import type {Metadata} from "next";
import PublishedScansPanel from "../PublishedScansPanel";
import DailyResultsPanel from "../DailyResultsPanel";

export const metadata:Metadata={
 title:"SCANS & RESULTS — PDUFA Source Verification and Daily Reports",
 description:"Scan controls, source verification, and dated research results in one workspace."
};

export default function ScansPage(){
 return <main className="shell">
  <h1>SCANS & RESULTS</h1>
  <p>Run and verify source collections, then inspect published daily research findings below.</p>
  <section aria-label="Scan controls and source status">
   <h2>SCANS — Controls & Status</h2>
   <PublishedScansPanel/>
  </section>
  <details style={{marginTop:24,border:"1px solid #45627b",borderRadius:8,padding:16}}>
   <summary style={{cursor:"pointer",fontWeight:700,fontSize:18}}>▼ RESULTS — Daily Research & Historical Reports</summary>
   <DailyResultsPanel/>
  </details>
 </main>;
}
