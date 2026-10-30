"use client";

import { useEffect, useRef, useState } from "react";
import { eventCursor, initialRun, NCT_PATTERN, NctSseParser, nodeLabel, parseSnapshot, reduceNctEvent,
  savedPointer, type NctEvent, type NctRunState, type RunPointer } from "../lib/nct-live-stream";

const POINTER_KEY = "pdufa_nct_processing_run_v1";
const endpoint = (nct: string, run?: string) => "/api/nct-stream/" + encodeURIComponent(nct) + "/runs" + (run ? "/" + encodeURIComponent(run) : "");

function remember(pointer: RunPointer) {
  try { localStorage.setItem(POINTER_KEY, JSON.stringify({ run_id: pointer.run_id, nct_id: pointer.nct_id })); } catch { /* Processing still works when browser storage is disabled. */ }
}
function forget() {
  try { localStorage.removeItem(POINTER_KEY); } catch { /* No evidence or session credentials are stored here. */ }
}
function aborted(error: unknown) {
  return error instanceof Error && error.name === "AbortError";
}
function reconnectPause(attempt: number, signal: AbortSignal) {
  return new Promise<void>(resolve => {
    const finish = () => { clearTimeout(timer); signal.removeEventListener("abort", finish); resolve(); };
    const timer = setTimeout(finish, 500 * 2 ** attempt);
    signal.addEventListener("abort", finish, { once: true });
    if (signal.aborted) finish();
  });
}
function valueText(value: unknown) {
  return value === undefined || value === null ? "No source value available" : typeof value === "string" ? value : JSON.stringify(value);
}

export function ProcessingNode({ event }: { event: NctEvent }) {
  return <article data-node-id={event.node_id} data-state={event.status} style={{ padding: "10px 0", borderBottom: "1px solid #c8d1c8" }}>
    <strong>{event.status === "LOADING" ? <span className="nct-processing-spinner" role="img" aria-label="Processing" /> : null}
      {nodeLabel(event.node_id)} · {event.status.replaceAll("_", " ")}</strong>
    {event.value !== undefined && event.value !== null ? <div style={{ overflowWrap: "anywhere", whiteSpace: "pre-wrap" }}>{valueText(event.value)}</div> : null}
    {event.source ? <p className="subtle" style={{ margin: "6px 0" }}>
      <a href={event.source.url} target="_blank" rel="noopener noreferrer">Source</a> · Verified {event.source.verified_at}
      <br />SHA-256: <code style={{ overflowWrap: "anywhere" }}>{event.source.sha256}</code>
    </p> : null}
  </article>;
}

