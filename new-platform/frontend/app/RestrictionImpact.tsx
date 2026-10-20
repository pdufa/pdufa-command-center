"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import { defaultRestrictionSettings, isRegisteredTrial, type ImpactRecord, type RestrictionEvidence } from "../lib/restriction-impact";
import { calculateCatalogImpact, catalogDefinition, catalogVerdict, defaultCatalogEntries, restoreCatalogEntries,
  type CatalogEntry, type CustomField, type RestrictionStage } from "../lib/restriction-catalog";
import styles from "./RestrictionImpact.module.css";

const count = (n: number) => n.toLocaleString("en-US");
const DRAFT_KEY = "pdufa-restriction-catalog-v1";
const FIELD_OPTIONS: [CustomField, string][] = [["note", "Description only"], ["marketCapMillions", "Latest market cap ($M)"],
  ["runwayMonths", "Cash runway (months)"], ["pdufaDays", "Days until PDUFA"], ["rvol", "Relative volume"],
  ["rsi14", "RSI (14)"], ["avgDollarVolume20", "Average dollar volume"], ["close", "Last closing price"]];
type Inspection = { id: string; kind: "new" | "alone" | "unknown" };
function stageLabel(stage: RestrictionStage) { return stage === "GEM_JR" ? "GEM JR" : stage || "Blank"; }
function StageOptions() { return <><option value="">Blank</option><option value="PIPELINE">Pipeline</option><option value="GEM_JR">GEM JR</option><option value="GEM">GEM</option></>; }

