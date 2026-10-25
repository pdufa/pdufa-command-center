"use strict";
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
const Component = require("../app/ScientificAssessment.tsx").default;
const ID = "TRIAL|NCT02142738";
const success = () => ({
  connection: "connected",
  exactTrialIdentityMatched: true,
  archivedRecordPresent: true,
  independentScientificReview: "not_certified_by_connection_test",
  approvalProbability: null,
  scoresAssignedByConnectionTest: false,
});
const textOf = tree => JSON.stringify(tree.toJSON());

test("connection proxy protects session and uses only a fixed isolated source", () => {
  const route = fs.readFileSync(
    path.join(__dirname, "../app/api/scientific-assessment/connection/route.ts"), "utf8",
  );
  assert.match(route, /authConfigured\(\)/);
  assert.match(route, /hasSession\(/);
  assert.match(route, /\^TRIAL/);
  assert.match(route, /PDUFA_SCIENTIFIC_API_BASE_URL/);
  assert.doesNotMatch(route, /process\.env\.PDUFA_API_BASE_URL/);
  assert.match(route, /x-pdufa-internal-key/);
  assert.match(route, /private, no-store/);
  assert.match(route, /approvalProbability: null/);
  assert.match(route, /scoresAssignedByConnectionTest: false/);
  assert.doesNotMatch(route, /method:\s*"(POST|PUT|PATCH|DELETE)"|runScan\(|placeOrder\(/);
});

test("connection test is explicit and verifies only upstream identity, not clinical evidence", async () => {
  let view, original = global.fetch;
  const calls = [];
  global.fetch = async (url, options) => {
    calls.push({url, options});
    return { ok: true, status: 200, json: async () => success() };
  };
  try {
    await act(async () => { view = create(React.createElement(Component, { exactId: ID })); });
    assert.equal(calls.length, 0, "connection probe must not run automatically");
    assert.equal(view.root.findAllByType("button").length, 2);
    await act(async () => { await view.root.findAllByType("button")[1].props.onClick(); });
    assert.equal(calls.length, 1);
    assert.equal(calls[0].url, "/api/scientific-assessment/connection?exact_id=" + encodeURIComponent(ID));
    assert.equal(calls[0].options.cache, "no-store");
    const output = textOf(view);
    assert.match(output, /Connected to the isolated scientific API/);
    assert.match(output, /Archived registry source is present/);
    assert.match(output, /Independent scientific verification and FDA outcome prediction remain unavailable/);
    assert.doesNotMatch(output, /Scientific score: \d+/);
  } finally {
    if (view) await act(async () => view.unmount());
    global.fetch = original;
  }
});

test("failed isolated-service internal key cannot produce connected claim", async () => {
  let view, original = global.fetch;
  global.fetch = async () => ({ ok: false, status: 502 });
  try {
    await act(async () => { view = create(React.createElement(Component, { exactId: ID })); });
    await act(async () => { await view.root.findAllByType("button")[1].props.onClick(); });
    const output = textOf(view);
    assert.match(output, /Scientific API access key was rejected/);
    assert.doesNotMatch(output, /Connected to the isolated scientific API/);
  } finally {
    if (view) await act(async () => view.unmount());
    global.fetch = original;
  }
});

test("invalid identity and forged score state fail closed", async () => {
  let view, original = global.fetch;
  global.fetch = async () => ({
    ok: true, status: 200,
    json: async () => ({...success(),exactTrialIdentityMatched:false,approvalProbability:99}),
  });
  try {
    await act(async () => { view = create(React.createElement(Component, { exactId: ID })); });
    await act(async () => { await view.root.findAllByType("button")[1].props.onClick(); });
    assert.match(textOf(view), /response failed validation/);
    assert.doesNotMatch(textOf(view), /Connected to the isolated scientific API/);
  } finally {
    if (view) await act(async () => view.unmount());
    global.fetch = original;
  }
});

test("moving to another exact NCT clears previous connection assertion", async () => {
  let view, original = global.fetch;
  global.fetch = async () => ({ ok: true, status: 200, json: async () => success() });
  try {
    await act(async () => { view = create(React.createElement(Component, { exactId: ID })); });
    await act(async () => { await view.root.findAllByType("button")[1].props.onClick(); });
    assert.match(textOf(view), /Connected to the isolated scientific API/);
    await act(async () => {
      view.update(React.createElement(Component, { exactId: "TRIAL|NCT04280705" }));
    });
    assert.doesNotMatch(textOf(view), /Connected to the isolated scientific API/);
  } finally {
    if (view) await act(async () => view.unmount());
    global.fetch = original;
  }
});


test("malformed or unscoped trial IDs never enable or invoke scientific controls", async () => {
  const original = global.fetch;
  const calls = [];
  global.fetch = async (...args) => {
    calls.push(args);
    throw new Error("Unexpected request for invalid scientific identity");
  };
  try {
    for (const invalid of [
      "NCT02142738",
      "TRIAL\\BROKEN",
      "TRIAL|NCT0214273",
      "TRIAL|NCT02142738?unexpected=1",
    ]) {
      let view;
      try {
        await act(async () => {
          view = create(React.createElement(Component, { exactId: invalid }));
        });
        const buttons = view.root.findAllByType("button");
        assert.equal(buttons.length, 2);
        assert.ok(buttons.every(button => button.props.disabled === true),
          "Both scientific controls must be disabled for " + invalid);
        await act(async () => {
          for (const button of buttons) await button.props.onClick();
        });
        assert.equal(calls.length, 0);
      } finally {
        if (view) await act(async () => view.unmount());
      }
    }
  } finally {
    global.fetch = original;
  }
});
