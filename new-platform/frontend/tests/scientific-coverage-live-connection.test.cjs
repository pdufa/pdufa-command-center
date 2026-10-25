"use strict";
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const Module = require("node:module");
const ts = require("typescript");
const React = require("react");
const { act, create } = require("react-test-renderer");
global.IS_REACT_ACT_ENVIRONMENT = true;

require.extensions[".tsx"] = (mod, file) => mod._compile(
  ts.transpileModule(fs.readFileSync(file, "utf8"), {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2022,
      jsx: ts.JsxEmit.ReactJSX,
      esModuleInterop: true,
    },
  }).outputText, file,
);
const originalLoad = Module._load;
let Page;
try {
  Module._load = function(request, parent, isMain) {
    if (request === "next/link") return function TestLink(props) {
      return React.createElement("a", { href: props.href }, props.children);
    };
    return originalLoad.call(this, request, parent, isMain);
  };
  Page = require("../app/science/coverage/page.tsx").default;
} finally {
  Module._load = originalLoad;
}

const PILOT_ID = "TRIAL|NCT02142738";
const url = "/api/scientific-assessment/connection?exact_id=" + encodeURIComponent(PILOT_ID);
const connected = () => ({
  connection: "connected",
  exactTrialIdentityMatched: true,
  archivedRecordPresent: true,
  independentScientificReview: "not_certified_by_connection_test",
  approvalProbability: null,
  scoresAssignedByConnectionTest: false,
});
const output = view => JSON.stringify(view.toJSON());

async function mount() {
  let view;
  await act(async () => { view = create(React.createElement(Page)); });
  return view;
}

async function verify(view) {
  const buttons = view.root.findAllByType("button");
  const button = buttons.find(b => output(view).includes("Verify isolated scientific API (pilot)")
    && JSON.stringify(b.props.children).includes("Verify isolated scientific API"));
  assert.ok(button, "explicit scientific connection button is visible");
  await act(async () => {
    button.props.onClick();
    await new Promise(resolve => setImmediate(resolve));
  });
}

test("no automatic GET, explicit connection only, never a science score", async () => {
  const before = global.fetch, calls = [];
  global.fetch = async (requestUrl, options) => {
    calls.push({ requestUrl, options });
    return { status: 200, ok: true, json: async () => connected() };
  };
  let view;
  try {
    view = await mount();
    assert.equal(calls.length, 0, "neither coverage nor connection may auto-fetch");
    await verify(view);
    assert.equal(calls.length, 1);
    assert.equal(calls[0].requestUrl, url);
    assert.equal(calls[0].options.cache, "no-store");
    assert.equal(calls[0].options.method, undefined, "read-only GET");
    assert.match(output(view), /CONNECTED: preview authenticated/);
    assert.match(output(view), /Independent scientific evidence and FDA outcome prediction remain UNVERIFIED/);
    assert.doesNotMatch(output(view), /approvalProbability":\s*[0-9]/);
  } finally {
    if (view) await act(async () => view.unmount());
    global.fetch = before;
  }
});

test("a rejected Render credential does not imply successful connection", async () => {
  const before = global.fetch;
  global.fetch = async () => ({ status: 502, ok: false });
  let view;
  try {
    view = await mount();
    await verify(view);
    assert.match(output(view), /rejected the preview access key/);
    assert.doesNotMatch(output(view), /CONNECTED: preview authenticated/);
  } finally {
    if (view) await act(async () => view.unmount());
    global.fetch = before;
  }
});

test("forged positive approval or missing independent-review caution fails closed", async () => {
  const before = global.fetch;
  global.fetch = async () => ({
    status: 200,
    ok: true,
    json: async () => ({ ...connected(), approvalProbability: 97 }),
  });
  let view;
  try {
    view = await mount();
    await verify(view);
    assert.match(output(view), /Scientific connection response failed validation/);
    assert.doesNotMatch(output(view), /CONNECTED: preview authenticated/);
  } finally {
    if (view) await act(async () => view.unmount());
    global.fetch = before;
  }
});

test("new portal cannot call a source-write or ordinary non-scientific API route", () => {
  const source = fs.readFileSync(path.join(__dirname, "../app/science/coverage/page.tsx"), "utf8");
  assert.match(source, /\/api\/scientific-assessment\/connection\?exact_id=/);
  assert.match(source, /PILOT_EXACT_ID = "TRIAL\|NCT02142738"/);
  assert.doesNotMatch(source, /startBatchImport\(|runScan\(|placeOrder\(|\/api\/scientific-assessment\/review-submission/);
  assert.match(source, /independentScientificReview !== "not_certified_by_connection_test"/);
  assert.match(source, /approvalProbability !== null/);
});
