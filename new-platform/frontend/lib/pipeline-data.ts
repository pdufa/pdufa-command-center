export type PipelineRecord = {
  id: string; programId?: string; ticker: string; company?: string; drug?: string;
  indication?: string; nctId?: string; stage?: string; pdufaDate?: string;
  capInRange?: boolean; marketCap?: number | null;
};

export const PIPELINE_STAGES = ["Early Phase 1", "Phase 1", "Phase 1/2", "Phase 2", "Phase 2/3", "Phase 3", "Phase 3 Results", "NDA/BLA Submission", "FDA Acceptance", "PDUFA Decision", "Post-Decision", "Phase 4", "Not Applicable", "Unknown"];
export type PipelineSortKey = "programId" | "ticker" | "stage" | "nctId" | "status" | "primaryCompletion" | "pdufaDate" | "marketCap" | "pValueCount";
export type PipelineSort = { key: PipelineSortKey; direction: "asc" | "desc" };
export type RegistrySortIndex = Record<string, { status?: string; primary_completion_date?: string | null; p_value_count: number }>;
const COLLATOR = new Intl.Collator("en", { numeric: true, sensitivity: "base" });

export function needsRegistrySort(key: PipelineSortKey) {
  return key === "status" || key === "primaryCompletion" || key === "pValueCount";
}

export function sortPipelineRows<T extends PipelineRecord>(rows: T[], sort: PipelineSort, registry: RegistrySortIndex = {}) {
  function date(value?: string | null) {
    const iso = value?.trim().slice(0, 10);
    if (!iso || !/^\d{4}(-\d{2}){0,2}$/.test(iso)) return null;
    const parsed = Date.parse(iso.length === 4 ? iso + "-01-01" : iso.length === 7 ? iso + "-01" : iso);
    return Number.isFinite(parsed) ? parsed : null;
  }
  function value(row: T): string | number | null | undefined {
    const nct = trialId(row), saved = registry[nct];
    switch (sort.key) {
      case "programId": return row.programId;
      case "ticker": return row.ticker;
      case "stage": { const index = PIPELINE_STAGES.indexOf(row.stage || "Unknown"); return index < 0 ? PIPELINE_STAGES.length : index; }
      case "nctId": return nct;
      case "status": return saved?.status || (nct ? null : "REGULATORY PROGRAM");
      case "primaryCompletion": return date(saved?.primary_completion_date);
      case "pdufaDate": return date(row.pdufaDate);
      case "marketCap": return row.marketCap;
      case "pValueCount": return saved?.p_value_count;
    }
  }
  const missing = (item: string | number | null | undefined) => item == null || item === "" || (typeof item === "number" && !Number.isFinite(item));
  return [...rows].sort((a, b) => {
    const left = value(a), right = value(b);
    // Missing values stay last in either direction; a reported zero is data.
    if (missing(left) !== missing(right)) return missing(left) ? 1 : -1;
    const comparison = missing(left) ? 0 : typeof left === "number" && typeof right === "number" ?
      left - right : COLLATOR.compare(String(left), String(right));
    return comparison * (sort.direction === "asc" ? 1 : -1) ||
      COLLATOR.compare(a.ticker, b.ticker) || COLLATOR.compare(a.drug || "", b.drug || "") || COLLATOR.compare(a.id, b.id);
  });
}

export function trialId(row: PipelineRecord) {
  const value = row.nctId || row.id.match(/\bNCT\d{8}\b/)?.[0] || "";
  return /^NCT\d{8}$/.test(value) ? value : "";
}

export function filterPipelineRows<T extends PipelineRecord>(rows: T[], filters: {
  query?: string; onlyBand?: boolean; stages?: string[]; dates?: string[];
}, dateBand: (row: T) => string) {
  const query = (filters.query || "").toLowerCase();
  return rows.filter(row =>
    (!filters.onlyBand || row.capInRange) &&
    (!query || [row.ticker, row.company, row.drug, row.indication, row.nctId, row.programId, row.id]
      .some(value => (value || "").toLowerCase().includes(query))) &&
    (!filters.stages?.length || filters.stages.includes(row.stage || "Unknown")) &&
    (!filters.dates?.length || filters.dates.includes(dateBand(row)))
  );
}

