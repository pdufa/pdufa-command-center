const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const taskText = fs.readFileSync(path.join(root, "app", "installation-audit", "master-build-tasks.ts"), "utf8");
const auditText = fs.readFileSync(path.join(root, "app", "api", "installation-audit", "live-task-evidence", "route.ts"), "utf8");
const progressText = fs.readFileSync(path.join(root, "app", "installation-audit", "MasterBuildProgress.tsx"), "utf8");
const registry = JSON.parse(fs.readFileSync(path.join(root, "public", "installation-audit", "task-evidence.json"), "utf8"));
const sections = [...taskText.matchAll(/^  \[([\s\S]*?)^  \],?/gm)]
  .map(match => [...match[1].matchAll(/^\s+"([^"]+)"/gm)].map(item => item[1]));
const catalog = new Map(sections.flatMap((tasks, i) => tasks.map((label, j) =>
  [String(i + 1).padStart(2, "0") + "-" + String(j + 1).padStart(3, "0"), label])));
const taskLinks = [...auditText.matchAll(/taskId:"(\d{2}-\d{3})",requirement:"([^"]+)"/g)]
  .map(match => ({id: match[1], label: match[2]}));

test("Master task inventory has 15 nonempty sections and unique task identifiers", () => {
  assert.equal(sections.length, 15);
  assert.equal(catalog.size, sections.reduce((n, tasks) => n + tasks.length, 0));
  for (const tasks of sections) assert.ok(tasks.length > 0);
});

test("Live audit links each operational observation to its exact requirement", () => {
  assert.ok(taskLinks.length >= 7);
  assert.equal(new Set(taskLinks.map(item => item.id)).size, taskLinks.length);
  for (const item of taskLinks) assert.equal(catalog.get(item.id), item.label,
    "Observation " + item.id + " has drifted from the master inventory");
  assert.match(auditText, /masterLabel===item\.requirement/);
  assert.match(auditText, /result:"mapping_error"/);
});

test("Verified registry entries have a dated, source-linked evidence record", () => {
  const tasks = registry.tasks || {};
  for (const [id, row] of Object.entries(tasks)) {
    assert.ok(catalog.has(id), "Unrecognized registry task " + id);
    if (row.status === "Verified") {
      assert.ok(Number.isFinite(Date.parse(row.checkedAt)), "Undated verified task " + id);
      assert.match(row.evidenceUrl, /^https:\/\//, "Missing evidence URL for " + id);
    }
  }
});

test("Live connectivity and prediction safety observations cannot silently certify tasks", () => {
  assert.match(auditText, /automatedAcceptanceCoverage:0/);
  assert.match(auditText, /body\.decision==="ABSTAIN"/);
  assert.match(auditText, /body\.validated_decision_available===false/);
  assert.match(auditText, /body\.adjudication_status==="NOT_ADJUDICATED"/);
  assert.match(auditText, /observations:mappedObservations/);
  assert.match(progressText, /Unverified does not mean unfinished/);
  assert.match(progressText, /not acceptance/);
});
