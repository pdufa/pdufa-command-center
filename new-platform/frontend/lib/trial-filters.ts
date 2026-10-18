export type TrialFilterFacts = {
  registeredPhase?: string; trialStatus?: string;
  resultsReleased?: boolean; resultsDate?: string; primaryOutcome?: string;
  safety?: string; firstFinancingClosed?: boolean; secondFinancingClosed?: boolean;
  firstClose?: string; secondClose?: string; independentFinancings?: string;
  milestones?: string[]; outcome?: string; runwayMonths?: number | null;
  dilution?: string; evidence?: string[]; lists?: string[];
};
export type TrialFilterRecord = {
  id: string; ticker: string; company?: string; drug?: string; indication?: string;
  nctId?: string; marketCap?: number | null; trialFilters?: TrialFilterFacts;
};
export type TrialFilterValues = {
  registeredPhase: string; resultsReleased: boolean; primaryOutcome: string;
  secondFinancingClosed: boolean; firstFinancingClosed: boolean;
  company: string; drug: string; indication: string; nctId: string;
  trialStatus: string; safety: string; resultsWindow: string;
  firstCloseWindow: string; secondCloseWindow: string; independentFinancings: string;
  regulatoryMilestone: string; outcome: string; runway: string; dilution: string;
  evidence: string; membership: string;
};
export const EMPTY_TRIAL_FILTERS: TrialFilterValues = {
  registeredPhase: "", resultsReleased: false, primaryOutcome: "", secondFinancingClosed: false,
  firstFinancingClosed: false, company: "", drug: "", indication: "", nctId: "",
  trialStatus: "", safety: "", resultsWindow: "", firstCloseWindow: "", secondCloseWindow: "",
  independentFinancings: "", regulatoryMilestone: "", outcome: "", runway: "", dilution: "",
  evidence: "", membership: "",
};
export const QUALIFICATION_CRITERIA = [
  { key: "phase3", label: "Phase 3 trial", help: "Registered Phase 3, including trials now at later stages. Phase 2/3 remains separate." },
  { key: "released", label: "Phase 3 results released", help: "A source-linked public readout or posted Phase 3 registry results. Trial completion alone does not qualify." },
  { key: "successful", label: "Successful Phase 3 verified", help: "Exact-program primary endpoint met, supported by dated results evidence. Posted results alone do not prove success." },
  { key: "financed", label: "Second post-readout financing closed", help: "Saved reviewed evidence for two separate SEC-documented closes after this exact program's readout. A new SEC recheck is separate." },
] as const;
export type QualificationKey = typeof QUALIFICATION_CRITERIA[number]["key"];

export function criterionChecked(filters: TrialFilterValues, key: QualificationKey) {
  return key === "phase3" ? filters.registeredPhase === "Phase 3" : key === "released" ? filters.resultsReleased :
    key === "successful" ? filters.primaryOutcome === "SUCCESS" : filters.secondFinancingClosed;
}
export function withCriterion(filters: TrialFilterValues, key: QualificationKey, enabled: boolean): TrialFilterValues {
  return { ...filters, ...(key === "phase3" ? { registeredPhase: enabled ? "Phase 3" : "" } :
    key === "released" ? { resultsReleased: enabled } : key === "successful" ? { primaryOutcome: enabled ? "SUCCESS" : "" } :
    { secondFinancingClosed: enabled }) };
}
export function activeTrialFilters(filters?: TrialFilterValues) {
  return filters ? Object.values(filters).filter(value => value !== "" && value !== false).length : 0;
}

