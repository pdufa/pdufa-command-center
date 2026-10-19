import type { Candidate } from "../app/Workspace";

export type PipelinePage = {
  version: string; total: number; offset: number; limit: number;
  rows: Candidate[]; nextOffset: number | null;
};

export function validatePipelinePage(value: unknown, offset: number, limit: number,
  version?: string): PipelinePage {
  if (!value || typeof value !== "object") throw new Error("Invalid pipeline page");
  const page = value as PipelinePage;
  if (typeof page.version !== "string" || !/^[a-f0-9]{64}$/.test(page.version) ||
      (version && page.version !== version) ||
      !Number.isSafeInteger(page.total) || page.total < 0 ||
      page.offset !== offset || page.limit !== limit ||
      !Array.isArray(page.rows) || page.rows.length > limit ||
      page.rows.some(row => !row || typeof row.id !== "string" || !row.id || typeof row.ticker !== "string") ||
      new Set(page.rows.map(row => row.id)).size !== page.rows.length ||
      page.rows.length !== Math.min(limit, Math.max(0, page.total - offset)) ||
      page.nextOffset !== (offset + page.rows.length < page.total ? offset + page.rows.length : null)) {
    throw new Error("Inconsistent pipeline page");
  }
  return page;
}
