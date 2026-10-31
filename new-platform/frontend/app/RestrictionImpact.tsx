"use client";
import { Fragment, useEffect, useMemo, useRef, useState, type Dispatch, type SetStateAction } from "react";
import { defaultRestrictionSettings, isRegisteredTrial, type ImpactRecord, type RestrictionEvidence } from "../lib/restriction-impact";
import { calculateCatalogImpact, catalogDefinition, catalogVerdict, defaultCatalogEntries, restoreCatalogEntries,
  catalogStages, catalogStagePriority, selectedRestrictionList, insertRestrictionIntoList, removeRestrictionFromList, marketCapLimitLabel, RESTRICTION_STAGES, RESTRICTION_PURPOSE_GROUPS, restrictionPurposeGroup, type CatalogEntry, type CustomField, type RestrictionStage } from "../lib/restriction-catalog";
import { poolRuleDefinition } from "../lib/pool-pipeline-restrictions";
import styles from "./RestrictionImpact.module.css";

const count = (n: number) => n.toLocaleString("en-US");
const DRAFT_KEY = "pdufa-restriction-catalog-v1";
const FIELD_OPTIONS: [CustomField, string][] = [["note", "Description only"], ["marketCapMillions", "Latest market cap ($M)"],
  ["runwayMonths", "Cash runway (months)"], ["pdufaDays", "Days until PDUFA"], ["rvol", "Relative volume"],
  ["rsi14", "RSI (14)"], ["avgDollarVolume20", "Average dollar volume"], ["close", "Last closing price"]];
type Inspection = { id: string; kind: "new" | "alone" | "unknown" };
function stageLabel(stage: RestrictionStage) { return stage === "GEM_JR" ? "GEM JR" : stage || "Blank"; }
function StageOptions({ poolPipelineOnly=false }: { poolPipelineOnly?:boolean }) { return <><option value="">{poolPipelineOnly?"Pool · unassigned":"Blank"}</option><option value="PIPELINE">Pipeline</option>{!poolPipelineOnly && <><option value="GEM_JR">GEM JR</option><option value="GEM">GEM</option></>}</>; }

// Subject matter determines each rule's single display group. Original FS/FA
// associations remain visible separately and unchanged in the rule row.