function dateMatches(value: string | undefined, window: string, today: string) {
  if (!window) return true;
  if (window === "UNKNOWN") return !value;
  if (!value || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const age = (Date.parse(today + "T00:00:00Z") - Date.parse(value + "T00:00:00Z")) / 86400000;
  return Number.isFinite(age) && age >= 0 && (window === "OLDER" ? age > 365 : age <= Number(window));
}
function pacificDate() {
  const parts = new Intl.DateTimeFormat("en-CA", { timeZone: "America/Los_Angeles", year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(new Date());
  const values = Object.fromEntries(parts.map(part => [part.type, part.value]));
  return values.year + "-" + values.month + "-" + values.day;
}
function fieldMatches(value: string | undefined, selected: string) {
  return !selected || (selected === "UNKNOWN" ? !value || value === "UNKNOWN" || value === "Unknown" : value === selected);
}
function contains(value: string | undefined, selected: string) {
  return !selected || (value || "").toLowerCase().includes(selected.trim().toLowerCase());
}

export function matchesTrialFilters(row: TrialFilterRecord, filters?: TrialFilterValues, asOf?: string) {
  if (!filters || !activeTrialFilters(filters)) return true;
  const facts = row.trialFilters || {};
  if (!fieldMatches(row.ticker, filters.company) || !contains(row.drug, filters.drug) ||
      !contains(row.indication, filters.indication) || !contains(row.nctId || row.id.match(/NCT\d{8}/)?.[0], filters.nctId) ||
      !fieldMatches(facts.registeredPhase, filters.registeredPhase) || !fieldMatches(facts.trialStatus, filters.trialStatus) ||
      !fieldMatches(facts.primaryOutcome, filters.primaryOutcome) || !fieldMatches(facts.safety, filters.safety) ||
      !fieldMatches(facts.dilution, filters.dilution) || !fieldMatches(facts.outcome, filters.outcome) ||
      !fieldMatches(facts.independentFinancings, filters.independentFinancings)) return false;
  if ((filters.resultsReleased && facts.resultsReleased !== true) ||
      (filters.firstFinancingClosed && facts.firstFinancingClosed !== true) ||
      (filters.secondFinancingClosed && facts.secondFinancingClosed !== true)) return false;
  if (filters.regulatoryMilestone && !(facts.milestones || []).includes(filters.regulatoryMilestone)) return false;
  if (filters.evidence && !(facts.evidence || (row.trialFilters ? [] : ["MISSING"])).includes(filters.evidence)) return false;
  if (filters.membership && !(facts.lists || ["PIPELINE"]).includes(filters.membership)) return false;
  if (filters.runway) {
    const months = facts.runwayMonths;
    if (filters.runway === "UNKNOWN") { if (months != null) return false; }
    else if (months == null || !Number.isFinite(months) ||
      (filters.runway === "UNDER12" ? months >= 12 : months < Number(filters.runway))) return false;
  }
  if (filters.resultsWindow || filters.firstCloseWindow || filters.secondCloseWindow) {
    const today = asOf || pacificDate();
    if (!dateMatches(facts.resultsDate, filters.resultsWindow, today) ||
        !dateMatches(facts.firstClose, filters.firstCloseWindow, today) ||
        !dateMatches(facts.secondClose, filters.secondCloseWindow, today)) return false;
  }
  return true;
}

export function trialFilterSummary(filters: TrialFilterValues) {
  const labels: Partial<Record<keyof TrialFilterValues, string>> = {
    registeredPhase: "Registered phase", resultsReleased: "Phase 3 results released", primaryOutcome: "Primary endpoint",
    firstFinancingClosed: "First post-readout close verified", secondFinancingClosed: "Second post-readout close verified",
    company: "Company", drug: "Drug", indication: "Indication", nctId: "NCT", trialStatus: "Trial status",
    safety: "Safety", resultsWindow: "Results date", firstCloseWindow: "First close date", secondCloseWindow: "Second close date",
    independentFinancings: "Independent financings", regulatoryMilestone: "Regulatory milestone", outcome: "FDA outcome",
    runway: "Cash runway", dilution: "Dilution", evidence: "Evidence", membership: "List",
  };
  return (Object.entries(filters) as [keyof TrialFilterValues, string | boolean][])
    .filter(([, value]) => value !== "" && value !== false)
    .map(([key, value]) => labels[key] + (value === true ? "" : ": " + String(value).replaceAll("_", " "))).join(" · ");
}
