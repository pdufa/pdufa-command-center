import type {Metadata} from "next";
import Link from "next/link";
import {MAIN_DAILY_EVIDENCE} from "../../lib/main-daily-evidence";
import {FOCUS_FINAL_TRIAL_AUDIT} from "../../lib/focus-final-gate-checks";
import InstallationProgressDashboard from "./InstallationProgressDashboard";

export const metadata:Metadata={
  title:"MAIN · Core Platform and Pipeline acceptance | PDUFA",
  description:"Seven active MAIN checks: Core Platform and Pipeline, with immutable legacy acceptance history."
};

const release={
  date:"November 7, 2026",
  commit:"87654a48170ad1cfa27f61aafcfcd6a0029c45c9",
  ci:"https://github.com/pdufa/pdufa-command-center/actions/runs/42390222836",
  frontend:"https://github.com/pdufa/pdufa-command-center/actions/runs/42390222867",
  nct:"https://github.com/pdufa/pdufa-command-center/actions/runs/42390222945",
  wt:"https://github.com/pdufa/pdufa-command-center/actions/runs/42390222920",
  deployment:"https://vercel.com/pdufa/pdufa-new-dashboard/7MYqsncqaDWQHuJJabtfCd7d21ze"
} as const;

const card={border:"1px solid #c9d9d1",borderRadius:10,padding:16,background:"#fff"} as const;
const fine={fontSize:13,lineHeight:1.55,color:"#46594d"} as const;
const grid={display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(min(100%,250px),1fr))",gap:12} as const;

/** The user-retained MAIN acceptance scope: Core Platform (3) + Pipeline (4).
 * These gate IDs come from the immutable dated historical inventory. Keeping
 * a gate in the active checklist does NOT make its old status current evidence.
 * All removed branches remain in the historical audit, not the active scope.
 * Trial-specific Pipeline review is restricted to final FOCUS NCTs.
 */
export const MAIN_ACTIVE_GATE_IDS=[
  "core-platform.code","core-platform.deployment","core-platform.runtime",
  "pipeline.code","pipeline.deployment","pipeline.runtime","pipeline.evidence"
] as const;

function Status({name,status,detail}:{name:string;status:string;detail:string}){
  return <section style={card}><h2 style={{fontSize:18,margin:"0 0 10px"}}>{name}</h2>
    <p style={{fontSize:20,fontWeight:700,margin:"0 0 8px"}}>{status}</p>
    <p style={{...fine,margin:0}}>{detail}</p>
  </section>;
}

