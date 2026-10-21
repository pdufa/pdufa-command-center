import { availableGemRestrictionOptions, checkboxGroupsForStage, gemPresetAssociations } from "../app/GemQualificationChecklist";
import type { Candidate } from "../app/Workspace";
import { RESTRICTIONS, restrictionVerdict, type ImpactRecord,
  type RestrictionEvidence, type RestrictionSettings, type Verdict } from "./restriction-impact";

export type RestrictionStage = "" | "PIPELINE" | "GEM_JR" | "GEM";
export const RESTRICTION_STAGES: Exclude<RestrictionStage, "">[] = ["PIPELINE", "GEM_JR", "GEM"];
export type CustomField = "note" | "marketCapMillions" | "runwayMonths" | "pdufaDays" | "rvol" | "rsi14" | "avgDollarVolume20" | "close";
export type CatalogEntry = { id: string; enabled: boolean; priority?: string; stage: RestrictionStage; additionalStages?: Exclude<RestrictionStage, "">[]; stagePriorities?: Partial<Record<Exclude<RestrictionStage, "">, string>>; value: string; maximum: string;
  title?: string; field?: CustomField; operator?: ">=" | "<=" };
export type CatalogDefinition = { id: string; title: string; help: string; category: string; value?: string;
  maximum?: string; unit?: string; warning?: boolean; numeric?: boolean; associations?: string[] };
const groups = checkboxGroupsForStage("GEM_JR");
const gemChecks = [...groups.clinical, ...groups.trading];
const gemById = new Map(gemChecks.map(check => ["gem_" + check[0], check]));
const coreValues: Record<string, Pick<CatalogDefinition, "value" | "unit" | "numeric">> = {
  minCap: { value: "300", unit: "$ millions", numeric: true }, maxCap: { value: "10000", unit: "$ millions", numeric: true },
  phase: { value: "3", unit: "minimum phase", numeric: true }, runway: { value: "12", unit: "months", numeric: true },
  pdufaWindow: { value: "730", unit: "days", numeric: true },
};
const gemValues: Record<string, Partial<CatalogDefinition>> = {
  cash: { title: "SEC cash runway", value: "12", unit: "minimum months", numeric: true },
  marketcap: { title: "Current market-cap range", value: "300", maximum: "10000", unit: "$ millions, minimum / maximum", numeric: true },
  window: { title: "PDUFA timing window", value: "30", maximum: "90", unit: "days, minimum / maximum", numeric: true },
  volume: { title: "Relative volume", value: "1.5", unit: "minimum relative volume", numeric: true },
  rsi: { title: "RSI range", value: "45", maximum: "65", unit: "RSI minimum / maximum", numeric: true },
  liquidity: { title: "20-day average dollar volume", value: "5000000", unit: "minimum USD / day", numeric: true },
};
export const RESTRICTION_CATALOG: CatalogDefinition[] = [
  ...RESTRICTIONS.map(rule => ({ ...rule, category: rule.proposed ? "Proposed Pipeline addition" : "Approved Pipeline rule", associations: rule.id==="runway"?gemPresetAssociations("cash"):[], ...coreValues[rule.id] })),
  ...gemChecks.filter(([key])=>key!=="cash").map(([key, title]) => ({ id: "gem_" + key, title, category: "Existing GEM JR / GEM option",
    help: "Uses the existing stage-checklist evidence for the exact program. Select a stage and enter a priority number to include it in this page’s live screen.", associations: gemPresetAssociations(key), ...gemValues[key] })),
  ...availableGemRestrictionOptions().map(rule => ({ id: "alert_" + rule.key, title: rule.title,
    category: "Optional clinical / regulatory goal", value: rule.goal, unit: rule.unit,
    numeric: !!rule.number, help: "This is the same optional goal available in the GEM JR checklist. A goal is not evidence; this check stays unknown until source-verified facts are linked." })),
  { id: "gem_jr_source", title: "GEM JR screening passed", category: "GEM input option", associations: gemPresetAssociations("gem_jr_source"),
    help: "Uses the results of the assigned GEM JR rules on this page. With no enabled GEM JR rules, qualification is unknown. Saved GEM JR membership alone is not proof of passing a screen." },
];

/**
 * Display-only importance order. This classification NEVER changes FS/FA preset
 * membership, scan priority, user thresholds, stage assignments or persisted IDs.
 */
