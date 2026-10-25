/** Read-only CSV for the isolated pilot's 8-layer × 40-assessment × 8-depth
 * independent review INVENTORY. It does not approve a source, compute a grade,
 * or assign any scientific or regulatory prediction. Fail closed on data drift.
 */
export type ScientificDepthMatrix = {
  nctId: string;
  layers: { id: string; assessments: string[] }[];
  verification: {
    required_assessments: 40;
    verified_assessments: 0;
    ready_for_analysis: false;
    scientific_score: null;
    approval_probability: null;
  };
  depthReview: {
    requiredTasks: 320;
    completedTasks: 0;
    depthLevels: { level: number; id: string; objective: string }[];
    tasks: {
      assessmentId: string;
      depthLevel: number;
      depthId: string;
      status: "pending_independent_review";
      independentlyVerified: false;
      scientificScore: null;
    }[];
    readyForScientificConclusion: false;
    approvalProbability: null;
  };
};

const HEADER = [
  "nct_id", "layer", "assessment", "depth_level", "depth", "review_objective",
  "review_status", "independently_verified", "scientific_score", "fda_approval_probability",
];

/** Quote every cell; escape spreadsheet formula prefixes even after whitespace. */
function csvCell(value: string | number): string {
  let safe = String(value);
  if (/^[\s\u0000-\u001f]*[=+\-@]/.test(safe)) safe = "'" + safe;
  return '"' + safe.replaceAll('"', '""') + '"';
}

/** Only eligible after the live API response passes the trial UI's validation.
 * Revalidate on export so a change to that UI cannot silently forge reviewed rows.
 */
export function buildScientificDepthReviewCsv(matrix: ScientificDepthMatrix): string {
  if (!matrix || !/^NCT[0-9]{8}$/.test(matrix.nctId)
      || matrix.verification?.required_assessments !== 40
      || matrix.verification.verified_assessments !== 0
      || matrix.verification.ready_for_analysis !== false
      || matrix.verification.scientific_score !== null
      || matrix.verification.approval_probability !== null
      || matrix.depthReview?.requiredTasks !== 320
      || matrix.depthReview.completedTasks !== 0
      || matrix.depthReview.readyForScientificConclusion !== false
      || matrix.depthReview.approvalProbability !== null
      || !Array.isArray(matrix.layers) || matrix.layers.length !== 8
      || !Array.isArray(matrix.depthReview.depthLevels)
      || matrix.depthReview.depthLevels.length !== 8
      || !Array.isArray(matrix.depthReview.tasks)
      || matrix.depthReview.tasks.length !== 320) {
    throw new Error("Scientific task export blocked: inventory is unverified or incomplete.");
  }
  const ids = new Set<string>();
  for (const layer of matrix.layers) {
    if (!/^[a-z][a-z0-9_]*$/.test(layer.id)
        || !Array.isArray(layer.assessments) || layer.assessments.length !== 5) {
      throw new Error("Scientific task export blocked: invalid assessment layer.");
    }
    for (const assessment of layer.assessments) {
      if (!/^[a-z][a-z0-9_]*$/.test(assessment)) {
        throw new Error("Scientific task export blocked: invalid assessment identifier.");
      }
      const id = layer.id + "." + assessment;
      if (ids.has(id)) throw new Error("Scientific task export blocked: duplicate assessment.");
      ids.add(id);
    }
  }
  if (ids.size !== 40 || !matrix.depthReview.depthLevels.every((depth, index) =>
    depth.level === index + 1
    && /^[a-z][a-z0-9_]*$/.test(depth.id)
    && typeof depth.objective === "string"
    && depth.objective.length > 0 && depth.objective.length <= 300
  )) {
    throw new Error("Scientific task export blocked: depth plan mismatch.");
  }
  const seen = new Set<string>();
  const rows: string[] = [HEADER.map(csvCell).join(",")];
  // Stable order: each of the 40 assessment definitions followed by depth 1–8.
  const byKey = new Map<string, ScientificDepthMatrix["depthReview"]["tasks"][number]>();
  for (const task of matrix.depthReview.tasks) {
    const key = task.assessmentId + ":" + task.depthLevel;
    if (!ids.has(task.assessmentId)
        || !Number.isInteger(task.depthLevel)
        || task.depthLevel < 1 || task.depthLevel > 8
        || task.depthId !== matrix.depthReview.depthLevels[task.depthLevel - 1].id
        || task.status !== "pending_independent_review"
        || task.independentlyVerified !== false
        || task.scientificScore !== null || seen.has(key)) {
      throw new Error("Scientific task export blocked: review status cannot be verified.");
    }
    seen.add(key);
    byKey.set(key, task);
  }
  if (seen.size !== 320) {
    throw new Error("Scientific task export blocked: depth reviews are missing.");
  }
  for (const layer of matrix.layers) for (const assessment of layer.assessments) {
    const assessmentId = layer.id + "." + assessment;
    for (const depth of matrix.depthReview.depthLevels) {
      const task = byKey.get(assessmentId + ":" + depth.level);
      if (!task) throw new Error("Scientific task export blocked: task crosswalk incomplete.");
      rows.push([
        matrix.nctId, layer.id, assessmentId, depth.level, depth.id, depth.objective,
        "PENDING_INDEPENDENT_REVIEW", "FALSE", "NOT_ASSIGNED", "NOT_ASSIGNED",
      ].map(csvCell).join(","));
    }
  }
  return rows.join("\r\n") + "\r\n";
}
