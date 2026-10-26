const installedChecks = [
  {
    name: "Production dashboard deployment",
    result: "Vercel reported READY for the main-branch deployment on October 25, 2026.",
    limit: "READY confirms deployment state, not an authenticated end-to-end production acceptance test.",
    source: "https://pdufa-new-dashboard-oxqx3ehj9-pdufa.vercel.app",
    sourceLabel: "Dated deployment",
  },
  {
    name: "Isolated SCIENCE integration regressions",
    result: "16 of 16 GitHub Actions workflows passed for the pinned isolated integration commit.",
    limit: "This is an isolated preview validation, not production SCIENCE release authorization or verified clinical evidence.",
    source: "https://github.com/pdufa/pdufa-command-center/commit/ec48768d69ce5548c5edf770ebba04cc492f4568",
    sourceLabel: "Pinned integration commit",
  },
  {
    name: "Independent installation checklist",
    result: "15 existing sections keep code, deployment, runtime and evidence gates distinct.",
    limit: "The checklist must not infer percentage of work completed from successful builds.",
    source: "https://github.com/pdufa/pdufa-command-center/issues/331",
    sourceLabel: "Acceptance requirements",
  },
] as const;

export default function IndependentInstallationLane() {
  return <section aria-labelledby="independent-installation-lane" style={{margin:"22px 0",padding:"18px",border:"1px solid #cbd5e1",borderRadius:9,background:"#f8fafc"}}>
    <h2 id="independent-installation-lane">Installation continuation — independent of reviewer keys</h2>
    <p><strong>Dated checkpoint: October 25, 2026.</strong> Reviewer key setup and encrypted-evidence delivery are <strong>deferred by the owner, not completed</strong>. The primary reviewer, independent custody keyholder, encrypted transfer, actual human source reviews and FDA decision-cycle adjudication remain pending. No keys, private evidence or reviewer access are created here.</p>
    <p><strong>Continue safely:</strong> build and regression verification, Pipeline and GEM JR/GEM/WT read-only integrity audits, nightly scan evidence reconciliation, backup recovery rehearsals, and source/denominator validation can proceed independently. The checks below are pinned historical observations, not live probes.</p>
    <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(250px,1fr))",gap:12}}>
      {installedChecks.map(item=><article key={item.name} style={{background:"white",border:"1px solid #e2e8f0",borderRadius:7,padding:12}}>
        <h3 style={{fontSize:16,margin:"0 0 8px"}}>{item.name}</h3>
        <p style={{margin:"0 0 8px"}}>{item.result}</p>
        <p style={{margin:"0 0 8px",color:"#92400e"}}><strong>Limit:</strong> {item.limit}</p>
        <a href={item.source} target="_blank" rel="noopener noreferrer">{item.sourceLabel}</a>
      </article>)}
    </div>
    <p><strong>Still to verify:</strong> complete 8 PM Pacific scan execution and notifications, production backup restoration, trial-level scientific source provenance, qualified historical approval/nonapproval denominator, and time-forward calibration. No FDA approval probability or completed scientific readiness is asserted.</p>
    <p><strong>Unchanged:</strong> live scan schedules, broker/trading controls, all GEM JR/GEM/WT restriction membership and GEM JR/GEM FS/FA associations. This section is read-only and does not promote any acceptance gate.</p>
  </section>;
}
