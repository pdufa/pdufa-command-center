export type FieldState = "OBSERVED" | "CALCULATED" | "MODELED" | "STALE" | "REVIEW" | "CONFLICTING" | "MISSING";
export type EnrichmentField = { id: string; label: string; group: string; kind: "retrieved" | "calculated" | "modeled"; scope: "company" | "program"; source: string; rule: string; maxAgeDays: number };
export type EnrichmentIndex = {
  schemaVersion: 1; generatedAt: string; asOf: string; status: string; fields: EnrichmentField[]; companyCount: number;
  lists: Record<"PIPELINE" | "GEM_JR" | "GEM", { records: number; fields: Record<string, Record<FieldState, number>> }>;
  financialCollection?: {status?: string; attempted?: number; collected?: number; remaining?: number};
  marketCollection?: {status?: string; configuration?: string; attempted?: number; collected?: number; remaining?: number; feed?: string};
};
type Cell = [unknown, FieldState, number, string, string, string];
export type EnrichmentShard = { schemaVersion: 1; ticker: string; generatedAt: string; asOf: string; sources: string[];
  company: Record<string, Cell>; records: Record<string, { ticker: string; fields: Record<string, Cell> }> };
export type FieldDetail = EnrichmentField & {value: unknown; status: FieldState; sourceUrl: string; observedAt: string; retrievedAt: string; note: string};
export type EnrichmentDetail = {ticker: string; exactKey: string | null; generatedAt: string; asOf: string; evaluatedOn: string; fields: FieldDetail[]};
const STATES: FieldState[] = ["OBSERVED", "CALCULATED", "MODELED", "STALE", "REVIEW", "CONFLICTING", "MISSING"];
const READY = new Set(["OBSERVED", "CALCULATED", "MODELED"]);
export const enrichmentTicker = (value: string) => /^[A-Z0-9][A-Z0-9.-]{0,14}$/.test(value.trim().toUpperCase()) ? value.trim().toUpperCase() : "";
export const enrichmentKey = (value: string) => value.length <= 240 && /^(TRIAL|APPLICATION|RESULT)\|[^\x00-\x1f]+$/.test(value) ? value : "";
export function pacificToday() {
  return new Intl.DateTimeFormat("en-CA", {timeZone: "America/Los_Angeles", year: "numeric", month: "2-digit", day: "2-digit"}).format(new Date());
}
function validDay(value: string) {
  return /^\d{4}-\d{2}-\d{2}$/.test(value) && Number.isFinite(Date.parse(value)) && new Date(value).toISOString().slice(0, 10) === value;
}
function age(value: string, today: string) {
  const day = value.slice(0, 10);
  return validDay(day) && validDay(today) ? (Date.parse(today)-Date.parse(day))/86400000 : null;
}
export function validateEnrichmentIndex(value: unknown): EnrichmentIndex {
  const d = value as EnrichmentIndex;
  if (!d || d.schemaVersion !== 1 || !validDay(d.asOf) || !Number.isFinite(Date.parse(d.generatedAt)) || !Array.isArray(d.fields) || d.fields.length !== 50 || new Set(d.fields.map(f => f.id)).size !== 50) throw new Error("Invalid shared field catalog");
  for (const field of d.fields) {
    if (!/^[a-z][a-z0-9_]*$/.test(field.id) || !field.label || !field.source || !["company", "program"].includes(field.scope) || !Number.isInteger(field.maxAgeDays) || field.maxAgeDays < 1) throw new Error("Invalid shared field definition");
  }
  for (const [kind, count] of [["retrieved", 35], ["calculated", 10], ["modeled", 5]] as const) {
    if (d.fields.filter(f => f.kind === kind).length !== count) throw new Error("Field totals do not reconcile");
  }
  for (const stage of ["PIPELINE", "GEM_JR", "GEM"] as const) {
    const list = d.lists?.[stage];
    if (!list || !Number.isInteger(list.records) || list.records < 0) throw new Error("Invalid enrichment list count");
    for (const field of d.fields) {
      const counts = list.fields[field.id];
      if (!counts || STATES.some(s => !Number.isInteger(counts[s]) || counts[s] < 0) || STATES.reduce((n, s) => n+counts[s], 0) !== list.records) throw new Error("Coverage does not reconcile");
    }
  }
  return d;
}
export function enrichmentDetail(index: EnrichmentIndex, shard: EnrichmentShard, ticker: string, key = "", today = pacificToday()): EnrichmentDetail {
  if (!shard || shard.schemaVersion !== 1 || shard.ticker !== ticker || shard.generatedAt !== index.generatedAt || !Array.isArray(shard.sources) || !shard.company || !shard.records) throw new Error("Shared data publication mismatch");
  const record = key ? shard.records[key] : undefined;
  if (key && (!record || record.ticker !== ticker)) throw new Error("Exact program was not found for this company");
  const fields = index.fields.map(field => {
    const cell = (field.scope === "company" ? shard.company : record?.fields)?.[field.id];
    const result: FieldDetail = {...field, value: null, status: "MISSING", sourceUrl: "", observedAt: "", retrievedAt: "", note: key ? "No sourced observation is saved for this field." : field.scope === "program" ? "Open an exact trial or application to inspect this field." : "No sourced company observation is saved."};
    if (!cell) return result;
    if (!Array.isArray(cell) || cell.length !== 6 || !STATES.includes(cell[1]) || !Number.isInteger(cell[2]) || typeof cell[3] !== "string" || typeof cell[4] !== "string" || typeof cell[5] !== "string") throw new Error("Invalid field observation");
    const source = shard.sources[cell[2]];
    if (typeof source !== "string") throw new Error("Field source is missing");
    result.value = cell[0]; result.status = cell[1]; result.observedAt = cell[3]; result.retrievedAt = cell[4]; result.note = cell[5];
    try { const u = new URL(source); if (u.protocol === "https:" && !u.username && !u.password) result.sourceUrl = source; } catch { /* An unsourced saved value remains review-only. */ }
    const checkedAge = age(cell[4], today), observedAge = cell[3] ? age(cell[3], today) : 0;
    if (READY.has(result.status)) {
      if (!result.sourceUrl || checkedAge === null || checkedAge < 0 || observedAge !== null && observedAge < 0) result.status = "REVIEW";
      else if (checkedAge > field.maxAgeDays) result.status = "STALE";
    }
    return result;
  });
  // Date distances are evaluated for today even if the saved publication is older.
  for (const [id, input] of [["days_to_pdufa", "pdufa_date"], ["days_to_completion", "primary_completion"]]) {
    const out = fields.find(f => f.id === id), target = fields.find(f => f.id === input);
    if (out && target && typeof target.value === "string" && validDay(target.value)) out.value = -age(target.value, today)!;
  }
  const completeness = fields.find(f => f.id === "evidence_completeness");
  if (completeness) {
    const inputs = fields.filter(f => f.kind !== "modeled" && f.id !== completeness.id);
    completeness.value = inputs.filter(f => READY.has(f.status)).length / inputs.length * 100;
    completeness.status = "CALCULATED";
    completeness.note = "Recomputed for the evaluation date from available non-modeled inputs. This is availability, not a scientific quality score.";
  }
  return {ticker, exactKey: key || null, generatedAt: index.generatedAt, asOf: index.asOf, evaluatedOn: today, fields};
}
export function availableCount(counts: Record<FieldState, number>) {
  return counts.OBSERVED+counts.CALCULATED+counts.MODELED;
}
