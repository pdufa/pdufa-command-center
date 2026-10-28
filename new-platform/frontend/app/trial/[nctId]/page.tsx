"use client";

import { useMemo } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import TrialFields from "../../TrialFields";
import ScientificAssessment from "../../ScientificAssessment";
import Scientific800Handoff from "../../Scientific800Handoff";
import TrialSciencePilot from "../../TrialSciencePilot";
import TrialScienceArchive from "../../TrialScienceArchive";
import { PILOT_NCT } from "../../../lib/trial-science-pilot";
import TrialWorkflowCounts from "../../TrialWorkflowCounts";
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
        <Link className="streamlit-fallback" href="/">← Dashboard</Link>
      </nav>
    </header>
    <TrialWorkflowCounts />
    {!valid ?
      <div className="panel" role="alert">Invalid trial identifier. Open a full trial sheet from a linked NCT row in PIPELINE, GEM JR, or GEM.</div> :
      <><TrialFields row={row} standalone /><TrialScienceArchive nctId={nct} />{nct === PILOT_NCT && <TrialSciencePilot />}<ScientificAssessment exactId={"TRIAL|" + nct} /><Scientific800Handoff exactId={"TRIAL|" + nct} /></>
    }
  </main>;
}