export const RESTRICTION_PURPOSE_GROUPS = [
  { id: "MARKET_CAP", title: "1. MARKET CAPITALIZATION", note: "Entry and current company market-cap limits" },
  { id: "CLINICAL_RESULTS", title: "2. CLINICAL TRIAL RESULTS & SUCCESS", note: "Phase 3 outcomes, pivotal evidence, statistical strength and safety" },
  { id: "FDA", title: "3. FDA & REGULATORY STATUS", note: "FDA pathway, designations, reviews, advisory meetings and holds" },
  { id: "COMPANY", title: "4. COMPANY ELIGIBILITY", note: "Public listing, identifiable company, drug and indication" },
  { id: "FINANCIAL", title: "5. FINANCIAL STRENGTH & CASH RUNWAY", note: "Financing, dilution and available cash runway" },
  { id: "DEVELOPMENT", title: "6. TRIAL PHASE & DEVELOPMENT PROGRESS", note: "Trial phase, registry status, program activity and GEM JR inputs" },
  { id: "PDUFA", title: "7. PDUFA DATES & CATALYSTS", note: "Decision timing, upcoming events and verified PDUFA dates" },
  { id: "EVIDENCE", title: "8. EVIDENCE QUALITY & VERIFICATION", note: "Issuer sources, SEC reconciliation and data freshness" },
  { id: "TRADING", title: "9. TRADING ACTIVITY & LIQUIDITY", note: "Relative volume, dollar liquidity and insider/institutional activity" },
  { id: "TECHNICAL", title: "10. TECHNICAL INDICATORS & PRICE TRENDS", note: "RSI, moving averages and closing prices" },
  { id: "OTHER", title: "11. OTHER / OPTIONAL RESTRICTIONS", note: "Commercial market opportunities and uncategorized custom checks" },
] as const;
export type RestrictionPurposeGroupId = typeof RESTRICTION_PURPOSE_GROUPS[number]["id"];
const RESTRICTION_PURPOSE_BY_ID: Record<string, RestrictionPurposeGroupId> = {
  minCap: "MARKET_CAP", maxCap: "MARKET_CAP", gem_marketcap: "MARKET_CAP",
  gem_phase3: "CLINICAL_RESULTS", alert_statistical_significance: "CLINICAL_RESULTS",
  alert_two_trial: "CLINICAL_RESULTS", alert_safety_cleanliness: "CLINICAL_RESULTS",
  fdaPath: "FDA", hold: "FDA", alert_priority_review: "FDA",
  alert_fast_track: "FDA", alert_accelerated_approval: "FDA",
  alert_breakthrough_rmat: "FDA", alert_star_pilot: "FDA",
  alert_no_adcom: "FDA", alert_favorable_adcom: "FDA", alert_orphan_unmet: "FDA",
  public: "COMPANY", identity: "COMPANY",
  runway: "FINANCIAL", gem_financing: "FINANCIAL", gem_dilution: "FINANCIAL",
  phase: "DEVELOPMENT", active: "DEVELOPMENT", gem_registry: "DEVELOPMENT", gem_jr_source: "DEVELOPMENT",
  progress: "PDUFA", pdufaWindow: "PDUFA", gem_pdufa: "PDUFA", gem_window: "PDUFA",
  documents: "EVIDENCE", gem_issuer: "EVIDENCE", gem_marketfresh: "EVIDENCE", gem_sec: "EVIDENCE",
  gem_volume: "TRADING", gem_liquidity: "TRADING", gem_insiders: "TRADING", gem_institutions: "TRADING",
  gem_rsi: "TECHNICAL", gem_trend: "TECHNICAL",
  alert_tam: "OTHER",
};
export function restrictionPurposeGroup(entry: Pick<CatalogEntry, "id" | "field">): RestrictionPurposeGroupId {
  if (entry.id.startsWith("custom_")) {
    const byField: Partial<Record<CustomField, RestrictionPurposeGroupId>> = {
      marketCapMillions: "MARKET_CAP", runwayMonths: "FINANCIAL", pdufaDays: "PDUFA",
      rvol: "TRADING", avgDollarVolume20: "TRADING", rsi14: "TECHNICAL", close: "TECHNICAL",
    };
    return entry.field ? byField[entry.field] || "OTHER" : "OTHER";
  }
  return RESTRICTION_PURPOSE_BY_ID[entry.id] || "OTHER";
}

