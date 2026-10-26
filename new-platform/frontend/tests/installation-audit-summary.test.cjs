const {test} = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const ts = require("typescript");

// Load the tracker calculator without requiring a Next.js server or credentials.
require.extensions[".ts"] = (module, file) => module._compile(
  ts.transpileModule(fs.readFileSync(file, "utf8"), {
    compilerOptions: {module:ts.ModuleKind.CommonJS, target:ts.ScriptTarget.ES2022},
  }).outputText, file
);
const {summarizeInstallationAudit, isAccepted, AUDIT_GROUPS} =
  require("../lib/installation-audit-summary.ts");

const source = fs.readFileSync(require("node:path").join(__dirname, "../app/installation-audit/page.tsx"), "utf8");
const checkLines = source.split("\n").filter(line => line.includes('  { component: "'));
function field(line, name) {
  const match = line.match(new RegExp(name + ': "([^"]+)"'));
  assert.ok(match, "Missing " + name + " in tracker row");
  return match[1];
}
const items = checkLines.map(line => ({
  component:field(line,"component"), code:field(line,"code"),
  deployment:field(line,"deployment"), runtime:field(line,"runtime"),
  evidence:field(line,"evidence"),
}));

test("all 15 committed acceptance sections are assigned exactly once to three workstreams", () => {
  assert.equal(AUDIT_GROUPS.length,3);
  assert.equal(items.length,15);
  const report = summarizeInstallationAudit(items);
  assert.deepEqual(report.groups.map(x=>x.items.length),[8,4,3]);
  assert.equal(report.total.sections,15);
  assert.equal(new Set(items.map(x=>x.component)).size,15);
});

test("published snapshot counts partial, implementation and unknown proof separately", () => {
  const {total,groups} = summarizeInstallationAudit(items);
  assert.equal(total.gates,59);
  assert.equal(total.excluded,1);
  assert.equal(total.implementationSignals,10);
  assert.equal(total.partial,7);
  assert.equal(total.unverified,42);
  assert.equal(total.independentlyVerified,0);
  assert.equal(total.accepted,0);
  assert.equal(total.gates, total.implementationSignals+total.partial+total.unverified+total.independentlyVerified);
  assert.equal(groups.reduce((n,g)=>n+g.totals.gates,0),59);
});

test("code, preview, and partial runtime do not produce false scientific or system acceptance", () => {
  for (const item of items) assert.equal(isAccepted(item),false,item.component);
  const qualified = items.map(item => ({
    ...item, code:"Code present", deployment:"Preview READY",
    runtime:"Verified", evidence:"Verified",
  }));
  assert.equal(summarizeInstallationAudit(qualified).total.accepted,15);
  assert.equal(isAccepted({...qualified[0],runtime:"Partial"}),false);
  assert.equal(isAccepted({...qualified[0],evidence:"Not verified"}),false);
});

test("missing, extra or duplicate acceptance work is rejected rather than silently undercounted", () => {
  assert.throws(()=>summarizeInstallationAudit(items.slice(1)),/Missing/);
  assert.throws(()=>summarizeInstallationAudit([...items,items[0]]),/Duplicate/);
  assert.throws(()=>summarizeInstallationAudit([...items,{...items[0],component:"Unclassified"}]),/Unclassified/);
});
