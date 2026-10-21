"use client";
import { Fragment, useEffect, useMemo, useRef, useState, type Dispatch, type SetStateAction } from "react";
import { defaultRestrictionSettings, isRegisteredTrial, type ImpactRecord, type RestrictionEvidence } from "../lib/restriction-impact";
import { calculateCatalogImpact, catalogDefinition, catalogVerdict, defaultCatalogEntries, restoreCatalogEntries,
  catalogStages, RESTRICTION_STAGES, type CatalogEntry, type CustomField, type RestrictionStage } from "../lib/restriction-catalog";
import styles from "./RestrictionImpact.module.css";

const count = (n: number) => n.toLocaleString("en-US");
const DRAFT_KEY = "pdufa-restriction-catalog-v1";
const FIELD_OPTIONS: [CustomField, string][] = [["note", "Description only"], ["marketCapMillions", "Latest market cap ($M)"],
  ["runwayMonths", "Cash runway (months)"], ["pdufaDays", "Days until PDUFA"], ["rvol", "Relative volume"],
  ["rsi14", "RSI (14)"], ["avgDollarVolume20", "Average dollar volume"], ["close", "Last closing price"]];
type Inspection = { id: string; kind: "new" | "alone" | "unknown" };
function stageLabel(stage: RestrictionStage) { return stage === "GEM_JR" ? "GEM JR" : stage || "Blank"; }
function StageOptions() { return <><option value="">Blank</option><option value="PIPELINE">Pipeline</option><option value="GEM_JR">GEM JR</option><option value="GEM">GEM</option></>; }

// Display groups come from the original FS/FA associations, never from editable stage assignments.
// A rule shared by two presets has one editable master row and a read-only cross-reference.
const ASSOCIATION_GROUPS = [
  { id: "PIPELINE", title: "PIPELINE", note: "Original Pipeline restrictions and proposals" },
  { id: "GEM JR FS", title: "GEM JR — FS", note: "Original GEM JR FS suggested requirements" },
  { id: "GEM JR FA", title: "GEM JR — FA", note: "Original GEM JR FA requirements" },
  { id: "GEM FS", title: "GEM — FS", note: "Original GEM FS suggested requirements" },
  { id: "GEM FA", title: "GEM — FA", note: "Original GEM FA input requirement" },
  { id: "INDEPENDENT", title: "OTHER / INDEPENDENT", note: "Optional, manual and custom restrictions without an FS/FA preset" },
] as const;
type AssociationGroupId = typeof ASSOCIATION_GROUPS[number]["id"];
function primaryGroup(entry: CatalogEntry): AssociationGroupId {
  const definition = catalogDefinition(entry);
  if (definition.category.includes("Pipeline")) return "PIPELINE";
  return (definition.associations?.[0] as AssociationGroupId | undefined) || "INDEPENDENT";
}
function isMemberOfGroup(entry: CatalogEntry, group: AssociationGroupId): boolean {
  if (group === "PIPELINE" || group === "INDEPENDENT") return primaryGroup(entry) === group;
  return !!catalogDefinition(entry).associations?.includes(group);
}
function groupTitle(id: AssociationGroupId): string {
  return ASSOCIATION_GROUPS.find(group => group.id === id)?.title || id;
}