export function catalogStages(entry:CatalogEntry):Exclude<RestrictionStage,"">[] {
  return [...new Set([entry.stage, ...(entry.additionalStages||[])].filter((value):value is Exclude<RestrictionStage,"">=>RESTRICTION_STAGES.includes(value as Exclude<RestrictionStage,"">)))];
}
/** Per-list priority keeps other stages intact when adding/reordering one list. */
export function catalogStagePriority(entry: CatalogEntry, stage: Exclude<RestrictionStage, "">): string {
  if(!catalogStages(entry).includes(stage))return "";
  return Object.prototype.hasOwnProperty.call(entry.stagePriorities || {}, stage)
    ? (entry.stagePriorities?.[stage] || "") : (entry.priority || "");
}
export function selectedRestrictionList(entries: CatalogEntry[], stage: Exclude<RestrictionStage, "">): CatalogEntry[] {
  return entries.filter(entry => catalogStages(entry).includes(stage) && entry.enabled &&
    !!catalogStagePriority(entry,stage) && !catalogDefinition(entry).warning)
    .sort((a,b)=>Number(catalogStagePriority(a,stage))-Number(catalogStagePriority(b,stage)));
}
/** Insert or move a single master rule; never changes static FS/FA associations. */
export function insertRestrictionIntoList(entries: CatalogEntry[], id: string, stage: Exclude<RestrictionStage, "">, index: number): CatalogEntry[] {
  const picked = entries.find(entry=>entry.id===id);
  if(!picked || catalogDefinition(picked).warning || !RESTRICTION_STAGES.includes(stage))return entries;
  const priorList=selectedRestrictionList(entries,stage).filter(entry=>entry.id!==id);
  const at=Number.isFinite(index)?Math.max(0,Math.min(priorList.length,Math.trunc(index))):0;
  const ordered=[...priorList.slice(0,at),picked,...priorList.slice(at)];
  const ranks=new Map(ordered.map((entry,i)=>[entry.id,String(i+1)]));
  return entries.map(entry=>{
    const rank=ranks.get(entry.id);
    if(!rank)return entry;
    if(entry.id!==id)return {...entry,stagePriorities:{...entry.stagePriorities,[stage]:rank}};
    const otherStages=catalogStages(entry).filter(value=>value!==stage);
    const savedOther=Object.fromEntries(otherStages.map(value=>[value,catalogStagePriority(entry,value)]));
    return {...entry,stage,additionalStages:otherStages,enabled:true,priority:entry.priority||"1",
      stagePriorities:{...savedOther,...entry.stagePriorities,[stage]:rank}};
  });
}
/** Remove a rule from one list only; keep its values, other memberships and FS/FA presets. */
export function removeRestrictionFromList(entries: CatalogEntry[], id: string, stage: Exclude<RestrictionStage, "">): CatalogEntry[] {
  if (!RESTRICTION_STAGES.includes(stage)) return entries;
  const current=selectedRestrictionList(entries,stage);
  if (!current.some(entry=>entry.id===id)) return entries;
  const ranks=new Map(current.filter(entry=>entry.id!==id).map((entry,i)=>[entry.id,String(i+1)]));
  return entries.map(entry=>{
    if (entry.id!==id) {
      const rank=ranks.get(entry.id);
      return rank ? {...entry,stagePriorities:{...entry.stagePriorities,[stage]:rank}} : entry;
    }
    const retained=catalogStages(entry).filter(other=>other!==stage);
    const primary=entry.stage===stage ? (retained[0]||"") : entry.stage;
    const otherRanks=Object.fromEntries(retained.map(other=>[other,catalogStagePriority(entry,other)]));
    return {...entry,stage:primary,additionalStages:retained.filter(other=>other!==primary),
      enabled:entry.enabled && retained.length>0,
      priority:primary ? catalogStagePriority(entry,primary) : "",
      stagePriorities:{...entry.stagePriorities,...otherRanks,[stage]:""}};
  });
}
export function defaultCatalogEntries(): CatalogEntry[] {
  // Four mandatory Pipeline eligibility criteria (market cap uses two existing bounds).
  // Unverified evidence stays UNKNOWN, never automatically excluded.
  const ranks: Record<string,string> = { minCap:"1", maxCap:"1", public:"2", phase:"3", fdaPath:"4" };
  return RESTRICTION_CATALOG.map(rule => ({
    id: rule.id, enabled: Object.hasOwn(ranks,rule.id),
    stage: Object.hasOwn(ranks,rule.id) ? "PIPELINE" : "",
    additionalStages: [], priority: ranks[rule.id] || "",
    stagePriorities: Object.hasOwn(ranks,rule.id) ? { PIPELINE:ranks[rule.id] } : {},
    value: rule.value || "", maximum: rule.maximum || ""
  }));
}
/** Display saved Market Cap thresholds as dollar values; never infer missing data. */
export function marketCapLimitLabel(entry: Pick<CatalogEntry, "id" | "value" | "maximum">): string | null {
  if (!["gem_marketcap","minCap","maxCap"].includes(entry.id)) return null;
  const amount = (raw:string) => {
    if (!raw?.trim()) return "not set";
    const value = Number(raw);
    if (!Number.isFinite(value) || value < 0) return "not set";
    const denomination = value >= 1000 ? "B" : "M";
    const number = value >= 1000 ? value / 1000 : value;
    return "$" + number.toLocaleString("en-US",{maximumFractionDigits:6}) + denomination;
  };
  if (entry.id === "gem_marketcap") return amount(entry.value) + " – " + amount(entry.maximum);
  return (entry.id === "minCap" ? "Min " : "Max ") + amount(entry.value);
}
export function catalogDefinition(entry: CatalogEntry): CatalogDefinition {
  return RESTRICTION_CATALOG.find(rule => rule.id === entry.id) || { id: entry.id,
    title: entry.title || "Custom restriction", category: "Custom restriction", value: entry.value,
    unit: entry.field === "note" ? "Description only · evidence needs verification" : entry.field,
    numeric: entry.field !== "note", help: "Description-only restrictions remain unknown. A numeric field, comparison and target use saved evidence; missing values need verification." };
}
function numeric(value: string) { const n = Number(value); return value.trim() && Number.isFinite(n) && n >= 0 ? n : null; }
function verdict(value: boolean | null): Verdict { return value === null ? "UNKNOWN" : value ? "PASS" : "FAIL"; }
function days(row: ImpactRecord, asOf: string) {
  const target = row.pdufaDate?.slice(0, 10), today = asOf.slice(0, 10);
  if (!target || !/^\d{4}-\d{2}-\d{2}$/.test(target) || !Number.isFinite(Date.parse(target)) || !Number.isFinite(Date.parse(today)) || new Date(target).toISOString().slice(0, 10) !== target) return null;
  return Math.round((Date.parse(target) - Date.parse(today)) / 86400000);
}
export function catalogVerdict(entry: CatalogEntry, row: ImpactRecord, settings: RestrictionSettings,
    evidence: RestrictionEvidence | null, asOf: string, junior?: Map<string, Verdict>): Verdict {
  const core = RESTRICTIONS.find(rule => rule.id === entry.id), value = numeric(entry.value), maximum = numeric(entry.maximum);
  if (core) {
    const keys: Partial<Record<string, "minCapMillions" | "maxCapMillions" | "minimumPhase" | "minRunwayMonths" | "maxPdufaDays">> = {
      minCap: "minCapMillions", maxCap: "maxCapMillions", phase: "minimumPhase", runway: "minRunwayMonths", pdufaWindow: "maxPdufaDays" };
    const key = keys[core.id];
    // A single runway rule serves both the Pipeline trial source and GEM's
    // SEC-backed technical runway: retain whichever verified field exists.
    if(core.id==="runway"){
      const months=(row as Candidate).technical?.runwayMonths ?? row.trialFilters?.runwayMonths;
      return value===null || months==null || !Number.isFinite(months) ? "UNKNOWN" : verdict(months>=value);
    }
    if (key) {
      if (value === null) return "UNKNOWN";
      const next = { ...settings }; next[key] = value;
      return restrictionVerdict(core.id, row, next, evidence, asOf);
    }
    return restrictionVerdict(core.id, row, settings, evidence, asOf);
  }
  if (entry.id === "gem_jr_source") return junior?.get(row.id) || "UNKNOWN";
  if (entry.id.startsWith("alert_")) return "UNKNOWN";
  const candidate = row as Candidate, technical = candidate.technical;
  if (gemById.has(entry.id)) {
    const key = entry.id.slice(4);
    if (key === "marketcap") {
      const cap = evidence?.issuers[row.ticker.toUpperCase()]?.marketCap;
      return cap == null || value === null || maximum === null ? "UNKNOWN" : verdict(cap >= value * 1e6 && cap <= maximum * 1e6);
    }
    if (key === "window") { const n = days(row, asOf); return n === null || value === null || maximum === null ? "UNKNOWN" : verdict(n >= value && n <= maximum); }
    if (["cash", "volume", "rsi", "liquidity"].includes(key)) {
      const n = key === "cash" ? technical?.runwayMonths ?? row.trialFilters?.runwayMonths : key === "volume" ? technical?.rvol : key === "rsi" ? technical?.rsi14 : technical?.avgDollarVolume20;
      return n == null || !Number.isFinite(n) || value === null || key === "rsi" && maximum === null ? "UNKNOWN" : verdict(n >= value && (key !== "rsi" || n <= maximum!));
    }
    return verdict(gemById.get(entry.id)![2](candidate));
  }
  if (!entry.id.startsWith("custom_") || entry.field === "note" || !entry.field || value === null) return "UNKNOWN";
  const n = entry.field === "marketCapMillions" ? (evidence?.issuers[row.ticker.toUpperCase()]?.marketCap ?? NaN) / 1e6
    : entry.field === "runwayMonths" ? technical?.runwayMonths ?? row.trialFilters?.runwayMonths
    : entry.field === "pdufaDays" ? days(row, asOf) : technical?.[entry.field];
  return n == null || !Number.isFinite(n) ? "UNKNOWN" : verdict(entry.operator === "<=" ? n <= value : n >= value);
}
export type CatalogStep = { id: string; stage: RestrictionStage; alonePass: number; aloneFail: number; aloneUnknown: number;
  step: number | null; before: number; newlyExcluded: number; remaining: number; passed: number; pending: number; newlyExcludedIds: Set<string> };
