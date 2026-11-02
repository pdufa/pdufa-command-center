import type {Metadata} from "next";
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
    <details data-tools-segment="pool" style={{margin:"12px 0",border:"1px solid #a5c7b2",borderRadius:10,background:"#f9fcfa"}}>
      <summary style={{cursor:"pointer",padding:"15px 12px",fontWeight:800,color:"#164f35",minHeight:48}}>
        POOL development stages and FDA designations
      </summary>
      <div style={{padding:"0 10px 10px"}}>
        <PoolStageExplorer/>
      </div>
    </details>
    <details data-tools-segment="phase3" style={{margin:"12px 0",border:"1px solid #a5c7b2",borderRadius:10,background:"#f9fcfa"}}>
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
