const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const ts = require("typescript");
for (const extension of [".ts", ".tsx"]) require.extensions[extension] = (loaded, file) => {
  const result = ts.transpileModule(fs.readFileSync(file, "utf8"), { compilerOptions: {
    module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true,
  } });
  loaded._compile(result.outputText, file);
};
// CSS modules affect styling only; the render test verifies semantic controls.
require.extensions[".css"] = loaded => { loaded.exports = new Proxy({}, { get: (_, key) => String(key) }); };
const impact = require("../lib/restriction-impact.ts");
const { buildRestrictionEvidence, parseEvidenceCsv } = require("../lib/restriction-evidence.ts");
const catalog = require("../lib/restriction-catalog.ts");
const asOf = "2026-10-20";
function settings(enabled = []) {
  const result = impact.defaultRestrictionSettings();
  for (const key of Object.keys(result.enabled)) result.enabled[key] = enabled.includes(key);
  return result;
}
const evidence = { fetchedAt: asOf, issues: [], sources: [], trialTypes: {}, issuers: {
  LOW: { listed: "PASS", marketCap: 299e6, capAsOf: asOf },
  MIN: { listed: "PASS", marketCap: 300e6, capAsOf: asOf },
  MAX: { listed: "PASS", marketCap: 10e9, capAsOf: asOf },
  HIGH: { listed: "PASS", marketCap: 10e9 + 1, capAsOf: asOf },
  OLD: { listed: "FAIL", marketCap: null, capAsOf: asOf },
} };
const rows = ["LOW", "MIN", "MAX", "HIGH", "OLD", "MISSING"].map((ticker, i) => ({
  id: "TRIAL|NCT" + String(i + 1).padStart(8, "0"), ticker, stage: "Phase 3",
}));
test("approved defaults preserve entry-time rules and every proposal starts off", () => {
  const draft = impact.defaultRestrictionSettings();
  assert.equal(draft.capBasis, "entry");
  assert.deepEqual(Object.keys(draft.enabled).filter(k => draft.enabled[k]), ["public", "minCap", "maxCap", "progress"]);
  for (const row of rows) assert.equal(impact.restrictionVerdict("minCap", row, draft, evidence, asOf), "UNKNOWN");
});
test("current-cap comparison includes exact boundaries and excludes each record only once", () => {
  const draft = settings(["public", "minCap", "maxCap"]); draft.capBasis = "current";
  const report = impact.calculateRestrictionImpact([...rows, rows[0]], draft, evidence, asOf);
  assert.equal(report.total, 6);
  assert.equal(report.steps[0].newlyExcluded, 1);
  assert.equal(report.steps[1].newlyExcluded, 1);
  assert.equal(report.steps[2].newlyExcluded, 1);
  assert.deepEqual([report.passed, report.pending, report.excluded], [2, 1, 3]);
  assert.equal(report.total, report.passed + report.pending + report.excluded);
});
test("unknowns continue through later rules and later known failures are counted", () => {
  const draft = settings(["public", "minCap", "progress"]); draft.capBasis = "entry";
  const sample = [{ id: "a", ticker: "MISSING", stage: "Post-Decision" }, { id: "b", ticker: "MIN", stage: "Phase 3" }];
  const report = impact.calculateRestrictionImpact(sample, draft, evidence, asOf);
  assert.equal(report.steps[3].newlyExcluded, 1);
  assert.equal(report.pending, 1);
  assert.equal(report.passed, 0);
  assert.equal(report.excluded, 1);
  // Passing a later rule never erases an earlier unknown.
  draft.enabled.documents = true; sample[1].phase3Source = "https://clinicaltrials.gov/study/NCT00000002";
  assert.equal(impact.calculateRestrictionImpact(sample, draft, evidence, asOf).pending, 1);
});
test("independent counts start from the full universe and disabled rules never affect the waterfall", () => {
  const draft = settings(); draft.capBasis = "current";
  const report = impact.calculateRestrictionImpact(rows, draft, evidence, asOf);
  assert.equal(report.steps[1].aloneFail, 1);
  assert.equal(report.steps[2].aloneFail, 1);
  assert.equal(report.excluded, 0);
  assert.ok(report.steps.every(step => step.remaining === rows.length && step.newlyExcluded === 0));
});
test("elapsed or missing PDUFA dates, registry-only FDA pathway and hold data stay unknown", () => {
  const draft = settings();
  const row = { id: "TRIAL|NCT00000001", ticker: "MIN", stage: "Phase 3", pdufaDate: "2026-10-19", phase3Source: "https://clinicaltrials.gov/study/NCT00000001" };
  assert.equal(impact.restrictionVerdict("progress", row, draft, evidence, asOf), "UNKNOWN");
  assert.equal(impact.restrictionVerdict("pdufaWindow", row, draft, evidence, asOf), "UNKNOWN");
  row.pdufaDate = "2026-10-20";
  assert.equal(impact.restrictionVerdict("progress", row, draft, evidence, asOf), "PASS");
  row.pdufaDate = "2026-02-31";
  assert.equal(impact.restrictionVerdict("pdufaWindow", row, draft, evidence, asOf), "UNKNOWN");
  assert.equal(impact.restrictionVerdict("fdaPath", row, draft, evidence, asOf), "UNKNOWN");
  draft.enabled.hold = true;
  assert.equal(impact.calculateRestrictionImpact([row], draft, evidence, asOf).excluded, 0);
});
test("CSV parsing preserves quoted indications, escaped quotes and embedded newlines", () => {
  assert.deepEqual(parseEvidenceCsv('\uFEFFticker,company\r\nABC,"A, B ""Pharma""\nInc."\r\n'), [{ ticker: "ABC", company: 'A, B "Pharma"\nInc.' }]);
  assert.throws(() => parseEvidenceCsv('a,b\n"unclosed,field'));
  assert.throws(() => parseEvidenceCsv('a,b\n1,2,3\n'));
});
test("partial published evidence never manufactures a public listing or cap", () => {
  const partial = buildRestrictionEvidence({ "company_registry.csv": "ticker,exchange,status\nABC,Nasdaq,OK\n" }, asOf);
  assert.equal(partial.issuers.ABC.listed, "PASS");
  assert.equal(partial.issuers.ABC.marketCap, null);
  assert.equal(partial.issues.length, 2);
});
test("the real saved universe reconciles public, cap and unknown categories as daily data changes", () => {
  const root = path.resolve(__dirname, "../../../data");
  const names = ["company_registry.csv", "phase_pipeline_market_caps.csv", "all_phase_trials.csv"];
  const saved = buildRestrictionEvidence(Object.fromEntries(names.map(name => [name, fs.readFileSync(path.join(root, name), "utf8")])), asOf);
  assert.deepEqual(saved.issues, []);
  const trials = parseEvidenceCsv(fs.readFileSync(path.join(root, "all_phase_trials.csv"), "utf8"));
  const other = parseEvidenceCsv(fs.readFileSync(path.join(root, "phase_pipeline.csv"), "utf8"));
  const merged = [...new Map([...other, ...trials].map(row => [row.nct_id, { id: "TRIAL|" + row.nct_id, ticker: row.ticker }])).values()];
  assert.ok(merged.length > 10000, "The entire saved trial universe is checked, not a displayed page");
  const draft = settings(["public", "minCap", "maxCap"]); draft.capBasis = "current";
  const report = impact.calculateRestrictionImpact(merged, draft, saved, asOf);
  const registry = new Set(parseEvidenceCsv(fs.readFileSync(path.join(root, "company_registry.csv"), "utf8")).map(row => row.ticker));
  const caps = new Map(parseEvidenceCsv(fs.readFileSync(path.join(root, "phase_pipeline_market_caps.csv"), "utf8")).map(row => [row.ticker, row]));
  const reference = { pass: 0, unknown: 0, unlisted: 0, below: 0, above: 0 };
  for (const row of merged) {
    const quote = caps.get(row.ticker);
    if (quote?.market_cap_status === "NOT_LISTED") reference.unlisted++;
    else if (!registry.has(row.ticker) || quote?.market_cap_status !== "VERIFIED" || !(Number(quote.market_cap) > 0)) reference.unknown++;
    else if (Number(quote.market_cap) < 300e6) reference.below++;
    else if (Number(quote.market_cap) > 10e9) reference.above++;
    else reference.pass++;
  }
  assert.deepEqual([report.passed, report.pending, report.excluded], [reference.pass, reference.unknown, reference.unlisted + reference.below + reference.above]);
  assert.equal(report.total, report.passed + report.pending + report.excluded);
});
test("the visible controls include every restriction, editable values, full baseline and entry-cap explanation", () => {
  const React = require("react"), { renderToStaticMarkup } = require("react-dom/server");
  const Component = require("../app/RestrictionImpact.tsx").default;
  const html = renderToStaticMarkup(React.createElement(Component, { rows, asOf }));
  assert.match(html, /LIVE SCAN SUMMARY/);
  assert.match(html, /At first entry — approved rule/);
  assert.match(html, /Latest saved cap — comparison/);
  assert.match(html, /Entry-date market caps have not been retained/);
  assert.match(html, /Minimum cap \(\$ millions\)/);
  assert.equal((html.match(/aria-label="Priority for /g) || []).length, catalog.RESTRICTION_CATALOG.length);
  assert.equal((html.match(/aria-label="Priority for [^"]*" value=""/g) || []).length, catalog.RESTRICTION_CATALOG.length);
});
test("priority selection, numeric edits and inline affected-record controls update without navigation", async () => {
  const React = require("react"), { create, act } = require("react-test-renderer");
  const Component = require("../app/RestrictionImpact.tsx").default;
  const before = { fetch: global.fetch, window: global.window, act: global.IS_REACT_ACT_ENVIRONMENT };
  global.IS_REACT_ACT_ENVIRONMENT = true;
  global.window = { setInterval: () => 1, clearInterval() {} };
  global.fetch = async () => ({ ok: true, json: async () => evidence });
  let renderer;
  try {
    await act(async () => { renderer = create(React.createElement(Component, { rows, asOf })); });
    const totals = () => renderer.root.findByProps({ "aria-atomic": "true" }).findAllByType("strong").map(node => node.children.join(""));
    assert.deepEqual(totals(), ["6", "6", "0", "0"]);
    for (const [i, id] of ["public", "minCap", "maxCap"].entries()) {
      const title = catalog.RESTRICTION_CATALOG.find(rule => rule.id === id).title;
      await act(async () => { renderer.root.findByProps({ "aria-label": "Priority for " + title }).props.onChange({ target: { value: String(i + 1) } }); });
    }
    await act(async () => { renderer.root.findByProps({ "aria-label": "Market-cap evidence" }).props.onChange({ target: { value: "current" } }); });
    assert.deepEqual(totals(), ["6", "3", "3", "1"]);
    await act(async () => { renderer.root.findByProps({ "aria-label": "Minimum cap ($ millions)" }).props.onChange({ target: { value: "301" } }); });
    assert.deepEqual(totals(), ["6", "2", "4", "1"]);
    const newExclusions = renderer.root.findAllByType("button").find(node => node.children.join("") === "NEW EXCLUSIONS" && !node.props.disabled);
    await act(async () => { newExclusions.props.onClick(); });
    assert.ok(renderer.root.findByProps({ "aria-label": "Affected records" }));
    await act(async () => { renderer.root.findByProps({ "aria-label": "Close affected records" }).props.onClick(); });
    assert.equal(renderer.root.findAllByProps({ "aria-label": "Affected records" }).length, 0);
    const capTitle = catalog.RESTRICTION_CATALOG.find(rule => rule.id === "minCap").title;
    await act(async () => { renderer.root.findByProps({ "aria-label": "Priority for " + capTitle }).props.onChange({ target: { value: "" } }); });
    assert.deepEqual(totals(), ["6", "4", "2", "1"]);
    await act(async () => { renderer.root.findAllByType("button").find(node => node.children.join("") === "RESET TO APPROVED RULES").props.onClick(); });
    assert.equal(renderer.root.findByProps({ "aria-label": "Market-cap evidence" }).props.value, "entry");
    assert.deepEqual(totals(), ["6", "6", "0", "0"]);
  } finally {
    if (renderer) await act(async () => renderer.unmount());
    global.fetch = before.fetch; global.window = before.window; global.IS_REACT_ACT_ENVIRONMENT = before.act;
  }
});
test("authenticated evidence endpoint reads real saved source data; unauthenticated calls perform no source reads", async () => {
  const { NextRequest } = require("next/server");
  const { GET } = require("../app/api/restriction-evidence/route.ts");
  const auth = require("../lib/auth.ts");
  const previous = { password: process.env.DASHBOARD_PASSWORD, key: process.env.SESSION_SIGNING_KEY, fetch: global.fetch };
  process.env.DASHBOARD_PASSWORD = "local-test-password-only";
  process.env.SESSION_SIGNING_KEY = "local-test-signing-key-with-at-least-32-characters";
  let calls = 0;
  global.fetch = async url => {
    calls++;
    const name = new URL(url).pathname.split("/").at(-1);
    assert.ok(["company_registry.csv", "phase_pipeline_market_caps.csv", "all_phase_trials.csv"].includes(name));
    return new Response(fs.readFileSync(path.resolve(__dirname, "../../../data", name), "utf8"));
  };
  try {
    const denied = await GET(new NextRequest("https://test.local/api/restriction-evidence"));
    assert.equal(denied.status, 401); assert.equal(calls, 0);
    const request = new NextRequest("https://test.local/api/restriction-evidence", { headers: { cookie: auth.COOKIE_NAME + "=" + auth.makeSession() } });
    const response = await GET(request), value = await response.json();
    assert.equal(response.status, 200); assert.equal(calls, 3);
    assert.equal(value.sources.length, 3); assert.deepEqual(value.issues, []);
    const sourceCaps = parseEvidenceCsv(fs.readFileSync(path.resolve(__dirname, "../../../data/phase_pipeline_market_caps.csv"), "utf8"));
    const example = sourceCaps.find(row => row.market_cap_status === "VERIFIED" && Number(row.market_cap) > 0);
    assert.equal(value.issuers[example.ticker].marketCap, Number(example.market_cap));
    assert.equal(response.headers.get("Cache-Control"), "private, no-store");
  } finally {
    global.fetch = previous.fetch;
    if (previous.password === undefined) delete process.env.DASHBOARD_PASSWORD; else process.env.DASHBOARD_PASSWORD = previous.password;
    if (previous.key === undefined) delete process.env.SESSION_SIGNING_KEY; else process.env.SESSION_SIGNING_KEY = previous.key;
  }
});
test("full catalog includes all original stage options and only approved Pipeline rules start assigned", () => {
  const entries = catalog.defaultCatalogEntries();
  assert.equal(entries.length, 39); assert.equal(new Set(entries.map(entry => entry.id)).size, 39);
  assert.deepEqual(entries.filter(entry => entry.stage).map(entry => [entry.id, entry.stage]), [["public", "PIPELINE"], ["minCap", "PIPELINE"], ["maxCap", "PIPELINE"], ["progress", "PIPELINE"]]);
  assert.equal(entries.filter(entry => entry.id.startsWith("gem_") && entry.id !== "gem_jr_source").length, 16);
  assert.equal(entries.filter(entry => entry.id.startsWith("alert_")).length, 10);
});
test("stage assignments chain from the original universe and Blank has no screening effect", () => {
  const entries = catalog.defaultCatalogEntries().map(entry => ({ ...entry, enabled: false, stage: "" }));
  for (const [id, stage] of [["public", "PIPELINE"], ["minCap", "GEM_JR"], ["maxCap", "GEM"]]) Object.assign(entries.find(e => e.id === id), { enabled: true, stage, priority: "1" });
  const draft = settings(); draft.capBasis = "current";
  const report = catalog.calculateCatalogImpact(rows, entries, draft, evidence, asOf);
  assert.deepEqual(report.stages.map(stage => [stage.before, stage.excluded, stage.remaining]), [[6, 1, 5], [5, 1, 4], [4, 1, 3]]);
  assert.deepEqual([report.passed, report.pending, report.excluded], [2, 1, 3]);
  for (const entry of entries) entry.stage = "";
  const blank = catalog.calculateCatalogImpact(rows, entries, draft, evidence, asOf);
  assert.equal(blank.excluded, 0); assert.equal(blank.passed, 6);
});
test("custom numeric comparisons use actual evidence and free-form descriptions never invent exclusions", () => {
  const custom = { id: "custom_test", stage: "GEM", enabled: true, priority: "1", title: "Cap at most $500M", field: "marketCapMillions", operator: "<=", value: "500", maximum: "" };
  const result = catalog.calculateCatalogImpact(rows, [custom], settings(), evidence, asOf);
  assert.deepEqual([result.passed, result.pending, result.excluded], [2, 2, 2]);
  const note = catalog.calculateCatalogImpact(rows, [{ ...custom, field: "note", title: "Primary p-value below 0.05" }], settings(), evidence, asOf);
  assert.deepEqual([note.passed, note.pending, note.excluded], [0, 6, 0]);
});
test("restored drafts preserve assignments and custom rules, reject invalid selectors, and restore missing catalog rows", () => {
  const custom = { id: "custom_saved", stage: "GEM_JR", enabled: true, title: "My rule", field: "note", operator: ">=", value: "", maximum: "" };
  const restored = catalog.restoreCatalogEntries([{ ...catalog.defaultCatalogEntries()[0], stage: "GEM" }, custom, { ...custom, id: "custom_bad", stage: "INVALID" }]);
  assert.equal(restored.length, 40); assert.equal(restored[0].stage, "GEM");
  assert.ok(restored.some(e => e.id === "custom_saved")); assert.ok(!restored.some(e => e.id === "custom_bad"));
});
test("Restrictions is a top-level page with a direct link and per-row four-option stage selectors", () => {
  const workspace = fs.readFileSync(path.resolve(__dirname, "../app/Workspace.tsx"), "utf8");
  assert.match(workspace, /requested === "RESTRICTIONS"/);
  assert.match(workspace, /setTop\("RESTRICTIONS"\)/);
  assert.match(workspace, />RESTRICTIONS<\/button>/);
  const React = require("react"), { renderToStaticMarkup } = require("react-dom/server");
  const Component = require("../app/RestrictionImpact.tsx").default;
  const html = renderToStaticMarkup(React.createElement(Component, { rows, asOf }));
  assert.equal((html.match(/aria-label="Stage for /g) || []).length, 39);
  assert.match(html, /value="">Blank<\/option>/); assert.match(html, /value="GEM_JR">GEM JR<\/option>/);
  assert.match(html, /WRITE A RESTRICTION/);
});

test("master cash runway replaces the duplicate GEM cash restriction and keeps FS association",()=>{
  const defs=catalog.RESTRICTION_CATALOG;
  assert.equal(defs.filter(rule=>rule.id==="runway"||rule.id==="gem_cash").length,1);
  assert.deepEqual(defs.find(rule=>rule.id==="runway").associations,["GEM JR FS"]);
  const old=[...catalog.defaultCatalogEntries(),{
    id:"gem_cash",stage:"GEM_JR",enabled:true,priority:"4",value:"12",maximum:""
  }];
  const restored=catalog.restoreCatalogEntries(old);
  assert.equal(restored.some(entry=>entry.id==="gem_cash"),false);
  const cash=restored.find(entry=>entry.id==="runway");
  assert.equal(cash.stage,"GEM_JR");
  assert.equal(cash.priority,"4");
  assert.equal(catalog.catalogVerdict(cash,{id:"TRIAL|NCT88888888",ticker:"CASH",technical:{runwayMonths:14}},settings(),evidence,asOf),"PASS");
});
test("one restriction may apply to multiple stages without duplicate catalog rows",()=>{
  const entries=catalog.defaultCatalogEntries().map(entry=>({...entry,stage:"",additionalStages:[],enabled:false,priority:""}));
  const one=entries.find(entry=>entry.id==="public");
  Object.assign(one,{stage:"PIPELINE",additionalStages:["GEM_JR","GEM"],enabled:true,priority:"1"});
  assert.deepEqual(catalog.catalogStages(one),["PIPELINE","GEM_JR","GEM"]);
  const report=catalog.calculateCatalogImpact(rows,entries,settings(),evidence,asOf);
  assert.equal(report.steps.get("public").stage,"PIPELINE");
  assert.equal(report.steps.get("GEM_JR|public").stage,"GEM_JR");
  assert.equal(report.steps.get("GEM|public").stage,"GEM");
  assert.equal(report.stages.length,3);
  assert.equal(report.excluded,1);
});

test("importance groups put Market Cap first and preserve one master restriction each", () => {
  assert.equal(catalog.RESTRICTION_PURPOSE_GROUPS[0].id, "MARKET_CAP");
  assert.deepEqual(
    catalog.RESTRICTION_CATALOG.filter(rule => ["minCap", "maxCap", "gem_marketcap"].includes(rule.id))
      .map(rule => catalog.restrictionPurposeGroup({id: rule.id})),
    ["MARKET_CAP", "MARKET_CAP", "MARKET_CAP"]
  );
  const groups = new Set(catalog.RESTRICTION_PURPOSE_GROUPS.map(group => group.id));
  const mapped = catalog.defaultCatalogEntries().map(entry => catalog.restrictionPurposeGroup(entry));
  assert.equal(mapped.length, 39);
  assert.ok(mapped.every(group => groups.has(group)));
  const React = require("react"), {renderToStaticMarkup} = require("react-dom/server");
  const Component = require("../app/RestrictionImpact.tsx").default;
  const html = renderToStaticMarkup(React.createElement(Component, {rows, asOf}));
  const cap = html.indexOf('data-purpose-group="MARKET_CAP"');
  const clinical = html.indexOf('data-purpose-group="CLINICAL_RESULTS"');
  const fda = html.indexOf('data-purpose-group="FDA"');
  assert.ok(cap >= 0 && clinical > cap && fda > clinical, "Market Cap first, then Clinical Results, then FDA");
  assert.equal((html.match(/aria-label="Priority for /g) || []).length, 39, "no duplicate editable master rows");
  assert.match(html, /GEM JR FS/);
  assert.match(html, /GEM JR FA/);
  assert.match(html, /GEM FS/);
  assert.match(html, /GEM FA/);
  assert.deepEqual(catalog.RESTRICTION_CATALOG.find(rule => rule.id === "gem_registry").associations,
    ["GEM JR FS", "GEM JR FA"], "Registry remains in both original presets");
  assert.deepEqual(catalog.RESTRICTION_CATALOG.find(rule => rule.id === "runway").associations,
    ["GEM JR FS"], "Runway keeps its original preset association");
});

test("purpose changes group display without changing restriction scan calculations or stored presets", () => {
  const entries = catalog.defaultCatalogEntries().map(entry => ({...entry}));
  const prior = JSON.stringify(entries);
  const before = catalog.calculateCatalogImpact(rows, entries, settings(), evidence, asOf);
  const sortedForDisplay = [...entries].sort((a, b) =>
    catalog.RESTRICTION_PURPOSE_GROUPS.findIndex(group => group.id === catalog.restrictionPurposeGroup(a)) -
    catalog.RESTRICTION_PURPOSE_GROUPS.findIndex(group => group.id === catalog.restrictionPurposeGroup(b)));
  const after = catalog.calculateCatalogImpact(rows, entries, settings(), evidence, asOf);
  assert.equal(JSON.stringify(entries), prior);
  assert.deepEqual([before.passed, before.pending, before.excluded],
    [after.passed, after.pending, after.excluded]);
  assert.equal(new Set(sortedForDisplay.map(entry => entry.id)).size, entries.length);
  assert.equal(catalog.restrictionPurposeGroup({id:"custom_market",field:"marketCapMillions"}),"MARKET_CAP");
});

test("compact default Restrictions view preserves editable rules and hidden diagnostics", () => {
  const React = require("react"), {renderToStaticMarkup} = require("react-dom/server");
  const Component = require("../app/RestrictionImpact.tsx").default;
  const html = renderToStaticMarkup(React.createElement(Component, {rows, asOf}));
  assert.match(html, /Trials remaining/);
  assert.match(html, /Impact details/);
  assert.match(html, /Write a custom restriction/);
  assert.match(html, /Breakdown by Pipeline, GEM JR and GEM/);
  assert.match(html, /data-purpose-group="MARKET_CAP"/);
  assert.doesNotMatch(html, /0\. FULL STARTING UNIVERSE/);
  assert.equal((html.match(/aria-label="Priority for /g) || []).length, 39);
  assert.equal((html.match(/aria-label="Stage for /g) || []).length, 39);
  assert.match(html, /GEM JR FS/); assert.match(html, /GEM JR FA/);
  assert.match(html, /GEM FS/); assert.match(html, /GEM FA/);
});

test("Add to List inserts Market Cap in Pipeline at #1 without changing other list ranks or FS/FA presets", () => {
  const entries=catalog.defaultCatalogEntries().map(entry=>({...entry}));
  const existing=entries.find(e=>e.id==="public");existing.priority="1";existing.enabled=true;
  const cap=entries.find(e=>e.id==="gem_marketcap");
  cap.stage="GEM_JR";cap.priority="8900";cap.enabled=true;
  const beforeJunior=catalog.selectedRestrictionList(entries,"GEM_JR").map(entry=>entry.id);
  const original=JSON.stringify(entries);
  const mapped=catalog.insertRestrictionIntoList(entries,"gem_marketcap","PIPELINE",0);
  assert.equal(JSON.stringify(entries),original);
  assert.equal(new Set(mapped.map(entry=>entry.id)).size,entries.length);
  assert.deepEqual(catalog.selectedRestrictionList(mapped,"PIPELINE").slice(0,2).map(entry=>entry.id),["gem_marketcap","public"]);
  assert.deepEqual(catalog.selectedRestrictionList(mapped,"GEM_JR").map(entry=>entry.id),beforeJunior);
  assert.equal(catalog.catalogStagePriority(mapped.find(e=>e.id==="gem_marketcap"),"PIPELINE"),"1");
  assert.equal(catalog.catalogStagePriority(mapped.find(e=>e.id==="gem_marketcap"),"GEM_JR"),"8900");
  assert.equal(mapped.find(e=>e.id==="gem_marketcap").priority,"8900");
  assert.deepEqual(catalog.RESTRICTION_CATALOG.find(rule=>rule.id==="gem_registry").associations,["GEM JR FS","GEM JR FA"]);
  assert.deepEqual(catalog.RESTRICTION_CATALOG.find(rule=>rule.id==="runway").associations,["GEM JR FS"]);
  const saved=catalog.restoreCatalogEntries(mapped);
  assert.deepEqual(catalog.selectedRestrictionList(saved,"PIPELINE").slice(0,2).map(entry=>entry.id),["gem_marketcap","public"]);
  const current=settings();current.capBasis="current";
  const result=catalog.calculateCatalogImpact(rows,saved,current,evidence,asOf);
  assert.equal(result.steps.get("gem_marketcap").step,1);
  assert.equal(result.stages[0].excluded,3); // market cap excludes LOW/HIGH; public-company rule also excludes OLD
});
test("Add to List preview does not mutate existing stored catalog and inactive lists stay inactive",()=>{
  const entries=catalog.defaultCatalogEntries();
  const before=JSON.stringify(entries);
  const next=catalog.insertRestrictionIntoList(entries,"gem_marketcap","PIPELINE",0);
  assert.equal(JSON.stringify(entries),before);
  assert.equal(catalog.selectedRestrictionList(entries,"PIPELINE").length,0);
  assert.equal(catalog.selectedRestrictionList(next,"PIPELINE")[0].id,"gem_marketcap");
  assert.equal(catalog.catalogStagePriority(next.find(e=>e.id==="gem_marketcap"),"GEM_JR"),"");
});
test("restriction popup displays list, defaults Market Cap to Pipeline #1, and applies chosen position",async()=>{
  const React=require("react"),{create,act}=require("react-test-renderer");
  const Component=require("../app/RestrictionImpact.tsx").default;
  const before={fetch:global.fetch,window:global.window,act:global.IS_REACT_ACT_ENVIRONMENT};
  global.IS_REACT_ACT_ENVIRONMENT=true;global.window={setInterval:()=>1,clearInterval(){}};
  global.fetch=async()=>({ok:true,json:async()=>evidence});
  let renderer;
  try {
    await act(async()=>{renderer=create(React.createElement(Component,{rows,asOf}));});
    const add=renderer.root.findByProps({"aria-label":"Add Current market-cap range to a list"});
    await act(async()=>{add.props.onClick();});
    assert.equal(renderer.root.findAllByProps({role:"dialog","aria-label":"Restriction list popup"}).length,1);
    assert.equal(renderer.root.findByProps({"aria-label":"Destination restriction list"}).props.value,"PIPELINE");
    assert.equal(renderer.root.findByProps({"aria-label":"Restriction list position"}).props.value,0);
    const preview=renderer.root.findAllByType("strong").map(n=>n.children.join("")).join(" ");
    assert.match(preview,/PREVIEW/);
    const apply=renderer.root.findAllByType("button").find(n=>String(n.children.join("")).includes("APPLY TO PIPELINE LIST"));
    await act(async()=>{apply.props.onClick();});
    assert.equal(renderer.root.findAllByProps({role:"dialog","aria-label":"Restriction list popup"}).length,0);
    assert.equal(renderer.root.findByProps({"aria-label":"Priority for Current market-cap range"}).props.value,"1");
  } finally {if(renderer)await act(async()=>renderer.unmount());global.fetch=before.fetch;global.window=before.window;global.IS_REACT_ACT_ENVIRONMENT=before.act;}
});
