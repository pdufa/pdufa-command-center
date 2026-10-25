const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const ts = require("typescript");
const React = require("react");
const { act, create } = require("react-test-renderer");
global.IS_REACT_ACT_ENVIRONMENT = true;

for (const ext of [".ts", ".tsx"]) {
  require.extensions[ext] = (mod, file) => mod._compile(
    ts.transpileModule(fs.readFileSync(file, "utf8"), {
      compilerOptions: {
        module: ts.ModuleKind.CommonJS,
        target: ts.ScriptTarget.ES2022,
        jsx: ts.JsxEmit.ReactJSX,
        esModuleInterop: true,
      },
    }).outputText, file,
  );
}
require.extensions[".css"] = mod => {
  mod.exports = new Proxy({}, { get: (_, key) => String(key) });
};

const {
  ARCHIVE_DOMAINS, ARCHIVE_NCT_PATTERN, isExactArchivedDossier,
  summarizeArchivedValue,
} = require("../lib/archived-science-dossier.ts");
const { default: TrialScienceArchive } = require("../app/TrialScienceArchive.tsx");

const P = "NCT02142738";
const Q = "NCT04280705";

function dossier(id = P) {
  const url = "https://clinicaltrials.gov/study/" + id;
  const clinical = [
    {
      field: "allocation",
      reported_value: "RANDOMIZED",
      source_url: url,
      source_locator: "protocolSection.designModule.designInfo.allocation",
      verification_status: "source_record_only",
      scientifically_verified: false,
    },
    {
      field: "primary_outcomes",
      reported_value: [{ measure: "Overall survival", timeFrame: "Until end of study" }],
      source_url: url,
      source_locator: "protocolSection.outcomesModule.primaryOutcomes",
      verification_status: "source_record_only",
      scientifically_verified: false,
    },
  ];
  return {
    model_version: "trial-science-dossier-v1",
    exact_program_id: "TRIAL|" + id,
    nct_id: id,
    source_url: url,
    source_sha256: "c".repeat(64),
    source_fetched_at: "2026-10-24T12:00:00+00:00",
    assessment_status: "incomplete",
    domains: Object.fromEntries(ARCHIVE_DOMAINS.map(name => [name, {
      status: name === "clinical_design" ? "source_record_only" : "not_assessed",
      claims: name === "clinical_design" ? clinical : [],
      score: null,
    }])),
    overall_score: null,
    fda_approval_probability: null,
    read_only: true,
    note: "Protocol metadata only; independent review not completed.",
  };
}

test("both archived trial identities are supported with eight unscored domains", () => {
  assert.equal(ARCHIVE_DOMAINS.length, 8);
  assert.ok(ARCHIVE_NCT_PATTERN.test(P));
  assert.ok(ARCHIVE_NCT_PATTERN.test(Q));
  assert.equal(isExactArchivedDossier(dossier(P), P), true);
  assert.equal(isExactArchivedDossier(dossier(Q), Q), true);
  assert.equal(isExactArchivedDossier(dossier(Q), P), false);
  assert.equal(isExactArchivedDossier(dossier(P), Q), false);
});

test("rejects swapped claims, any scores, extra domains and false verification", () => {
  const changes = [
    x => { x.model_version = "unknown"; },
    x => { x.exact_program_id = "TRIAL|NCT87654321"; },
    x => { x.nct_id = Q; },
    x => { x.source_url = "https://example.com/malicious"; },
    x => { x.source_sha256 = "tampered"; },
    x => { x.domains.advanced_inference.score = 99; },
    x => { x.domains.clinical_results.claims.push({...x.domains.clinical_design.claims[0]}); },
    x => { x.domains.clinical_design.claims[0].scientifically_verified = true; },
    x => { x.domains.clinical_design.claims[0].verification_status = "verified"; },
    x => { x.domains.clinical_design.claims[0].source_url = "https://attacker.invalid"; },
    x => { x.domains.clinical_design.claims[0].source_locator = "unrelated"; },
    x => { x.domains.clinical_design.claims[0].reported_value = "A".repeat(61000); },
    x => { x.domains.clinical_design.claims.push({...x.domains.clinical_design.claims[0]}); },
    x => { x.fda_approval_probability = 0.8; },
    x => { x.overall_score = 0; },
    x => { x.read_only = false; },
    x => { x.source_fetched_at = "invalid"; },
    x => { delete x.domains.regulatory_analysis; },
  ];
  for (const edit of changes) {
    const changed = structuredClone(dossier());
    edit(changed);
    assert.equal(isExactArchivedDossier(changed, P), false, String(edit));
  }
});

test("unassessed registry entries remain honest, not filled with invented evidence", () => {
  const item = dossier(Q);
  item.domains.clinical_design.claims = [];
  item.domains.clinical_design.status = "not_assessed";
  assert.equal(isExactArchivedDossier(item, Q), true);
  assert.equal(item.domains.clinical_results.score, null);
  assert.equal(item.domains.regulatory_analysis.claims.length, 0);
  assert.equal(summarizeArchivedValue({ primaryOutcome: "PFS" }), '{"primaryOutcome":"PFS"}');
  assert.equal(summarizeArchivedValue("X".repeat(2000)).length, 420);
});

