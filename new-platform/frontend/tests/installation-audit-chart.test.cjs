const {test} = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const ts = require("typescript");

require.extensions[".ts"] = (module, file) => module._compile(ts.transpileModule(
  fs.readFileSync(file, "utf8"),
  {compilerOptions: {module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022}},
).outputText, file);

const {summarizeInstallationAudit, isAccepted} = require("../lib/installation-audit-summary.ts");
const {AUDIT_BASELINE, compareAuditToBaseline} = require("../lib/installation-audit-history.ts");

const page = fs.readFileSync(path.join(__dirname,"../app/installation-audit/page.tsx"),"utf8");
const chart = fs.readFileSync(path.join(__dirname,"../app/installation-audit/InstallationProgressChart.tsx"),"utf8");
const items = page.split("\n").filter(line=>line.includes('  { component: "')).map(line=>{
  const fields={};
  for(const key of ["component","code","deployment","runtime","evidence"]){
    const match=line.match(new RegExp(key+': "([^"]+)"'));
    assert.ok(match,"missing "+key);
    fields[key]=match[1];
  }
  return fields;
});

test("chart uses actual audit rows, not a second hand-entered completion counter",()=>{
  assert.match(page,/import InstallationProgressChart from "\.\/InstallationProgressChart"/);
  assert.match(page,/<InstallationProgressChart groups=\{groups\} total=\{total\} \/>/);
  assert.match(chart,/compareAuditToBaseline\(groups, total\)/);
  assert.match(chart,/groups\.map\(/);
  assert.match(chart,/total\.accepted/);
  assert.match(chart,/role="img"/);
  assert.doesNotMatch(chart,/\bfetch\(|\bonClick=|\bonSubmit=|\buseEffect\(/);
});

test("current 15 requirements reconcile to every one of 59 applicable gates",()=>{
  const {groups,total}=summarizeInstallationAudit(items);
  assert.equal(total.sections,15);
  assert.equal(total.gates,59);
  assert.equal(total.excluded,1);
  assert.equal(total.accepted,0);
  assert.equal(total.independentlyVerified,2);
  assert.equal(total.implementationSignals,9);
  assert.equal(total.partial,10);
  assert.equal(total.unverified,38);
  assert.deepEqual(groups.map(g=>({
    name:g.name,
    sections:g.totals.sections,
    gates:g.totals.gates,
    code:g.totals.implementationSignals,
    partial:g.totals.partial,
    unknown:g.totals.unverified,
    accepted:g.totals.accepted,
  })),[
    {name:"Core Platform",sections:8,gates:31,code:6,partial:6,unknown:17,accepted:0},
    {name:"Scientific Assessment & Prediction",sections:4,gates:16,code:1,partial:2,unknown:13,accepted:0},
    {name:"Production Automation",sections:3,gates:12,code:2,partial:2,unknown:8,accepted:0},
  ]);
  assert.equal(groups.reduce((sum,g)=>sum+g.totals.gates,0),total.gates);
  for(const item of items) assert.equal(isAccepted(item),false);
});

test("historical snapshot stays pinned and its old mixed-scope criteria cannot produce a current delta",()=>{
  assert.equal(AUDIT_BASELINE.commit,"062ea740922d767148bc99565c4af43bd6eb43fa");
  assert.equal(AUDIT_BASELINE.total.gates,59);
  assert.equal(AUDIT_BASELINE.total.sections,15);
  assert.equal(AUDIT_BASELINE.total.accepted,0);
  assert.equal(AUDIT_BASELINE.total.implementationSignals,10);
  assert.equal(AUDIT_BASELINE.total.partial,7);
  assert.equal(AUDIT_BASELINE.total.unverified,42);
  assert.equal(AUDIT_BASELINE.groups.reduce((n,g)=>n+g.gates,0),59);
  assert.equal(AUDIT_BASELINE.groups.reduce((n,g)=>n+g.partial,0),7);
  assert.equal(AUDIT_BASELINE.groups.reduce((n,g)=>n+g.unverified,0),42);
  const {groups,total}=summarizeInstallationAudit(items);
  assert.equal(compareAuditToBaseline(groups,total),null);
});

test("scope drift or unreconciled counts suppress historical comparison",()=>{
  const {groups,total}=summarizeInstallationAudit(items);
  assert.equal(compareAuditToBaseline(groups,{...total,gates:60}),null);
  assert.equal(compareAuditToBaseline(groups,{...total,sections:16}),null);
  assert.equal(compareAuditToBaseline(groups,{...total,excluded:2}),null);
  assert.equal(compareAuditToBaseline(groups,{...total,unverified:39}),null);
  assert.equal(compareAuditToBaseline(groups.slice(1),total),null);
  assert.equal(compareAuditToBaseline([{...groups[0],totals:{...groups[0].totals,gates:30}},...groups.slice(1)],total),null);
});

test("a successful code signal or preview build never becomes a completed requirement",()=>{
  const current=items[0];
  assert.equal(current.code,"Code present");
  assert.equal(current.deployment,"Verified");
  assert.equal(current.runtime,"Partial");
  assert.equal(isAccepted(current),false);
  assert.match(chart,/not.*completed scientific or runtime requirement/);
  assert.match(chart,/not yet verified\/audited/);
  assert.match(chart,/not.*measure of engineering hours remaining/);
});
