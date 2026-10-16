"use client";

import { FormEvent, useEffect, useRef, useState } from "react";

type Stage = "PIPELINE" | "GEM_JR" | "GEM";
type Selections = Record<string, boolean>;
type Pending = { ticker: string; stage: Stage; selections: Selections; notes: string };
type AuthState = "checking" | "login" | "ready" | "unavailable";

const items = [
  { id: "cash", label: "Cash runway", goal: "12+ months" },
  { id: "market_cap", label: "Market capitalization", goal: "$300M–$10B" },
  { id: "approval", label: "Probability of approval", goal: "75%+ (estimate; verify source)" },
  { id: "short_interest", label: "Short interest", goal: "15%+ screening preference" },
  { id: "momentum", label: "30-day price momentum", goal: "Positive" },
  { id: "volume", label: "Relative trading volume", goal: "1.5x+ (provisional)" },
  { id: "financing", label: "Financing / warrants", goal: "No imminent dilution" },
  { id: "phase3", label: "Phase 3 evidence", goal: "Endpoints and p-values verified" },
  { id: "rsi", label: "RSI", goal: "45–65 (provisional)" },
  { id: "trend", label: "Trend / chart base", goal: "Confirmed support; compare SMA20/SMA50" },
  { id: "insiders", label: "Ownership flows", goal: "Review insider and institutional activity" },
  { id: "sources", label: "Source reconciliation", goal: "FDA + SEC + issuer evidence checked" },
  { id: "exit", label: "Hard stop and catalyst exit", goal: "Unambiguous exit policy before entry" },
  { id: "liquidity", label: "Liquidity and float", goal: "Review spreads and tradable float" },
  { id: "atr", label: "ATR and volatility", goal: "Set risk-based levels" },
  { id: "catalyst", label: "PDUFA date", goal: "Verify 30–60 / 30–90-day windows" }
];

const stages: Stage[] = ["PIPELINE", "GEM_JR", "GEM"];
const stageName = (stage: Stage) => stage === "GEM_JR" ? "GEM JR" : stage;
function stateUrl(ticker: string, stage: Stage) {
  return "/api/state?ticker=" + encodeURIComponent(ticker) + "&stage=" + encodeURIComponent(stage);
}

