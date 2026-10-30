export type ArchiveHealth = {
  archived_trials: number | null;
  archive_integrity: "PASS" | "REVIEW_REQUIRED";
  manifest_verification: "PASS" | "REVIEW_REQUIRED";
  last_verified: string | null;
  next_scheduled_verification: string | null;
  scientific_ready_trials: number | null;
  trials_needing_additional_evidence: number | null;
  trials_with_regulatory_outcome_evidence: number | null;
  inventory: Record<string, { present: number; missing: number }>;
  checks: Record<string, unknown>;
  scheduler: Record<string, unknown>;
  methodology?: string;
  definitions?: Record<string, string>;
  scientific_readiness_scope?: string;
};

const count = (value: unknown): value is number | null => value === null ||
  (typeof value === "number" && Number.isSafeInteger(value) && value >= 0);
const object = (value: unknown): value is Record<string, unknown> =>
  !!value && typeof value === "object" && !Array.isArray(value);

export function isArchiveHealth(value: unknown): value is ArchiveHealth {
  if (!object(value)) return false;
  const counts = ["archived_trials", "scientific_ready_trials", "trials_needing_additional_evidence",
    "trials_with_regulatory_outcome_evidence"];
  if (!counts.every(key => count(value[key]))) return false;
  if (!["PASS", "REVIEW_REQUIRED"].includes(String(value.archive_integrity)) ||
      !["PASS", "REVIEW_REQUIRED"].includes(String(value.manifest_verification))) return false;
  if (!["last_verified", "next_scheduled_verification"].every(key => value[key] === null ||
    (typeof value[key] === "string" && Number.isFinite(Date.parse(value[key] as string))))) return false;
  if (!object(value.inventory) || !object(value.checks) || !object(value.scheduler)) return false;
  if (value.definitions !== undefined && (!object(value.definitions) ||
      !Object.values(value.definitions).every(definition => typeof definition === "string"))) return false;
  if (value.scientific_readiness_scope !== undefined && typeof value.scientific_readiness_scope !== "string") return false;
  return Object.values(value.inventory).every(metric => object(metric) &&
    typeof metric.present === "number" && count(metric.present) &&
    typeof metric.missing === "number" && count(metric.missing));
}

export function archiveCount(value: number | null): string {
  return value === null ? "Unverified" : value.toLocaleString("en-US");
}

export function archiveTime(value: string | null): string {
  return value === null ? "Unverified" : new Intl.DateTimeFormat("en-US", {
    timeZone: "America/Los_Angeles", dateStyle: "medium", timeStyle: "long",
  }).format(new Date(value));
}

export function archiveLabel(value: string): string {
  return value.replaceAll("_", " ").replace(/\b\w/g, ch => ch.toUpperCase());
}
