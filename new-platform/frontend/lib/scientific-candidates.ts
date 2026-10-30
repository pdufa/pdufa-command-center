export type CandidateSummary = {
  nct_id: string;
  sponsor: string;
  products: string[];
  indications: string[];
  readiness: "READY" | "RELUCTANT" | "NOT READY";
  explanation: string;
  last_verified: string;
};
export type RegulatoryIdentifier = {
  associated_nct_id: string;
  identifier: string;
  status: "VERIFIED" | "CONFLICTING" | "UNRESOLVED";
  sponsor: string;
  products: string[];
  evidence: unknown;
  verified_at: string | null;
};
export type ScientificCandidates = {
  status: string;
  candidates_identified: number | null;
  candidates_independently_checked: number | null;
  ready: number | null;
  reluctant: number | null;
  not_ready: number | null;
  regulatory_identifiers_verified: number | null;
  regulatory_identifiers_unresolved: number | null;
  full_scientific_investigations_completed: number | null;
  scientific_dossiers_created: number | null;
  last_verified: string | null;
  candidates: CandidateSummary[];
  regulatory_identifiers: RegulatoryIdentifier[];
};
export function object(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === "object" && !Array.isArray(value);
}
const count = (value: unknown): value is number | null => value === null ||
  (typeof value === "number" && Number.isSafeInteger(value) && value >= 0);
const strings = (value: unknown): value is string[] => Array.isArray(value) && value.every(v => typeof v === "string");
const stamp = (value: unknown) => typeof value === "string" && Number.isFinite(Date.parse(value));
export function isScientificCandidates(value: unknown): value is ScientificCandidates {
  if (!object(value) || typeof value.status !== "string") return false;
  const fields = ["candidates_identified", "candidates_independently_checked", "ready", "reluctant", "not_ready",
    "regulatory_identifiers_verified", "regulatory_identifiers_unresolved", "full_scientific_investigations_completed", "scientific_dossiers_created"];
  if (!fields.every(key => count(value[key])) || !(value.last_verified === null || stamp(value.last_verified))) return false;
  if (!Array.isArray(value.candidates) || !Array.isArray(value.regulatory_identifiers)) return false;
  if (!value.candidates.every(v => object(v) && typeof v.nct_id === "string" && /^NCT[0-9]{8}$/.test(v.nct_id) &&
    typeof v.sponsor === "string" && strings(v.products) && strings(v.indications) && typeof v.explanation === "string" &&
    ["READY", "RELUCTANT", "NOT READY"].includes(String(v.readiness)) && stamp(v.last_verified))) return false;
  if (!value.regulatory_identifiers.every(v => object(v) && typeof v.associated_nct_id === "string" && /^NCT[0-9]{8}$/.test(v.associated_nct_id) &&
    typeof v.identifier === "string" && typeof v.sponsor === "string" && strings(v.products) &&
    ["VERIFIED", "CONFLICTING", "UNRESOLVED"].includes(String(v.status)) && (v.verified_at === null || stamp(v.verified_at)))) return false;
  const identified = value.candidates_identified, checked = value.candidates_independently_checked;
  const dossiers = value.scientific_dossiers_created;
  if (typeof identified === "number" && typeof dossiers === "number" && dossiers > identified) return false;
  if (typeof checked === "number" && typeof dossiers === "number" && checked > dossiers) return false;
  if (typeof dossiers === "number" && dossiers !== value.candidates.length) return false;
  if (typeof dossiers === "number" && [value.ready, value.reluctant, value.not_ready].every(v => typeof v === "number") &&
    (value.ready as number) + (value.reluctant as number) + (value.not_ready as number) !== dossiers) return false;
  for (const [key, readiness] of [["ready", "READY"], ["reluctant", "RELUCTANT"], ["not_ready", "NOT READY"]]) {
    if (typeof value[key] === "number" && value[key] !== value.candidates.filter(candidate => candidate.readiness === readiness).length) return false;
  }
  if (typeof value.full_scientific_investigations_completed === "number" && typeof value.ready === "number" &&
    value.full_scientific_investigations_completed > value.ready) return false;
  return new Set(value.candidates.map(v => v.nct_id)).size === value.candidates.length;
}
export function scientificCount(value: number | null): string {
  return value === null ? "Unverified" : value.toLocaleString("en-US");
}
export function scientificTime(value: string | null): string {
  return value === null ? "Unverified" : new Intl.DateTimeFormat("en-US", {
    timeZone: "America/Los_Angeles", dateStyle: "medium", timeStyle: "long",
  }).format(new Date(value));
}
export function sourceUrl(value: unknown): string | null {
  if (typeof value !== "string") return null;
  try { const url = new URL(value); return url.protocol === "https:" && !url.username && !url.password ? url.toString() : null; }
  catch { return null; }
}
