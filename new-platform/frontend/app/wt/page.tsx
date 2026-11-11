"use client";

import Workspace from "../Workspace";
import WtEtradeOrderPrep from "../WtEtradeOrderPrep";

/**
 * Restored WT research view. Placement in T ACTIVE saves a research label;
 * it must not submit paper or live broker orders.
 */
export default function WtPage() {
  return <>
    <WtEtradeOrderPrep />
    <Workspace
    initialNav="WT"
    onInspect={(_ticker, _stage, programId) => {
      if (!programId) return;
      document.getElementById("wt-entry-info-" + programId)?.scrollIntoView({ behavior: "smooth", block: "start" });
    }}
    />
  </>;
}
