import type {Metadata} from "next";
import PoolStageExplorer from "../PoolStageExplorer";
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
    <PoolStageExplorer/>
  </main>;
}
