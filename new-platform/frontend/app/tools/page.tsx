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
    <Phase3RegistryPostingSheets/>
    <details style={{margin:"14px 0",padding:"10px",border:"1px solid #bfd5c7",borderRadius:9}}>
      <summary style={{cursor:"pointer",fontWeight:750,color:"#18543b"}}>
        Separate issuer-announcement release verification · 2 historically unreleased, 3 released
      </summary>
      <Phase3ReadoutSheets/>
    </details>
    <PoolStageExplorer/>
  </main>;
}
