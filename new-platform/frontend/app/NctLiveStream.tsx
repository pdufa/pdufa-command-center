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
  const analyzing = useRef<{ nct: string; generation: number } | null>(null);
  const analysisKeys = useRef(new Map<string, string>());

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

  async function load(nct: string, pointer?: RunPointer, reuseExisting = false) {
    if (reuseExisting && analyzing.current?.nct === nct) return;
    if (reuseExisting && currentRun.current?.nct_id === nct) {
      setInput(nct);
      if (currentRun.current.terminal && (!pointer || pointer.run_id === currentRun.current.run_id)) return;
      pointer ||= { nct_id: nct, run_id: currentRun.current.run_id };
    }
    generation.current += 1;
    const current = generation.current;
    analyzing.current = reuseExisting ? { nct, generation: current } : null;
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
      let restoredState: NctRunState | undefined;
      if (reuseExisting && !pointer) {
        const latestResponse = await fetch(endpoint(nct) + "/latest", { cache: "no-store", signal });
        if (latestResponse.ok) {
          const latestData: unknown = await latestResponse.json();
          const latestPointer = savedPointer(latestData);
          if (!latestPointer || latestPointer.nct_id !== nct) throw new Error("Saved processing run identity could not be verified.");
          pointer = latestPointer;
          restoredState = parseSnapshot(latestData, pointer);
        } else if (latestResponse.status !== 404) {
          throw new Error(latestResponse.status === 401 ? "Sign-in expired. Sign in again." : "Saved processing run lookup is unavailable (" + latestResponse.status + ").");
        }
      }
      if (pointer) {
        if (restoredState) state = restoredState;
        else {
          const response = await fetch(endpoint(nct, pointer.run_id), { cache: "no-store", signal });
          if (!response.ok) throw new Error(response.status === 401 ? "Sign-in expired. Sign in again." : "Saved run is unavailable (" + response.status + ").");
          state = parseSnapshot(await response.json(), pointer);
        }
      } else {
        let requestKey = reuseExisting ? analysisKeys.current.get(nct) : undefined;
        if (!requestKey) {
          requestKey = crypto.randomUUID();
          if (reuseExisting) analysisKeys.current.set(nct, requestKey);
        }
        const response = await fetch(endpoint(nct), { method: "POST", cache: "no-store", signal,
          headers: { "Content-Type": "application/json" }, body: JSON.stringify({ request_key: requestKey, ...(reuseExisting ? { reuse_existing: true } : {}) }) });
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
    } finally {
      if (analyzing.current?.generation === current) analyzing.current = null;
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

  useEffect(() => {
    if (typeof window === "undefined") return;
    const handler = (event: Event) => {
      const detail: unknown = (event as CustomEvent<unknown>).detail;
      const nct = typeof detail === "string" ? detail : detail && typeof detail === "object" ? (detail as Record<string, unknown>).nct_id : null;
      if (typeof nct !== "string" || !NCT_PATTERN.test(nct)) return;
      const pointer = detail && typeof detail === "object" ? savedPointer(detail) : null;
      void load(nct, pointer || undefined, true);
    };
    window.addEventListener("pdufa:analyze-nct", handler);
    return () => window.removeEventListener("pdufa:analyze-nct", handler);
  }, []);

  type ReadinessStage = { id: string; status: string; missing?: string[]; reason?: string | null; depends_on?: string[] };
  type ReadinessReport = { nct_id: string; decision_pipeline?: ReadinessStage[]; checks_available?: number; checks_total?: number; missing?: string[]; assessments?: {id:string;status:string;reason?:string;value?:unknown;source_evidence_id?:string;required_fields?:string[];extracted_fields?:Record<string,unknown>;fields_complete?:boolean;adjudication_status?:string}[]; decision?:string };
  const [readiness, setReadiness] = useState<ReadinessReport | null>(null);
  const [readinessError, setReadinessError] = useState<string | null>(null);
  useEffect(() => {
    if (!run?.nct_id) { setReadiness(null); setReadinessError(null); return; }
    let active = true;
    setReadiness(null);
    setReadinessError(null);
    fetch("/api/phase3-trials/" + encodeURIComponent(run.nct_id) + "/readiness", {cache:"no-store"})
      .then(async response => { if (!response.ok) throw new Error("Scientific readiness unavailable (" + response.status + ")"); return response.json(); })
      .then((data: ReadinessReport) => { if (active) setReadiness(data); })
      .catch((error: Error) => { if (active) setReadinessError(error.message); });
    return () => { active = false; };
  }, [run?.nct_id, run?.terminal]);
  const [savedDecision, setSavedDecision] = useState<{decision:string;status:string;latest_prediction?:{scientific_readiness?:string;uncertainty?:string;created_at?:string}} | null>(null);
  useEffect(() => {
    if (!run?.nct_id) { setSavedDecision(null); return; }
    let active = true;
    setSavedDecision(null);
    fetch("/api/phase3-trials/" + encodeURIComponent(run.nct_id) + "/predictions", {cache:"no-store"})
      .then(async response => { if (!response.ok) throw new Error("Prediction records unavailable"); return response.json(); })
      .then(result => { if (active && result && typeof result.decision === "string") setSavedDecision(result); })
      .catch(() => { if (active) setSavedDecision(null); });
    return () => { active = false; };
  }, [run?.nct_id, run?.terminal]);
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
    <details open style={{margin:"12px 0",padding:12,border:"1px solid #b5c7b8",borderRadius:8}}>
      <summary style={{cursor:"pointer",fontWeight:700}}>50-Level Scientific Analysis — evidence and readiness</summary>
      <p className="subtle">Design target: 50 analytical levels. This section displays actual persisted trial-processing evidence below, not fabricated assessments. The four-level dependency graph is not a 50-level FDA decision model.</p>
      <p><strong>Trial:</strong> {run?.nct_id || "No trial selected"} · <strong>Evidence checks:</strong> {nodes.filter(n=>n.status==="VERIFIED").length} verified / {nodes.length} received</p>
      <details open><summary>SCIENCE → OUTCOME → MAIN — decision requirements</summary>
        {readinessError ? <p role="status">Readiness service: {readinessError}. FDA decision remains ABSTAIN.</p> : null}
        {!readiness && !readinessError ? <p role="status">Checking scientific readiness…</p> : null}
        {readiness ? <p><strong>Readiness checks:</strong> {readiness.checks_available ?? 0} / {readiness.checks_total ?? 0} available · <strong>FDA decision: ABSTAIN</strong></p> : null}
        {(readiness?.decision_pipeline || []).map(stage => <details key={stage.id}>
          <summary><strong>{stage.id} — {stage.status}</strong></summary>
          <p>{stage.reason || "Evidence requirements recorded."}</p>
          {stage.depends_on?.length ? <p>Depends on: {stage.depends_on.join(", ")}</p> : null}
          {stage.missing?.length ? <ul>{stage.missing.map(item => <li key={item}>{item.replaceAll("_", " ")}</li>)}</ul> : <p>No missing requirements listed for this stage.</p>}
        </details>)}
        <details><summary>Individual evidence and assessment statuses</summary>
          {(readiness?.assessments || []).map(item => <details key={item.id}><summary>{item.id.replaceAll("_", " ")} — {item.status}</summary>
            {item.value !== undefined && item.value !== null ? <p>Recorded value: {String(item.value)}</p> : null}
            {item.reason ? <p>{item.reason}</p> : null}
            {item.source_evidence_id ? <p>Evidence ID: {item.source_evidence_id}</p> : null}
            {item.required_fields?.length ? <div>
              <p><strong>Quantitative evidence:</strong> {item.fields_complete ? "Fields recorded; independent adjudication still required" : "Incomplete"} · <strong>Adjudication:</strong> {item.adjudication_status || "NOT ADJUDICATED"}</p>
              <ul>{item.required_fields.map(field => {
                const value = item.extracted_fields?.[field];
                const present = value !== null && value !== undefined && String(value).trim() !== "";
                return <li key={field}>{field.replaceAll("_", " ")}: {present ? String(value) : "MISSING"}</li>;
              })}</ul>
            </div> : null}
          </details>)}
        </details>
      </details>
      <details open><summary>SCIENCE — collected evidence</summary>
        {nodes.filter(n=>n.level>=3).length ? nodes.filter(n=>n.level>=3).map(n=><ProcessingNode key={"science-"+n.node_id} event={n}/>) : <p>No scientific source checks received. Start a trial run.</p>}
        <p className="subtle">Source verification is not a completed efficacy, safety, or statistical scientific assessment.</p>
      </details>
      <details><summary>OUTCOME — regulatory evidence</summary>
        {nodes.filter(n=>n.level===2).length ? nodes.filter(n=>n.level===2).map(n=><ProcessingNode key={"outcome-"+n.node_id} event={n}/>) : <p>No regulatory assessment events received.</p>}
        <p className="subtle">No verified PASS, CRL or EXTENSION probability is available from these processing events.</p>
      </details>
      <details><summary>MAIN — decision and readiness</summary>
        {nodes.filter(n=>n.level===1).length ? nodes.filter(n=>n.level===1).map(n=><ProcessingNode key={"main-"+n.node_id} event={n}/>) : <p>No MAIN processing event received.</p>}
        <p role="status" aria-live="polite"><strong>FDA decision prediction: {savedDecision?.decision && savedDecision.decision !== "ABSTAIN" ? savedDecision.decision + " — SAVED RECORD (NOT VALIDATED)" : "ABSTAIN — NOT READY"}.</strong> {savedDecision?.latest_prediction ? " Readiness: " + (savedDecision.latest_prediction.scientific_readiness || "unverified") + ". " + (savedDecision.latest_prediction.uncertainty || "") : busy ? "Evidence collection is running; the scientific decision engine has not been validated." : "No verified decision prediction available from this processing run."}</p>
      </details>
      <details><summary>Missing evidence and decision requirements</summary>
        {nodes.filter(n=>n.status==="FAILED"||n.status==="INSUFFICIENT_EVIDENCE"||n.status==="PENDING").length ? nodes.filter(n=>n.status==="FAILED"||n.status==="INSUFFICIENT_EVIDENCE"||n.status==="PENDING").map(n=><ProcessingNode key={"missing-"+n.node_id} event={n}/>) : <p>No failed, insufficient or pending source checks in the received events. This does not establish complete FDA evidence.</p>}
        <p><strong>CRITICAL:</strong> A validated scientific/regulatory assessment, contemporaneous FDA review evidence where available, and independent calibration are still required before a defensible PASS / CRL / EXTENSION probability can be shown.</p>
      </details>
      <details><summary>50 assessment requirements — evidence gates</summary>
        <p className="subtle">Each requirement is independently tracked as NOT ASSESSED until an evidence-backed assessment is implemented. Verified source fields alone never count as a passed scientific test.</p>
        {([
          ["Trial identity and provenance",["NCT identity","Sponsor identity","Drug identity","Indication identity","Phase 3 status","Source freshness"]],
          ["Efficacy",["Primary endpoint definition","Primary endpoint outcome","Effect size","Confidence interval","Statistical significance","Clinical relevance","Multiplicity handling"]],
          ["Trial integrity",["Randomization","Blinding","Comparator validity","Sample size and power","Protocol amendments","Missing data","Intention-to-treat analysis"]],
          ["Safety",["Adverse events","Serious adverse events","Discontinuations","Deaths","Exposure duration","Safety subgroup consistency"]],
          ["Regulatory",["Application type and number","Submission acceptance","PDUFA target verification","FDA meeting evidence","Advisory committee evidence","Labeling considerations","Regulatory precedent"]],
          ["Manufacturing",["CMC readiness","Facility inspection status","Manufacturing consistency","Supply-chain risk","Quality-system findings"]],
          ["External validity",["Population representativeness","Subgroup robustness","Cross-trial consistency","Standard-of-care comparison","Independent replication"]],
          ["Decision calibration",["Evidence cutoff date","Data leakage check","Historical cohort selection","Prospective prediction lock","Outcome adjudication","Calibration and uncertainty","PASS/CRL/EXTENSION decision gate"]],
        ] as const).map(([group, requirements]) => <details key={group}><summary>{group} · {requirements.length} requirements · NOT ASSESSED</summary>
          <ol>{requirements.map(item=><li key={item}><strong>{item}</strong> — NOT ASSESSED; evidence-backed analysis required.</li>)}</ol>
        </details>)}
      </details>
      <details><summary>Implementation and validation status</summary>
        <p>Target depth: 50. Live evidence-processing dependency depth: 4. Verified operational 50-level analysis: not established. Independently validated historical decision accuracy: not established. No trading authorization.</p>
      </details>
    </details>
    {[4, 3, 2, 1].map(level => <details key={level} open={level === 4 || level === 1}>
      <summary>{level === 4 ? "Source checks" : level === 1 ? "MAIN processing state" : "Level " + level + " dependencies"}</summary>
      {nodes.filter(event => event.level === level).map(event => <ProcessingNode key={event.node_id} event={event} />)}
    </details>)}
    <p className="subtle">PENDING means queued. Only LOADING steps show a processing indicator. FAILED and INSUFFICIENT EVIDENCE require review; parent status comes from persisted dependency events.</p>
    <style>{`.nct-processing-spinner{display:inline-block;width:12px;height:12px;margin-right:8px;border:2px solid #b9c6ba;border-top-color:#214e2c;border-radius:50%;animation:nct-processing-rotate .8s linear infinite}@keyframes nct-processing-rotate{to{transform:rotate(360deg)}}@media(prefers-reduced-motion:reduce){.nct-processing-spinner{animation:none;border-style:dotted}}`}</style>
  </section>;
}
