/**
 * Evidence-gated installation tracker math.
 *
 * These are audit stage counts, NOT percent of engineering effort completed.
 * Code-present and Preview READY are implementation signals, never runtime
 * verification or scientific acceptance. Missing proof stays open.
 */
export type AuditGate = "Code present" | "Preview READY" | "Partial" |
  "Not verified" | "Not audited" | "Not applicable" | "Verified";

export type AuditItem = {
  component: string;
  code: AuditGate;
  deployment: AuditGate;
  runtime: AuditGate;
  evidence: AuditGate;
};

export const AUDIT_GROUPS = [
  { name: "Core Platform", components: [
    "Core Platform", "Pipeline", "POOL / PIPELINE", "Evidence Verification",
    "Regulatory Intelligence", "Investment Analysis", "Results & Reporting",
    "Final Acceptance",
  ] },
  { name: "Scientific Assessment & Prediction", components: [
    "Scientific Assessment", "Historical Trial Database", "Prediction Engine",
    "Prediction Validation",
  ] },
  { name: "Production Automation", components: [
    "Nightly Scanning", "Automation", "Backup & Recovery",
  ] },
] as const;

export type AuditTotals = {
  sections: number;
  accepted: number;
  gates: number;
  independentlyVerified: number;
  implementationSignals: number;
  partial: number;
  unverified: number;
  excluded: number;
};

export type AuditGroup = {
  name: string;
  items: AuditItem[];
  totals: AuditTotals;
};

const stages = ["code", "deployment", "runtime", "evidence"] as const;
const newTotals = (): AuditTotals => ({
  sections: 0, accepted: 0, gates: 0, independentlyVerified: 0,
  implementationSignals: 0, partial: 0, unverified: 0, excluded: 0,
});

/** All applicable stages must have positive proof, including runtime and evidence. */
export function isAccepted(item: AuditItem): boolean {
  const codeReady = item.code === "Code present" || item.code === "Verified";
  const deployed = item.deployment === "Preview READY" || item.deployment === "Verified";
  const runtimeProven = item.runtime === "Verified";
  const evidenceProven = item.evidence === "Verified" || item.evidence === "Not applicable";
  return codeReady && deployed && runtimeProven && evidenceProven;
}

/** MAIN technical acceptance is independent of the four research sections.
 * Exclude Final Acceptance itself to avoid a circular prerequisite.
 */
export function mainTechnicalAcceptance(items: readonly AuditItem[]) {
  const {groups} = summarizeInstallationAudit(items);
  const required = [...groups[0].items.filter(item => item.component !== "Final Acceptance"), ...groups[2].items];
  const open = required.filter(item => !isAccepted(item) || item.deployment !== "Verified");
  return {ready:open.length === 0,accepted:required.length-open.length,total:required.length,open:open.map(item=>item.component)};
}

function summarize(items: readonly AuditItem[]): AuditTotals {
  const totals = newTotals();
  for (const item of items) {
    totals.sections++;
    if (isAccepted(item)) totals.accepted++;
    for (const stage of stages) {
      const value = item[stage];
      if (value === "Not applicable") { totals.excluded++; continue; }
      totals.gates++;
      if (value === "Verified") totals.independentlyVerified++;
      else if (value === "Code present" || value === "Preview READY") totals.implementationSignals++;
      else if (value === "Partial") totals.partial++;
      else totals.unverified++;
    }
  }
  return totals;
}

export function summarizeInstallationAudit(items: readonly AuditItem[]): {
  groups: AuditGroup[];
  total: AuditTotals;
} {
  const indexed = new Map<string, AuditItem>();
  for (const item of items) {
    if (indexed.has(item.component)) throw new Error("Duplicate installation audit component: " + item.component);
    indexed.set(item.component, item);
  }
  const groups: AuditGroup[] = AUDIT_GROUPS.map(group => {
    const groupItems = group.components.map(component => {
      const item = indexed.get(component);
      if (!item) throw new Error("Missing installation audit component: " + component);
      return item;
    });
    return {name: group.name, items: groupItems, totals: summarize(groupItems)};
  });
  const included = groups.reduce((n, group) => n + group.items.length, 0);
  if (included !== items.length) throw new Error("Unclassified installation audit components: " + (items.length - included));
  return {groups, total: summarize(items)};
}
