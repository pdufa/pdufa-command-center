const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const ts = require("typescript");
for (const ext of [".ts", ".tsx"]) require.extensions[ext] = (m, file) => m._compile(ts.transpileModule(fs.readFileSync(file, "utf8"), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true }
}).outputText, file);
const lib = require("../lib/approved-drug-sales.ts");
const csv = fs.readFileSync(path.join(__dirname, "../../../data/approved_drug_sales_verified.csv"), "utf8");
const index = lib.buildSalesIndex(csv, "2026-10-22T19:00:00Z");
const { parseEvidenceCsv } = require("../lib/restriction-evidence.ts");
const records = parseEvidenceCsv(csv);
const toCsv = rows => [Object.keys(records[0]), ...rows.map(row => Object.keys(records[0]).map(key => row[key]))]
  .map(row => row.map(value => '"' + String(value).replaceAll('"', '""') + '"').join(",")).join("\n");
const React = require("react");
const { renderToStaticMarkup } = require("react-dom/server");
const { create, act } = require("react-test-renderer");
const Sales = require("../app/ApprovedDrugSales.tsx");
global.IS_REACT_ACT_ENVIRONMENT = true;

test("all saved sales records match only their issuer ticker, not a product or similar company", () => {
  assert.deepEqual(Object.keys(index.byTicker).sort(), ["ALNY", "BCRX", "VRTX"]);
  assert.equal(Object.values(index.byTicker).flat().length, 26);
  assert.equal(lib.companySales(index, " vrtx ").periods.flatMap(p => p.products).length, 10);
  assert.equal(lib.companySales(index, "BCRX").periods.flatMap(p => p.products).length, 4);
  assert.equal(lib.companySales(index, "ALNY").periods.flatMap(p => p.products).length, 12);
  for (const ticker of ["VRT", "TRIKAFTA", "AXSM", "Vertex Pharmaceuticals"]) assert.equal(lib.companySales(index, ticker).status, "not-recorded");
});

test("annual and half-year periods stay separate and repeated company figures are not summed", () => {
  const vertex = lib.companySales(index, "VRTX");
  assert.deepEqual(vertex.periods.map(p => p.period), ["H1 2026", "FY2025", "FY2024"]);
  assert.equal(vertex.periods[0].listedProductsSubtotal, 6047.8);
  assert.equal(vertex.periods[0].companyFigure, 6320.8);
  assert.equal(vertex.periods[1].listedProductsSubtotal, 11325.9);
  assert.equal(vertex.periods[1].companyFigure, 11970.6);
  const biocryst = lib.companySales(index, "BCRX").periods[0];
  assert.equal(biocryst.listedProductsSubtotal, 601.839);
  assert.equal(biocryst.companyFigure, 874.837);
  assert.match(biocryst.products[0].note, /license revenue/);
  assert.equal(lib.companySales(index, "ALNY").periods[0].listedProductsSubtotal, 2986.549);
});

test("equivalent period spellings cannot duplicate the same issuer/product disclosure", () => {
  assert.throws(() => lib.buildSalesIndex(toCsv([records[0], { ...records[0], period: "FY 2025" }]), "now"), /Duplicate/);
});

test("malformed, unsafe or ambiguous sales evidence fails rather than becoming zero revenue", () => {
  for (const change of [
    { individual_sales: "NaN" }, { individual_sales: "" }, { individual_sales: "-1" },
    { individual_sales: "1e3" }, { currency: "USD" }, { period: "2025" },
    { verified_on: "2026-02-31" }, { source_url: "https://www.sec.gov.evil.example/a" },
    { source_url: "https://user:pass@www.sec.gov/a" }, { source_url: "http://www.sec.gov/a" }
  ]) assert.throws(() => lib.buildSalesIndex(toCsv([{ ...records[0], ...change }]), "now"));
  assert.throws(() => lib.buildSalesIndex(toCsv([records[0], { ...records[1], company: "Other issuer" }]), "now"), /conflicting company/);
  const zero = lib.companySales(lib.buildSalesIndex(toCsv([{ ...records[0], individual_sales: "0" }]), "now"), "VRTX");
  assert.equal(zero.periods[0].listedProductsSubtotal, 0);
});

test("conflicting issuer totals are withheld while individual product disclosures remain visible", () => {
  const data = lib.companySales(lib.buildSalesIndex(toCsv([records[0], { ...records[1], company_net_sales: "1" }]), "now"), "VRTX");
  assert.equal(data.periods[0].companyFigure, null);
  assert.equal(data.periods[0].companyFigureConflict, true);
  const html = renderToStaticMarkup(React.createElement(Sales.SalesDisclosureView, { data }));
  assert.match(html, /Conflicting disclosures/);
  assert.match(html, /TRIKAFTA\/KAFTRIO/);
});