export default function RestrictionImpact({ rows, asOf, cached = false, onRefresh, managedEntries, onManagedEntriesChange, poolPipelineOnly = false }: {
  rows: ImpactRecord[]; asOf: string; cached?: boolean; onRefresh?: () => void; managedEntries?:CatalogEntry[]; onManagedEntriesChange?:Dispatch<SetStateAction<CatalogEntry[]>>; poolPipelineOnly?: boolean;
}) {
  const activeStages: readonly ("PIPELINE"|"GEM_JR"|"GEM")[] = poolPipelineOnly ? ["PIPELINE"] : RESTRICTION_STAGES;
  const ruleDefinition = poolPipelineOnly ? poolRuleDefinition : catalogDefinition;
  const [localEntries, setLocalEntries] = useState(defaultCatalogEntries);
  const entries = managedEntries ?? localEntries;
  const setEntries = onManagedEntriesChange ?? setLocalEntries;
  const [settings, setSettings] = useState(defaultRestrictionSettings);
  const [scope, setScope] = useState("all"), [showStage, setShowStage] = useState("all"), [purposeFilter, setPurposeFilter] = useState("all"), [search, setSearch] = useState("");
  const [ready, setReady] = useState(false), [saved, setSaved] = useState("");
  const [description, setDescription] = useState(""), [customStage, setCustomStage] = useState<RestrictionStage>("");
  const [customField, setCustomField] = useState<CustomField>("note"), [customOperator, setCustomOperator] = useState<">=" | "<=">(">="), [customValue, setCustomValue] = useState("");
  const [evidence, setEvidence] = useState<RestrictionEvidence | null>(null);
  const [error, setError] = useState(""), [loading, setLoading] = useState(false), [version, setVersion] = useState(0);
  const [inspection, setInspection] = useState<Inspection | null>(null), [page, setPage] = useState(0);
  const [scanOpen,setScanOpen]=useState(false);
  const [listPopup,setListPopup]=useState(false);
  const [listStage,setListStage]=useState<"PIPELINE"|"GEM_JR"|"GEM">("PIPELINE");
  const [listRuleId,setListRuleId]=useState("gem_marketcap");
  const [listPosition,setListPosition]=useState(0);
  const [removePending,setRemovePending]=useState<{id:string;stage:Exclude<RestrictionStage,"">}|null>(null);
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
  const marketCapEntry = entries.find(entry=>entry.id==="gem_marketcap");
  const marketCapLists = marketCapEntry && marketCapEntry.enabled
    ? catalogStages(marketCapEntry).filter(stage=>!!catalogStagePriority(marketCapEntry,stage)) : [];
  const capStats=useMemo(()=>{let within=0,outside=0,unknown=0;for(const row of rows.filter(isRegisteredTrial)){const issuer=evidence?.issuers[row.ticker.toUpperCase()];const cap=issuer?.marketCap;if(typeof cap!=="number"||!Number.isFinite(cap)||cap<=0)unknown++;else if(cap>=300000000&&cap<=10000000000)within++;else outside++;}return {within,outside,unknown,total:within+outside+unknown};},[rows,evidence]);
  const scoped = useMemo(() => scope === "trials" ? rows.filter(isRegisteredTrial) : rows, [rows, scope]);
  const report = useMemo(() => calculateCatalogImpact(scoped, entries, settings, evidence, asOf), [scoped, entries, settings, evidence, asOf]);
  const sequentialImpact = useMemo(() => {
    const universe = [...new Map(scoped.map(row => [row.id, row])).values()];
    const selected = activeStages.flatMap(stage => selectedRestrictionList(entries, stage)
      .filter(entry => entry.enabled && !ruleDefinition(entry).warning).map(entry => ({ entry, stage })));
    const caps = selected.filter(item => restrictionPurposeGroup(item.entry) === "MARKET_CAP");
    const rest = selected.filter(item => restrictionPurposeGroup(item.entry) !== "MARKET_CAP");
    const ordered = [...caps, ...rest];
    const seen = new Set<string>();
    const unique = ordered.filter(item => { if (seen.has(item.entry.id)) return false; seen.add(item.entry.id); return true; });
    let survivors = universe;
    const steps = unique.map(({entry, stage}) => {
      const before = survivors.length;
      let removed = 0, unknown = 0;
      survivors = survivors.filter(row => {
        const verdict = catalogVerdict(entry, row, settings, evidence, asOf, report.junior);
        if (verdict === "FAIL") { removed++; return false; }
        if (verdict === "UNKNOWN") unknown++;
        return true;
      });
      return { id: entry.id, title: ruleDefinition(entry).title, stage, before, removed, remaining: survivors.length, unknown };
    });
    const capSteps = steps.filter(step => caps.some(item => item.entry.id === step.id));
    return { initial: universe.length, afterCap: capSteps.length ? capSteps[capSteps.length - 1].remaining : universe.length,
      capUnknown: capSteps.reduce((total, step) => total + step.unknown, 0), steps, final: survivors.length, hasCap: capSteps.length > 0 };
  }, [scoped, entries, settings, evidence, asOf, report.junior]);
  const individualImpact = useMemo(() => entries.map(entry => {
    const rule = ruleDefinition(entry);
    const step = report.steps.get(entry.id) || report.steps.get(catalogStages(entry)[0] + "|" + entry.id);
    const excluded = rule.warning ? 0 : (step?.aloneFail ?? 0);
    return { entry, rule, excluded, unknown: step?.aloneUnknown ?? report.total,
      passed: step?.passed ?? 0, remaining: report.total - excluded };
  }).sort((a, b) => b.excluded - a.excluded || a.rule.title.localeCompare(b.rule.title)), [entries, report]);
  function exportIndividualImpact() {
    const header = ["Restriction","Stage","Original FS/FA","Active","Warning only","Starting trials","Excluded alone","Remaining","Verified pass","Unknown","Percent excluded"];
    const quote = (value: string | number | boolean) => '"' + String(value).replace(/"/g, '""') + '"';
    const lines = [header, ...individualImpact.map(item => [
      item.rule.title, catalogStages(item.entry).join(" / "), (item.rule.associations || []).join(" / "),
      item.entry.enabled && catalogStages(item.entry).some(stage => !!catalogStagePriority(item.entry, stage)),
      !!item.rule.warning, report.total, item.excluded, item.remaining, item.passed, item.unknown,
      report.total ? (100 * item.excluded / report.total).toFixed(2) : "0.00",
    ])].map(line => line.map(quote).join(",")).join("\r\n");
    const url = URL.createObjectURL(new Blob(["\uFEFF" + lines], { type: "text/csv;charset=utf-8" }));
    const anchor = document.createElement("a");
    anchor.href = url; anchor.download = "pdufa-individual-restriction-impact.csv";
    document.body.appendChild(anchor); anchor.click(); anchor.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  const visible = entries.filter(entry => (showStage === "all" || catalogStages(entry).includes(showStage as Exclude<RestrictionStage, "">)) &&
    (!search || (ruleDefinition(entry).title + " " + ruleDefinition(entry).category + " " + (ruleDefinition(entry).associations || []).join(" ")).toLowerCase().includes(search.toLowerCase()))).sort((a,b) => Number(!!a.priority)-Number(!!b.priority) || (a.stage||"").localeCompare(b.stage||"") || Number(a.priority||0)-Number(b.priority||0));
  const sections = [
    { id: "available", title: "AVAILABLE — NOT NUMBERED", members: visible.filter(entry => !entry.priority) },
    { id: "selected", title: "SELECTED — NUMBERED RESTRICTIONS", members: visible.filter(entry => !!entry.priority) },
  ].map(section => ({
    ...section,
    groups: RESTRICTION_PURPOSE_GROUPS.filter(group => purposeFilter === "all" || purposeFilter === group.id)
      .map(group => ({ ...group, members: section.members.filter(entry => restrictionPurposeGroup(entry) === group.id) }))
      .filter(group => group.members.length > 0),
  })).filter(section => section.groups.length > 0);
  const listEntries = selectedRestrictionList(entries,listStage);
  const positionOptions = listEntries.filter(entry=>entry.id!==listRuleId);
  const proposedEntries = useMemo(()=>listPopup
    ? insertRestrictionIntoList(entries,listRuleId,listStage,listPosition) : entries,
    [entries,listRuleId,listStage,listPosition,listPopup]);
  const proposedReport = useMemo(()=>listPopup ? calculateCatalogImpact(scoped,proposedEntries,settings,evidence,asOf) : null,
    [listPopup,scoped,proposedEntries,settings,evidence,asOf]);
  const currentStage = report.stages.find(item=>item.stage===listStage);
  const proposedStage = proposedReport?.stages.find(item=>item.stage===listStage);
  function openListPopup(id:string) {
    const entry=entries.find(item=>item.id===id);
    const dest=restrictionPurposeGroup(entry||{id})==="MARKET_CAP"?"PIPELINE" : (entry?.stage||"PIPELINE");
    setListRuleId(id);setListStage(dest);setListPosition(0);setListPopup(true);
  }
  function openStageListPopup(stage: Exclude<RestrictionStage, "">, ruleId?:string, position=0) {
    const list=selectedRestrictionList(entries,stage);
    const suggested=stage==="PIPELINE"?"gem_marketcap":stage==="GEM_JR"?"gem_phase3":"gem_pdufa";
    setListStage(stage);
    setListRuleId(ruleId||list[0]?.id||suggested);
    setListPosition(position);
    setListPopup(true);
  }
  function applyListSelection() {
    const chosen=entries.find(entry=>entry.id===listRuleId);
    if(!chosen||ruleDefinition(chosen).warning)return;
    setEntries(current=>insertRestrictionIntoList(current,listRuleId,listStage,listPosition));
    setSaved("Restriction added to "+stageLabel(listStage)+" list");
    setListPopup(false);
  }
  function requestRemoveFromList(id:string,stage:Exclude<RestrictionStage,"">) {
    if (!selectedRestrictionList(entries,stage).some(entry=>entry.id===id)) return;
    setListPopup(false);
    setRemovePending({id,stage});
  }
  function confirmRemoveFromList() {
    if (!removePending) return;
    const {id,stage}=removePending;
    setEntries(current=>removeRestrictionFromList(current,id,stage));
    setSaved(ruleDefinition(entries.find(entry=>entry.id===id)!).title+" removed from "+stageLabel(stage)+" list");
    setRemovePending(null);
  }
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
    setDescription(""); setCustomValue(""); setShowStage("all"); setPurposeFilter("all"); setSearch("");
  }
  const capDates = [...new Set(Object.values(evidence?.issuers || {}).map(issuer => issuer.capAsOf.slice(0, 10)).filter(Boolean))].sort();
  return <section className={"panel " + styles.panel} aria-labelledby="restriction-impact-title" id="restrictions">
    <div className={styles.heading}><div><h2 id="restriction-impact-title">{poolPipelineOnly?"POOL → PIPELINE RESTRICTIONS":"RESTRICTIONS"}</h2>
      <p>{poolPipelineOnly?"Choose available Pool rules and assign them to Pipeline. No GEM JR/GEM or FS/FA association is used. Market cap remains $300M–$10B.":"Market Cap first. Select a stage, set the restriction and see how many trials remain. FS/FA associations stay unchanged."}</p></div>
      <div className={styles.buttons}><button type="button" className="secondary" disabled={loading} onClick={() => { setVersion(v => v + 1); onRefresh?.(); }}>{loading ? "REFRESHING…" : "REFRESH DATA"}</button></div></div>
    <section className={styles.listOverview} aria-label={poolPipelineOnly?"Independent Pool/Pipeline restrictions":"Three restriction lists"}>
      <div className={styles.listOverviewHeading}><h3>{poolPipelineOnly?"PIPELINE ASSIGNED RESTRICTIONS":"RESTRICTION LISTS"}</h3><small>{poolPipelineOnly?"Available rules remain in Pool until assigned. No GEM JR/GEM lists or FS/FA links.":"Pipeline, GEM JR and GEM are side by side. Select a rule or use ADD / REORDER. Original FS/FA associations stay unchanged."}</small></div>
      <div className={styles.listOverviewScroll} role="region" aria-label={poolPipelineOnly?"Pipeline restriction list":"Pipeline GEM JR and GEM restriction lists"} tabIndex={0}>
        <div className={styles.listOverviewGrid}>
          {activeStages.map(stage=>{
            const selected=selectedRestrictionList(entries,stage);
            const stageResult=report.stages.find(item=>item.stage===stage);
            return <section key={stage} className={styles.listOverviewCard} aria-label={stageLabel(stage)+" restriction list"} data-restriction-list={stage}>
              <div className={styles.listOverviewCardHeading}>
                <h4>{stageLabel(stage).toUpperCase()}</h4>
                <span>{selected.length} active</span>
              </div>
              <div className={styles.listOverviewCardCount}><strong>{stageResult?count(stageResult.remaining):"—"}</strong><span>trials remain after this stage</span></div>
              <div className={styles.listOverviewMembers}>
                {selected.length?<ol>{selected.map((entry,i)=><li key={entry.id} className={styles.listOverviewMemberRow}>
                  <button type="button" className={styles.listOverviewEdit} aria-label={"Edit "+ruleDefinition(entry).title+" in "+stageLabel(stage)+" list"}
                    onClick={()=>openStageListPopup(stage,entry.id,i)}>
                    <strong>#{catalogStagePriority(entry,stage)}</strong>
                    <span className={styles.listOverviewRuleText}>
                      <span>{ruleDefinition(entry).title}</span>
                      {marketCapLimitLabel(entry) && <small className={styles.marketCapNumbers}>{marketCapLimitLabel(entry)}</small>}
                    </span>
                  </button>
                  <button type="button" className={styles.listOverviewRemove}
                    aria-label={"Remove "+ruleDefinition(entry).title+" from "+stageLabel(stage)+" list"}
                    onClick={()=>requestRemoveFromList(entry.id,stage)}>REMOVE ×</button>
                </li>)}</ol>:<p>No active restrictions yet.</p>}
              </div>
              <button type="button" className={styles.listOverviewAction} aria-label={"Edit "+stageLabel(stage)+" restriction list"}
                onClick={()=>openStageListPopup(stage)}>ADD / REORDER</button>
            </section>;
          })}
        </div>
      </div>
    </section>
    <div className={styles.marketCapShortcut} aria-label="Market cap restriction quick access">
      <div><strong>CURRENT MARKET-CAP RANGE</strong>
        <p>Minimum ${marketCapEntry?.value || "300"}M · Maximum ${marketCapEntry?.maximum || "10000"}M</p>
        <small>{marketCapLists.length ? marketCapLists.map(stage=>stageLabel(stage)+" #"+catalogStagePriority(marketCapEntry!,stage)).join(" · ") : "Not active in a scan list"}</small>
      </div>
      <div className={styles.buttons}>
        <button type="button" onClick={()=>openListPopup("gem_marketcap")}>ADD MARKET CAP TO PIPELINE</button>
        <button type="button" className="secondary" onClick={()=>{setPurposeFilter("MARKET_CAP");setShowStage("all");setSearch("");}}>SHOW MARKET CAP RESTRICTIONS</button>
      </div>
    </div>
    <p className={styles.note}>Tap <strong>ADD TO LIST</strong> beside a restriction to choose its list and position. Numbered rules appear in SELECTED below; use the shortcut above to reach Market Cap directly.</p>
    <p className={styles.note} role="status">{saved || "Loading saved assignments…"}</p>
    <div className={styles.controls}>
      <label>Starting universe<select aria-label="Starting universe" value={scope} onChange={event => { setScope(event.target.value); setPage(0); }}><option value="all">All dashboard entries ({count(rows.length)})</option><option value="trials">Registered trials only ({count(rows.filter(isRegisteredTrial).length)})</option></select></label>
      <label>Market-cap evidence<select aria-label="Market-cap evidence" value={settings.capBasis} onChange={event => setSettings(current => ({ ...current, capBasis: event.target.value as "entry" | "current" }))}><option value="entry">At first entry — approved rule</option><option value="current">Latest saved cap — comparison</option></select></label>
    </div>
    <p className={styles.notice}>{settings.capBasis === "entry" ? "Entry-date market caps have not been retained. The approved Pipeline cap checks need verification. Select Latest saved cap for the current-cap comparison."
      : "CURRENT-CAP COMPARISON: the approved Pipeline cap checks use latest saved caps for this preview. Your approved rule applies at first entry. Existing GEM current-cap options use latest saved caps in either mode."}</p>
    {(cached || error) && <p role="alert" className={styles.notice}>{cached ? "Trial universe is locally cached; latest-source verification is pending. " : ""}{error}</p>}
    {!!evidence?.issues.length && <p role="status" className={styles.notice}>{evidence.issues.join(" ")}</p>}
    <div className={styles.buttons}><button type="button" onClick={()=>setCapPopup(true)}>SCAN PIPELINE MARKET CAP $300M–$10B</button><button type="button" onClick={()=>openListPopup("gem_marketcap")}>VIEW / EDIT RESTRICTION LISTS</button><button type="button" onClick={()=>setScanOpen(true)}>VIEW FULL SCAN RESULTS</button></div>
    {capPopup && <section role="dialog" aria-modal="true" aria-label="Market cap scan" style={{position:"fixed",inset:0,zIndex:10001,background:"white",color:"black",overflowY:"auto",padding:20}}><button type="button" onClick={()=>setCapPopup(false)}>CLOSE ×</button><h2>PIPELINE MARKET CAP SCAN</h2><p>Latest saved market caps, not historical entry-date caps. Registered trials only. Inclusive range: $300 million to $10 billion.</p><div className={styles.totals}><div><span>Trials checked</span><strong>{count(capStats.total)}</strong></div><div><span>Within range</span><strong>{count(capStats.within)}</strong></div><div><span>Outside range</span><strong>{count(capStats.outside)}</strong></div><div><span>Unknown cap</span><strong>{count(capStats.unknown)}</strong></div></div><p>Data fetched: {evidence?.fetchedAt||"Not available"}. Counts reflect available source evidence and do not imply historical Pipeline qualification.</p></section>}
    <h3>LIVE SCAN SUMMARY</h3>
    <div className={styles.totals} aria-live="polite" aria-atomic="true"><div><span>Trials checked</span><strong>{count(report.total)}</strong></div><div><span>Trials remaining</span><strong>{count(report.total-report.excluded)}</strong></div><div><span>Excluded</span><strong>{count(report.excluded)}</strong></div><div><span>Need verification</span><strong>{count(report.pending)}</strong></div></div>
    <details className={styles.extra}><summary>{poolPipelineOnly?"Pipeline restriction breakdown":"Breakdown by Pipeline, GEM JR and GEM"}</summary><p className={styles.note}>Verified passes: {count(report.passed)}. Remaining includes records awaiting verification.</p>
      <div className={styles.stageTotals}>{report.stages.filter(stage=>activeStages.includes(stage.stage)).map(stage => <div key={stage.stage}><strong>{stageLabel(stage.stage)}</strong><span>Starts {count(stage.before)} · Excludes {count(stage.excluded)}</span><b>{count(stage.remaining)} remain</b><small>{count(stage.passed)} pass · {count(stage.pending)} need verification</small></div>)}</div>
    </details>
    <details className={styles.extra}><summary>Write a custom restriction</summary><form className={styles.customForm} onSubmit={addCustom} aria-label="Add a custom restriction"><h3>WRITE A RESTRICTION</h3>
      <label>Restriction<textarea aria-label="Custom restriction" maxLength={400} value={description} onChange={event => setDescription(event.target.value)} placeholder="Write your restriction here…" required /></label>
      <div className={styles.controls}><label>Apply to<select aria-label="New restriction stage" value={customStage} onChange={event => setCustomStage(event.target.value as RestrictionStage)}><StageOptions poolPipelineOnly={poolPipelineOnly} /></select></label>
        <label>Evidence field<select aria-label="New restriction evidence field" value={customField} onChange={event => setCustomField(event.target.value as CustomField)}>{FIELD_OPTIONS.map(([key, title]) => <option key={key} value={key}>{title}</option>)}</select></label>
        {customField !== "note" && <><label>Comparison<select aria-label="New restriction comparison" value={customOperator} onChange={event => setCustomOperator(event.target.value as ">=" | "<=")}><option value=">=">At least ≥</option><option value="<=">At most ≤</option></select></label><label>Target<input aria-label="New restriction target" type="number" min="0" step="any" value={customValue} onChange={event => setCustomValue(event.target.value)} required /></label></>}</div>
      <p className={styles.note}>Description-only restrictions are saved as checks needing verification. Select a numeric evidence field to calculate an exclusion count.</p>
      <button type="submit" disabled={!description.trim()}>ADD RESTRICTION</button>
    </form></details>
    <div className={styles.controls}><label>Restriction purpose<select aria-label="Restriction purpose group" value={purposeFilter} onChange={event => setPurposeFilter(event.target.value)}><option value="all">All groups — importance order</option>{RESTRICTION_PURPOSE_GROUPS.map(group => <option key={group.id} value={group.id}>{group.title}</option>)}</select></label>
      <label>Show rules<select aria-label="Show restriction stage" value={showStage} onChange={event => setShowStage(event.target.value)}><option value="all">Full list — all stages</option><StageOptions poolPipelineOnly={poolPipelineOnly} /></select></label>
      <label>Find restriction<input type="search" aria-label="Find restriction" maxLength={100} value={search} onChange={event => setSearch(event.target.value)} placeholder="Name or category" /></label></div>
    <p className={styles.note}>{visible.length} of {entries.length} restrictions shown. Use ADD TO LIST to see existing list members and insert a rule at #1 or any position.</p>
    <section aria-label="Sequential restriction impact after market cap">
      <h3>SEQUENTIAL RESTRICTION REDUCTION — MARKET CAP FIRST</h3>
      <div className={styles.totals}>
        <div><span>Starting trials</span><strong>{count(sequentialImpact.initial)}</strong></div>
        <div><span>After market-cap restrictions</span><strong>{count(sequentialImpact.afterCap)}</strong></div>
        <div><span>After all active restrictions</span><strong>{count(sequentialImpact.final)}</strong></div>
      </div>
      <p className={styles.note}><strong>Each row starts with the remaining trials from the previous row.</strong> Market-cap restrictions run first, followed by the other active Pipeline, GEM JR, and GEM rules in their list order. Trials with missing evidence are kept and shown as Unknown, not silently excluded. A rule assigned to multiple lists is counted once in this combined reduction view; the separate list assignments are unchanged.</p>
      {!sequentialImpact.hasCap && <p role="alert" className={styles.notice}>No active market-cap restriction is assigned. Add the $300M–$10B market-cap rule to Pipeline to establish the requested starting population.</p>}
      <div className={styles.scroll} role="region" aria-label="Sequential restriction impact table" tabIndex={0}>
        <table className={styles.table}>
          <thead><tr><th>Step</th><th>Restriction</th><th>Trials entering</th><th>Removed now</th><th>Trials left</th><th>Unknown this step</th></tr></thead>
          <tbody>{sequentialImpact.steps.map((step, i) => <tr key={step.id}>
            <td>{i + 1}</td><th scope="row">{step.title}<small>{stageLabel(step.stage)}</small></th>
            <td>{count(step.before)}</td><td><strong>{count(step.removed)}</strong></td>
            <td><strong>{count(step.remaining)}</strong></td><td>{count(step.unknown)}</td>
          </tr>)}</tbody>
        </table>
      </div>
      <p className={styles.note}>Market cap at original Pipeline entry cannot be fully verified where historical entry-date values are missing. This table is a sequential evidence-based preview, not proof that all remaining trials passed every rule.</p>
      <details className={styles.extra}><summary>Compare all restrictions independently (not sequentially)</summary>
        <p className={styles.note}>This optional comparison tests each rule against the original {count(report.total)} entries. Do not add those exclusions together.</p>
        <div className={styles.buttons}><button type="button" onClick={exportIndividualImpact}>DOWNLOAD INDEPENDENT RULE COUNTS (CSV)</button></div>
        <div className={styles.scroll} role="region" aria-label="Independent restriction comparison" tabIndex={0}>
          <table className={styles.table}><thead><tr><th>Rule</th><th>Removed alone</th><th>Remaining alone</th><th>Unknown</th></tr></thead>
          <tbody>{individualImpact.map(item => <tr key={item.entry.id}><th scope="row">{item.rule.title}</th><td>{count(item.excluded)}</td><td>{count(item.remaining)}</td><td>{count(item.unknown)}</td></tr>)}</tbody></table>
        </div>
      </details>
    </section>
    <h3>RESTRICTIONS — MARKET CAP FIRST</h3><div className={styles.scroll} role="region" aria-label="Sequential restriction effects" tabIndex={0}><table className={styles.table + " " + styles.catalog}><caption>Each restriction appears once. Open details for extra diagnostics.</caption>
      <thead><tr><th>Scan order / restriction</th><th>Apply to</th><th>{poolPipelineOnly?"Independent pool":"Original FS / FA"}</th><th>Target</th><th>Results</th><th>More</th></tr></thead><tbody>
        {sections.map(section => <Fragment key={section.id}>
          <tr style={{background:"#dcece0"}}><th scope="colgroup" colSpan={6} style={{fontWeight:800,fontSize:15}}>{section.title} · {section.members.length} unique restrictions</th></tr>
          {section.groups.map(group => <Fragment key={group.id}>
            <tr data-purpose-group={group.id} style={{background:"#eaf2eb"}}><th scope="colgroup" colSpan={6}><strong style={{fontSize:15}}>{group.title} · {group.members.length}</strong><small style={{fontWeight:400,marginLeft:10}}>{group.note}</small></th></tr>
            {group.members.map(entry => { const rule = ruleDefinition(entry);
              const step = report.steps.get(entry.id) || report.steps.get(catalogStages(entry)[0] + "|" + entry.id)!, used = entry.enabled && catalogStages(entry).some(stage=>!!catalogStagePriority(entry,stage)) && !rule.warning;
          return <tr key={entry.id} className={!used ? styles.inactive : undefined}>
            <th scope="row"><label className={styles.rule}><span style={{display:"inline-flex",alignItems:"center",gap:4,flexShrink:0}}><strong>{entry.stage === "PIPELINE" ? "P" : entry.stage === "GEM_JR" ? "J" : entry.stage === "GEM" ? "G" : "—"}</strong><input style={{width:64,minWidth:54}} type="number" min="1" max="9999" step="1" placeholder="#" aria-label={"Priority for " + rule.title} value={entry.stage ? catalogStagePriority(entry,entry.stage) : entry.priority || ""} onChange={event => { const value=event.target.value; if(value && (!/^\d{1,4}$/.test(value) || Number(value)<1))return; update(entry.id,{priority:value,enabled:!!value,stagePriorities:entry.stage?{...entry.stagePriorities,[entry.stage]:value}:entry.stagePriorities}); }} /></span><span>{rule.title}<small>{rule.warning ? "WARNING ONLY" : (entry.stage && catalogStagePriority(entry,entry.stage) ? "Scan order "+catalogStagePriority(entry,entry.stage) : "Not in scan")}</small></span></label>
              {entry.id.startsWith("custom_") && <input aria-label={"Edit " + rule.title} maxLength={400} value={entry.title} onChange={event => update(entry.id, { title: event.target.value })} />}
              <button type="button" className="secondary" style={{marginTop:8}} aria-label={"Add "+rule.title+" to a list"} disabled={!!rule.warning} onClick={()=>openListPopup(entry.id)}>ADD TO LIST</button>
              <details><summary>How this is checked</summary><p>{rule.help}</p></details></th>
            <td data-label="Apply to"><select aria-label={"Stage for " + rule.title} value={entry.stage} onChange={event => { const next=event.target.value as RestrictionStage; update(entry.id,{stage:next,additionalStages:(entry.additionalStages||[]).filter(stage=>stage!==next)}); }}><StageOptions poolPipelineOnly={poolPipelineOnly} /></select>
              {!poolPipelineOnly && <details><summary>Additional stages</summary><div style={{display:"flex",flexWrap:"wrap",gap:8,marginTop:6}}>{activeStages.filter(stage=>stage!==entry.stage).map(stage=><label key={stage} style={{display:"inline-flex",alignItems:"center",gap:3,fontSize:11}}><input type="checkbox" aria-label={"Also apply "+rule.title+" to "+stage} checked={(entry.additionalStages||[]).includes(stage)} onChange={event=>update(entry.id,{additionalStages:event.target.checked?[...new Set([...(entry.additionalStages||[]),stage])]: (entry.additionalStages||[]).filter(value=>value!==stage)})}/>{stage==="GEM_JR"?"JR":stage==="PIPELINE"?"P":"G"}</label>)}</div></details>}
              <small>{used ? "Assigned to "+catalogStages(entry).map(stage=>stage==="GEM_JR"?"JR":stage).join(", ") : catalogStages(entry).length ? "No priority / warning only" : "Unassigned · no effect"}</small></td>
            <td data-label={poolPipelineOnly?"Independent pool":"Original FS / FA"}>{rule.associations?.length ? rule.associations.join(" · ") : "Independent"}</td>
            <td data-label="Value / target">{entry.id.startsWith("custom_") ? <div className={styles.valueFields}><select aria-label={"Evidence field for " + rule.title} value={entry.field} onChange={event => update(entry.id, { field: event.target.value as CustomField })}>{FIELD_OPTIONS.map(([key, title]) => <option key={key} value={key}>{title}</option>)}</select>{entry.field !== "note" && <><select aria-label={"Comparison for " + rule.title} value={entry.operator} onChange={event => update(entry.id, { operator: event.target.value as ">=" | "<=" })}><option value=">=">At least ≥</option><option value="<=">At most ≤</option></select><input aria-label={"Target for " + rule.title} type="number" min="0" step="any" value={entry.value} onChange={event => update(entry.id, { value: event.target.value })} /></>}</div>
              : rule.value !== undefined ? <div className={styles.valueFields}><input aria-label={entry.id === "minCap" ? "Minimum cap ($ millions)" : entry.id === "maxCap" ? "Maximum cap ($ millions)" : "Target for " + rule.title} type={rule.numeric ? "number" : "text"} min={rule.numeric ? "0" : undefined} step="any" maxLength={400} value={entry.value} onChange={event => update(entry.id, { value: event.target.value })} />{rule.maximum !== undefined && <input aria-label={"Maximum for " + rule.title} type="number" min="0" step="any" value={entry.maximum} onChange={event => update(entry.id, { maximum: event.target.value })} />}<small>{rule.unit}</small></div> : "No numerical target"}</td>
            <td data-label="Results">{entry.stage ? <>{count(step.remaining)} remain<small>{count(step.pending)} need verification</small></> : "Unassigned"}</td>
            <td data-label="More"><details className={styles.rowDetails}><summary>Impact details</summary>
              <div className={styles.ruleMetrics}><div><strong>{rule.warning ? "Warning" : count(step.aloneFail)}</strong><small>Excluded alone</small></div><div><strong>{used ? count(step.newlyExcluded) : "—"}</strong><small>New exclusions</small></div><div><strong>{count(step.aloneUnknown)}</strong><small>Unknown alone</small></div><div><strong>{count(step.passed)}</strong><small>Verified pass</small></div></div>
              {(entry.additionalStages||[]).filter(stage=>stage!==entry.stage).map(stage=>{const extra=report.steps.get(stage+"|"+entry.id);return extra ? <small key={stage}>{stage==="GEM_JR"?"JR":stage}: {count(extra.newlyExcluded)} additional exclusions</small>:null;})}
              <div className={styles.inspectButtons}><button type="button" className="secondary" disabled={!step.newlyExcluded} onClick={() => inspect(entry.id, "new")}>NEW EXCLUSIONS</button><button type="button" className="secondary" disabled={!step.aloneFail} onClick={() => inspect(entry.id, "alone")}>EXCLUDED ALONE</button><button type="button" className="secondary" disabled={!step.aloneUnknown} onClick={() => inspect(entry.id, "unknown")}>UNKNOWN ALONE</button>
              {entry.id.startsWith("custom_") && <button type="button" className="secondary" onClick={() => { setEntries(current => current.filter(e => e.id !== entry.id)); if (inspection?.id === entry.id) setInspection(null); }}>REMOVE CUSTOM RULE</button>}</div>
            </details></td>
          </tr>;
            })}
          </Fragment>)}
        </Fragment>)}</tbody></table></div>

    {removePending && <section role="dialog" aria-modal="true" aria-label="Confirm restriction removal" className={styles.listBackdrop}>
      <div className={styles.removeModal}>
        <h2>REMOVE FROM {stageLabel(removePending.stage).toUpperCase()}?</h2>
        <p>Remove <strong>{ruleDefinition(entries.find(entry=>entry.id===removePending.id)!).title}</strong>{marketCapLimitLabel(entries.find(entry=>entry.id===removePending.id)!)?" ("+marketCapLimitLabel(entries.find(entry=>entry.id===removePending.id)!)+")":""} from the <strong>{stageLabel(removePending.stage)}</strong> restriction list?</p>
        <p>{poolPipelineOnly?"This returns the rule to Pool, retaining its values. No scan starts.":"This only removes the rule from this list. Other list assignments, saved values and original FS/FA associations remain unchanged. No scan is started."}</p>
        {removePending.id==="gem_marketcap" && <p>The separate minimum and maximum Pipeline market-cap restrictions remain if assigned.</p>}
        <div className={styles.removeActions}>
          <button type="button" className={styles.confirmRemoveButton} onClick={confirmRemoveFromList}>CONFIRM REMOVE</button>
          <button type="button" className="secondary" onClick={()=>setRemovePending(null)}>CANCEL</button>
        </div>
      </div>
    </section>}
    {listPopup && <section role="dialog" aria-modal="true" aria-label="Restriction list popup" className={styles.listBackdrop}>
      <div className={styles.listModal}>
        <div className={styles.heading}><div><h2>ADD TO RESTRICTION LIST</h2><p>{poolPipelineOnly?"Choose an independent Pool rule to assign to Pipeline.":"See the existing restrictions and select where this rule goes. The original FS/FA presets are not changed."}</p></div>
          <button type="button" className="secondary" onClick={()=>setListPopup(false)}>CLOSE ×</button></div>
        <div className={styles.controls}>
          <label>Destination list<select aria-label="Destination restriction list" value={listStage}
            onChange={event=>{setListStage(event.target.value as "PIPELINE"|"GEM_JR"|"GEM");setListPosition(0);}}>
            {activeStages.map(stage=><option key={stage} value={stage}>{stageLabel(stage)}</option>)}</select></label>
          <label>Restriction to add<select aria-label="Restriction to add" value={listRuleId}
            onChange={event=>{setListRuleId(event.target.value);setListPosition(0);}}>
            {entries.filter(entry=>!ruleDefinition(entry).warning).map(entry=><option key={entry.id} value={entry.id}>{ruleDefinition(entry).title}{marketCapLimitLabel(entry) ? " ("+marketCapLimitLabel(entry)+")" : ""}</option>)}</select></label>
          <label>Position in list<select aria-label="Restriction list position" value={Math.min(listPosition,positionOptions.length)} onChange={event=>setListPosition(Number(event.target.value))}>
            <option value={0}>#1 — first</option>
            {positionOptions.map((entry,i)=><option key={entry.id} value={i+1}>#{i+2} — after {ruleDefinition(entry).title}{marketCapLimitLabel(entry) ? " ("+marketCapLimitLabel(entry)+")" : ""}</option>)}
          </select></label>
        </div>
        <h3>{stageLabel(listStage)} — CURRENT RESTRICTIONS ({listEntries.length})</h3>
        <div className={styles.listRows} role="region" aria-label="Current restriction list">
          {listEntries.length?<ol>{listEntries.map((entry,i)=><li key={entry.id}>
            <span><strong>#{i+1}</strong> {ruleDefinition(entry).title}</span>
            {marketCapLimitLabel(entry) && <small className={styles.marketCapNumbers}>{marketCapLimitLabel(entry)}</small>}
            <small>{ruleDefinition(entry).associations?.join(" · ")||"Independent"}</small>
            <button type="button" className={styles.listRemoveInline}
              aria-label={"Remove "+ruleDefinition(entry).title+" from "+stageLabel(listStage)+" list"}
              onClick={()=>requestRemoveFromList(entry.id,listStage)}>REMOVE ×</button>
          </li>)}</ol>:<p>No active restrictions in this list yet.</p>}
        </div>
        <div className={styles.listPreview} aria-live="polite">
          <strong>PREVIEW — {stageLabel(listStage)}</strong>
          <span>Before: {currentStage?count(currentStage.remaining):"—"} remaining</span>
          <span>After: {proposedStage?count(proposedStage.remaining):"—"} remaining</span>
          <span>Needs verification: {proposedStage?count(proposedStage.pending):"—"}</span>
        </div>
        {listRuleId==="gem_marketcap"&&<p className={styles.note}>Current market-cap range uses latest saved caps, not historical market caps at Pipeline entry. This is a comparison preview.</p>}
        <div className={styles.buttons}><button type="button" onClick={applyListSelection}>APPLY TO {stageLabel(listStage).toUpperCase()} LIST</button>
          <button type="button" className="secondary" onClick={()=>setListPopup(false)}>CANCEL</button></div>
      </div>
    </section>}
    {scanOpen && <section role="dialog" aria-modal="true" aria-label="Scan results" style={{position:"fixed",inset:0,zIndex:9999,background:"white",color:"black",overflowY:"auto",padding:16}}><button type="button" onClick={()=>setScanOpen(false)}>CLOSE ×</button><h2>FULL SCAN RESULTS</h2><p>Scanned {count(report.total)} · Passed {count(report.passed)} · Excluded {count(report.excluded)} · Needs verification {count(report.pending)}</p><div className={styles.scroll}><table><thead><tr><th>Priority</th><th>Restriction</th><th>New exclusions</th><th>Remaining</th><th>Pending</th></tr></thead><tbody>{entries.filter(e=>report.steps.get(e.id)?.step).sort((a,b)=>(report.steps.get(a.id)?.step||0)-(report.steps.get(b.id)?.step||0)).map(e=>{const step=report.steps.get(e.id)!;return <tr key={e.id}><td>{e.stage==="PIPELINE"?"P":e.stage==="GEM_JR"?"J":"G"}{e.priority}</td><td>{ruleDefinition(e).title}</td><td>{count(step.newlyExcluded)}</td><td>{count(step.remaining)}</td><td>{count(step.pending)}</td></tr>})}</tbody></table></div><h3>REMAINING TRIALS</h3><p>Use the NEW EXCLUSIONS buttons in the restriction table to inspect removed records.</p><div className={styles.scroll}><table><thead><tr><th>Trial</th><th>Ticker</th><th>Drug</th></tr></thead><tbody>{report.rows.filter(row=>![...report.steps.values()].some(step=>step.step && step.newlyExcludedIds.has(row.id))).slice(0,250).map(row=><tr key={row.id}><td>{row.programId||row.id}</td><td>{row.ticker}</td><td>{row.drug||"Unknown"}</td></tr>)}</tbody></table></div><p>Showing first 250 remaining records.</p></section>}
    {!visible.length && <p>No restrictions match this list view.</p>}
    {inspection && selectedEntry && <section className={styles.inspection} aria-label="Affected records"><div className={styles.heading}><h4>{ruleDefinition(selectedEntry).title} — {inspection.kind === "new" ? "new exclusions at this step" : inspection.kind === "alone" ? "excluded by this rule alone" : "needs verification for this rule"} ({count(inspected.length)})</h4><button type="button" className="secondary" onClick={() => setInspection(null)} aria-label="Close affected records">CLOSE ×</button></div>
      <div className={styles.scroll}><table><thead><tr><th>Program / record</th><th>Ticker</th><th>Drug</th><th>Stage</th></tr></thead><tbody>{inspected.slice(currentPage * 25, (currentPage + 1) * 25).map(row => <tr key={row.id}><td>{row.programId || row.id}</td><td>{row.ticker}</td><td>{row.drug || "Not recorded"}</td><td>{row.stage || "Unknown"}</td></tr>)}</tbody></table></div>
      {!inspected.length && <p>No matching records under the current assignments.</p>}
      <div className={styles.buttons}><button type="button" className="secondary" disabled={currentPage === 0} onClick={() => setPage(currentPage - 1)}>PREVIOUS 25</button><span>Page {currentPage + 1} of {pages}</span><button type="button" className="secondary" disabled={currentPage + 1 >= pages} onClick={() => setPage(currentPage + 1)}>NEXT 25</button></div></section>}
    <details className={styles.extra}><summary>Data dates and advanced options</summary><p className={styles.note}>Trial universe as of {asOf}. Evidence {evidence ? "fetched " + new Date(evidence.fetchedAt).toLocaleString() : loading ? "loading…" : "unavailable"}. Saved cap dates: {capDates.length ? capDates.join(", ") : "not available"}. Published evidence refreshes every five minutes while visible.</p><button type="button" className="secondary" onClick={() => { setEntries(defaultCatalogEntries()); setSettings(defaultRestrictionSettings()); setInspection(null); setPage(0); }}>RESET TO APPROVED RULES</button></details>
    {evidence && <details className={styles.sources}><summary>Data sources ({evidence.sources.length})</summary><ul>{evidence.sources.map(source => <li key={source.name}><a href={source.url} target="_blank" rel="noopener noreferrer">{source.name}</a> · {count(source.rows)} saved rows</li>)}</ul></details>}
  </section>;
}
