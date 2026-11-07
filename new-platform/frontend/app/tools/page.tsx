import type {Metadata} from "next";
import Link from "next/link";
import PoolStageExplorer from "../PoolStageExplorer";
import styles from "../FunnelWorkspace.module.css";

export const metadata:Metadata={
 title:"TOOLS — POOL and FOCUS | PDUFA",
 description:"Only the master trial POOL and the results-released Phase 3 FDA/PDUFA candidate list."
};

export default function ToolsPage(){
 return <main className={styles.root}>
  <header className={styles.header}><p className={styles.eyebrow}>PDUFA · RESEARCH TOOLS</p><h1>TOOLS</h1></header>
  <section data-tools-primary-trial-lists="true" style={{border:"2px solid #43885f",borderRadius:11,background:"#f0f9f3",padding:15,margin:"14px 0"}}>
   <h2 style={{margin:"0 0 9px",fontSize:19}}>The two active trial spreadsheets</h2>
   <p><strong>POOL</strong> is the unrestricted master inventory. <strong>FOCUS</strong> contains only $300M–$10B public-company candidates with publicly released Phase 3 results and an ongoing FDA filing or PDUFA path.</p>
   <p><Link href="/pool">Open master POOL</Link>{" · "}<Link href="/focus">Open FOCUS</Link></p>
  </section>
  <details data-tools-segment="pool" style={{margin:"12px 0",border:"1px solid #a5c7b2",borderRadius:10,padding:12}}>
   <summary style={{cursor:"pointer",fontWeight:800}}>POOL development stages and FDA designations</summary>
   <PoolStageExplorer/>
  </details>
 </main>;
}
