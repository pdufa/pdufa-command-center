import { availableGemRestrictionOptions, checkboxGroupsForStage } from "../app/GemQualificationChecklist";
import type { Candidate } from "../app/Workspace";
import { RESTRICTIONS, restrictionVerdict, type ImpactRecord,
  type RestrictionEvidence, type RestrictionSettings, type Verdict } from "./restriction-impact";

export type RestrictionStage = "" | "PIPELINE" | "GEM_JR" | "GEM";
export const RESTRICTION_STAGES: Exclude<RestrictionStage, "">[] = ["PIPELINE", "GEM_JR", "GEM"];
export type CustomField = "note" | "marketCapMillions" | "runwayMonths" | "pdufaDays" | "rvol" | "rsi14" | "avgDollarVolume20" | "close";
export type CatalogEntry = { id: string; enabled: boolean; stage: RestrictionStage; value: string; maximum: string;
  title?: string; field?: CustomField; operator?: ">=" | "<=" };
export type CatalogDefinition = { id: string; title: string; help: string; category: string; value?: string;
  maximum?: string; unit?: string; warning?: boolean; numeric?: boolean };
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
  ...RESTRICTIONS.map(rule => ({ ...rule, category: rule.proposed ? "Proposed Pipeline addition" : "Approved Pipeline rule", ...coreValues[rule.id] })),
  ...gemChecks.map(([key, title]) => ({ id: "gem_" + key, title, category: "Existing GEM JR / GEM option",
    help: "Uses the existing stage-checklist evidence for the exact program. Choose a stage and check Use to include it in this page’s live screen.", ...gemValues[key] })),
  ...availableGemRestrictionOptions().map(rule => ({ id: "alert_" + rule.key, title: rule.title,
    category: "Optional clinical / regulatory goal", value: rule.goal, unit: rule.unit,
    numeric: !!rule.number, help: "This is the same optional goal available in the GEM JR checklist. A goal is not evidence; this check stays unknown until source-verified facts are linked." })),
  { id: "gem_jr_source", title: "GEM JR screening passed", category: "GEM input option",
    help: "Uses the results of the assigned GEM JR rules on this page. With no enabled GEM JR rules, qualification is unknown. Saved GEM JR membership alone is not proof of passing a screen." },
];
export function defaultCatalogEntries(): CatalogEntry[] {
  return RESTRICTION_CATALOG.map(rule => ({ id: rule.id, enabled: rule.category === "Approved Pipeline rule",
    stage: rule.category === "Approved Pipeline rule" ? "PIPELINE" : "", value: rule.value || "", maximum: rule.maximum || "" }));
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
    for (const entry of entries.filter(item => item.stage === stage)) {
      const a = alone(entry), before = summary().remaining, newlyExcludedIds = new Set<string>();
      const used = entry.enabled && !catalogDefinition(entry).warning;
      if (used) for (let i = 0; i < rows.length; i++) {
        const id = rows[i].id, prior = states.get(id)!;
        if (prior === "FAIL") continue;
        if (a.values[i] === "FAIL") { states.set(id, "FAIL"); newlyExcludedIds.add(id); }
        else if (a.values[i] === "UNKNOWN") states.set(id, "UNKNOWN");
      }
      steps.set(entry.id, { id: entry.id, stage, alonePass: a.alonePass, aloneFail: a.aloneFail, aloneUnknown: a.aloneUnknown,
        step: used ? ++stepNumber : null, before, newlyExcluded: newlyExcludedIds.size, ...summary(), newlyExcludedIds });
    }
    const s = summary(); stages.push({ stage, before: beforeStage, ...s, excluded: beforeStage - s.remaining });
    if (stage === "GEM_JR" && entries.some(e => e.stage === stage && e.enabled && !catalogDefinition(e).warning)) junior = new Map(states);
  }
  for (const entry of entries.filter(item => item.stage === "")) {
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
    return { id: e.id.slice(0, 100), enabled: e.enabled, stage: e.stage, value: e.value.slice(0, 400), maximum: e.maximum.slice(0, 400),
      ...(e.id.startsWith("custom_") ? { title: e.title!.slice(0, 400), field: e.field, operator: e.operator === "<=" ? "<=" : ">=" } : {}) };
  };
  const saved = new Map(raw.slice(0, 140).map(clean).filter((entry): entry is CatalogEntry => !!entry).map(entry => [entry.id, entry]));
  return [...defaults.map(entry => saved.get(entry.id) || entry), ...[...saved.values()].filter(entry => entry.id.startsWith("custom_")).slice(0, 100)];
}