export default function MainStatus(){
  const checked=MAIN_DAILY_EVIDENCE.valid;
  const historicalDay=checked?MAIN_DAILY_EVIDENCE.history.at(-1)?.asOf:null;
  const activeGateRows=checked?MAIN_ACTIVE_GATE_IDS.map(id=>{
    const observation=MAIN_DAILY_EVIDENCE.observations.find(g=>g.id===id);
    if(!observation)return null;
    return {...observation,
      sourceKind:"Historical observation · not fresh acceptance",
      note:id.startsWith("pipeline.")
        ?"Reverify this Pipeline installation requirement against the "+FOCUS_FINAL_TRIAL_AUDIT.trialCount+" exact NCTs in the current final FOCUS list. The 2026-10-26 status is archival; other clinical phases and research datasets are excluded."
        :observation.note};
  }).filter((g):g is NonNullable<typeof g>=>g!==null):[];
  const activeScopeValid=checked&&activeGateRows.length===7&&
    MAIN_ACTIVE_GATE_IDS.every(id=>activeGateRows.some(g=>g.id===id))&&
    new Set(activeGateRows.map(g=>g.id)).size===7;
  const historicalProofsInActiveScope=activeGateRows.filter(g=>g.status==="Verified").length;
  return <main className="shell" style={{maxWidth:1100,margin:"0 auto",padding:"20px 12px 45px"}}>
    <div className="topline">PDUFA COMMAND CENTER · MAIN</div>
    <h1>MAIN · Technical status and prediction readiness</h1>
    <section data-testid="main-owner-only" style={{...card,background:"#eefaf5",margin:"12px 0",borderColor:"#a0cbb7"}}>
      <strong>OWNER-ONLY ASSESSMENTS · LEVELS 1–20</strong>
      <p style={fine}>Only you review, accept, reject or revise assessments.
        No external clinical or statistical reviewer, source attestor, independent challenger or third-party signoff is required.
        Exact-NCT source evidence, phase checks, missingness, history, security and prospective calibration remain internal controls.
        No owner review or validated FDA probability is implied by system readiness.</p>
    </section>
    <p>This is an evidence and operating-status view, <strong>not a third active trial list</strong>.
      POOL is the complete research inventory; FOCUS is the screened post-Phase-3 population.
      P3 and P3 POST-DATA are retired spreadsheet identities; historical evidence remains read-only. Clinical Phase 3 research remains valid for FOCUS and owner-controlled medical analysis.</p>
    <section style={{...card,margin:"18px 0"}} aria-label="PDUFA Precision Monitoring Dashboard">
      <h2 style={{marginTop:0}}>Precision Monitoring Dashboard</h2>
      <p style={fine}>Read-only installation progress, live source observations, 12 medical-level checkpoints,
      trial evidence gaps, change history and Telegram delivery readiness. Missing or unvalidated predictions remain ABSTAIN.</p>
      <Link href="/precision-monitoring">Open Precision Monitoring Dashboard</Link>
    </section>
    <InstallationProgressDashboard/>
    <section style={{...card,margin:"18px 0"}} aria-label="Dated release verification">
      <h2 style={{marginTop:0}}>Verified release snapshot · {release.date}</h2>
      <p><strong>Production deployment: READY.</strong> The associated main-branch commit is{" "}
        <code>{release.commit.slice(0,8)}</code>. On that commit, the Command Center CI
        (including backend regressions, Next.js typecheck/tests/build, backup integrity,
        source identity and duplicate checks) completed successfully.</p>
      <p style={fine}>These are exact release checks, not a claim that every protected runtime
        screen, current FDA source, clinical score or prediction has been accepted.</p>
      <div style={{display:"flex",gap:16,flexWrap:"wrap"}}>
        <a href={release.ci} target="_blank" rel="noopener noreferrer">Command Center CI</a>
        <a href={release.frontend} target="_blank" rel="noopener noreferrer">Frontend checks</a>
        <a href={release.nct} target="_blank" rel="noopener noreferrer">NCT checks</a>
        <a href={release.wt} target="_blank" rel="noopener noreferrer">WT UI checks</a>
        <a href={release.deployment} target="_blank" rel="noopener noreferrer">Production deployment</a>
      </div>
    </section>
    <section style={{...card,margin:"16px 0"}} aria-label="Authenticated production runtime smoke evidence">
      <h2 style={{marginTop:0}}>Verified production runtime smoke · November 7, 2026</h2>
      <p><strong>PASS — live production checks.</strong> The separately executed installation smoke
        passed public page checks, anonymous API isolation, normal dashboard login,
        backend and PostgreSQL health, POOL versus historical Phase 3 queue reconciliation,
        and distinct TOOLS Phase / FDA designation intersection counts.</p>
      <p>The all-phase $300M–$10B dated market-cap screen reconciled
        <strong> 2,698 of 11,644</strong> source clinical trial records:
        115 lacked verified cap data, 8,830 were outside the cap range, and 1 trial
        was excluded by the listing screen. These are <strong>not</strong> 2,698 completed
        Phase 3 programs or a certified FOCUS population. The original-source
        issuer listing, licensing rights, pivotal readout and FDA application dates
        remain subject to your own eligibility and original-source checks; no outside reviewer is required.</p>
      <p style={fine}>This is a time-specific read-only runtime probe and not
        complete technical acceptance, a passed backup restore, a new trial promotion,
        or validated FDA prediction accuracy.</p>
      <a href="https://github.com/pdufa/pdufa-command-center/actions/runs/42394008611"
        target="_blank" rel="noopener noreferrer">Inspect successful production smoke run and exact log evidence</a>
    </section>
    <div style={grid} aria-label="Separate evidence gates">
      <Status name="MAIN · technical acceptance"
        status="Still open"
        detail="The active MAIN checklist contains only Core Platform and Pipeline checks. Evidence from the dated 31-gate archive is not an automatic new acceptance."/>
      <Status name="SCIENCE · trial review"
        status="Owner review pending"
        detail="Phase-correct source evidence and owner-reviewed scientific investigation coverage remain incomplete. No outside reviewer is required; published facts alone are not assessment scores."/>
      <Status name="OUTCOME · FDA prediction"
        status="ABSTAIN"
        detail="No prospectively calibrated PASS / CRL / EXTENSION forecast has passed the application-cycle, freeze, outcome and historical backtest checks. The owner controls assessment acceptance."/>
    </div>
    <section style={{...card,marginTop:16}} aria-label="Active MAIN Core Platform and Pipeline gates">
      <h2 style={{marginTop:0}}>Current MAIN scope · 7 gates · Core Platform and Pipeline only</h2>
      <p style={fine}>Only two sections remain in the active MAIN checklist: <strong>Core Platform (3)</strong> and <strong>Pipeline (4)</strong>.
        The other six former sections (24 gates) have been removed from active MAIN acceptance.
        Core Platform checks the shared infrastructure; Pipeline trial checks apply only to the {FOCUS_FINAL_TRIAL_AUDIT.trialCount} exact-NCT final FOCUS listing.
        Separate FDA monitoring, source analysis and reporting continue operating. RAAS is permanently retired from active analysis, predictions, scans and installation requirements; its historical records remain read-only archives.
        Historic October 26 statuses are not fresh verification, and no archived scan is restored.</p>
      {activeScopeValid ? <details>
        <summary style={{cursor:"pointer",fontWeight:700}}>
          View all {activeGateRows.length} active MAIN gates · {historicalProofsInActiveScope} October 26 historical proof recorded,
          {" "}{activeGateRows.length-historicalProofsInActiveScope} without historical verification · all require current-scope review
        </summary>
        <div style={{overflowX:"auto",marginTop:12}}>
          <table style={{width:"100%",borderCollapse:"collapse",fontSize:13,minWidth:600}}>
            <thead><tr>
              <th scope="col" style={{textAlign:"left",padding:9,borderBottom:"2px solid #bdcdc4"}}>Gate</th>
              <th scope="col" style={{textAlign:"left",padding:9,borderBottom:"2px solid #bdcdc4"}}>Audit state</th>
              <th scope="col" style={{textAlign:"left",padding:9,borderBottom:"2px solid #bdcdc4"}}>Evidence gap / finding</th>
            </tr></thead>
            <tbody>{activeGateRows.map((gate,index)=><tr key={gate.id} style={{background:index%2?"#f7faf8":"#fff"}}>
              <th scope="row" style={{textAlign:"left",padding:9,borderBottom:"1px solid #e3ebe7",verticalAlign:"top"}}>{gate.id}</th>
              <td style={{padding:9,borderBottom:"1px solid #e3ebe7",verticalAlign:"top",whiteSpace:"nowrap"}}>{gate.status}</td>
              <td style={{padding:9,borderBottom:"1px solid #e3ebe7",verticalAlign:"top"}}><span style={{fontStyle:"italic"}}>{gate.sourceKind}.</span>{" "}{gate.note}{" "}
                <a href={gate.evidenceUri} target="_blank" rel="noopener noreferrer">Source</a>
              </td>
            </tr>)}</tbody>
          </table>
        </div>
      </details> : <p role="alert">The 7-check Core Platform / Pipeline active scope cannot be established from saved evidence.</p>}
    </section>
    <section style={{...card,marginTop:16}} aria-label="Active final FOCUS trial acceptance cohort">
      <h2 style={{marginTop:0}}>Final trial acceptance · {FOCUS_FINAL_TRIAL_AUDIT.trialCount} FOCUS trials only</h2>
      <p><strong>{FOCUS_FINAL_TRIAL_AUDIT.trialCount} unique NCTs</strong> across {FOCUS_FINAL_TRIAL_AUDIT.uniqueCompanies} recorded tickers, from the final-list Google Sheets snapshot dated {FOCUS_FINAL_TRIAL_AUDIT.asOf}.
        These are the <strong>only trial records</strong> subject to current MAIN acceptance gate assessment. POOL and the historical Phase 3/TOOLS all-phase tallies stay as references and do not count toward the final-trial gate denominator.</p>
      <p><strong>{FOCUS_FINAL_TRIAL_AUDIT.totalChecks} trial-specific evidence checks</strong> ({FOCUS_FINAL_TRIAL_AUDIT.checksPerTrial} per trial) · 0 owner-reviewed trial assessments recorded · {FOCUS_FINAL_TRIAL_AUDIT.pointers} recorded source pointers · {FOCUS_FINAL_TRIAL_AUDIT.review} requiring source review · {FOCUS_FINAL_TRIAL_AUDIT.missing} missing source evidence.</p>
      <p style={fine}>Evidence pointers, historical market-cap figures and planned FDA filings are not yet owner-checked eligibility or live data. The 7 active MAIN technical installation checks remain distinct from these per-trial checks; accepting platform infrastructure never makes an individual trial FDA qualified.</p>
      <Link href="/focus">Inspect all final-list trials and expandable gate findings</Link>
    </section>
    <details style={{marginTop:16}} aria-label="Archived superseded 31-gate MAIN evidence">
      <summary style={{cursor:"pointer",fontSize:13}}>Archived October 2026 31-gate acceptance record (not active)</summary>
    <section style={{...card,marginTop:16}} aria-label="Historical MAIN acceptance inventory">
      <h2 style={{marginTop:0}}>Original historical acceptance baseline</h2>
      {checked?<p><strong>{MAIN_DAILY_EVIDENCE.verified} of {MAIN_DAILY_EVIDENCE.total}</strong>
        {" "}historical technical gates verified ·
        {" "}<strong>{MAIN_DAILY_EVIDENCE.acceptedSections} of {MAIN_DAILY_EVIDENCE.sections}</strong> sections fully accepted.</p>:
        <p role="alert">Saved MAIN evidence did not validate; historical progress is withheld.</p>}
      <p style={fine}>Snapshot: <strong>{historicalDay??"Not verified"}</strong> (Pacific).
        This is an immutable historical scope, not today's percentage.
        A green production build must not retroactively mark the other gates complete.
        The full 31-gate record is archived and is not the current MAIN checklist.</p>
      <Link href="/installation-audit">Open archived 31-gate evidence and the separate scientific/outcome audits</Link>
    </section>
    </details>
    <section style={{...card,marginTop:16}} aria-label="Next verified work">
      <h2 style={{marginTop:0}}>Next MAIN acceptance step</h2>
      <p>Verify the authenticated deployed POOL → FOCUS handoff for the {FOCUS_FINAL_TRIAL_AUDIT.trialCount} exact final-list NCTs only, checking
        company, drug, indication and FDA application/cycle identities, then reconcile
        those results with the registry and nightly artifacts. Keep missing evidence as
        <strong> UNKNOWN</strong>, and preserve all original trial history and read-only archived legacy rating records.</p>
      <p style={fine}>No scan is dispatched, trial promoted, score changed, FDA probability
        generated or trading permission granted by this page.</p>
      <div style={{display:"flex",gap:16,flexWrap:"wrap"}}>
        <Link href="/pool">Open POOL</Link>
        <Link href="/focus">Open FOCUS</Link>
        <Link href="/predictions">Review FDA prediction blockers</Link>
      </div>
    </section>
  </main>;
}
