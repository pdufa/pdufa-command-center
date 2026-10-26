import type { AuditGroup, AuditTotals } from "./installation-audit-summary";

/**
 * One immutable GitHub-anchored comparison point, NOT a synthetic daily history.
 * Values were read from installation-audit/page.tsx at the exact merged ref.
 */
export const AUDIT_BASELINE = {
  commit: "062ea740922d767148bc99565c4af43bd6eb43fa",
  committedAt: "2026-10-26T00:05:00Z",
  url: "https://github.com/pdufa/pdufa-command-center/blob/062ea740922d767148bc99565c4af43bd6eb43fa/new-platform/frontend/app/installation-audit/page.tsx",
  groups: [
    { name: "Core Platform", sections: 8, gates: 31, independentlyVerified: 0, implementationSignals: 7, partial: 4, unverified: 20, accepted: 0 },
    { name: "Scientific Assessment & Prediction", sections: 4, gates: 16, independentlyVerified: 0, implementationSignals: 1, partial: 2, unverified: 13, accepted: 0 },
    { name: "Production Automation", sections: 3, gates: 12, independentlyVerified: 0, implementationSignals: 2, partial: 1, unverified: 9, accepted: 0 },
  ],
  total: {
    sections: 15, accepted: 0, gates: 59, independentlyVerified: 0,
    implementationSignals: 10, partial: 7, unverified: 42, excluded: 1,
  },
} as const;

export type AuditChange = {
  fullyAccepted: number;
  individuallyVerified: number;
  implementationSignals: number;
  partial: number;
  unverified: number;
};

const valid = (t: AuditTotals) =>
  t.gates === t.independentlyVerified + t.implementationSignals + t.partial + t.unverified &&
  t.accepted >= 0 && t.accepted <= t.sections &&
  t.excluded >= 0;

/**
 * When scope/denominators differ, a delta would be misleading. Return null and
 * report that the underlying requirement set changed instead of guessing.
 */
export function compareAuditToBaseline(groups: readonly AuditGroup[], total: AuditTotals): AuditChange | null {
  if (!valid(total) ||
      total.sections !== AUDIT_BASELINE.total.sections ||
      total.gates !== AUDIT_BASELINE.total.gates ||
      total.excluded !== AUDIT_BASELINE.total.excluded ||
      groups.length !== AUDIT_BASELINE.groups.length) return null;

  for (const [i, group] of groups.entries()) {
    const baseline = AUDIT_BASELINE.groups[i];
    if (group.name !== baseline.name ||
        group.totals.sections !== baseline.sections ||
        group.totals.gates !== baseline.gates ||
        !valid(group.totals)) return null;
  }

  return {
    fullyAccepted: total.accepted - AUDIT_BASELINE.total.accepted,
    individuallyVerified: total.independentlyVerified - AUDIT_BASELINE.total.independentlyVerified,
    implementationSignals: total.implementationSignals - AUDIT_BASELINE.total.implementationSignals,
    partial: total.partial - AUDIT_BASELINE.total.partial,
    unverified: total.unverified - AUDIT_BASELINE.total.unverified,
  };
}
