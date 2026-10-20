import type { TrialFilterFacts } from "./trial-filters";

export type Verdict = "PASS" | "FAIL" | "UNKNOWN";
export type RestrictionId = "public" | "minCap" | "maxCap" | "progress" | "fdaPath" | "phase" | "active" | "identity" | "documents" | "runway" | "pdufaWindow" | "hold";
export type ImpactRecord = {
  id: string; programId?: string; ticker: string; company?: string; drug?: string;
  indication?: string; nctId?: string; stage?: string; pdufaDate?: string;
  phase3Source?: string; fdaSource?: string; trialFilters?: TrialFilterFacts;
};
export type IssuerEvidence = { listed: Verdict; marketCap: number | null; capAsOf: string };
export type RestrictionEvidence = {
  fetchedAt: string; issuers: Record<string, IssuerEvidence>;
  trialTypes: Record<string, string[]>; issues: string[];
  sources: { name: string; url: string; rows: number }[];
};
export type RestrictionSettings = {
  enabled: Record<RestrictionId, boolean>; minCapMillions: number; maxCapMillions: number;
  minRunwayMonths: number; maxPdufaDays: number; minimumPhase: number;
  capBasis: "entry" | "current";
};
export const RESTRICTIONS: { id: RestrictionId; title: string; proposed?: boolean; warning?: boolean; help: string }[] = [
  { id: "public", title: "Publicly traded company", help: "Match the saved public-company registry. A saved NOT_LISTED finding fails; an absent match needs verification." },
  { id: "minCap", title: "Minimum market cap", help: "Your approved rule uses market cap when first admitted. Entry caps have not been retained. Latest saved cap is available as a separate comparison." },
  { id: "maxCap", title: "Maximum market cap", help: "The upper limit is inclusive. Missing or unverified cap evidence needs verification; current cap never substitutes for entry cap in approved-rule mode." },
  { id: "progress", title: "Progressing toward / upcoming PDUFA", help: "Saved closed FDA events fail. A future, sourced PDUFA date supports an upcoming event. Clinical phase or a completed trial alone does not establish an FDA filing plan." },
  { id: "fdaPath", title: "FDA drug / biologic pathway", proposed: true, help: "An FDA-hosted drug/application source supports the pathway. Registry intervention type alone does not establish FDA jurisdiction. Exclusively non-drug/biologic interventions fail this proposed screen." },
  { id: "phase", title: "Minimum clinical phase", proposed: true, help: "Phase 3 is the proposed default. Combined Phase 2/3 includes Phase 3. Later regulatory stages also pass. Missing phase needs verification." },
  { id: "active", title: "Active development program", proposed: true, help: "An active registry status supports current activity. Completion, suspension or termination of one trial does not establish the status of the whole drug program; those need program-level verification." },
  { id: "identity", title: "Identifiable drug and indication", proposed: true, help: "Both a named investigational treatment and indication must be recorded. Placebo-only or missing names need verification." },
  { id: "documents", title: "Clinical / regulatory documentation", proposed: true, help: "A saved ClinicalTrials.gov, FDA, SEC or issuer source URL must be recorded. This tests source availability, not a fresh document-content review." },
  { id: "runway", title: "Minimum cash runway", proposed: true, help: "Uses the existing source-checked runway assessment. Missing or invalid runway stays unknown." },
  { id: "pdufaWindow", title: "Maximum days until PDUFA", proposed: true, help: "Applies to recorded scheduled dates. Unscheduled or elapsed targets need verification; elapsed targets do not imply an FDA decision." },
  { id: "hold", title: "Unresolved clinical hold", proposed: true, warning: true, help: "Warning only. Hold status has not been collected for this complete universe, so it remains unknown and never excludes a record." },
];
export function defaultRestrictionSettings(): RestrictionSettings {
  return { enabled: Object.fromEntries(RESTRICTIONS.map(r => [r.id, !r.proposed])) as Record<RestrictionId, boolean>,
    minCapMillions: 300, maxCapMillions: 10000, minRunwayMonths: 12,
    maxPdufaDays: 730, minimumPhase: 3, capBasis: "entry" };
}
export function nctOf(row: ImpactRecord) {
  const nct = row.nctId || row.id.match(/\bNCT\d{8}\b/)?.[0] || "";
  return /^NCT\d{8}$/.test(nct) ? nct : "";
}
export function isRegisteredTrial(row: ImpactRecord) {
  return /^TRIAL\|NCT\d{8}$/.test(row.id);
}
function linked(value?: string) {
  try { const url = new URL(value || ""); return url.protocol === "https:" && !!url.hostname && !url.username; }
  catch { return false; }
}
function fdaSource(value?: string) {
  try { const url = new URL(value || ""); return linked(value) && (url.hostname === "fda.gov" || url.hostname.endsWith(".fda.gov")); }
  catch { return false; }
}
function daysUntil(value: string | undefined, asOf: string) {
  const valid = (s: string) => /^\d{4}-\d{2}-\d{2}$/.test(s) && Number.isFinite(Date.parse(s)) && new Date(s).toISOString().slice(0, 10) === s;
  const target = (value || "").slice(0, 10), today = asOf.slice(0, 10);
  return valid(target) && valid(today) ? Math.round((Date.parse(target) - Date.parse(today)) / 86400000) : null;
}
function phaseNumber(row: ImpactRecord): number | null {
  if (["NDA/BLA Submission", "FDA Acceptance", "PDUFA Decision", "Post-Decision"].includes(row.stage || "")) return 4;
  const phase = row.trialFilters?.registeredPhase || row.stage;
  return ({ "Early Phase 1": 1, "Phase 1": 1, "Phase 1/2": 2, "Phase 2": 2,
    "Phase 2/3": 3, "Phase 3": 3, "Phase 3 Results": 3, "Phase 4": 4 } as Record<string, number>)[phase || ""] ?? null;
}
export function restrictionVerdict(id: RestrictionId, row: ImpactRecord, settings: RestrictionSettings,
    evidence: RestrictionEvidence | null, asOf: string): Verdict {
  const issuer = evidence?.issuers[row.ticker.toUpperCase()];
  switch (id) {
    case "public": return issuer?.listed ?? "UNKNOWN";
    case "minCap": case "maxCap": {
      // No entry-time ledger exists. Never relabel a current quote as an entry cap.
      const cap = settings.capBasis === "current" ? issuer?.marketCap : null;
      if (typeof cap !== "number" || !Number.isFinite(cap) || cap <= 0) return "UNKNOWN";
      const limit = (id === "minCap" ? settings.minCapMillions : settings.maxCapMillions) * 1e6;
      if (!Number.isFinite(limit) || limit < 0) return "UNKNOWN";
      return (id === "minCap" ? cap >= limit : cap <= limit) ? "PASS" : "FAIL";
    }
    case "progress": {
      if (row.stage === "Post-Decision") return "FAIL";
      const days = daysUntil(row.pdufaDate, asOf);
      return days !== null && days >= 0 && (linked(row.fdaSource) || linked(row.phase3Source)) ? "PASS" : "UNKNOWN";
    }
    case "fdaPath": {
      if (fdaSource(row.fdaSource)) return "PASS";
      const types = evidence?.trialTypes[nctOf(row)] || [];
      return types.length && types.every(t => !["DRUG", "BIOLOGICAL", "GENETIC"].includes(t)) ? "FAIL" : "UNKNOWN";
    }
    case "phase": {
      const phase = phaseNumber(row);
      return phase === null ? "UNKNOWN" : phase >= settings.minimumPhase ? "PASS" : "FAIL";
    }
    case "active": return ["RECRUITING", "ACTIVE_NOT_RECRUITING", "NOT_YET_RECRUITING", "ENROLLING_BY_INVITATION"]
      .includes(row.trialFilters?.trialStatus || "") ? "PASS" : row.stage === "Post-Decision" ? "FAIL" : "UNKNOWN";
    case "identity": return row.drug?.trim() && row.indication?.trim() && !/^(?:placebo|unknown|not recorded|n\/a)$/i.test(row.drug.trim()) ? "PASS" : "UNKNOWN";
    case "documents": return linked(row.phase3Source) || linked(row.fdaSource) ? "PASS" : "UNKNOWN";
    case "runway": {
      const runway = row.trialFilters?.runwayMonths;
      return typeof runway === "number" && Number.isFinite(runway) && runway >= 0
        ? runway >= settings.minRunwayMonths ? "PASS" : "FAIL" : "UNKNOWN";
    }
    case "pdufaWindow": {
      const days = daysUntil(row.pdufaDate, asOf);
      return days === null || days < 0 ? "UNKNOWN" : days <= settings.maxPdufaDays ? "PASS" : "FAIL";
    }
    case "hold": return "UNKNOWN";
  }
}
export type ImpactStep = {
  id: RestrictionId; enabled: boolean; warning: boolean;
  alonePass: number; aloneFail: number; aloneUnknown: number;
  before: number; newlyExcluded: number; remaining: number; passed: number; pending: number;
  newlyExcludedIds: Set<string>;
};
export function calculateRestrictionImpact(input: ImpactRecord[], settings: RestrictionSettings,
    evidence: RestrictionEvidence | null, asOf: string) {
  // Count exact source identities once, independent of every table/search/page filter.
  const rows = [...new Map(input.map(row => [row.id, row])).values()];
  const states = new Map<string, Verdict>(rows.map(row => [row.id, "PASS"]));
  const steps: ImpactStep[] = [];
  for (const rule of RESTRICTIONS) {
    const alone = { PASS: 0, FAIL: 0, UNKNOWN: 0 }, newlyExcludedIds = new Set<string>();
    const before = [...states.values()].filter(s => s !== "FAIL").length;
    for (const row of rows) {
      const verdict = restrictionVerdict(rule.id, row, settings, evidence, asOf);
      alone[verdict]++;
      if (!settings.enabled[rule.id] || rule.warning) continue;
      const previous = states.get(row.id)!;
      if (previous === "FAIL") continue;
      if (verdict === "FAIL") { states.set(row.id, "FAIL"); newlyExcludedIds.add(row.id); }
      else if (verdict === "UNKNOWN") states.set(row.id, "UNKNOWN");
      // A later pass cannot erase an earlier evidence gap.
    }
    const summary = { PASS: 0, FAIL: 0, UNKNOWN: 0 };
    for (const state of states.values()) summary[state]++;
    steps.push({ id: rule.id, enabled: settings.enabled[rule.id], warning: !!rule.warning,
      alonePass: alone.PASS, aloneFail: alone.FAIL, aloneUnknown: alone.UNKNOWN,
      before, newlyExcluded: newlyExcludedIds.size, remaining: summary.PASS + summary.UNKNOWN,
      passed: summary.PASS, pending: summary.UNKNOWN, newlyExcludedIds });
  }
  const final = steps.at(-1)!;
  return { rows, total: rows.length, steps, passed: final.passed, pending: final.pending,
    excluded: rows.length - final.remaining };
}