export default function NctLiveStream() {
  const [input, setInput] = useState("");
  const [run, setRun] = useState<NctRunState | null>(null);
  const [notice, setNotice] = useState("Enter one NCT identifier to start its persisted processing run.");
  const [interrupted, setInterrupted] = useState(false);
  const [busy, setBusy] = useState(false);
  const currentRun = useRef<NctRunState | null>(null);
  const generation = useRef(0);
  const controller = useRef<AbortController | null>(null);

  const update = (state: NctRunState, current: number) => {
    if (generation.current !== current) return;
    currentRun.current = state;
    setRun(state);
  };

  async function follow(pointer: RunPointer, current: number, signal: AbortSignal) {
    for (let attempt = 0; attempt <= 3; attempt += 1) {
      if (signal.aborted || generation.current !== current) return;
      try {
        const latest = currentRun.current;
        if (!latest || latest.run_id !== pointer.run_id || latest.nct_id !== pointer.nct_id) throw new Error("Processing selection changed");
        const response = await fetch(endpoint(pointer.nct_id, pointer.run_id) + "/events?after=" + latest.sequence, {
          cache: "no-store", signal,
          headers: { Accept: "text/event-stream", "Last-Event-ID": eventCursor(latest) },
        });
        if (!response.ok || !response.body) throw new Error(response.status === 401 ? "Sign-in expired. Sign in again." : "Processing stream unavailable (" + response.status + ").");
        if (!(response.headers.get("content-type") || "").toLowerCase().startsWith("text/event-stream")) throw new Error("The server did not return a processing stream.");
        const parser = new NctSseParser(pointer);
        const reader = response.body.getReader();
        try {
          while (true) {
            const { done, value } = await reader.read();
            if (signal.aborted || generation.current !== current) return;
            const events = parser.feed(value || new Uint8Array(), done);
            for (const event of events) {
              const previous = currentRun.current;
              if (!previous) throw new Error("Processing state is unavailable");
              update(reduceNctEvent(previous, event), current);
            }
            if (currentRun.current?.terminal) {
              setNotice("Processing run completed. Evidence status is separate from scientific assessment or trading eligibility.");
              setInterrupted(false); setBusy(false);
              return;
            }
            if (done) throw new Error("Connection ended before the completion event.");
          }
        } finally {
          await reader.cancel().catch(() => {});
          reader.releaseLock();
        }
      } catch (error) {
        if (signal.aborted || generation.current !== current || aborted(error)) return;
        if (attempt === 3 || (error instanceof Error && error.message.includes("Sign-in expired"))) {
          setNotice((error instanceof Error ? error.message : "Processing connection interrupted.") + " Saved results are retained. Resume this run to continue.");
          setInterrupted(true); setBusy(false);
          return;
        }
        setNotice("Connection interrupted. Reconnecting to the saved run (" + (attempt + 1) + "/3)…");
        await reconnectPause(attempt, signal);
      }
    }
  }

  async function load(nct: string, pointer?: RunPointer) {
    generation.current += 1;
    const current = generation.current;
    controller.current?.abort();
    const nextController = new AbortController();
    controller.current = nextController;
    const signal = nextController.signal;
    currentRun.current = null;
    setRun(null); setInterrupted(false); setBusy(false);
    if (!NCT_PATTERN.test(nct)) { setNotice("Enter an exact identifier such as NCT01234567."); return; }
    setInput(nct); setBusy(true);
    if (pointer) update(initialRun(pointer.run_id, pointer.nct_id), current);
    setNotice(pointer ? "Restoring the saved processing run…" : "Starting a persisted processing run…");
    try {
      let state: NctRunState;
      if (pointer) {
        const response = await fetch(endpoint(nct, pointer.run_id), { cache: "no-store", signal });
        if (!response.ok) throw new Error(response.status === 401 ? "Sign-in expired. Sign in again." : "Saved run is unavailable (" + response.status + ").");
        state = parseSnapshot(await response.json(), pointer);
      } else {
        const response = await fetch(endpoint(nct), { method: "POST", cache: "no-store", signal,
          headers: { "Content-Type": "application/json" }, body: JSON.stringify({ request_key: crypto.randomUUID() }) });
        if (!response.ok) throw new Error(response.status === 401 ? "Sign-in expired. Sign in again." : "Unable to start this trial run (" + response.status + ").");
        const data: unknown = await response.json();
        const created = savedPointer(data);
        if (!created || created.nct_id !== nct || !data || typeof data !== "object" || typeof (data as Record<string, unknown>).dossier_id !== "string") throw new Error("Processing run identity could not be verified.");
        state = initialRun(created.run_id, created.nct_id, (data as { dossier_id: string }).dossier_id);
      }
      if (signal.aborted || generation.current !== current) return;
      update(state, current);
      const saved = { nct_id: state.nct_id, run_id: state.run_id };
      remember(saved);
      if (state.terminal) { setNotice("Saved completed processing run restored. Scientific assessments remain separate."); setBusy(false); return; }
      setNotice("Processing events will appear as each step finishes.");
      await follow(saved, current, signal);
    } catch (error) {
      if (signal.aborted || generation.current !== current || aborted(error)) return;
      setNotice(error instanceof Error ? error.message : "Unable to load this processing run.");
      setInterrupted(!!pointer); setBusy(false);
    }
  }

  useEffect(() => {
    let pointer: RunPointer | null = null;
    try { pointer = savedPointer(JSON.parse(localStorage.getItem(POINTER_KEY) || "null")); } catch { forget(); }
    if (pointer) void load(pointer.nct_id, pointer);
    return () => { generation.current += 1; controller.current?.abort(); };
    // Restore once; subsequent selections start from the form or Resume button.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const nodes = Object.values(run?.nodes || {}).sort((a, b) => a.sequence - b.sequence);
  return <section className="panel" aria-label="Live NCT processing" id="nct-live-processing">
    <h2>NCT · Live processing</h2>
    <p className="subtle">One trial and one persisted run. Source checks appear as they complete. A VERIFIED field does not certify scientific validity, FDA approval, prediction reliability or trading eligibility.</p>
    <form onSubmit={event => { event.preventDefault(); void load(input.trim().toUpperCase()); }}>
      <label htmlFor="nct-live-input">ClinicalTrials.gov identifier</label>{" "}
      <input id="nct-live-input" value={input} onChange={event => setInput(event.target.value)} maxLength={11} placeholder="NCT01234567" autoComplete="off" />{" "}
      <button type="submit">Start processing</button>
    </form>
    <p role="status" aria-live="polite">{notice}</p>
    {run ? <p className="subtle">{run.nct_id} · Run <code>{run.run_id}</code> · Event {run.sequence}{busy ? " · connected or reconnecting" : ""}</p> : null}
    {interrupted && run ? <button type="button" onClick={() => void load(run.nct_id, { nct_id: run.nct_id, run_id: run.run_id })}>Resume saved run</button> : null}
    {[4, 3, 2, 1].map(level => <details key={level} open={level === 4 || level === 1}>
      <summary>{level === 4 ? "Source checks" : level === 1 ? "MAIN processing state" : "Level " + level + " dependencies"}</summary>
      {nodes.filter(event => event.level === level).map(event => <ProcessingNode key={event.node_id} event={event} />)}
    </details>)}
    <p className="subtle">PENDING means queued. Only LOADING steps show a processing indicator. FAILED and INSUFFICIENT EVIDENCE require review; parent status comes from persisted dependency events.</p>
    <style>{`.nct-processing-spinner{display:inline-block;width:12px;height:12px;margin-right:8px;border:2px solid #b9c6ba;border-top-color:#214e2c;border-radius:50%;animation:nct-processing-rotate .8s linear infinite}@keyframes nct-processing-rotate{to{transform:rotate(360deg)}}@media(prefers-reduced-motion:reduce){.nct-processing-spinner{animation:none;border-style:dotted}}`}</style>
  </section>;
}
