/**
 * Separate EMPTY reviewer A/B handoffs for the full 800-method scientific plan.
 *
 * These are editable human-review templates only, not submitted or authenticated
 * scientific evidence. The existing 320-task A/B review and local audit remain
 * independent and unchanged. Nothing is saved to the backend.
 */
import { buildScientific800ReviewCsv } from "./scientific-800-review-csv";
import { buildScientific800EvidenceMap } from "./scientific-800-evidence-map";
import type { ScientificDepthMatrix } from "./scientific-depth-review-csv";
import type { ScientificInputAudit } from "./scientific-evidence-requirements-csv";

function cell(value: string | number): string {
  let safe = String(value).replace(/[\u0000-\u001f\u007f]+/g, " ");
  if (/^\s*[=+\-@]/u.test(safe)) safe = "'" + safe;
  return '"' + safe.replaceAll('"', '""') + '"';
}

/**
 * Revalidate both the complete 40×8 existing archive handoff and the 16
 * exact-NCT evidence-input gates before generating a 40×20 reviewer template.
 *
 * The A/B slots are identifiers for two different *future* qualified people.
 * Blank names, source bytes, and signatures MUST NOT be treated as signoff.
 */
export function buildScientific800ReviewerHandoffCsv(
  matrix: ScientificDepthMatrix,
  audit: ScientificInputAudit,
  reviewerSlot: "A" | "B",
): string {
  if (reviewerSlot !== "A" && reviewerSlot !== "B") {
    throw new Error("Scientific 800 reviewer export blocked: invalid reviewer slot.");
  }

  const map = buildScientific800EvidenceMap(matrix, audit);
  const baseCsv = buildScientific800ReviewCsv(matrix);
  if (!baseCsv.endsWith("\r\n") || map.totalPendingTasks !== 800
      || map.layers.length !== 8 || map.nctId !== matrix.nctId) {
    throw new Error("Scientific 800 reviewer export blocked: invalid source inventory.");
  }
  const baseLines = baseCsv.slice(0, -2).split("\r\n");
  if (baseLines.length !== 801) {
    throw new Error("Scientific 800 reviewer export blocked: incomplete task rows.");
  }

  const appended = [
    "reviewer_slot", "linked_requirement_ids", "linked_archive_inputs_present",
    "linked_requirements_total", "reviewer_name", "qualification_verified",
    "original_document_url", "original_document_sha256", "document_public_date",
    "document_section_or_table", "source_bytes_verified", "review_finding_notes",
    "reviewer_decision", "reviewer_signature", "submission_status",
  ];

  const header = baseLines[0] + "," + appended.map(cell).join(",");
  const rows: string[] = [header];

  for (let taskIndex = 0; taskIndex < 800; taskIndex++) {
    // The validated base generator emits 100 task rows per source layer:
    // five assessments, each repeated across 20 distinct methodology depths.
    const layer = map.layers[Math.floor(taskIndex / 100)];
    if (!layer || layer.pendingTasks !== 100 || layer.assessmentIds.length !== 5
        || layer.independentlyReviewedTasks !== 0
        || layer.dependencies.length !== layer.sourceInputsRequired) {
      throw new Error("Scientific 800 reviewer export blocked: layer/task mismatch.");
    }
    const fields = [
      reviewerSlot,
      layer.dependencies.map(r => r.id).join(";"),
      layer.sourceInputsPresent,
      layer.sourceInputsRequired,
      "", "NOT_VERIFIED", "", "", "", "", "NOT_VERIFIED", "",
      "NOT_SUBMITTED", "", "NOT_SUBMITTED",
    ];
    rows.push(baseLines[taskIndex + 1] + "," + fields.map(cell).join(","));
  }
  if (rows.length !== 801) {
    throw new Error("Scientific 800 reviewer export blocked: wrong output count.");
  }
  return rows.join("\r\n") + "\r\n";
}