export function pipelineAvailability<T extends PipelineRecord>(rows: T[], filters: {
  query?: string; onlyBand?: boolean;
}, dateBand: (row: T) => string, stages: string[], bands: string[]) {
  // Checkbox selections choose the displayed results, not the available totals.
  const available = filterPipelineRows(rows, { query: filters.query, onlyBand: filters.onlyBand }, dateBand);
  const stageTotals = new Map<string, number>(), dateTotals = new Map<string, number>();
  for (const row of available) {
    const stage = row.stage || "Unknown", band = dateBand(row);
    stageTotals.set(stage, (stageTotals.get(stage) || 0) + 1);
    dateTotals.set(band, (dateTotals.get(band) || 0) + 1);
  }
  return { rows: available,
    stageCounts: stages.map(label => ({ label, count: stageTotals.get(label) || 0 })),
    dateCounts: bands.map(label => ({ label, count: dateTotals.get(label) || 0 })),
  };
}

export function pageRows<T>(rows: T[], requestedPage: number, size: number) {
  const pages = Math.max(1, Math.ceil(rows.length / size));
  const page = Math.min(Math.max(0, requestedPage), pages - 1);
  return { page, pages, start: rows.length ? page * size + 1 : 0,
    end: Math.min(rows.length, (page + 1) * size), rows: rows.slice(page * size, (page + 1) * size) };
}

export type Json = null | boolean | number | string | Json[] | { [key: string]: Json };
export function object(value: Json | undefined): { [key: string]: Json } {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}
export function label(key: string) {
  return key.replace(/Module$|Section$/g, "").replace(/([a-z0-9])([A-Z])/g, "$1 $2")
    .replaceAll("_", " ").replace(/^./, letter => letter.toUpperCase());
}
export function registrySections(study: { [key: string]: Json }) {
  const sections: { id: string; title: string; data: Json }[] = [];
  for (const [key, value] of Object.entries(study)) {
    if (["protocolSection", "resultsSection", "documentSection", "derivedSection"].includes(key)
        && value && typeof value === "object" && !Array.isArray(value)) {
      for (const [module, data] of Object.entries(value)) {
        sections.push({ id: key + "." + module,
          title: (key === "resultsSection" ? "Results · " : key === "documentSection" ? "Documents · " : key === "derivedSection" ? "Derived · " : "") + label(module), data });
      }
    } else {
      sections.push({ id: key, title: label(key), data: value });
    }
  }
  return sections;
}

export function reportedAnalyses(study: { [key: string]: Json }) {
  const outcomes = object(object(study.resultsSection).outcomeMeasuresModule).outcomeMeasures;
  if (!Array.isArray(outcomes)) return [];
  return outcomes.flatMap((raw, outcomeIndex) => {
    const outcome = object(raw);
    const groups = Array.isArray(outcome.groups) ? outcome.groups.map(object) : [];
    return (Array.isArray(outcome.analyses) ? outcome.analyses : []).map((rawAnalysis, analysisIndex) => {
      const analysis = object(rawAnalysis);
      const ids = Array.isArray(analysis.groupIds) ? analysis.groupIds : [];
      return { outcomeIndex: outcomeIndex + 1, analysisIndex: analysisIndex + 1,
        endpoint: outcome.title, type: outcome.type, timeFrame: outcome.timeFrame,
        groups: ids.map(id => groups.find(group => group.id === id)?.title || id),
        pValue: analysis.pValue, method: analysis.statisticalMethod, analysis };
    }).filter(row => row.pValue !== undefined && row.pValue !== null && row.pValue !== "");
  });
}