export default function RestrictionImpact({ rows, asOf, cached = false, onRefresh, managedEntries, onManagedEntriesChange }: {
  rows: ImpactRecord[]; asOf: string; cached?: boolean; onRefresh?: () => void; managedEntries?:CatalogEntry[]; onManagedEntriesChange?:Dispatch<SetStateAction<CatalogEntry[]>>;
}) {
  const [localEntries, setLocalEntries] = useState(defaultCatalogEntries);
  const entries = managedEntries ?? localEntries;
  const setEntries = onManagedEntriesChange ?? setLocalEntries;
  const [settings, setSettings] = useState(defaultRestrictionSettings);
  const [scope, setScope] = useState("all"), [showStage, setShowStage] = useState("all"), [groupFilter, setGroupFilter] = useState("all"), [search, setSearch] = useState("");
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
    try { if(!managedEntries){const raw = window.localStorage.getItem(DRAFT_KEY); if (raw) setEntries(restoreCatalogEntries(JSON.parse(raw)));} }
    catch { setSaved("Draft storage unavailable"); }
    setReady(true);
  }, []);
  useEffect(() => {
    if (!ready) return;
    if(managedEntries){setSaved("Master restrictions saved for this browser");return;}
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
  const [capPopup,setCapPopup]=useState(false);
  const capStats=useMemo(()=>{let within=0,outside=0,unknown=0;for(const row of rows.filter(isRegisteredTrial)){const issuer=evidence?.issuers[row.ticker.toUpperCase()];const cap=issuer?.marketCap;if(typeof cap!=="number"||!Number.isFinite(cap)||cap<=0)unknown++;else if(cap>=300000000&&cap<=10000000000)within++;else outside++;}return {within,outside,unknown,total:within+outside+unknown};},[rows,evidence]);
  const scoped = useMemo(() => scope === "trials" ? rows.filter(isRegisteredTrial) : rows, [rows, scope]);
  const report = useMemo(() => calculateCatalogImpact(scoped, entries, settings, evidence, asOf), [scoped, entries, settings, evidence, asOf]);
  const visible = entries.filter(entry => (showStage === "all" || catalogStages(entry).includes(showStage as Exclude<RestrictionStage, "">)) &&
    (!search || (catalogDefinition(entry).title + " " + catalogDefinition(entry).category + " " + (catalogDefinition(entry).associations || []).join(" ")).toLowerCase().includes(search.toLowerCase()))).sort((a,b) => Number(!!a.priority)-Number(!!b.priority) || (a.stage||"").localeCompare(b.stage||"") || Number(a.priority||0)-Number(b.priority||0));
  const sections = [
    { id: "available", title: "AVAILABLE — NOT NUMBERED", members: visible.filter(entry => !entry.priority) },
    { id: "selected", title: "SELECTED — NUMBERED RESTRICTIONS", members: visible.filter(entry => !!entry.priority) },
  ].map(section => ({
    ...section,
    groups: ASSOCIATION_GROUPS.filter(group => groupFilter === "all" || groupFilter === group.id)
      .map(group => ({ ...group, members: section.members.filter(entry => isMemberOfGroup(entry, group.id)) }))
      .filter(group => group.members.length > 0),
  })).filter(section => section.groups.length > 0);
  const selectedEntry = entries.find(entry => entry.id === inspection?.id), selectedStep = report.steps.get(inspection?.id || "") || (selectedEntry ? report.steps.get(catalogStages(selectedEntry)[0] + "|" + selectedEntry.id) : undefined);
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
    setDescription(""); setCustomValue(""); setShowStage("all"); setGroupFilter("all"); setSearch("");
  }
  const capDates = [...new Set(Object.values(evidence?.issuers || {}).map(issuer => issuer.capAsOf.slice(0, 10)).filter(Boolean))].sort();
  return <section className={"panel " + styles.panel} aria-labelledby="restriction-impact-title" id="restrictions">
    <div className={styles.heading}><div><h2 id="restriction-impact-title">RESTRICTIONS</h2>
      <p>Restrictions are organized by their original Pipeline, GEM JR FS, GEM JR FA, GEM FS and GEM FA groups. Shared associations are linked to one master rule; no preset assignments are changed. Number a rule to move it into the selected groups below.</p></div>
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
    <button type="button" onClick={()=>setCapPopup(true)}>SCAN PIPELINE MARKET CAP $300M–$10B</button>
    {capPopup && <section role="dialog" aria-modal="true" aria-label="Market cap scan" style={{position:"fixed",inset:0,zIndex:10001,background:"white",color:"black",overflowY:"auto",padding:20}}><button type="button" onClick={()=>setCapPopup(false)}>CLOSE ×</button><h2>PIPELINE MARKET CAP SCAN</h2><p>Latest saved market caps, not historical entry-date caps. Registered trials only. Inclusive range: $300 million to $10 billion.</p><div className={styles.totals}><div><span>Trials checked</span><strong>{count(capStats.total)}</strong></div><div><span>Within range</span><strong>{count(capStats.within)}</strong></div><div><span>Outside range</span><strong>{count(capStats.outside)}</strong></div><div><span>Unknown cap</span><strong>{count(capStats.unknown)}</strong></div></div><p>Data fetched: {evidence?.fetchedAt||"Not available"}. Counts reflect available source evidence and do not imply historical Pipeline qualification.</p></section>}
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
    <div className={styles.controls}><label>Association group<select aria-label="Restriction association group" value={groupFilter} onChange={event => setGroupFilter(event.target.value)}><option value="all">All original groups</option>{ASSOCIATION_GROUPS.map(group => <option key={group.id} value={group.id}>{group.title}</option>)}</select></label>
      <label>Show rules<select aria-label="Show restriction stage" value={showStage} onChange={event => setShowStage(event.target.value)}><option value="all">Full list — all stages</option><StageOptions /></select></label>
      <label>Find restriction<input type="search" aria-label="Find restriction" maxLength={100} value={search} onChange={event => setSearch(event.target.value)} placeholder="Name or category" /></label></div>
    <p className={styles.note}>{visible.length} of {entries.length} unique restrictions match your search and stage. Original FS / FA groups remain separate; a shared restriction has one editable row with read-only cross-references in its other groups. A numbered rule moves into SELECTED at the bottom. “Excluded alone” starts from the full universe; “New exclusions” follows stage priority order. Unknown evidence remains pending.</p>
    <h3>RESTRICTIONS BY ORIGINAL ASSOCIATION GROUP</h3><p className={styles.note}>P = Pipeline · J = GEM JR · G = GEM. FS and FA memberships stay exactly as originally defined. Registry is shared by GEM JR FS and FA; Cash Runway is shared by Pipeline and GEM JR FS. A shared reference is not an extra restriction. Numbered rules remain at the bottom.</p><div className={styles.scroll} role="region" aria-label="Sequential restriction effects" tabIndex={0}><table className={styles.table + " " + styles.catalog}><caption>Full restriction catalog and live effect. Rules within each stage run in numerical priority order. Rules without priority numbers have no cumulative effect.</caption>
      <thead><tr><th>Priority / restriction</th><th>Apply to</th><th>FS / FA association</th><th>Value / target</th><th>Excluded alone</th><th>New exclusions</th><th>Remaining / pending</th><th>Inspect</th></tr></thead><tbody>
        <tr className={styles.start}><th scope="row">0. FULL STARTING UNIVERSE</th><td colSpan={5}>Every source record before restrictions</td><td>{count(report.total)}</td><td>Unfiltered</td></tr>
        {sections.map(section => <Fragment key={section.id}>
          <tr style={{background:"#dcece0"}}><th scope="colgroup" colSpan={8} style={{fontWeight:800,fontSize:15}}>{section.title} · {section.members.length} unique restrictions</th></tr>
          {section.groups.map(group => <Fragment key={group.id}>
            <tr style={{background:"#eaf2eb"}}><th scope="colgroup" colSpan={8}><strong style={{fontSize:15}}>{group.title} · {group.members.length}</strong><small style={{fontWeight:400,marginLeft:10}}>{group.note}</small></th></tr>
            {group.members.map(entry => { const rule = catalogDefinition(entry);
              if (groupFilter === "all" && primaryGroup(entry) !== group.id) return <tr key={group.id+"-shared-"+entry.id} style={{background:"#f6f9f6"}}>
                <th scope="row">{rule.title}<small>Shared original association: {group.title}</small></th>
                <td colSpan={7} style={{fontWeight:500}}>Same master restriction, editable once under <strong>{groupTitle(primaryGroup(entry))}</strong>. Its settings and scan effects are shared, not duplicated.</td>
              </tr>;
              const step = report.steps.get(entry.id) || report.steps.get(catalogStages(entry)[0] + "|" + entry.id)!, used = entry.enabled && !!entry.priority && catalogStages(entry).length > 0 && !rule.warning;
          return <tr key={entry.id} className={!used ? styles.inactive : undefined}>
            <th scope="row"><label className={styles.rule}><span style={{display:"inline-flex",alignItems:"center",gap:4,flexShrink:0}}><strong>{entry.stage === "PIPELINE" ? "P" : entry.stage === "GEM_JR" ? "J" : entry.stage === "GEM" ? "G" : "—"}</strong><input style={{width:64,minWidth:54}} type="number" min="1" max="9999" step="1" placeholder="#" aria-label={"Priority for " + rule.title} value={entry.priority || ""} onChange={event => { const value=event.target.value; if(value && (!/^\d{1,4}$/.test(value) || Number(value)<1))return; update(entry.id,{priority:value,enabled:!!value}); }} /></span><span>{rule.title}<small>{rule.category}{rule.warning ? " · WARNING ONLY" : ""}</small></span></label>
              {entry.id.startsWith("custom_") && <input aria-label={"Edit " + rule.title} maxLength={400} value={entry.title} onChange={event => update(entry.id, { title: event.target.value })} />}
              <details><summary>How this is checked</summary><p>{rule.help}</p></details></th>
            <td data-label="Apply to"><select aria-label={"Stage for " + rule.title} value={entry.stage} onChange={event => { const next=event.target.value as RestrictionStage; update(entry.id,{stage:next,additionalStages:(entry.additionalStages||[]).filter(stage=>stage!==next)}); }}><StageOptions /></select>
              <div style={{display:"flex",flexWrap:"wrap",gap:8,marginTop:6}}>{RESTRICTION_STAGES.filter(stage=>stage!==entry.stage).map(stage=><label key={stage} style={{display:"inline-flex",alignItems:"center",gap:3,fontSize:11}}><input type="checkbox" aria-label={"Also apply "+rule.title+" to "+stage} checked={(entry.additionalStages||[]).includes(stage)} onChange={event=>update(entry.id,{additionalStages:event.target.checked?[...new Set([...(entry.additionalStages||[]),stage])]: (entry.additionalStages||[]).filter(value=>value!==stage)})}/>{stage==="GEM_JR"?"JR":stage==="PIPELINE"?"P":"G"}</label>)}</div>
              <small>{used ? "Assigned to "+catalogStages(entry).map(stage=>stage==="GEM_JR"?"JR":stage).join(", ") : catalogStages(entry).length ? "No priority / warning only" : "Unassigned · no effect"}</small></td>
            <td data-label="FS / FA association">{rule.associations?.length ? rule.associations.join(" · ") : "Independent"}<small>Existing preset mapping</small></td>
            <td data-label="Value / target">{entry.id.startsWith("custom_") ? <div className={styles.valueFields}><select aria-label={"Evidence field for " + rule.title} value={entry.field} onChange={event => update(entry.id, { field: event.target.value as CustomField })}>{FIELD_OPTIONS.map(([key, title]) => <option key={key} value={key}>{title}</option>)}</select>{entry.field !== "note" && <><select aria-label={"Comparison for " + rule.title} value={entry.operator} onChange={event => update(entry.id, { operator: event.target.value as ">=" | "<=" })}><option value=">=">At least ≥</option><option value="<=">At most ≤</option></select><input aria-label={"Target for " + rule.title} type="number" min="0" step="any" value={entry.value} onChange={event => update(entry.id, { value: event.target.value })} /></>}</div>
              : rule.value !== undefined ? <div className={styles.valueFields}><input aria-label={entry.id === "minCap" ? "Minimum cap ($ millions)" : entry.id === "maxCap" ? "Maximum cap ($ millions)" : "Target for " + rule.title} type={rule.numeric ? "number" : "text"} min={rule.numeric ? "0" : undefined} step="any" maxLength={400} value={entry.value} onChange={event => update(entry.id, { value: event.target.value })} />{rule.maximum !== undefined && <input aria-label={"Maximum for " + rule.title} type="number" min="0" step="any" value={entry.maximum} onChange={event => update(entry.id, { maximum: event.target.value })} />}<small>{rule.unit}</small></div> : "No numerical target"}</td>
            <td data-label="Excluded alone">{rule.warning ? "Warning only" : count(step.aloneFail)}<small>{count(step.aloneUnknown)} unknown alone</small></td>
            <td data-label="New exclusions">{used ? <>{count(step.newlyExcluded)}{(entry.additionalStages||[]).filter(stage=>stage!==entry.stage).map(stage=>{const extra=report.steps.get(stage+"|"+entry.id);return extra ? <small key={stage}>{stage==="GEM_JR"?"JR":stage}: {count(extra.newlyExcluded)} additional</small>:null;})}</> : "No effect"}</td>
            <td data-label="Remaining / pending">{entry.stage ? <>{count(step.remaining)} remain<small>{count(step.passed)} pass · {count(step.pending)} need verification</small></> : "—"}</td>
            <td data-label="Inspect"><div className={styles.inspectButtons}><button type="button" className="secondary" disabled={!step.newlyExcluded} onClick={() => inspect(entry.id, "new")}>NEW EXCLUSIONS</button><button type="button" className="secondary" disabled={!step.aloneFail} onClick={() => inspect(entry.id, "alone")}>EXCLUDED ALONE</button><button type="button" className="secondary" disabled={!step.aloneUnknown} onClick={() => inspect(entry.id, "unknown")}>UNKNOWN ALONE</button>
              {entry.id.startsWith("custom_") && <button type="button" className="secondary" onClick={() => { setEntries(current => current.filter(e => e.id !== entry.id)); if (inspection?.id === entry.id) setInspection(null); }}>REMOVE CUSTOM RULE</button>}</div></td>
          </tr>;
            })}
          </Fragment>)}
        </Fragment>)}</tbody></table></div>
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
