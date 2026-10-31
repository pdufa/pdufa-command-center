const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const ts = require("typescript");
const moduleFile = path.join(__dirname, "../lib/pipeline-data.ts");

for (const extension of [".ts", ".tsx"]) require.extensions[extension] = (loaded, file) => {
  const result = ts.transpileModule(fs.readFileSync(file, "utf8"), { compilerOptions: {
    module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX,
    esModuleInterop: true,
  } });
  loaded._compile(result.outputText, file);
};

const { filterPipelineRows, pipelineAvailability, pageRows, trialId, registrySections, reportedAnalyses, sortPipelineRows } = require(moduleFile);
const { COMPETITIVE_STRATEGIES } = require("../lib/competitive-strategies.ts");

const records = [
  { id: "TRIAL|NCT00000001", programId: "PDUFA-000001", ticker: "AAA", drug: "Drug A", stage: "Phase 1", capInRange: true, band: "NO PDUFA YET" },
  { id: "TRIAL|NCT00000002", programId: "PDUFA-000002", ticker: "AAA", drug: "Drug B", stage: "Phase 3", capInRange: false, band: "31–60 DAYS" },
  { id: "RESULT|NCT00000003", ticker: "BBB", drug: "Drug C", stage: "Phase 3 Results", capInRange: true, band: "31–60 DAYS" },
  { id: "FDA|4", ticker: "CCC", stage: "PDUFA Decision", capInRange: true, band: "61–90 DAYS" },
];

test("checked phases use OR; date, cap and text use AND; clear includes every program", () => {
  const select = filters => filterPipelineRows(records, filters, row => row.band);
  assert.deepEqual(select({ stages: ["Phase 1", "Phase 3"] }).map(row => row.id), records.slice(0, 2).map(row => row.id));
  assert.equal(select({ stages: ["Phase 3"] }).length, 1);
  assert.equal(select({ stages: ["Phase 3 Results"] }).length, 1);
  assert.equal(select({ stages: ["Phase 3"], onlyBand: true }).length, 0);
  assert.equal(select({ dates: ["31–60 DAYS"], query: "bBb" }).length, 1);
  assert.equal(select({ query: "PDUFA-000002" })[0].drug, "Drug B");
  assert.equal(select({ stages: [], dates: [] }).length, 4);
  assert.equal(select({ stages: ["Phase 4"] }).length, 0);
  assert.equal(trialId(records[0]), "NCT00000001");
  assert.equal(trialId(records[3]), "");
});

test("checking or clearing phases and dates never zeros their available counts", () => {
  const stages = ["Phase 1", "Phase 3", "Phase 3 Results", "PDUFA Decision"];
  const bands = ["NO PDUFA YET", "31–60 DAYS", "61–90 DAYS"];
  const band = row => row.band;
  const baseline = pipelineAvailability(records, {}, band, stages, bands);
  assert.deepEqual(baseline.stageCounts.map(item => item.count), [1, 1, 1, 1]);
  assert.deepEqual(baseline.dateCounts.map(item => item.count), [1, 2, 1]);
  for (const selected of [
    { stages: ["Phase 1", "Phase 3"], dates: [] },
    { stages: ["Phase 3"], dates: ["NO PDUFA YET"] },
    { stages: [], dates: [] },
  ]) {
    const available = pipelineAvailability(records, selected, band, stages, bands);
    assert.deepEqual(available.stageCounts, baseline.stageCounts);
    assert.deepEqual(available.dateCounts, baseline.dateCounts);
    assert.equal(available.rows.length, 4);
  }
  assert.equal(filterPipelineRows(records, { stages: ["Phase 3"], dates: ["NO PDUFA YET"] }, band).length, 0);
  const screened = pipelineAvailability(records, { onlyBand: true }, band, stages, bands);
  assert.equal(screened.rows.length, 3);
  assert.deepEqual(screened.stageCounts.map(item => item.count), [1, 0, 1, 1]);
  assert.equal(pipelineAvailability(records, { query: "AAA" }, band, stages, bands).rows.length, 2);
});

test("competitive-strategy priorities are complete, uniquely ranked, and clearly evidence-gated", () => {
  assert.equal(COMPETITIVE_STRATEGIES.length, 10);
  assert.deepEqual(COMPETITIVE_STRATEGIES.map(strategy => strategy.rank), [1,2,3,4,5,6,7,8,9,10]);
  assert.equal(new Set(COMPETITIVE_STRATEGIES.map(strategy => strategy.id)).size, 10);
  for (const strategy of COMPETITIVE_STRATEGIES) {
    assert.ok(strategy.label && strategy.potentialBenefit && strategy.evidenceRequired);
  }
  assert.equal(COMPETITIVE_STRATEGIES[0].id, "efficacy");
  assert.equal(COMPETITIVE_STRATEGIES.at(-1).id, "differentiation");
});

test("pagination covers every filtered record once and clamps an old page after filters change", () => {
  const all = Array.from({ length: 107 }, (_, index) => ({ id: index }));
  const paged = [0, 1, 2].flatMap(page => pageRows(all, page, 50).rows);
  assert.deepEqual(paged, all);
  assert.deepEqual(pageRows(records.slice(0, 1), 8, 25), { page: 0, pages: 1, start: 1, end: 1, rows: records.slice(0, 1) });
  assert.equal(pageRows([], 0, 25).start, 0);
});

