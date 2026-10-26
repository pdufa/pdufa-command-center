import pinned from "../data/main-phase3-qualification-snapshot-20261026.json";
import MainPhase3NightlyHealth from "./MainPhase3NightlyHealth";
import {parsePinnedResearchSnapshot} from "../lib/main-phase3-research-snapshot";
import styles from "./MainPhase3ResearchPanel.module.css";

const number=(n:number)=>n.toLocaleString("en-US");
function Stat({label,value,note}:{label:string;value:string;note:string}){
  return <div className={styles.stat}>
    <span>{label}</span><strong>{value}</strong><small>{note}</small>
  </div>;
}

/** Archived original-source research cohort. Never the live Pipeline/GEM list. */
export default function MainPhase3ResearchPanel() {
  let report: ReturnType<typeof parsePinnedResearchSnapshot>;
  try {report=parsePinnedResearchSnapshot(pinned);}
  catch {return <section className={styles.shell} aria-label="MAIN historical research scorecard">
    <p role="alert">MAIN historical research snapshot did not pass identity validation. Counts withheld.</p>
  </section>;}
  return <section className={styles.shell} aria-label="MAIN historical Phase 3 research qualification scorecard">
    <div className={styles.header}>
      <div>
        <h2>MAIN · Phase 3 historical research</h2>
        <p>Archived original-source verification · {report.sourcePacificDate} · <strong>NOT LIVE</strong></p>
      </div>
      <a href={report.sourceRunUrl} target="_blank" rel="noopener noreferrer">
        View verified GitHub run #{report.sourceRunId}
      </a>
    </div>
    <p className={styles.scope} role="note">
      These <strong>741 historical NCT study records</strong> are not the current Pipeline,
      GEM JR or GEM membership lists. This dated research report does not update those
      lists, trading signals, or their independent FS/FA presets.
    </p>
    <div className={styles.metrics} aria-label="Primary research progress metrics">
      <Stat label="Original registry identities" value={number(report.historicalTrialCount)+"/741"}
            note="Trial source identity; not clinical qualification"/>
      <Stat label="Mandatory checks verified" value={number(report.gateChecksPass)+"/"+number(report.gateChecksDenominator)}
            note="Only the registry-identity gate is verified"/>
      <Stat label="Mandatory checks unresolved" value={number(report.gateChecksReview)+"/"+number(report.gateChecksDenominator)}
            note="Eight external gates per historical trial"/>
      <Stat label="Commercial-rights submissions" value={number(report.rightsSlotsWithSubmissions)+"/"+number(report.rightsReviewChecklistSlots)}
            note="Six source-review checks for each historical trial"/>
    </div>
    <p className={styles.qualification}>
      <strong>Qualified Pipeline count: UNKNOWN (not zero).</strong> Independently verified
      current commercial rights: <strong>{report.independentlyVerifiedCurrentRightsTrials}/741</strong>.
      No trial is promoted because a source URL, SEC index or reviewer assertion exists.
    </p>
    <MainPhase3NightlyHealth />
    <details className={styles.details}>
      <summary>All nine mandatory checks · PASS / FAIL / REVIEW</summary>
      <div className={styles.tableScroll}>
        <table>
          <thead><tr><th scope="col">Requirement</th><th scope="col">PASS / 741</th>
            <th scope="col">FAIL / 741</th><th scope="col">REVIEW / 741</th></tr></thead>
          <tbody>{report.mandatoryGates.map(gate=><tr key={gate.gate}>
            <th scope="row">{gate.gate.replaceAll("_"," ")}</th>
            <td>{number(gate.pass)}/741</td><td>{number(gate.fail)}/741</td>
            <td>{number(gate.review)}/741</td>
          </tr>)}</tbody>
        </table>
      </div>
    </details>
    <details className={styles.details}>
      <summary>Secondary source coverage and unresolved blockers</summary>
      <div className={styles.secondary}>
        <dl>
          <div><dt>Trial records with provisional registered drugs</dt><dd>{report.trialsWithProvisionalRegisteredDrug}/741</dd></div>
          <div><dt>SEC issuer indexes retrieved</dt><dd>{report.secIssuerIndexesFetched}/130</dd></div>
          <div><dt>SEC primary-document requests attempted</dt><dd>{report.secPrimaryDocumentsAttempted}/{report.secPrimaryDocumentsSelected}</dd></div>
          <div><dt>SEC documents not attempted, identifying contact missing</dt><dd>{report.secPrimaryDocumentsNotAttemptedMissingContact}/{report.secPrimaryDocumentsSelected}</dd></div>
          <div><dt>SEC primary documents fetched</dt><dd>{report.secPrimaryDocumentsFetched}/{report.secPrimaryDocumentsSelected}</dd></div>
          <div><dt>Historical trials with issuer primary text</dt><dd>{report.trialIssuerTextAvailable}/741</dd></div>
          <div><dt>Rights review slots with reviewer reports</dt><dd>{report.rightsSlotsWithReviewerReports}/{report.rightsReviewChecklistSlots}</dd></div>
          <div><dt>Trials with any submitted rights evidence</dt><dd>{report.trialsWithAnySubmissions}/741</dd></div>
        </dl>
        <p>Remaining dependency: configure a legitimate <code>SEC_USER_AGENT</code> identifying
          contact to attempt SEC document retrieval. A missing document does not imply absent rights.</p>
      </div>
    </details>
    <p className={styles.foot}>Pinned to GitHub verification run #{report.sourceRunId}, not a current scan.
      A newer GitHub run does not automatically change this archived display.
      Historical research counts must never be added to the live Pipeline or GEM counts.
    </p>
  </section>;
}
