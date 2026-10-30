"use client";
import { useEffect, useRef, useState } from "react";

type Leaf = { node_id: string; label: string; status: string; value?: unknown; spinner?: boolean };
type Event = { type: string; nct_id: string; node_id?: string; label?: string; status?: string; value?: unknown; spinner?: boolean; decision?: string; section?: string; available?: number; total?: number };

export default function PredictionTab() {
  const [code, setCode] = useState("");
  const [active, setActive] = useState("");
  const [leaves, setLeaves] = useState<Leaf[]>([]);
  const [state, setState] = useState("Enter an NCT number to load saved trial evidence.");
  const [decision, setDecision] = useState("ABSTAIN");
  const [identityProgress, setIdentityProgress] = useState<{ available: number; total: number; status: string } | null>(null);
  const controller = useRef<AbortController | null>(null);
  const generation = useRef(0);
  useEffect(() => () => controller.current?.abort(), []);
  async function load() {
    const nct = code.trim().toUpperCase();
    generation.current += 1;
    const current = generation.current;
    controller.current?.abort();
    controller.current = new AbortController();
    setActive(nct); setLeaves([]); setDecision("ABSTAIN"); setIdentityProgress(null);
    if (!/^NCT[0-9]{8}$/.test(nct)) { setState("Enter an exact NCT identifier."); return; }
    setState("Retrieving saved trial evidence…");
    try {
      const response = await fetch("/api/prediction-events/" + nct, {
        cache: "no-store", signal: controller.current.signal,
      });
      if (!response.ok || !response.body) throw new Error(response.status === 404 ? "No saved dossier for this trial." : "Evidence stream unavailable.");
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");
        let index: number;
        while ((index = buffer.indexOf("\n\n")) !== -1) {
          const frame = buffer.slice(0, index);
          buffer = buffer.slice(index + 2);
          const line = frame.split("\n").find(x => x.startsWith("data: "));
          if (!line || generation.current !== current) continue;
          const event = JSON.parse(line.slice(6)) as Event;
          if (event.nct_id !== nct) continue;
          if (event.type === "leaf" && event.node_id && event.label && event.status) {
            const leaf: Leaf = { node_id: event.node_id, label: event.label, status: event.status, value: event.value, spinner: event.spinner };
            setLeaves(prev => [...prev.filter(x => x.node_id !== leaf.node_id), leaf]);
          }
          if (event.type === "progress" && event.section === "trial_identity" && typeof event.available === "number" && typeof event.total === "number") {
            setIdentityProgress({ available: event.available, total: event.total, status: event.status || "PARTIAL" });
          }
          if (event.type === "complete") { setDecision(event.decision || "ABSTAIN"); setState("Saved evidence loaded. Full scientific prediction pending."); }
        }
      }
    } catch (error) {
      if (generation.current === current && !(error instanceof DOMException && error.name === "AbortError"))
        setState(error instanceof Error ? error.message : "Evidence stream failed.");
    }
  }
  return <section className="panel" aria-label="PREDICTION tab" id="prediction-tab">
    <h2>PREDICTION · Bottom-up trial evidence</h2>
    <p className="subtle">Enter one NCT code. Saved evidence appears item by item. New scientific research and prediction calculations are not yet active.</p>
    <form onSubmit={event => { event.preventDefault(); void load(); }}>
      <label htmlFor="prediction-nct">Trial code</label>{" "}
      <input id="prediction-nct" value={code} onChange={event => setCode(event.target.value)} placeholder="NCT01234567" maxLength={11} />{" "}
      <button type="submit">Load trial</button>
    </form>
    <p role="status">{state}</p>
    {active && <p><strong>{active}</strong> · MAIN: {decision}</p>}
    <details open><summary>Trial identity · {identityProgress?.available ?? leaves.filter(x => x.status === "AVAILABLE").length}/{identityProgress?.total ?? 4} available</summary>
      {leaves.map(leaf => <div key={leaf.node_id} style={{ margin: "8px 0" }}>
        <strong>{leaf.spinner ? "◌ " : leaf.status === "AVAILABLE" ? "✓ " : "⚠ "}{leaf.label}</strong>
        <div style={{ overflowWrap: "anywhere" }}>{leaf.value == null ? "Unavailable" : JSON.stringify(leaf.value)}</div>
      </div>)}
    </details>
    <details><summary>SCIENCE · 0/40 assessed</summary><p>Scientific assessment processing not installed.</p></details>
    <details><summary>OUTCOME · Pending</summary><p>Independent regulatory assessment pending.</p></details>
    <details><summary>MAIN · {decision}</summary><p>Not authorized as a trading recommendation.</p></details>
  </section>;
}
