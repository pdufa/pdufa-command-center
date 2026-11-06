import type {Metadata} from "next";
import Link from "next/link";
import PoolStageExplorer from "../PoolStageExplorer";
import Phase3SourceOnlySheets from "../Phase3SourceOnlySheets";
import styles from "../FunnelWorkspace.module.css";
export const metadata:Metadata={title:"TOOLS — Trial Stages and FDA Designations | PDUFA",
 description:"Trial source evidence, TOP/BOTTOM Phase 3 spreadsheets and FDA designation controls."};
export default function ToolsPage(){
 return <main className={styles.root}>
  <header className={styles.header}><p className={styles.eyebrow}>PDUFA · RESEARCH TOOLS</p><h1>TOOLS</h1></header>
  <section data-tools-primary-phase3="true" style={{border:"2px solid #43885f",borderRadius:11,
   background:"#f0f9f3",padding:15,margin:"14px 0"}}>
   <h2 style={{margin:"0 0 7px",fontSize:19}}>TOP and BOTTOM Phase 3 spreadsheets</h2>
   <p>Surveys and ratings are cancelled. Trial tables, market-cap screens and source evidence remain active.</p>
   <Link href="/raas-top-bottom">Open TOP and BOTTOM trial spreadsheets</Link>
   <p style={{margin:"10px 0 0",fontSize:13}}><strong>762-trial missing-data recheck:</strong>{" "}
    <Link href="/api/phase3-missing-data-audit?format=csv">Download evidence gaps for all 30 analytical questions (CSV)</Link>.
    Expand “Phase 3 · Public Data Release” below for the interactive per-question audit.</p>
  </section>
  <details data-tools-segment="pool" style={{margin:"12px 0",border:"1px solid #a5c7b2",borderRadius:10,padding:12}}>
   <summary style={{cursor:"pointer",fontWeight:800}}>POOL development stages and FDA designations</summary>
   <PoolStageExplorer/>
  </details>
  <details data-tools-segment="phase3" id="raas-top-bottom-sheets" style={{margin:"12px 0",border:"1px solid #a5c7b2",borderRadius:10,padding:12}}>
   <summary style={{cursor:"pointer",fontWeight:800}}>Phase 3 · Public Data Release — TOP and BOTTOM</summary>
   <Phase3SourceOnlySheets/>
  </details>
 </main>;
}
