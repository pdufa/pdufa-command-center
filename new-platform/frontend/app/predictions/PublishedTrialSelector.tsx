"use client";

import { useEffect, useState } from "react";
import EvidenceSegmentControls from "./EvidenceSegmentControls";
import ResearchEvidenceStatus from "./ResearchEvidenceStatus";
import depth20 from "../../lib/prediction-depths-20.json";
import depthExtension from "../../lib/prediction-depths-21-50.json";

type Trial = {id: string; programId?: string; ticker?: string; drug?: string; nctId?: string; fdaSource?: string; phase3Source?: string};
type Workspace = {asOf?: string; mode?: string; sourceHealth?: {state?: string}; members?: {GEM_JR?: {rows?: Trial[]}; GEM?: {rows?: Trial[]}}};
type Candidate = Trial & {groups: string[]};
const DEPTH_LEVELS = [...depth20.levels, ...depthExtension.additional_levels].sort((a,b) => a.depth_level - b.depth_level);

function publishedCandidates(data: Workspace): Candidate[] {
  if (!data.asOf || data.mode === "STALE_PREVIOUS_FETCH" || data.sourceHealth?.state === "STALE") return [];
  const found = new Map<string, Candidate>();
  for (const [group, rows] of [["GEM JR", data.members?.GEM_JR?.rows], ["GEM", data.members?.GEM?.rows]] as const) {
    if (!Array.isArray(rows)) continue;
    for (const row of rows) {
      if (!row || !row.id || !(row.fdaSource?.startsWith("https://") || row.phase3Source?.startsWith("https://"))) continue;
      // Prefer a program-specific key; never merge separate clinical trial IDs by ticker alone.
      const identity = row.programId && row.nctId ? row.programId + "|" + row.nctId : row.id;
      const current = found.get(identity);
      if (current) { if (!current.groups.includes(group)) current.groups.push(group); }
      else found.set(identity, {...row, groups: [group]});
    }
  }
  return [...found.values()].sort((a,b) => (a.ticker || a.id).localeCompare(b.ticker || b.id));
}

export default function PublishedTrialSelector() {
  const [rows, setRows] = useState<Candidate[]>([]);
  const [selected, setSelected] = useState("");
  const [query, setQuery] = useState("");
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
        setStatus(candidates.length ? "Published GEM JR / GEM records with source references (not independently verified)" : "No sourced candidates in the published GEM JR / GEM lists.");
      }).catch(() => {if (!controller.signal.aborted) setStatus("Published workspace unavailable; no trial records displayed.");});
    return () => controller.abort();
  }, []);
  const trial = rows.find(row => (row.programId && row.nctId ? row.programId + "|" + row.nctId : row.id) === selected);
  const matches = rows.filter(row => [row.ticker, row.programId, row.drug, row.nctId, row.id].some(value => value?.toLowerCase().includes(query.toLowerCase())));
  return <section style={{background:"#f1f8f2",border:"1px solid #9fb7a5",padding:18}}>
    <h2>Choose a published trial</h2>
    <p role="status">{status}{asOf ? " · Source snapshot: " + asOf : ""}</p>
    <label htmlFor="published-prediction-trial">GEM JR / GEM sourced records</label><br/>
    <input aria-label="Search published trials" placeholder="Search ticker, program, drug, or NCT" value={query} onChange={event => setQuery(event.target.value)} style={{padding:10,width:"100%",maxWidth:680,display:"block",margin:"8px 0"}} />
    <p>{matches.length} matching sourced trial records</p>
    <select id="published-prediction-trial" value={selected} onChange={event => setSelected(event.target.value)}
      style={{padding:10,width:"100%",maxWidth:680}}>
      <option value="">Select a trial…</option>
      {matches.map(row => <option key={row.programId && row.nctId ? row.programId + "|" + row.nctId : row.id} value={row.programId && row.nctId ? row.programId + "|" + row.nctId : row.id}>{row.ticker || row.programId || row.id} · {row.drug || row.nctId || row.id} · {row.groups.join(" + ")}</option>)}
    </select>
    {trial && <div><p>Program: {trial.programId || trial.id} · NCT: {trial.nctId || "Not recorded"} · Membership: {trial.groups.join(", ")}</p>
      <p>{trial.fdaSource?.startsWith("https://") ? <a href={trial.fdaSource} target="_blank" rel="noopener noreferrer">FDA source ↗</a> : null}
      {" "}{trial.phase3Source?.startsWith("https://") ? <a href={trial.phase3Source} target="_blank" rel="noopener noreferrer">Phase 3 source ↗</a> : null}</p></div>}
    {trial && <ResearchEvidenceStatus programId={selected} />}
    {trial && <EvidenceSegmentControls trialKey={selected} />}
    {trial && <section aria-label="Selected trial scientific investigation protocol">
      <h3>50-level scientific investigation — {trial.ticker || trial.id}</h3>
      <p>0 / 50 independently assessed. This is a required-work checklist, not completed analysis or verified evidence.</p>
      <progress value={0} max={50} aria-label="Completed investigation levels" />
      {DEPTH_LEVELS.map(level => <details key={level.level_id} style={{margin:"8px 0",padding:10,border:"1px solid #b4c7b9"}}>
        <summary>{level.level_id} · {level.title} — NOT STARTED</summary>
        <p>{level.objective}</p>
        <p>Linked scientific questions: {level.question_ids.join(", ")}</p>
        <strong>Evidence required:</strong><ul>{level.requirements.map((requirement,i) => <li key={i}>{requirement}</li>)}</ul>
        <p>Independent findings: NOT AVAILABLE · Confidence: NOT ESTABLISHED · Decision: ABSTAIN</p>
      </details>)}
    </section>}
    <p><button disabled>START PREDICTION</button></p>
    <p>Selection is read-only. Source links have not been independently checked for identity, chronology, or content. No verified Phase 3 results-release or WT feed is asserted; scientific worker not connected. No prediction is issued.</p>
  </section>;
}
