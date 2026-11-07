import type {Metadata} from "next";
import Link from "next/link";
import {MAIN_DAILY_EVIDENCE} from "../../lib/main-daily-evidence";

export const metadata:Metadata={
  title:"MAIN · Technical status and evidence gates | PDUFA",
  description:"Verified release checks, dated installation evidence, and separate SCIENCE and OUTCOME readiness."
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

function Status({name,status,detail}:{name:string;status:string;detail:string}){
  return <section style={card}><h2 style={{fontSize:18,margin:"0 0 10px"}}>{name}</h2>
    <p style={{fontSize:20,fontWeight:700,margin:"0 0 8px"}}>{status}</p>
    <p style={{...fine,margin:0}}>{detail}</p>
  </section>;
}

export default function MainStatus(){
  const checked=MAIN_DAILY_EVIDENCE.valid;
  const historicalDay=checked?MAIN_DAILY_EVIDENCE.history.at(-1)?.asOf:null;
  return <main className="shell" style={{maxWidth:1100,margin:"0 auto",padding:"20px 12px 45px"}}>
    <div className="topline">PDUFA COMMAND CENTER · MAIN</div>
    <h1>MAIN · Technical status and prediction readiness</h1>
    <p>This is an evidence and operating-status view, <strong>not a third active trial list</strong>.
      POOL is the complete research inventory; FOCUS is the screened post-Phase-3 population.
      Historical records are retained without reactivating GEM JR, GEM, TOP or BOTTOM.</p>
    <section style={{...card,margin:"18px 0"}} aria-label="Dated release verification">
      <h2 style={{marginTop:0}}>Latest release evidence · {release.date}</h2>
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
    <div style={grid} aria-label="Separate evidence gates">
      <Status name="MAIN · technical acceptance"
        status="Still open"
        detail="Release and CI checks pass, but complete authenticated runtime, source health, scheduling, recovery and program eligibility require separate acceptance evidence."/>
      <Status name="SCIENCE · trial review"
        status="Not certified"
        detail="Phase-correct source evidence and independently reviewed scientific investigation coverage remain incomplete. Published trial facts are not automatically scores."/>
      <Status name="OUTCOME · FDA prediction"
        status="ABSTAIN"
        detail="No independently calibrated PASS / CRL / EXTENSION forecast has passed the application-cycle, freeze, outcome and historical backtest gates."/>
    </div>
    <section style={{...card,marginTop:16}} aria-label="Historical MAIN acceptance inventory">
      <h2 style={{marginTop:0}}>Dated MAIN acceptance baseline</h2>
      {checked?<p><strong>{MAIN_DAILY_EVIDENCE.verified} of {MAIN_DAILY_EVIDENCE.total}</strong>
        {" "}historical technical gates verified ·
        {" "}<strong>{MAIN_DAILY_EVIDENCE.acceptedSections} of {MAIN_DAILY_EVIDENCE.sections}</strong> sections fully accepted.</p>:
        <p role="alert">Saved MAIN evidence did not validate; historical progress is withheld.</p>}
      <p style={fine}>Snapshot: <strong>{historicalDay??"Not verified"}</strong> (Pacific).
        This is an immutable historical scope, not today's percentage.
        A green production build must not retroactively mark the other gates complete.
        The old inventory contains retired architecture references and must not be
        treated as today's POOL/FOCUS membership policy.</p>
      <Link href="/installation-audit">Inspect dated installation gates and protected SCIENCE / OUTCOME checks</Link>
    </section>
    <section style={{...card,marginTop:16}} aria-label="Next verified work">
      <h2 style={{marginTop:0}}>Next MAIN acceptance step</h2>
      <p>Verify the authenticated deployed POOL → FOCUS handoff against exact trial,
        company, drug, indication and FDA application/cycle identities, then reconcile
        those results with the registry and nightly artifacts. Keep missing evidence as
        <strong> UNKNOWN</strong>, and preserve all original trial and RAAS history.</p>
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