export default function Home() {
  const [auth, setAuth] = useState<AuthState>("checking");
  const [password, setPassword] = useState("");
  const [authError, setAuthError] = useState("");
  const [tickerInput, setTickerInput] = useState("OCGN");
  const [ticker, setTicker] = useState("OCGN");
  const [stage, setStage] = useState<Stage>("GEM_JR");
  const [selections, setSelections] = useState<Selections>({});
  const [notes, setNotes] = useState("");
  const [loaded, setLoaded] = useState(false);
  const [status, setStatus] = useState("Connecting…");
  const pending = useRef<Pending | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const queue = useRef<Promise<void>>(Promise.resolve());
  const versions = useRef<Record<string, number>>({});
  const activeKey = useRef("OCGN|GEM_JR");

  useEffect(() => {
    fetch("/api/auth", { cache: "no-store" }).then(async response => {
      if (response.status === 503) { setAuth("unavailable"); return; }
      if (!response.ok) throw new Error("Unable to check sign-in");
      setAuth((await response.json()).authenticated ? "ready" : "login");
    }).catch(() => setAuth("unavailable"));
  }, []);

  useEffect(() => {
    if (auth !== "ready") return;
    const key = ticker + "|" + stage;
    activeKey.current = key;
    const controller = new AbortController();
    setLoaded(false);
    setStatus("Loading saved checklist…");
    fetch(stateUrl(ticker, stage), { signal: controller.signal, cache: "no-store" })
      .then(async response => {
        if (!response.ok) throw new Error("Checklist could not be loaded (" + response.status + ")");
        return response.json();
      }).then(data => {
        if (controller.signal.aborted) return;
        versions.current[key] = data.version;
        setSelections(data.selections || {});
        setNotes(data.notes || "");
        setLoaded(true);
        setStatus("Restored saved selections");
      }).catch(error => {
        if (!controller.signal.aborted) setStatus(String(error));
      });
    return () => controller.abort();
  }, [auth, ticker, stage]);

  function flushPending(): Promise<void> {
    if (timer.current) clearTimeout(timer.current);
    timer.current = null;
    const change = pending.current;
    pending.current = null;
    if (!change) return queue.current;
    const key = change.ticker + "|" + change.stage;
    queue.current = queue.current.catch(() => {}).then(async () => {
      if (activeKey.current === key) setStatus("Saving…");
      const version = versions.current[key] ?? 0;
      try {
        const response = await fetch(stateUrl(change.ticker, change.stage), {
          method: "PUT", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ version, selections: change.selections, notes: change.notes })
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
          if (activeKey.current === key) setStatus(
            response.status === 409 ? "Conflict — reload checklist before editing" :
              "Save failed — check connection; your change is still on screen"
          );
          return;
        }
        versions.current[key] = data.version;
        if (activeKey.current === key && !pending.current) setStatus("Saved automatically");
      } catch {
        if (activeKey.current === key) setStatus("Save failed — check your connection");
      }
    });
    return queue.current;
  }

  function queueChange(nextSelections: Selections, nextNotes: string, delay: number) {
    pending.current = { ticker, stage, selections: nextSelections, notes: nextNotes };
    setStatus("Unsaved change…");
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => { void flushPending(); }, delay);
  }

  async function signIn(event: FormEvent) {
    event.preventDefault();
    setAuthError("");
    const response = await fetch("/api/auth", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password })
    }).catch(() => null);
    if (response?.ok) { setPassword(""); setAuth("ready"); }
    else setAuthError("Sign-in failed. Check the setup password.");
  }

  async function signOut() {
    await flushPending();
    await fetch("/api/auth", { method: "DELETE" });
    setAuth("login");
    setSelections({});
    setNotes("");
  }

  function selectStage(next: Stage) {
    void flushPending();
    setStage(next);
  }

  function loadTicker(event: FormEvent) {
    event.preventDefault();
    const value = tickerInput.trim().toUpperCase();
    if (!/^[A-Z0-9][A-Z0-9.-]{0,14}$/.test(value)) {
      setStatus("Enter a valid ticker, e.g. OCGN");
      return;
    }
    void flushPending();
    setTicker(value);
  }

  const checked = items.filter(item => selections[item.id]).length;

  if (auth === "checking") return <main className="shell"><h1>PDUFA Command Center</h1><p>Checking setup…</p></main>;
  if (auth === "unavailable") return <main className="shell"><h1>PDUFA Command Center</h1><div className="panel"><h2>Setup required</h2><p>Configure the new platform environment variables before signing in. The existing Streamlit app remains untouched.</p></div></main>;
  if (auth === "login") return (
    <main className="shell">
      <div className="topline">NEW PLATFORM · ISOLATED TEST INSTALL</div>
      <h1>PDUFA Command Center</h1>
      <form className="panel login" onSubmit={signIn}>
        <h2>Sign in to the new platform</h2>
        <label htmlFor="password">Setup password</label>
        <input id="password" type="password" autoComplete="current-password" value={password} onChange={event => setPassword(event.target.value)} required />
        <button type="submit">Sign in</button>
        {authError && <p role="alert" className="error">{authError}</p>}
        <p className="subtle">This is a separate development installation. Streamlit has not been replaced.</p>
      </form>
    </main>
  );

  return (
    <main className="shell">
      <div className="topline">NEW PLATFORM · ISOLATED TEST INSTALL</div>
      <header className="head">
        <div><h1>PDUFA Command Center</h1><p className="subtle">PIPELINE → GEM JR → GEM · Per-ticker autosaved checklist</p></div>
        <button className="secondary" onClick={() => void signOut()}>Sign out</button>
      </header>
      <div className="banner"><strong>Streamlit is preserved.</strong> This is the new platform setup; survey execution and live trading remain disabled.</div>
      <div className="panel controls">
        <form onSubmit={loadTicker}>
          <label htmlFor="ticker">Ticker</label>
          <input id="ticker" value={tickerInput} onChange={event => setTickerInput(event.target.value)} maxLength={15} />
          <button type="submit">Load ticker</button>
        </form>
        <label htmlFor="stage">Stage</label>
        <select id="stage" value={stage} onChange={event => selectStage(event.target.value as Stage)}>
          {stages.map(s => <option key={s} value={s}>{stageName(s)}</option>)}
        </select>
      </div>
      <div className="layout">
        <section className="panel">
          <div className="sectionhead"><div><h2>{ticker} · {stageName(stage)}</h2><p className="subtle">Illustrative checklist — full scoring rules will migrate later</p></div><span className="counter">{checked}/{items.length}</span></div>
          <div aria-live="polite" className="saveState">{status}</div>
          {loaded ? items.map(item => (
            <label key={item.id} className="criteria">
              <input type="checkbox" checked={Boolean(selections[item.id])} onChange={event => {
                const updated = { ...selections, [item.id]: event.target.checked };
                setSelections(updated);
                queueChange(updated, notes, 100);
              }} />
              <span className="criterionText"><strong>{item.label}</strong><span className="goal">GOAL · {item.goal}</span></span>
            </label>
          )) : <p>Loading saved choices…</p>}
        </section>
        <aside className="panel notes">
          <h2>Research notes</h2>
          <p className="subtle">Typing saves after a short pause. Return to this ticker and stage to restore notes.</p>
          <textarea disabled={!loaded} rows={13} value={notes} placeholder="Add entry rationale, financing evidence, risks, and next actions…" onChange={event => {
            const value = event.target.value;
            setNotes(value);
            queueChange(selections, value, 650);
          }} />
          <div className="subtle small">Database-backed. No cookies are used to store your checklist answers.</div>
        </aside>
      </div>
    </main>
  );
}
