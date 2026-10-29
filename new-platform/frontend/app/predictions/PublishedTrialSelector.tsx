"use client";

import { useEffect, useState } from "react";

type Trial = {id: string; programId?: string; ticker?: string; drug?: string; nctId?: string; fdaSource?: string; phase3Source?: string};
type Workspace = {asOf?: string; mode?: string; sourceHealth?: {state?: string}; members?: {GEM_JR?: {rows?: Trial[]}; GEM?: {rows?: Trial[]}}};
type Candidate = Trial & {groups: string[]};

function publishedCandidates(data: Workspace): Candidate[] {
  if (!data.asOf || data.mode === "STALE_PREVIOUS_FETCH" || data.sourceHealth?.state === "STALE") return [];
  const found = new Map<string, Candidate>();
  for (const [group, rows] of [["GEM JR", data.members?.GEM_JR?.rows], ["GEM", data.members?.GEM?.rows]] as const) {
    if (!Array.isArray(rows)) continue;
    for (const row of rows) {
      if (!row || !row.id || !(row.fdaSource?.startsWith("https://") || row.phase3Source?.startsWith("https://"))) continue;
      const current = found.get(row.id);
      if (current) { if (!current.groups.includes(group)) current.groups.push(group); }
      else found.set(row.id, {...row, groups: [group]});
    }
  }
  return [...found.values()].sort((a,b) => (a.ticker || a.id).localeCompare(b.ticker || b.id));
}

export default function PublishedTrialSelector() {
  const [rows, setRows] = useState<Candidate[]>([]);
  const [selected, setSelected] = useState("");
  const [asOf, setAsOf] = useState("");
  const [status, setStatus] = useState("Loading published GEM JR / GEM records…");
  useEffect(() => {
    const controller = new AbortController();
    fetch("/api/workspace", {cache: "no-store", signal: controller.signal})
      .then(async response => {if (!response.ok) throw Error("Published workspace unavailable"); return response.json() as Promise<Workspace>;})
      .then(data => {
        if (controller.signal.aborted) return;
        const candidates = publishedCandidates(data);
        setRows(candidates);
        setAsOf(data.asOf || "");
        setStatus(candidates.length ? "Published sourced GEM JR / GEM candidates" : "No sourced eligible candidates in the published GEM JR / GEM lists.");
      }).catch(() => {if (!controller.signal.aborted) setStatus("Published workspace unavailable; no trial records displayed.");});
    return () => controller.abort();
  }, []);
  const trial = rows.find(row => row.id === selected);
  return <section style={{background:"#f1f8f2",border:"1px solid #9fb7a5",padding:18}}>
    <h2>Choose a published trial</h2>
    <p role="status">{status}{asOf ? " · Source snapshot: " + asOf : ""}</p>
    <label htmlFor="published-prediction-trial">GEM JR / GEM sourced records</label><br/>
    <select id="published-prediction-trial" value={selected} onChange={event => setSelected(event.target.value)}
      style={{padding:10,width:"100%",maxWidth:680}}>
      <option value="">Select a trial…</option>
      {rows.map(row => <option key={row.id} value={row.id}>{row.ticker || row.programId || row.id} · {row.drug || row.nctId || row.id} · {row.groups.join(" + ")}</option>)}
    </select>
    {trial && <div><p>Program: {trial.programId || trial.id} · NCT: {trial.nctId || "Not recorded"} · Membership: {trial.groups.join(", ")}</p>
      <p>{trial.fdaSource?.startsWith("https://") ? <a href={trial.fdaSource} target="_blank" rel="noopener noreferrer">FDA source ↗</a> : null}
      {" "}{trial.phase3Source?.startsWith("https://") ? <a href={trial.phase3Source} target="_blank" rel="noopener noreferrer">Phase 3 source ↗</a> : null}</p></div>}
    <p><button disabled>START PREDICTION</button></p>
    <p>Selection is read-only. No verified Phase 3 results-release or WT feed is asserted; scientific worker not connected. No prediction is issued.</p>
  </section>;
}