test("sorts the entire matching set numerically before pagination and keeps missing values last", () => {
  const all = Array.from({ length: 107 }, (_, index) => ({ id: String(index), ticker: "T" + index, marketCap: index * 1e6 }));
  const sorted = sortPipelineRows(all, { key: "marketCap", direction: "desc" });
  assert.equal(pageRows(sorted, 0, 25).rows[0].marketCap, 106e6);
  assert.equal(pageRows(sorted, 4, 25).rows.at(-1).marketCap, 0);
  const numericIds = [{ id: "a", ticker: "A", programId: "PDUFA-10" }, { id: "b", ticker: "B", programId: "PDUFA-2" }, { id: "c", ticker: "C" }];
  assert.deepEqual(sortPipelineRows(numericIds, { key: "programId", direction: "asc" }).map(row => row.id), ["b", "a", "c"]);
  assert.deepEqual(sortPipelineRows(numericIds, { key: "programId", direction: "desc" }).map(row => row.id), ["a", "b", "c"]);
  assert.equal(all[0].id, "0");
  const dates = [{ id: "1", ticker: "A", pdufaDate: "2027-01-01" }, { id: "2", ticker: "B", pdufaDate: "2026-12-31T00:00:00Z" }, { id: "3", ticker: "C" }];
  assert.deepEqual(sortPipelineRows(dates, { key: "pdufaDate", direction: "asc" }).map(row => row.id), ["2", "1", "3"]);
});

test("registry date, status and p-value count sorting uses every trial, including reported zero", () => {
  const index = {
    NCT00000001: { status: "RECRUITING", primary_completion_date: "2027-02", p_value_count: 0 },
    NCT00000002: { status: "COMPLETED", primary_completion_date: "2026-12-31", p_value_count: 12 },
    NCT00000003: { status: "ACTIVE_NOT_RECRUITING", primary_completion_date: "2027-01-01", p_value_count: 2 },
  };
  assert.deepEqual(sortPipelineRows(records, { key: "pValueCount", direction: "desc" }, index).map(row => row.id), [records[1].id, records[2].id, records[0].id, records[3].id]);
  assert.equal(sortPipelineRows(records, { key: "pValueCount", direction: "asc" }, index)[0].id, records[0].id);
  assert.equal(sortPipelineRows(records, { key: "primaryCompletion", direction: "asc" }, index)[0].id, records[1].id);
  assert.equal(sortPipelineRows(records, { key: "status", direction: "asc" }, index)[0].id, records[2].id);
  assert.deepEqual(sortPipelineRows([records[2], records[1], records[0]], { key: "stage", direction: "asc" }).map(row => row.stage), ["Phase 1", "Phase 3", "Phase 3 Results"]);
});

test("the rendered data area lists only selected-phase rows and preserves an empty result state", () => {
  const React = require("react");
  const { renderToStaticMarkup } = require("react-dom/server");
  const PipelineData = require("../app/PipelineData.tsx").default;
  const filtered = filterPipelineRows(records, { stages: ["Phase 1"] }, row => row.band);
  const html = renderToStaticMarkup(React.createElement(PipelineData, { rows: filtered }));
  assert.match(html, /1 matching trials \/ programs/);
  assert.match(html, /Drug A/);
  assert.doesNotMatch(html, /Drug B|Drug C/);
  assert.match(html, /All data/);
  assert.match(html, /Competitive strategies/);
  assert.match(html, /View ranked 1–10/);
  assert.match(html, /Therapy not yet assessed/);
  assert.match(html, /NOT verified advantages for this therapy/);
  assert.ok(html.indexOf("Superior clinical efficacy") < html.indexOf("Market differentiation and exclusivity"));
  assert.match(html, /aria-sort="ascending"/);
  assert.match(html, /Sort by market cap/);
  assert.doesNotMatch(html, /Sort by indication|Sort by drug/);
  assert.match(renderToStaticMarkup(React.createElement(PipelineData, { rows: [] })), /No trials or programs match these filters/);
  const many = Array.from({ length: 107 }, (_, index) => ({ id: String(index), ticker: String(index).padStart(3, "0") }));
  const paginated = renderToStaticMarkup(React.createElement(PipelineData, { rows: many }));
  assert.match(paginated, /107 matching trials \/ programs/);
  // Score popovers also expose aria-expanded; count actual table records.
  const body = paginated.match(/<tbody>([\s\S]*?)<\/tbody>/)?.[1] || "";
  assert.equal((body.match(/<tr(?:\s[^>]*)?>/g) || []).length, 25);
});

test("every registry module and future field remains browsable; p-values keep endpoint and group context", () => {
  const study = { protocolSection: { designModule: { phases: ["PHASE1"] } },
    resultsSection: { outcomeMeasuresModule: { outcomeMeasures: [{ title: "Primary endpoint", type: "PRIMARY", groups: [{ id: "A", title: "Drug" }], analyses: [{ pValue: "<0.001", groupIds: ["A"] }] }, { title: "Secondary", analyses: [{ pValue: 0 }] }] } },
    documentSection: { largeDocumentModule: { filename: "protocol.pdf" } }, futureSection: { keep: false } };
  const sections = registrySections(study);
  assert.equal(sections.length, 4);
  assert.deepEqual(sections.find(section => section.id === "futureSection").data, { keep: false });
  const analyses = reportedAnalyses(study);
  assert.equal(analyses.length, 2);
  assert.equal(analyses[0].endpoint, "Primary endpoint");
  assert.deepEqual(analyses[0].groups, ["Drug"]);
  assert.equal(analyses[1].pValue, 0);
  assert.equal(reportedAnalyses({ protocolSection: { outcomesModule: { pValue: "0.05 planned threshold" } } }).length, 0);
});
