const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const source = path.resolve(__dirname, "../app/medical-intelligence-preview");
const page = fs.readFileSync(path.join(source, "page.tsx"), "utf8");
const control = fs.readFileSync(path.join(source, "ContinuousMedicalAnalysis.tsx"), "utf8");
const proxy = fs.readFileSync(path.resolve(__dirname, "../app/api/medical-intelligence-preview/continuous/route.ts"), "utf8");

test("mounting main medical page loads the continuous panel without starting a job", () => {
  assert.match(page, /<ContinuousMedicalAnalysis/);
  assert.doesNotMatch(page, /getRegistryStudy|await\s+fetch\s*\(/);
  assert.match(control, /onClick=\{\(\) => void action\("start"\)\}/);
  assert.match(control, /if \(run\?\.status !== "RUNNING"/);
  assert.match(control, /void refresh\(undefined, true\)/);
  assert.doesNotMatch(control, /useEffect\(\(\) => \{\s*void action\("start"\)/);
});
test("operator sees stage details, stops and resumes without restarting", () => {
  assert.match(control, /Run All 12 Stages/);
  assert.match(control, /Stop after current stage/);
  assert.match(control, /Resume saved run/);
  assert.match(control, /run\.stages\.map/);
  assert.match(control, /completedStages/);
  assert.match(control, /ABSTAIN/);
  assert.match(control, /not/);
});
test("persistent operations are protected by session and same-origin write", () => {
  assert.match(proxy, /hasSession/);
  assert.match(proxy, /export async function GET/);
  assert.match(proxy, /export async function POST/);
  assert.match(proxy, /req\.headers\.get\("origin"\) !== req\.nextUrl\.origin/);
  assert.match(proxy, /focus\.records\.some/);
  assert.match(proxy, /PDUFA_API_BASE_URL/);
  assert.match(proxy, /PDUFA_INTERNAL_API_KEY/);
  assert.match(proxy, /private, no-store/);
});
