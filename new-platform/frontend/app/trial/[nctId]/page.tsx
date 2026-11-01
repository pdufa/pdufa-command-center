"use client";

import { useMemo } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import TrialFields from "../../TrialFields";
import TrialWorkflowCounts from "../../TrialWorkflowCounts";
import FullTrialTimeline from "../../FullTrialTimeline";
import type { Candidate } from "../../Workspace";

export default function FullTrialSheet() {
  const params = useParams<{nctId:string}>();
  const nct = typeof params.nctId === "string" ? params.nctId.toUpperCase() : "";
  const valid = /^NCT\d{8}$/.test(nct);
  const row = useMemo<Candidate>(() => ({
    id: "TRIAL|" + nct,
    ticker: "CLINICAL TRIAL",
    drug: nct,
    nctId: nct,
  }), [nct]);

  return <main className="shell standalone-trial-sheet">
    <header className="trial-sheet-top">
      <div>
        <span className="topline">PDUFA COMMAND CENTER · FULL CLINICAL TRIAL SHEET</span>
        <h1>{valid ? nct : "Invalid trial ID"}</h1>
        <p className="subtle">One exact ClinicalTrials.gov trial · full saved registry record · original evidence preserved</p>
      </div>
      <nav aria-label="Trial sheet navigation">
        <Link style={{color:"#17644c"}} href="/">← Dashboard</Link>
      </nav>
    </header>
    {valid&&<FullTrialTimeline nctId={nct}/>}
    <TrialWorkflowCounts />
    {!valid ?
      <div className="panel" role="alert">Invalid trial identifier. Open a full trial sheet from a linked NCT record in POOL or PIPELINE.</div> :
      <TrialFields row={row} standalone />
    }
  </main>;
}
