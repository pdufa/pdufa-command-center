import type {Metadata} from "next";
import PublishedScansPanel from "../PublishedScansPanel";
import DailyResultsPanel from "../DailyResultsPanel";
import GoalPage from "../goal/GoalPage";

export const metadata:Metadata={
 title:"SCAN — PDUFA Source Verification, Results & Readiness",
 description:"One workspace for scan controls, published daily results, and research operations readiness."
};

const expanderStyle={marginTop:24,border:"1px solid #45627b",borderRadius:8,padding:16};
const summaryStyle={cursor:"pointer",fontWeight:700,fontSize:18};

export default function ScansPage(){
 return <main className="shell">
  <h1>SCAN</h1>
  <p>Scan controls, daily research findings, and system readiness in one location. Expand sections to inspect detailed records.</p>
  <section aria-label="Scan controls and source status">
   <h2>Scan Controls & Status</h2>
   <PublishedScansPanel/>
  </section>
  <details style={expanderStyle}>
   <summary style={summaryStyle}>RESULTS — Daily Research & Historical Reports</summary>
   <DailyResultsPanel/>
  </details>
  <details style={expanderStyle}>
   <summary style={summaryStyle}>GOAL — Research Operations & Readiness</summary>
   <GoalPage embedded/>
  </details>
 </main>;
}
