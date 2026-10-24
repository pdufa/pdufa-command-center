"use client";

const checks = [
  { name: "Source ZIP integrity", status: "Verified in isolated audit", detail: "Archive structure and CRC checked; this is not a complete application restore." },
  { name: "GitHub source recovery", status: "Passed", detail: "Frontend and backend clean-source recovery workflow passed." },
  { name: "Google Drive ZIP application rebuild", status: "Pending", detail: "The exact Drive archive has not completed a clean frontend production build." },
  { name: "Database restore", status: "Pending", detail: "A verified portable database export and isolated restore are still required." },
  { name: "Google Sheets restore", status: "Pending", detail: "October 22 and 23 snapshots were compared, not restored into production." },
  { name: "Full-system portable ZIP", status: "Not installed", detail: "No verified one-click full-system export or one-click restore is available yet." },
] as const;

export default function BackupStatusPanel() {
  return <section className="panel" aria-label="Full-system backup and restore status">
    <h2>BACKUP · Full-system recovery</h2>
    <p className="subtle">Read-only recovery checklist. A source-code ZIP alone does not include live database records, secrets, deployment settings, or every connected Google Sheet.</p>
    <p><a href="https://drive.google.com/drive/folders/1IFj70jCBp6TTX3yzMOvYJlGbij6YQ5Bu" target="_blank" rel="noopener noreferrer">Open existing Google Drive backup folder ↗</a></p>
    <div style={{display:"grid",gap:12}}>
      {checks.map(check => <div key={check.name} style={{border:"1px solid #9daea0",borderRadius:8,padding:12,background:"#fff"}}>
        <strong>{check.name}</strong>
        <p style={{margin:"6px 0",fontWeight:700}}>{check.status}</p>
        <p className="subtle" style={{margin:0}}>{check.detail}</p>
      </div>)}
    </div>
    <p className="workspace-banner" role="status">Full-system restore is NOT certified. No backup export, production restore, scheduled scan, or trade is initiated from this page.</p>
  </section>;
}