test("next proxy enforces login and exact-NCT identity and never writes", () => {
  const route = fs.readFileSync(path.join(__dirname,
    "../app/api/scientific-assessment/archived/[nctId]/route.ts"), "utf8");
  assert.match(route, /authConfigured\(\)/);
  assert.match(route, /hasSession\(/);
  assert.match(route, /ARCHIVE_NCT_PATTERN\.test\(nctId\)/);
  assert.match(route, /isExactArchivedDossier\(data, nctId\)/);
  assert.match(route, /Cache-Control.*private, no-store/);
  assert.match(route, /encodeURIComponent\(exactId\)/);
  assert.doesNotMatch(route, /method:\s*"(?:POST|PUT|DELETE)"|runScan\(|placeOrder\(/);
  const sheet = fs.readFileSync(path.join(__dirname,
    "../app/trial/[nctId]/page.tsx"), "utf8");
  assert.match(sheet, /<TrialScienceArchive nctId=\{nct\} \/>/);
  assert.match(sheet, /nct === PILOT_NCT && <TrialSciencePilot \/>/);
  const home = fs.readFileSync(path.join(__dirname, "../app/page.tsx"), "utf8");
  assert.match(home, /href="\/trial\/NCT02142738"/);
  assert.match(home, /href="\/trial\/NCT04280705"/);
});

test("one selected archived record loads on explicit click, without bulk fetch", async () => {
  const prev = global.fetch;
  const calls = [];
  let view;
  try {
    global.fetch = async (url, options) => {
      calls.push({url, options});
      return { ok: true, status: 200, json: async () => dossier(Q) };
    };
    await act(async () => { view = create(React.createElement(TrialScienceArchive, { nctId: Q })); });
    assert.equal(calls.length, 0);
    await act(async () => { view.root.findByType("button").props.onClick(); });
    assert.equal(calls.length, 1);
    assert.equal(calls[0].url, "/api/scientific-assessment/archived/" + Q);
    assert.equal(calls[0].options.cache, "no-store");
    const out = JSON.stringify(view.toJSON());
    assert.match(out, /NCT04280705/);
    assert.match(out, /Registered primary outcomes/);
    assert.match(out, /Overall survival/);
    assert.match(out, /Mechanism of action/);
    assert.match(out, /score not assigned/);
    assert.match(out, /Scientific assessment incomplete/);
    assert.doesNotMatch(out, /FDA approval probability: [0-9]/);
  } finally {
    if (view) await act(async () => view.unmount());
    global.fetch = prev;
  }
});

test("unarchived 404 is explicit missing evidence, not a negative scientific finding", async () => {
  const prev = global.fetch;
  let view;
  try {
    global.fetch = async () => ({ ok: false, status: 404 });
    await act(async () => { view = create(React.createElement(TrialScienceArchive, { nctId: P })); });
    await act(async () => { view.root.findByType("button").props.onClick(); });
    const out = JSON.stringify(view.toJSON());
    assert.match(out, /has not been imported into the scientific archive/);
    assert.doesNotMatch(out, /Registered primary outcomes/);
  } finally {
    if (view) await act(async () => view.unmount());
    global.fetch = prev;
  }
});

test("cross-trial response is refused rather than displayed under the selected NCT", async () => {
  const prev = global.fetch;
  let view;
  try {
    global.fetch = async () => ({ ok: true, status: 200, json: async () => dossier(P) });
    await act(async () => { view = create(React.createElement(TrialScienceArchive, { nctId: Q })); });
    await act(async () => { view.root.findByType("button").props.onClick(); });
    const out = JSON.stringify(view.toJSON());
    assert.match(out, /Trial identity or source provenance failed validation/);
    assert.doesNotMatch(out, /Registered primary outcomes/);
  } finally {
    if (view) await act(async () => view.unmount());
    global.fetch = prev;
  }
});

test("changing exact trial clears previous results before new evidence is loaded", async () => {
  const prev = global.fetch;
  let view;
  try {
    global.fetch = async () => ({ ok: true, status: 200, json: async () => dossier(P) });
    await act(async () => { view = create(React.createElement(TrialScienceArchive, { nctId: P })); });
    await act(async () => { view.root.findByType("button").props.onClick(); });
    assert.match(JSON.stringify(view.toJSON()), /Registered primary outcomes/);
    await act(async () => { view.update(React.createElement(TrialScienceArchive, { nctId: Q })); });
    assert.doesNotMatch(JSON.stringify(view.toJSON()), /Registered primary outcomes/);
    assert.match(JSON.stringify(view.toJSON()), /NCT04280705/);
  } finally {
    if (view) await act(async () => view.unmount());
    global.fetch = prev;
  }
});