export default function RestrictionImpact({ rows, asOf, cached = false, onRefresh }: {
  rows: ImpactRecord[]; asOf: string; cached?: boolean; onRefresh?: () => void;
}) {
  const [entries, setEntries] = useState(defaultCatalogEntries);
  const [settings, setSettings] = useState(defaultRestrictionSettings);
  const [scope, setScope] = useState("all"), [showStage, setShowStage] = useState("all"), [search, setSearch] = useState("");
  const [ready, setReady] = useState(false), [saved, setSaved] = useState("");
  const [description, setDescription] = useState(""), [customStage, setCustomStage] = useState<RestrictionStage>("");
  const [customField, setCustomField] = useState<CustomField>("note"), [customOperator, setCustomOperator] = useState<">=" | "<=">(">="), [customValue, setCustomValue] = useState("");
  const [evidence, setEvidence] = useState<RestrictionEvidence | null>(null);
  const [error, setError] = useState(""), [loading, setLoading] = useState(false), [version, setVersion] = useState(0);
  const [inspection, setInspection] = useState<Inspection | null>(null), [page, setPage] = useState(0);
  const [scanOpen,setScanOpen]=useState(false);
  const refreshRef = useRef(onRefresh);
  useEffect(() => { refreshRef.current = onRefresh; }, [onRefresh]);
  useEffect(() => {
    try { const raw = window.localStorage.getItem(DRAFT_KEY); if (raw) setEntries(restoreCatalogEntries(JSON.parse(raw))); }
    catch { setSaved("Draft storage unavailable"); }
    setReady(true);
  }, []);
  useEffect(() => {
    if (!ready) return;
    try { window.localStorage.setItem(DRAFT_KEY, JSON.stringify(entries)); setSaved("Draft saved on this browser"); }
    catch { setSaved("Changes are open; this browser could not save the draft"); }
  }, [entries, ready]);
  useEffect(() => {
    const controller = new AbortController(); let active = true;
    setLoading(true); setError("");
    void fetch("/api/restriction-evidence", { cache: "no-store", signal: controller.signal }).then(async response => {
      if (!response.ok) throw new Error("Restriction evidence could not be refreshed. Affected checks need verification.");
      const value: RestrictionEvidence = await response.json();
      if (!value?.issuers || !value.trialTypes || !Array.isArray(value.sources) || !Array.isArray(value.issues) || typeof value.fetchedAt !== "string") throw new Error("Invalid restriction evidence.");
      if (active) setEvidence(value);
    }).catch(cause => { if (active && !controller.signal.aborted) { setEvidence(null); setError(cause instanceof Error ? cause.message : "Restriction evidence unavailable"); } })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; controller.abort(); };
  }, [version, asOf]);
  useEffect(() => {
    const timer = window.setInterval(() => { if (document.visibilityState === "visible") { setVersion(v => v + 1); refreshRef.current?.(); } }, 300000);
    return () => window.clearInterval(timer);
  }, []);
  const scoped = useMemo(() => scope === "trials" ? rows.filter(isRegisteredTrial) : rows, [rows, scope]);
  const report = useMemo(() => calculateCatalogImpact(scoped, entries, settings, evidence, asOf), [scoped, entries, settings, evidence, asOf]);
  const visible = entries.filter(entry => (showStage === "all" || entry.stage === showStage) &&
    (!search || (catalogDefinition(entry).title + " " + catalogDefinition(entry).category).toLowerCase().includes(search.toLowerCase()))).sort((a,b) => Number(!!a.priority)-Number(!!b.priority) || (a.stage||"").localeCompare(b.stage||"") || Number(a.priority||0)-Number(b.priority||0));
  const selectedEntry = entries.find(entry => entry.id === inspection?.id), selectedStep = report.steps.get(inspection?.id || "");
  const inspected = useMemo(() => {
    if (!inspection || !selectedEntry || !selectedStep) return [];
    return report.rows.filter(row => inspection.kind === "new" ? selectedStep.newlyExcludedIds.has(row.id) :
      catalogVerdict(selectedEntry, row, settings, evidence, asOf, report.junior) === (inspection.kind === "unknown" ? "UNKNOWN" : "FAIL"));
  }, [inspection, selectedEntry, selectedStep, report.rows, report.junior, settings, evidence, asOf]);
  const pages = Math.max(1, Math.ceil(inspected.length / 25)), currentPage = Math.min(page, pages - 1);
  function update(id: string, patch: Partial<CatalogEntry>) { setEntries(current => current.map(entry => entry.id === id ? { ...entry, ...patch } : entry)); setPage(0); }
  function inspect(id: string, kind: Inspection["kind"]) { setInspection({ id, kind }); setPage(0); }
  function addCustom(event: React.FormEvent) {
    event.preventDefault(); if (!description.trim() || entries.filter(e => e.id.startsWith("custom_")).length >= 100) return;
    setEntries(current => [...current, { id: "custom_" + crypto.randomUUID(), title: description.trim(), stage: customStage,
      enabled: false, priority: "", field: customField, operator: customOperator, value: customValue, maximum: "" }]);
    setDescription(""); setCustomValue(""); setShowStage("all"); setSearch("");
  }
  const capDates = [...new Set(Object.values(evidence?.issuers || {}).map(issuer => issuer.capAsOf.slice(0, 10)).filter(Boolean))].sort();
  return <section className={"panel " + styles.panel} aria-labelledby="restriction-impact-title" id="restrictions">
    <div className={styles.heading}><div><h2 id="restriction-impact-title">RESTRICTIONS</h2>
      <p>Enter a priority number to select a restriction automatically, edit its value, and choose <strong>Blank, Pipeline, GEM JR, or GEM</strong>.</p></div>
      <div className={styles.buttons}><button type="button" className="secondary" disabled={loading} onClick={() => { setVersion(v => v + 1); onRefresh?.(); }}>{loading ? "REFRESHING…" : "REFRESH PUBLISHED DATA"}</button>
        <button type="button" className="secondary" onClick={() => { setEntries(defaultCatalogEntries()); setSettings(defaultRestrictionSettings()); setInspection(null); setPage(0); }}>RESET TO APPROVED RULES</button></div></div>
    <p className={styles.note}>Blank leaves a rule unassigned. Numbered, assigned rules screen in <strong>Pipeline → GEM JR → GEM</strong> order; each stage starts with the preceding stage’s remaining records. This page previews the effects; saved stage memberships and the existing scan selections stay as recorded.</p>
    <p className={styles.note} role="status">{saved || "Loading saved assignments…"}</p>
    <div className={styles.controls}>
      <label>Starting universe<select aria-label="Starting universe" value={scope} onChange={event => { setScope(event.target.value); setPage(0); }}><option value="all">All dashboard entries ({count(rows.length)})</option><option value="trials">Registered trials only ({count(rows.filter(isRegisteredTrial).length)})</option></select></label>
      <label>Market-cap evidence<select aria-label="Market-cap evidence" value={settings.capBasis} onChange={event => setSettings(current => ({ ...current, capBasis: event.target.value as "entry" | "current" }))}><option value="entry">At first entry — approved rule</option><option value="current">Latest saved cap — comparison</option></select></label>
    </div>
    <p className={styles.notice}>{settings.capBasis === "entry" ? "Entry-date market caps have not been retained. The approved Pipeline cap checks need verification. Select Latest saved cap for the current-cap comparison."
      : "CURRENT-CAP COMPARISON: the approved Pipeline cap checks use latest saved caps for this preview. Your approved rule applies at first entry. Existing GEM current-cap options use latest saved caps in either mode."}</p>
    {(cached || error) && <p role="alert" className={styles.notice}>{cached ? "Trial universe is locally cached; latest-source verification is pending. " : ""}{error}</p>}
    {!!evidence?.issues.length && <p role="status" className={styles.notice}>{evidence.issues.join(" ")}</p>}
    <button type="button" onClick={()=>setScanOpen(true)}>SCAN SELECTED RESTRICTIONS — FULL RESULTS</button>
    <h3>LIVE EFFECT FROM THE BEGINNING</h3>
    <div className={styles.totals} aria-live="polite" aria-atomic="true"><div><span>Starting universe</span><strong>{count(report.total)}</strong></div><div><span>Excluded across assigned rules</span><strong>{count(report.excluded)}</strong></div><div><span>Pass all enabled checks</span><strong>{count(report.passed)}</strong></div><div><span>Needs verification</span><strong>{count(report.pending)}</strong></div></div>
    <div className={styles.stageTotals}>{report.stages.map(stage => <div key={stage.stage}><strong>{stageLabel(stage.stage)}</strong><span>Starts {count(stage.before)} · Excludes {count(stage.excluded)}</span><b>{count(stage.remaining)} remain</b><small>{count(stage.passed)} pass · {count(stage.pending)} need verification</small></div>)}</div>
    <form className={styles.customForm} onSubmit={addCustom} aria-label="Add a custom restriction"><h3>WRITE A RESTRICTION</h3>
      <label>Restriction<textarea aria-label="Custom restriction" maxLength={400} value={description} onChange={event => setDescription(event.target.value)} placeholder="Write your restriction here…" required /></label>
      <div className={styles.controls}><label>Apply to<select aria-label="New restriction stage" value={customStage} onChange={event => setCustomStage(event.target.value as RestrictionStage)}><StageOptions /></select></label>
        <label>Evidence field<select aria-label="New restriction evidence field" value={customField} onChange={event => setCustomField(event.target.value as CustomField)}>{FIELD_OPTIONS.map(([key, title]) => <option key={key} value={key}>{title}</option>)}</select></label>
        {customField !== "note" && <><label>Comparison<select aria-label="New restriction comparison" value={customOperator} onChange={event => setCustomOperator(event.target.value as ">=" | "<=")}><option value=">=">At least ≥</option><option value="<=">At most ≤</option></select></label><label>Target<input aria-label="New restriction target" type="number" min="0" step="any" value={customValue} onChange={event => setCustomValue(event.target.value)} required /></label></>}</div>
      <p className={styles.note}>Description-only restrictions are saved as checks needing verification. Select a numeric evidence field to calculate an exclusion count.</p>
      <button type="submit" disabled={!description.trim()}>ADD RESTRICTION</button>
    </form>
    <div className={styles.controls}><label>Show rules<select aria-label="Show restriction stage" value={showStage} onChange={event => setShowStage(event.target.value)}><option value="all">Full list — all stages</option><StageOptions /></select></label>
      <label>Find restriction<input type="search" aria-label="Find restriction" maxLength={100} value={search} onChange={event => setSearch(event.target.value)} placeholder="Name or category" /></label></div>
    <p className={styles.note}>{visible.length} of {entries.length} restrictions shown. A numbered rule automatically moves to the selected list below; clear its number to return it to available restrictions. List search changes visibility only. “Excluded alone” always starts from the full universe. “New exclusions” counts additional removals at the numbered step. Remaining includes unknowns.</p>
    <h3>AVAILABLE RESTRICTIONS ABOVE · SELECTED RESTRICTIONS AT BOTTOM</h3><p className={styles.note}>P = Pipeline · J = GEM JR · G = GEM. Enter a number to select; delete it to deselect. Numbers are independent within each stage.</p><div className={styles.scroll} role="region" aria-label="Sequential restriction effects" tabIndex={0}><table className={styles.table + " " + styles.catalog}><caption>Full restriction catalog and live effect. Rules within each stage run in numerical priority order. Rules without priority numbers have no cumulative effect.</caption>
      <thead><tr><th>Priority / restriction</th><th>Apply to</th><th>Value / target</th><th>Excluded alone</th><th>New exclusions</th><th>Remaining / pending</th><th>Inspect</th></tr></thead><tbody>
        <tr className={styles.start}><th scope="row">0. FULL STARTING UNIVERSE</th><td colSpan={4}>Every source record before restrictions</td><td>{count(report.total)}</td><td>Unfiltered</td></tr>
        {visible.map(entry => { const rule = catalogDefinition(entry), step = report.steps.get(entry.id)!, used = entry.enabled && !!entry.priority && !!entry.stage && !rule.warning;
          return <tr key={entry.id} className={!used ? styles.inactive : undefined}>
            <th scope="row"><label className={styles.rule}><span style={{display:"inline-flex",alignItems:"center",gap:4,flexShrink:0}}><strong>{entry.stage === "PIPELINE" ? "P" : entry.stage === "GEM_JR" ? "J" : entry.stage === "GEM" ? "G" : "—"}</strong><input style={{width:64,minWidth:54}} type="number" min="1" max="9999" step="1" placeholder="#" aria-label={"Priority for " + rule.title} value={entry.priority || ""} onChange={event => { const value=event.target.value; if(value && (!/^\d{1,4}$/.test(value) || Number(value)<1))return; update(entry.id,{priority:value,enabled:!!value}); }} /></span><span>{rule.title}<small>{rule.category}{rule.warning ? " · WARNING ONLY" : ""}</small></span></label>
              {entry.id.startsWith("custom_") && <input aria-label={"Edit " + rule.title} maxLength={400} value={entry.title} onChange={event => update(entry.id, { title: event.target.value })} />}
              <details><summary>How this is checked</summary><p>{rule.help}</p></details></th>
            <td data-label="Apply to"><select aria-label={"Stage for " + rule.title} value={entry.stage} onChange={event => update(entry.id, { stage: event.target.value as RestrictionStage })}><StageOptions /></select><small>{used ? "Step " + step.step : entry.stage ? "No priority / warning only" : "Unassigned · no effect"}</small></td>
            <td data-label="Value / target">{entry.id.startsWith("custom_") ? <div className={styles.valueFields}><select aria-label={"Evidence field for " + rule.title} value={entry.field} onChange={event => update(entry.id, { field: event.target.value as CustomField })}>{FIELD_OPTIONS.map(([key, title]) => <option key={key} value={key}>{title}</option>)}</select>{entry.field !== "note" && <><select aria-label={"Comparison for " + rule.title} value={entry.operator} onChange={event => update(entry.id, { operator: event.target.value as ">=" | "<=" })}><option value=">=">At least ≥</option><option value="<=">At most ≤</option></select><input aria-label={"Target for " + rule.title} type="number" min="0" step="any" value={entry.value} onChange={event => update(entry.id, { value: event.target.value })} /></>}</div>
              : rule.value !== undefined ? <div className={styles.valueFields}><input aria-label={entry.id === "minCap" ? "Minimum cap ($ millions)" : entry.id === "maxCap" ? "Maximum cap ($ millions)" : "Target for " + rule.title} type={rule.numeric ? "number" : "text"} min={rule.numeric ? "0" : undefined} step="any" maxLength={400} value={entry.value} onChange={event => update(entry.id, { value: event.target.value })} />{rule.maximum !== undefined && <input aria-label={"Maximum for " + rule.title} type="number" min="0" step="any" value={entry.maximum} onChange={event => update(entry.id, { maximum: event.target.value })} />}<small>{rule.unit}</small></div> : "No numerical target"}</td>
            <td data-label="Excluded alone">{rule.warning ? "Warning only" : count(step.aloneFail)}<small>{count(step.aloneUnknown)} unknown alone</small></td>
            <td data-label="New exclusions">{used ? count(step.newlyExcluded) : "No effect"}</td>
            <td data-label="Remaining / pending">{entry.stage ? <>{count(step.remaining)} remain<small>{count(step.passed)} pass · {count(step.pending)} need verification</small></> : "—"}</td>
            <td data-label="Inspect"><div className={styles.inspectButtons}><button type="button" className="secondary" disabled={!step.newlyExcluded} onClick={() => inspect(entry.id, "new")}>NEW EXCLUSIONS</button><button type="button" className="secondary" disabled={!step.aloneFail} onClick={() => inspect(entry.id, "alone")}>EXCLUDED ALONE</button><button type="button" className="secondary" disabled={!step.aloneUnknown} onClick={() => inspect(entry.id, "unknown")}>UNKNOWN ALONE</button>
              {entry.id.startsWith("custom_") && <button type="button" className="secondary" onClick={() => { setEntries(current => current.filter(e => e.id !== entry.id)); if (inspection?.id === entry.id) setInspection(null); }}>REMOVE CUSTOM RULE</button>}</div></td>
          </tr>;
        })}</tbody></table></div>
    {scanOpen && <section role="dialog" aria-modal="true" aria-label="Scan results" style={{position:"fixed",inset:0,zIndex:9999,background:"white",color:"black",overflowY:"auto",padding:16}}><button type="button" onClick={()=>setScanOpen(false)}>CLOSE ×</button><h2>FULL SCAN RESULTS</h2><p>Scanned {count(report.total)} · Passed {count(report.passed)} · Excluded {count(report.excluded)} · Needs verification {count(report.pending)}</p><div className={styles.scroll}><table><thead><tr><th>Priority</th><th>Restriction</th><th>New exclusions</th><th>Remaining</th><th>Pending</th></tr></thead><tbody>{entries.filter(e=>report.steps.get(e.id)?.step).sort((a,b)=>(report.steps.get(a.id)?.step||0)-(report.steps.get(b.id)?.step||0)).map(e=>{const step=report.steps.get(e.id)!;return <tr key={e.id}><td>{e.stage==="PIPELINE"?"P":e.stage==="GEM_JR"?"J":"G"}{e.priority}</td><td>{catalogDefinition(e).title}</td><td>{count(step.newlyExcluded)}</td><td>{count(step.remaining)}</td><td>{count(step.pending)}</td></tr>})}</tbody></table></div><h3>REMAINING TRIALS</h3><p>Use the NEW EXCLUSIONS buttons in the restriction table to inspect removed records.</p><div className={styles.scroll}><table><thead><tr><th>Trial</th><th>Ticker</th><th>Drug</th></tr></thead><tbody>{report.rows.filter(row=>![...report.steps.values()].some(step=>step.step && step.newlyExcludedIds.has(row.id))).slice(0,250).map(row=><tr key={row.id}><td>{row.programId||row.id}</td><td>{row.ticker}</td><td>{row.drug||"Unknown"}</td></tr>)}</tbody></table></div><p>Showing first 250 remaining records.</p></section>}
    {!visible.length && <p>No restrictions match this list view.</p>}
    {inspection && selectedEntry && <section className={styles.inspection} aria-label="Affected records"><div className={styles.heading}><h4>{catalogDefinition(selectedEntry).title} — {inspection.kind === "new" ? "new exclusions at this step" : inspection.kind === "alone" ? "excluded by this rule alone" : "needs verification for this rule"} ({count(inspected.length)})</h4><button type="button" className="secondary" onClick={() => setInspection(null)} aria-label="Close affected records">CLOSE ×</button></div>
      <div className={styles.scroll}><table><thead><tr><th>Program / record</th><th>Ticker</th><th>Drug</th><th>Stage</th></tr></thead><tbody>{inspected.slice(currentPage * 25, (currentPage + 1) * 25).map(row => <tr key={row.id}><td>{row.programId || row.id}</td><td>{row.ticker}</td><td>{row.drug || "Not recorded"}</td><td>{row.stage || "Unknown"}</td></tr>)}</tbody></table></div>
      {!inspected.length && <p>No matching records under the current assignments.</p>}
      <div className={styles.buttons}><button type="button" className="secondary" disabled={currentPage === 0} onClick={() => setPage(currentPage - 1)}>PREVIOUS 25</button><span>Page {currentPage + 1} of {pages}</span><button type="button" className="secondary" disabled={currentPage + 1 >= pages} onClick={() => setPage(currentPage + 1)}>NEXT 25</button></div></section>}
    <p className={styles.note}>Trial universe as of {asOf}. Evidence {evidence ? "fetched " + new Date(evidence.fetchedAt).toLocaleString() : loading ? "loading…" : "unavailable"}. Saved cap dates: {capDates.length ? capDates.join(", ") : "not available"}. Published evidence refreshes every five minutes while visible.</p>
    {evidence && <details className={styles.sources}><summary>Data sources ({evidence.sources.length})</summary><ul>{evidence.sources.map(source => <li key={source.name}><a href={source.url} target="_blank" rel="noopener noreferrer">{source.name}</a> · {count(source.rows)} saved rows</li>)}</ul></details>}
  </section>;
}