export function calculateCatalogImpact(input: ImpactRecord[], entries: CatalogEntry[], settings: RestrictionSettings,
    evidence: RestrictionEvidence | null, asOf: string) {
  const rows = [...new Map(input.map(row => [row.id, row])).values()];
  const states = new Map<string, Verdict>(rows.map(row => [row.id, "PASS"]));
  const stages: { stage: Exclude<RestrictionStage, "">; before: number; remaining: number; passed: number; pending: number; excluded: number }[] = [];
  const steps = new Map<string, CatalogStep>();
  let junior: Map<string, Verdict> | undefined, stepNumber = 0;
  const summary = () => { const values = [...states.values()]; return { remaining: values.filter(v => v !== "FAIL").length,
    passed: values.filter(v => v === "PASS").length, pending: values.filter(v => v === "UNKNOWN").length }; };
  const alone = (entry: CatalogEntry) => {
    const values = rows.map(row => catalogVerdict(entry, row, settings, evidence, asOf, junior));
    return { values, alonePass: values.filter(v => v === "PASS").length, aloneFail: values.filter(v => v === "FAIL").length, aloneUnknown: values.filter(v => v === "UNKNOWN").length };
  };
  for (const stage of RESTRICTION_STAGES) {
    const beforeStage = summary().remaining;
    for (const entry of entries.filter(item => catalogStages(item).includes(stage)).sort((a,b) => Number(catalogStagePriority(a,stage) || 0) - Number(catalogStagePriority(b,stage) || 0))) {
      const a = alone(entry), before = summary().remaining, newlyExcludedIds = new Set<string>();
      const rank=catalogStagePriority(entry,stage);
      const used = entry.enabled && !!rank && Number(rank) > 0 && !catalogDefinition(entry).warning;
      if (used) for (let i = 0; i < rows.length; i++) {
        const id = rows[i].id, prior = states.get(id)!;
        if (prior === "FAIL") continue;
        if (a.values[i] === "FAIL") { states.set(id, "FAIL"); newlyExcludedIds.add(id); }
        else if (a.values[i] === "UNKNOWN") states.set(id, "UNKNOWN");
      }
      steps.set(stage === entry.stage ? entry.id : stage + "|" + entry.id, { id: entry.id, stage, alonePass: a.alonePass, aloneFail: a.aloneFail, aloneUnknown: a.aloneUnknown,
        step: used ? ++stepNumber : null, before, newlyExcluded: newlyExcludedIds.size, ...summary(), newlyExcludedIds });
    }
    const s = summary(); stages.push({ stage, before: beforeStage, ...s, excluded: beforeStage - s.remaining });
    if (stage === "GEM_JR" && entries.some(e => catalogStages(e).includes(stage) && e.enabled && !!catalogStagePriority(e,stage) && !catalogDefinition(e).warning)) junior = new Map(states);
  }
  for (const entry of entries.filter(item => catalogStages(item).length === 0)) {
    const a = alone(entry); steps.set(entry.id, { id: entry.id, stage: "", alonePass: a.alonePass, aloneFail: a.aloneFail, aloneUnknown: a.aloneUnknown,
      step: null, before: rows.length, newlyExcluded: 0, remaining: rows.length, passed: rows.length, pending: 0, newlyExcludedIds: new Set() });
  }
  const final = summary();
  return { rows, total: rows.length, stages, steps, ...final, excluded: rows.length - final.remaining, junior };
}
export function restoreCatalogEntries(raw: unknown): CatalogEntry[] {
  const defaults = defaultCatalogEntries();
  if (!Array.isArray(raw)) return defaults;
  const stages = new Set(["", ...RESTRICTION_STAGES]), fields = new Set(["note", "marketCapMillions", "runwayMonths", "pdufaDays", "rvol", "rsi14", "avgDollarVolume20", "close"]);
  const clean = (entry: unknown): CatalogEntry | null => {
    if (!entry || typeof entry !== "object") return null;
    const e = entry as CatalogEntry;
    if (typeof e.id !== "string" || !stages.has(e.stage) || typeof e.enabled !== "boolean" || typeof e.value !== "string" || typeof e.maximum !== "string") return null;
    if (e.id.startsWith("custom_") && (typeof e.title !== "string" || !e.title.trim() || !fields.has(e.field || ""))) return null;
    return { id: e.id.slice(0, 100), enabled: e.enabled && (!!e.priority || Object.values(e.stagePriorities || {}).some(Boolean)), priority: typeof e.priority === "string" && /^[1-9]\d{0,3}$/.test(e.priority) ? e.priority : "", stage: e.stage, additionalStages: Array.isArray(e.additionalStages) ? [...new Set(e.additionalStages.filter(stage => stage !== e.stage && RESTRICTION_STAGES.includes(stage)))].slice(0, 2) : [], stagePriorities:Object.fromEntries(RESTRICTION_STAGES.flatMap(stage=>{
      const value=e.stagePriorities?.[stage];
      return typeof value==="string" && (value==="" || /^[1-9]\d{0,3}$/.test(value)) ? [[stage,value]] : [];
    })) as Partial<Record<Exclude<RestrictionStage, "">, string>>,
    value: e.value.slice(0, 400), maximum: e.maximum.slice(0, 400),
      ...(e.id.startsWith("custom_") ? { title: e.title!.slice(0, 400), field: e.field, operator: e.operator === "<=" ? "<=" : ">=" } : {}) };
  };
  const saved = new Map(raw.slice(0, 140).map(clean).filter((entry): entry is CatalogEntry => !!entry).map(entry => [entry.id, entry]));
  const legacyCash=saved.get("gem_cash"),canonicalCash=saved.get("runway");
  if(legacyCash && (!canonicalCash || !canonicalCash.priority && !!legacyCash.priority)){
    const stages=[...new Set([...catalogStages(canonicalCash||defaults.find(entry=>entry.id==="runway")!),...catalogStages(legacyCash)])];
    const primary=(canonicalCash?.stage||legacyCash.stage||stages[0]||"") as RestrictionStage;
    saved.set("runway",{...(canonicalCash||defaults.find(entry=>entry.id==="runway")!),stage:primary,
      additionalStages:stages.filter(stage=>stage!==primary),enabled:legacyCash.enabled,
      priority:legacyCash.priority||canonicalCash?.priority||"",value:legacyCash.value||canonicalCash?.value||"12"});
  }
  return [...defaults.map(entry => saved.get(entry.id) || entry), ...[...saved.values()].filter(entry => entry.id.startsWith("custom_")).slice(0, 100)];
}

