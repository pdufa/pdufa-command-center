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
  require.extensions[ext] = (mod, filename) => mod._compile(
    ts.transpileModule(fs.readFileSync(filename, "utf8"), {
      compilerOptions: {
        module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022,
        jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true,
      },
    }).outputText, filename,
  );
}
const Component = require("../app/ScientificAssessment.tsx").default;
const { buildScientificSourceReviewHandoff } =
  require("../lib/scientific-captured-archive-check.ts");
const NCT = "NCT02142738";
const route = "/api/scientific-assessment/captured-source-manifest?nct_id=NCT02142738";
const makeDoc = (char, gateId) => ({
  documentId: char.repeat(32), gateId, sourceType: "official_agency_document",
  sha256: char.repeat(64), byteLength: 107,
  captureStatus: "byte_integrity_checked_unverified",
  scientificVerificationComplete: false,
});
const manifest = (...documents) => ({
  nctId: NCT, sourceDocumentCount: documents.length,
  allCapturedBytesRehashed: true, independentSourceVerificationCompleted: false,
  scientificScore: null, fdaApprovalProbability: null, documents,
});
const saved = (data) => buildScientificSourceReviewHandoff(NCT, data);
const stringify = view => JSON.stringify(view.toJSON());
const getInput = (view, label) => view.root.findAllByType("input")
  .find(node => node.props["aria-label"] === label);
const getButton = (view, text) => view.root.findAllByType("button")
  .find(node => JSON.stringify(node.props.children).includes(text));

test("saved handoff is compared to NEW authenticated rehashed manifest, not ordinary dashboard", async () => {
  let view;
  const original = global.fetch;
  const calls = [];
  const prior = manifest(makeDoc("a", "protocol_sap"));
  const fresh = manifest(makeDoc("a", "protocol_sap"), makeDoc("b", "official_regulatory"));
  global.fetch = async (url, options) => {
    calls.push({url, options});
    return { ok: true, status: 200, json: async () => fresh };
  };
  try {
    await act(async () => {
      view = create(React.createElement(Component, { exactId: "TRIAL|" + NCT }));
    });
    assert.equal(calls.length, 0, "No automatic source archive network request");
    await act(async () => {
      getInput(view, "Choose earlier four-gate source handoff").props.onChange({
        target: { files: [{ size: 2500, text: async () => saved(prior) }] },
      });
    });
    const liveBtn = getButton(view, "Compare saved handoff to LIVE captured archive");
    assert.ok(liveBtn && !liveBtn.props.disabled);
    await act(async () => { await liveBtn.props.onClick(); });
    assert.equal(calls.length, 1);
    assert.equal(calls[0].url, route);
    assert.equal(calls[0].options.cache, "no-store");
    assert.equal(calls[0].options.body, undefined);
    const output = stringify(view);
    assert.match(output, /Authenticated live captured archive comparison/);
    assert.match(output, /CAPTURED INVENTORY CHANGED/);
    assert.match(output, /Saved captured PDFs:/);
    assert.match(output, /live captured PDFs:/);
    assert.match(output, /Original source authenticated: NO/);
    assert.match(output, /FDA approval probability: NOT ASSIGNED/);
    await act(async () => {
      view.update(React.createElement(Component, { exactId: "TRIAL|NCT00000001" }));
    });
    assert.doesNotMatch(stringify(view), /Saved captured PDFs:/);
  } finally {
    if (view) await act(async () => view.unmount());
    global.fetch = original;
  }
});

test("denied upstream cannot present a false no-change result or scientific verification", async () => {
  let view;
  const original = global.fetch;
  const calls = [];
  global.fetch = async (url, options) => {
    calls.push({url, options});
    return { ok: false, status: 401, json: async () => ({ error: "session expired" }) };
  };
  try {
    await act(async () => {
      view = create(React.createElement(Component, { exactId: "TRIAL|" + NCT }));
    });
    await act(async () => {
      getInput(view, "Choose earlier four-gate source handoff").props.onChange({
        target: { files: [{ size: 2000, text: async () => saved(manifest()) }] },
      });
    });
    await act(async () => {
      await getButton(view, "Compare saved handoff to LIVE captured archive").props.onClick();
    });
    assert.equal(calls.length, 1);
    assert.equal(calls[0].url, route);
    assert.match(stringify(view), /Live archive comparison BLOCKED/);
    assert.doesNotMatch(stringify(view), /NO REPORTED CHANGE/);
    assert.doesNotMatch(stringify(view), /Authenticated live captured archive comparison/);
  } finally {
    if (view) await act(async () => view.unmount());
    global.fetch = original;
  }
});

test("saved JSON never uploaded; no secret fallback or medical-grade promotion calls", () => {
  const source = fs.readFileSync(path.join(__dirname, "../app/ScientificAssessment.tsx"), "utf8");
  const body = source.slice(source.indexOf("async function compareSavedHandoffToLiveArchive()"),
    source.indexOf("  /** On-demand read-only pinned archive metadata", source.indexOf("async function compareSavedHandoffToLiveArchive()")));
  assert.match(body, /earlierHandoffFile\.text\(\)/);
  assert.match(body, /cache: "no-store"/);
  assert.match(body, /buildScientificSourceReviewHandoff\("NCT02142738", liveManifest\)/);
  assert.match(body, /compareFourGateSourceHandoffs\(saved, liveHandoff\)/);
  assert.match(body, /if \(!response\.ok\) throw/);
  assert.doesNotMatch(body, /method: "POST"|PDUFA_API_BASE_URL|upload|saveToDatabase|approve/);
});
