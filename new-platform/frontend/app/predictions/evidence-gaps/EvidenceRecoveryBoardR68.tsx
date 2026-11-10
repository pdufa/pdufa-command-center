"use client";

import {useMemo,useState} from "react";
import Link from "next/link";
import {FOCUS_R68_EVIDENCE_RECOVERY} from "../../../lib/focus-r68-evidence-recovery";
import {FOCUS_R69_REGISTRY_PUBLICATION_LEADS} from "../../../lib/focus-r69-original-publication-leads";
import {FOCUS_R70_PUBLICATION_TRIAGE} from "../../../lib/focus-r70-publication-abstract-triage";
import OriginalPublicationLeadsR69 from "./OriginalPublicationLeadsR69";
import styles from "./EvidenceRecoveryBoardR68.module.css";

/** Source availability queue only: not a clinical grade, time-priority
 * medical determination, FDA cycle verification, or calibrated prediction.
 */
export default function EvidenceRecoveryBoardR68(){
  const work=FOCUS_R68_EVIDENCE_RECOVERY;
  const [query,setQuery]=useState("");
  const [filter,setFilter]=useState("ALL");
  const normalized=query.trim().toLowerCase();
  const rows=useMemo(()=>work?.rows.filter(row=>{
    const hasText=!normalized||[row.ticker,row.nct,...row.applicationCycles]
      .join(" ").toLowerCase().includes(normalized);
    const hasFilter=filter==="ALL"||
      (filter==="PRIMARY"&&!row.sourcePrimaryTableAvailable)||
      (filter==="SAFETY"&&!row.sourceSafetyArmsAvailable)||
      (filter==="METHODS"&&!row.sourcePdfPageLeadsAvailable)||
      (filter==="POSTED"&&row.sourcePrimaryTableAvailable&&
       row.sourceSafetyArmsAvailable&&row.sourcePdfPageLeadsAvailable);
    return hasText&&hasFilter;
  })??[],[work,normalized,filter]);

  if(!work)return <section aria-label="R68 scientific evidence recovery board"
    className={styles.shell}><h2>Scientific evidence recovery</h2>
    <p role="alert">Source provenance or exact trial/application membership
      could not be verified. Research findings have been withheld.</p></section>;

  return <section className={styles.shell}
      aria-label="R68 scientific evidence recovery board">
    <div className={styles.eyebrow}>MAIN · REVISION 68 · SOURCE-ONLY RESEARCH</div>
    <h1>Scientific evidence recovery · 29 FOCUS trials</h1>
    <p className={styles.intro}>This worklist shows what is present in the
      <strong> archived current registry and protocol/SAP source copies</strong>,
      and what requires independent recovery or review. Missing a field in
      these copies is <strong>not proof of a negative or failed trial</strong>.
      Research ordering reflects only missing-source categories, never the
      likelihood of FDA approval or treatment benefit.</p>
    <div className={styles.stats}>
      <div><small>Unique FOCUS trials</small><strong>{work.uniqueTrials}</strong></div>
      <div><small>Provisional application groups</small><strong>{work.provisionalApplicationCycles}</strong></div>
      <div><small>Current posted primary</small><strong>{work.postedPrimaryTrials}/29</strong></div>
      <div><small>Current safety-arm tables</small><strong>{work.currentSafetyArmTrials}/29</strong></div>
      <div><small>Current method PDF page leads</small><strong>{work.trialsWithCurrentPdfPageLeads}/29</strong></div>
      <div><small>Signed independent reviews</small><strong>0</strong></div>
    </div>
    <p className={styles.notice}>All <strong>{work.scientificDomainSourcePositions}</strong>
      scientific source-review slots remain <strong>UNASSESSED</strong>.
      The <strong>{work.originalMachinePageLeads}</strong> original PDF
      page leads are not finished tests. FDA approval/CRL/delay: <strong>ABSTAIN</strong>.
      Historical predictive accuracy: <strong>NOT CALIBRATED</strong>.</p>
    {FOCUS_R69_REGISTRY_PUBLICATION_LEADS&&<p className={styles.notice}
      aria-label="R69 original publication lead coverage">
      New original registry reference recovery: <strong>
      {FOCUS_R69_REGISTRY_PUBLICATION_LEADS.candidateReferenceCount}
      </strong> PubMed literature leads listed across <strong>
      {FOCUS_R69_REGISTRY_PUBLICATION_LEADS.casesWithUnverifiedPublicationLeads}
      </strong> of the 17 NCTs without posted primary tables. They are
      <strong> unverified references, not accepted exact-NCT trial results</strong>.
      The remaining 10 have no PubMed reference in the retained registry copy.
    </p>}
    {FOCUS_R70_PUBLICATION_TRIAGE&&<p className={styles.notice}
      aria-label="R70 publication abstract role counts">
      Phase 3 primary result candidates from article abstracts:
      <strong> {FOCUS_R70_PUBLICATION_TRIAGE.abstractPrimaryReportCandidates}</strong>
      {" "}publications for{" "}
      <strong>{FOCUS_R70_PUBLICATION_TRIAGE.uniqueTrialsWithPrimaryReportCandidates}</strong>
      {" "}exact NCTs. Other roles:{" "}
      <strong>{FOCUS_R70_PUBLICATION_TRIAGE.additionalSameTrialAnalyses}</strong>
      {" "}same-trial secondary analyses,{" "}
      <strong>{FOCUS_R70_PUBLICATION_TRIAGE.protocolPapers}</strong>
      {" "}protocol,{" "}
      <strong>{FOCUS_R70_PUBLICATION_TRIAGE.phase2NotPhase3}</strong>
      {" "}Phase 2 component,{" "}
      <strong>{FOCUS_R70_PUBLICATION_TRIAGE.earlierPhaseOtherCohort}</strong>
      {" "}earlier-phase cohort and{" "}
      <strong>{FOCUS_R70_PUBLICATION_TRIAGE.backgroundNotPivotal}</strong>
      {" "}background paper. None has passed independent full-text
      statistical adjudication; no scientific grades or FDA probabilities.
    </p>}
    <div className={styles.controls}>
      <label>Search ticker, NCT or application
        <input type="search" aria-label="Search source recovery trials"
          value={query} onChange={e=>setQuery(e.target.value)}
          placeholder="SVRA, CAPR, NCT..." />
      </label>
      <label>Original-source coverage
        <select aria-label="Filter source recovery trials" value={filter}
          onChange={e=>setFilter(e.target.value)}>
          <option value="ALL">All 29 source records</option>
          <option value="PRIMARY">Primary result table not posted here</option>
          <option value="SAFETY">Safety-arm table not posted here</option>
          <option value="METHODS">No current PDF page lead</option>
          <option value="POSTED">All three source types represented</option>
        </select>
      </label>
    </div>
    <p className={styles.results} role="status">
      Showing <strong>{rows.length}</strong> of {work.uniqueTrials} exact NCTs.
      No source category filter changes clinical assessment status.
    </p>
    <div className={styles.list}>
      {rows.map(trial=><details className={styles.case} key={trial.nct}
        aria-label={"R68 evidence for "+trial.nct}>
        <summary>
          <div className={styles.identity}><strong>{trial.ticker} · {trial.nct}</strong>
            <small>{trial.registryReportedPhase} · {trial.registryReportedStatus}</small>
            <small>Source updated {trial.originalSourceUpdatedDate}</small>
          </div>
          <div className={styles.sourceCounts}>
            <span>Primary: {trial.currentPostedPrimaryTables>0?
              trial.currentPostedPrimaryTables+" table(s)":"Not posted here"}</span>
            <span>Safety: {trial.currentSafetyArms>0?
              trial.currentSafetyArms+" arm(s)":"Not posted here"}</span>
            <span>Method PDFs: {trial.currentPdfFilesWithMachinePageLeads>0?
              trial.currentPdfFilesWithMachinePageLeads+" file(s)":"No page leads"}</span>
          </div>
          <span className={styles.kind}>Assessment: UNASSESSED ·
            {trial.missingInRetainedRegistryCopyCount} categories without source in this archive</span>
        </summary>
        <div className={styles.content}>
          <h2>Source recovery and independent review requirements</h2>
          <p>These are evidence tasks, <strong>not scored scientific conclusions</strong>.
            Source-reported status does not certify FDA submission or regulatory action.</p>
          <ol>{trial.sourceRecoveryTasks.map(item=><li key={item.key}>
            <strong>{item.label}</strong><span>{item.detail}</span>
          </li>)}</ol>
          {trial.designAndOriginalSourceExceptions.length>0&&
            <details className={styles.exceptions}><summary>
              Dated registry and original-source exception flags ·
              {trial.designAndOriginalSourceExceptions.length}
            </summary><ul>{trial.designAndOriginalSourceExceptions.map((x,i)=>
              <li key={i}>{x}</li>)}</ul>
            </details>}
          {!trial.sourcePrimaryTableAvailable&&
            <OriginalPublicationLeadsR69 nct={trial.nct}/>}
          <div className={styles.links}>
            <Link href={trial.assessmentUrl}>Open complete scientific assessment</Link>
            <Link href={trial.originalMethodPageUrl}>Open original PDF page leads</Link>
            <a href={trial.sourceRegistryUrl} target="_blank" rel="noopener noreferrer">
              Original ClinicalTrials.gov record</a>
          </div>
          <p className={styles.disclaimer}>Trial level:
            <strong> UNASSESSED SOURCE ONLY</strong>. Validated FDA prediction:
            <strong> ABSTAIN</strong>. No qualified review signatures, measured
            accuracy or FDA probability are represented.</p>
        </div>
      </details>)}
      {rows.length===0&&<p className={styles.noResults}>
        No matching original-source records. Reset search or filter.</p>}
    </div>
    <p className={styles.footer}>Source archives:
      <a href={work.originalSources.r60} target="_blank" rel="noopener noreferrer">R60 registry endpoints and safety</a>,
      <a href={work.originalSources.r63} target="_blank" rel="noopener noreferrer">R63 protocol/SAP pages</a>,
      <a href={work.originalSources.r65} target="_blank" rel="noopener noreferrer">R65 independent review intake</a>,
      <a href={work.originalSources.r66} target="_blank" rel="noopener noreferrer">R66 dated registry phase</a>.
      No reviewer data-entry endpoint is enabled here and production is unchanged.</p>
  </section>;
}
