/** Read-only UI checklist. No endpoint, score, reviewer access, or release decision. */
import type { PublishedCoverage } from "./scientific-cohort-coverage";

export type ScienceInstallationGate = {
  id: string;
  label: string;
  status: "CHECKED_IN_SESSION" | "NOT_CHECKED_IN_SESSION" | "INDEPENDENT_VERIFICATION_REQUIRED";
  explanation: string;
};

/** Only two limited, explicitly triggered browser checks can be marked checked.
 * All scientific/release gates remain independently blocked by design.
 */
export function scienceInstallationGates(
  publishedCoverage: PublishedCoverage | null,
  connectedInSession: boolean,
): ScienceInstallationGate[] {
  const publishedSourceChecked = publishedCoverage?.status === "PUBLISHED_SNAPSHOT_AUDIT";
  return [
    {
      id: "published_identity_source",
      label: "Published GEM JR / GEM / WT list identity audit",
      status: publishedSourceChecked ? "CHECKED_IN_SESSION" : "NOT_CHECKED_IN_SESSION",
      explanation: publishedSourceChecked
        ? "Current published source-health and exact-ID listing checked. Unlinked or conflicting trial mappings still need separate review."
        : "Run Check current list coverage. Stale or unavailable source health never counts as checked.",
    },
    {
      id: "isolated_preview_transport",
      label: "Signed-in preview-to-isolated-service pilot connection",
      status: connectedInSession ? "CHECKED_IN_SESSION" : "NOT_CHECKED_IN_SESSION",
      explanation: connectedInSession
        ? "This session authenticated the exact KEYNOTE-024 pilot connection only; it did not certify evidence or outcomes."
        : "Use Verify isolated scientific API (pilot) while signed in. Earlier screenshots do not count as this session's check.",
    },
    {
      id: "primary_document_provenance",
      label: "Original dated source documents and exact-trial provenance",
      status: "INDEPENDENT_VERIFICATION_REQUIRED",
      explanation: "Capture and independently verify original protocol/SAP, dated clinical outcomes and regulatory source content; an archive checksum alone is insufficient.",
    },
    {
      id: "qualified_reviewer_identity",
      label: "Qualified independent reviewer identity and credentials",
      status: "INDEPENDENT_VERIFICATION_REQUIRED",
      explanation: "Verify actual reviewer identity, professional qualifications and independence. Self-entered names or nominations do not satisfy this gate.",
    },
    {
      id: "signed_independent_adjudication",
      label: "Two-reviewer evidence and contradiction adjudication",
      status: "INDEPENDENT_VERIFICATION_REQUIRED",
      explanation: "Reconcile protocol, statistics, endpoints, safety and contradictory evidence with two independently authenticated reviewers and a signed decision.",
    },
    {
      id: "fda_prediction_validation",
      label: "Prospective FDA outcome calibration and validation",
      status: "INDEPENDENT_VERIFICATION_REQUIRED",
      explanation: "Validate representative outcome denominators, date-separated holdouts and model calibration; historical approvals do not produce future probabilities.",
    },
    {
      id: "production_release_authorization",
      label: "Explicit production release and rollback authorization",
      status: "INDEPENDENT_VERIFICATION_REQUIRED",
      explanation: "Requires separate production credentials, regression/rollback review and explicit release approval; this checklist cannot authorize a merge.",
    },
  ];
}
