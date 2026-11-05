import type {Metadata} from "next";
import Link from "next/link";
import PoolStageExplorer from "../PoolStageExplorer";
import Phase3ReadoutSheets from "../Phase3ReadoutSheets";
import Phase3RegistryPostingSheets from "../Phase3RegistryPostingSheets";
import styles from "../FunnelWorkspace.module.css";

export const metadata:Metadata={
  title:"TOOLS — POOL Development Stages & FDA Designations | PDUFA",
  description:"Read-only selectable POOL stage counts and saved FDA designation/source evidence in two scrollable checkbox dropdowns."
};
export default function ToolsPage(){
  return <main className={styles.root}>
    <header className={styles.header}>
      <p className={styles.eyebrow}>PDUFA · RESEARCH TOOLS</p>
      <h1>TOOLS</h1>
    </header>
    <section data-tools-primary-raas-762="true" style={{border:"2px solid #77a98a",
      borderRadius:11,background:"#f5fcf6",padding:15,margin:"14px 0 18px"}}>
      <h2 style={{margin:"0 0 7px",fontSize:19,color:"#164d30"}}>
       Priority 1 · RAAS scoring setup — 762 trials
      </h2>
      <p style={{margin:"0 0 12px",fontSize:13,lineHeight:1.5}}>
       Open one row per NCT, the 30 TOP + 30 BOTTOM scoring checklists,
       missing evidence, provisional review status and expandable history.
       Incomplete scores stay N/A; this is separate from FDA prediction research. RAAS grading is restricted to the source-classified TOP and BOTTOM spreadsheets; the full 11,000+ trial POOL is for screening only.
      </p>
      <Link href="/raas-762" style={{display:"inline-flex",padding:"11px 16px",
       borderRadius:8,border:"1px solid #6ea582",background:"#deefdf",
       color:"#154d2f",fontWeight:800,textDecoration:"none"}}>
       Open 762-trial RAAS scoring workspace
      </Link>
    </section>
    <details data-tools-segment="pool" style={{margin:"12px 0",border:"1px solid #a5c7b2",borderRadius:10,background:"#f9fcfa"}}>
      <summary style={{cursor:"pointer",padding:"15px 12px",fontWeight:800,color:"#164f35",minHeight:48}}>
        POOL development stages and FDA designations
      </summary>
      <div style={{padding:"0 10px 10px"}}>
        <PoolStageExplorer/>
      </div>
    </details>
    <details id="raas-top-bottom-sheets" data-tools-segment="phase3" style={{margin:"12px 0",border:"1px solid #a5c7b2",borderRadius:10,background:"#f9fcfa"}}>
      <summary style={{cursor:"pointer",padding:"15px 12px",fontWeight:800,color:"#164f35",minHeight:48}}>
        Phase 3 · Public Data Release — TOP 3 and BOTTOM P
      </summary>
      <div style={{padding:"0 10px 10px"}}>
        <Phase3ReadoutSheets/>
      </div>
    </details>
    <details style={{margin:"14px 0",padding:"10px",border:"1px solid #bfd5c7",borderRadius:9}}>
      <summary style={{cursor:"pointer",fontWeight:750,color:"#18543b"}}>
        Supplementary Phase 3 registry-posting spreadsheets and 38-question ratings (not public-readout classification)
      </summary>
      <Phase3RegistryPostingSheets/>
    </details>
  </main>;
}
