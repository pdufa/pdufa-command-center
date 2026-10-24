"use client";

import { useState } from "react";

type Manifest = { format: string; generatedAt: string; application: string; sourceArchive: { url: string; scope: string }; snapshotFolder: string; includedInDownload: string[]; excludedFromDownload: string[]; recoveryStatus: string };
const checks = [
  { name: "Source ZIP integrity", status: "Verified in isolated audit", detail: "Archive structure and CRC checked; this is not a complete application restore." },
  { name: "GitHub source recovery", status: "Passed", detail: "Frontend and backend clean-source recovery workflow passed." },
  { name: "Google Drive ZIP application rebuild", status: "Pending", detail: "The exact Drive archive has not completed a clean frontend production build." },
  { name: "Database restore", status: "Pending", detail: "A verified portable database export and isolated restore are still required." },
  { name: "Google Sheets restore", status: "Pending", detail: "October 22 and 23 snapshots were compared, not restored into production." },
  { name: "Full-system portable ZIP", status: "Not installed", detail: "No verified one-click full-system export or one-click restore is available yet." },
] as const;
const sourceArchive = "https://github.com/pdufa/pdufa-command-center/archive/refs/heads/main.zip";
const snapshotFolder = "https://drive.google.com/drive/folders/1IFj70jCBp6TTX3yzMOvYJlGbij6YQ5Bu";
export default function BackupStatusPanel() {
  const [message,setMessage] = useState("");
  function exportRecoveryManifest() {
    const manifest: Manifest = {
      format: "pdufa-recovery-manifest-v1", generatedAt: new Date().toISOString(),
      application: "PDUFA Command Center", sourceArchive: { url: sourceArchive, scope: "GitHub main source only; not a database or deployment export" },
      snapshotFolder, includedInDownload: ["Recovery manifest and source/snapshot locations"],
      excludedFromDownload: ["Application source ZIP", "Database", "Google Sheets content", "Secrets", "Vercel and Render configuration"],
      recoveryStatus: "INCOMPLETE - do not represent as a full-system backup"
    };
    const blob = new Blob([JSON.stringify(manifest,null,2)+"\\n"],{type:"application/json"});
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a"); anchor.href=url; anchor.download="pdufa-recovery-manifest.json";
    document.body.appendChild(anchor); anchor.click(); anchor.remove(); URL.revokeObjectURL(url);
    setMessage("Recovery manifest downloaded. This is NOT a complete backup ZIP.");
  }
  return <section className="panel" aria-label="Full-system backup and restore status">
    <h2>BACKUP · Full-system recovery</h2>
    <p className="subtle">The controls below provide a source archive and a recovery manifest. Neither contains live database records, secrets, deployment settings, or every connected Google Sheet.</p>
    <div style={{display:"flex",flexWrap:"wrap",gap:10,margin:"14px 0"}}>
      <a className="secondary" href={sourceArchive} style={{display:"inline-block",padding:"10px 14px",border:"2px solid #193b26",borderRadius:8,fontWeight:700}}>Download source ZIP ↗</a>
      <button type="button" onClick={exportRecoveryManifest}>Download recovery manifest</button>
      <a href={snapshotFolder} target="_blank" rel="noopener noreferrer" style={{padding:"10px 0"}}>Open Google Drive snapshots ↗</a>
    </div>
    {message && <p role="status">{message}</p>}
    <div style={{display:"grid",gap:12}}>
      {checks.map(check => <div key={check.name} style={{border:"1px solid #9daea0",borderRadius:8,padding:12,background:"#fff"}}>
        <strong>{check.name}</strong><p style={{margin:"6px 0",fontWeight:700}}>{check.status}</p>
        <p className="subtle" style={{margin:0}}>{check.detail}</p>
      </div>)}
    </div>
    <p className="workspace-banner" role="status">Full-system restore is NOT certified. These downloads do not initiate production restores, scans, trades, or database writes.</p>
  </section>;
}
