export type PipelineRecord = {
  id: string; programId?: string; ticker: string; company?: string; drug?: string;
  indication?: string; nctId?: string; stage?: string; pdufaDate?: string;
  capInRange?: boolean; marketCap?: number | null;
};

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