test("sales view changes reporting period without mixing years and preserves SEC links and revenue notes", async () => {
  let root;
  try {
    await act(async () => { root = create(React.createElement(Sales.SalesDisclosureView, { data: lib.companySales(index, "VRTX") })); });
    assert.match(JSON.stringify(root.toJSON()), /\$6,047.8 million/);
    await act(async () => root.root.findByType("select").props.onChange({ target: { value: "FY2025" } }));
    const html = JSON.stringify(root.toJSON());
    assert.match(html, /\$11,325.9 million/);
    assert.doesNotMatch(html, /\$6,047.8 million/);
    assert.equal(root.root.findAllByType("a").length, 4);
    assert.ok(root.root.findAllByType("a").every(a => a.props.href.startsWith("https://www.sec.gov/Archives/")));
  } finally { if (root) await act(async () => root.unmount()); }
});

test("missing sales are stated as not recorded, not no approved medicines or zero sales", () => {
  const html = renderToStaticMarkup(React.createElement(Sales.SalesDisclosureView, { data: lib.companySales(index, "AXSM") }));
  assert.match(html, /No approved-drug sales disclosures are saved for AXSM yet/);
  assert.doesNotMatch(html, /\$0|no approved products/i);
});

test("switching company cancels the previous request and never renders another issuer's figures", async () => {
  const originalFetch = global.fetch;
  const requests = [];
  global.fetch = (url, options) => new Promise(resolve => requests.push({ url, options, resolve }));
  let root;
  try {
    await act(async () => { root = create(React.createElement(Sales.default, { ticker: "VRTX" })); });
    await act(async () => root.update(React.createElement(Sales.default, { ticker: "BCRX" })));
    assert.equal(requests[0].options.signal.aborted, true);
    await act(async () => requests[0].resolve({ ok: true, json: async () => lib.companySales(index, "VRTX") }));
    assert.doesNotMatch(JSON.stringify(root.toJSON()), /TRIKAFTA|ALYFTREK/);
    await act(async () => requests[1].resolve({ ok: true, json: async () => lib.companySales(index, "BCRX") }));
    assert.match(JSON.stringify(root.toJSON()), /ORLADEYO/);
    assert.doesNotMatch(JSON.stringify(root.toJSON()), /TRIKAFTA|ALYFTREK/);
  } finally { if (root) await act(async () => root.unmount()); global.fetch = originalFetch; }
});

test("sales errors offer retry and do not imply that disclosures are absent", async () => {
  const originalFetch = global.fetch;
  let calls = 0, root;
  global.fetch = async () => { calls++; return calls === 1 ? { ok: false } : { ok: true, json: async () => lib.companySales(index, "BCRX") }; };
  try {
    await act(async () => { root = create(React.createElement(Sales.default, { ticker: "BCRX" })); });
    assert.match(JSON.stringify(root.toJSON()), /unavailable/);
    assert.doesNotMatch(JSON.stringify(root.toJSON()), /No approved-drug sales disclosures/);
    await act(async () => root.root.findByType("button").props.onClick());
    assert.match(JSON.stringify(root.toJSON()), /ORLADEYO/);
  } finally { if (root) await act(async () => root.unmount()); global.fetch = originalFetch; }
});

test("API requires the existing session, validates tickers and distinguishes missing records from source failures", async () => {
  const { NextRequest } = require("next/server");
  const auth = require("../lib/auth.ts");
  const route = require("../app/api/approved-drug-sales/route.ts");
  const previous = { password: process.env.DASHBOARD_PASSWORD, signing: process.env.SESSION_SIGNING_KEY, fetch: global.fetch };
  process.env.DASHBOARD_PASSWORD = "sales-test-password-only";
  process.env.SESSION_SIGNING_KEY = "sales-test-signing-key-not-for-production-123456";
  const cookie = auth.COOKIE_NAME + "=" + auth.makeSession();
  let calls = 0;
  global.fetch = async url => { calls++; assert.equal(url, lib.SALES_SOURCE_URL); return { ok: true, text: async () => csv }; };
  const request = (ticker, signed = true) => new NextRequest("http://localhost/api/approved-drug-sales?ticker=" + encodeURIComponent(ticker), { headers: signed ? { cookie } : {} });
  try {
    assert.equal((await route.GET(request("VRTX", false))).status, 401);
    assert.equal((await route.GET(request(""))).status, 400);
    assert.equal((await route.GET(request("../VRTX"))).status, 400);
    assert.equal(calls, 0);
    const available = await route.GET(request(" vrtx "));
    assert.equal(available.status, 200);
    assert.equal((await available.json()).periods[0].companyFigure, 6320.8);
    const missing = await route.GET(request("AXSM"));
    assert.equal(missing.status, 200);
    assert.equal((await missing.json()).status, "not-recorded");
    global.fetch = async () => ({ ok: false });
    assert.equal((await route.GET(request("VRTX"))).status, 503);
    global.fetch = async () => ({ ok: true, text: async () => "bad,ledger\nwrong,data" });
    assert.equal((await route.GET(request("VRTX"))).status, 503);
  } finally {
    global.fetch = previous.fetch;
    if (previous.password === undefined) delete process.env.DASHBOARD_PASSWORD; else process.env.DASHBOARD_PASSWORD = previous.password;
    if (previous.signing === undefined) delete process.env.SESSION_SIGNING_KEY; else process.env.SESSION_SIGNING_KEY = previous.signing;
  }
});
