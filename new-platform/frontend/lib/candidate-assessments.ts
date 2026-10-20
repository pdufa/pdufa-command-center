export type AssessmentStage = "PIPELINE" | "GEM_JR" | "GEM";
export const ASSESSMENT_STAGES: AssessmentStage[] = ["PIPELINE", "GEM_JR", "GEM"];
export const ASSESSMENT_WEIGHTS = { PIPELINE: [25,20,15,15,10,10,5], GEM_JR: [20,15,20,15,15,10,5], GEM: [25,20,15,15,10,10,5] };
export const ASSESSMENT_LABELS = {
  PIPELINE: ["Clinical efficacy / effect size", "Trial design / endpoint quality", "Statistical reliability", "Safety / tolerability", "Reproducibility / consistency", "Regulatory / development feasibility", "Competitive clinical differentiation"],
  GEM_JR: ["Clinical strength", "Next-milestone success", "Catalyst importance / timing", "Cash runway / financing risk", "Valuation / upside", "Competitive / commercial potential", "Market recognition / liquidity"],
  GEM: ["Clinical strength", "Next-milestone success", "Safety / regulatory readiness", "Catalyst importance / timing", "Cash runway / dilution", "Valuation / risk-adjusted upside", "Competitive / commercial potential"],
};
export const stageLabel = (stage: AssessmentStage) => stage.replaceAll("_", " ");
export const categoryId = (stage: AssessmentStage, index: number) => (stage === "PIPELINE" ? "P" : stage === "GEM_JR" ? "J" : "G") + (index + 1);
export type ScoreTuple = [number | null, number, number, ...number[]];
export type AssessmentIndexRecord = [string, ScoreTuple, ScoreTuple, ScoreTuple, string[]];
export type AssessmentIndex = {
  modelVersion: string; status: "COMPLETE"; version: string; workspaceVersion: string; asOf: string; computedAt: string;
  total: number; registryLinked: number; registryMissing: number; reviewSource: string; historyStatus: string;
  totals: Record<AssessmentStage, { complete: number; partial: number; missing: number }>;
  records: AssessmentIndexRecord[];
};
export function scoreFor(record: AssessmentIndexRecord | undefined, stage: AssessmentStage): ScoreTuple | undefined {
  return record?.[ASSESSMENT_STAGES.indexOf(stage) + 1] as ScoreTuple | undefined;
}
export function validateAssessmentIndex(value: unknown): AssessmentIndex {
  const data = value as AssessmentIndex;
  if (!data || data.status !== "COMPLETE" || typeof data.version !== "string" || !Array.isArray(data.records) || data.records.length !== data.total || new Set(data.records.map(r => r[0])).size !== data.total) throw new Error("Scoring coverage could not be verified");
  for (const record of data.records) {
    if (typeof record[0] !== "string" || !record[0] || !Array.isArray(record[4])) throw new Error("Invalid candidate score identity");
    ASSESSMENT_STAGES.forEach((stage, i) => {
      const tuple = record[i + 1] as ScoreTuple;
      if (!Array.isArray(tuple) || tuple.length !== 17 || tuple.slice(1).some(n => typeof n !== "number" || !Number.isFinite(n) || n < 0) || tuple[1] > tuple[2] + .02 || tuple[2] > 100 || (tuple[0] !== null && (typeof tuple[0] !== "number" || !Number.isFinite(tuple[0]) || tuple[2] < 99.99 || Math.abs(tuple[0] - tuple[1]) > .02))) throw new Error("Invalid evidence score");
      ASSESSMENT_WEIGHTS[stage].forEach((max, index) => { if (tuple[3 + index]! > tuple[10 + index]! + .02 || tuple[10 + index]! > max + .02) throw new Error("Category coverage does not reconcile"); });
    });
  }
  return data;
}
export type AssessmentMetric = { id: string; label: string; maximum: number; value: unknown; points: number | null; coverage: number; status: string; rule: string; source: string; checkedAt: string; sourceDate: string; note: string; observations?: unknown };
export type AssessmentCategory = { id: string; label: string; maximum: number; score: number | null; observedPoints: number; coverage: number; status: string; metrics: AssessmentMetric[] };
export type AssessmentModel = { score: number | null; observedPoints: number; coverage: number; status: string; categories: AssessmentCategory[] };
export type AssessmentDetail = {
  id: string; programId?: string; nctId: string; modelVersion: string; version: string; asOf: string; computedAt: string;
  models: Record<AssessmentStage, AssessmentModel>; riskFlags: string[];
  registryFetchedAt: string; registrySourceDate: string; historyStatus: string;
  qualification: { note: string }; reportedStatistics: Record<string, unknown>[]; data: unknown; missingEvidence: string[];
  history: { assessedAt: string; modelVersion: string; evidenceHash: string; models: ScoreTuple[]; riskFlags: string[] }[];
  changes: Partial<Record<AssessmentStage, { observedPoints: number; coverage: number }>>;
};
export function sortByAssessment<T extends { id: string }>(rows: T[], records: Map<string, AssessmentIndexRecord>, stage: AssessmentStage, sort: string): T[] {
  if (sort === "source") return rows;
  return [...rows].sort((a, b) => {
    const l = scoreFor(records.get(a.id), stage), r = scoreFor(records.get(b.id), stage);
    const left = sort === "coverage" ? l?.[2] : records.get(a.id)?.[4].length ? null : l?.[0], right = sort === "coverage" ? r?.[2] : records.get(b.id)?.[4].length ? null : r?.[0];
    if (left == null || right == null) return left == null && right == null ? 0 : left == null ? 1 : -1;
    return right - left;
  });
}
export function downloadJson(value: unknown, filename: string) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(value, null, 2)], { type: "application/json" }));
  const a = document.createElement("a"); a.href = url; a.download = filename; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
