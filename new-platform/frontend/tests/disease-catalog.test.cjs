const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const ts = require("typescript");
for (const extension of [".ts", ".tsx"]) require.extensions[extension] = (loaded, file) => {
  const result = ts.transpileModule(fs.readFileSync(file, "utf8"), { compilerOptions: {
    module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true,
  } });
  loaded._compile(result.outputText, file);
};
const catalog = require("../lib/disease-catalog.ts");
const source = require("../data/diseaseCatalog.json");

test("a fresh device has every bundled descriptor and placement, including all deeper source levels", () => {
  const index = catalog.buildDiseaseIndex(catalog.emptyDiseaseEdits());
  assert.equal(source.uniqueCount, 5168);
  assert.equal(index.unique.length, source.uniqueCount);
  assert.equal(index.nodes.length, source.placementCount);
  const levels = new Array(source.levelCounts.length).fill(0);
  for (const node of index.nodes) {
    const path = catalog.diseasePath(node.id, index);
    assert.equal(path.length, node.treeNumber.split(".").length);
    assert.equal(path[0].parentId, null);
    assert.ok(node.sourceUrl.endsWith(node.sourceId));
    assert.ok(!node.treeNumber.startsWith("C22"));
    levels[path.length - 1]++;
  }
  assert.deepEqual(levels, source.levelCounts);
  assert.ok(levels.slice(0, 5).every(count => count > 0));
  assert.equal(levels.length, 10);
  assert.equal(index.children.get(null).length, 23);
  assert.ok(index.byId.has("mesh:F03"));
});

test("search deduplicates multi-branch diseases and finds alternate names, IDs and rare diseases", () => {
  const index = catalog.buildDiseaseIndex(catalog.emptyDiseaseEdits());
  const lung = catalog.searchDiseases("D002289", index);
  assert.equal(lung.length, 1);
  assert.equal(lung[0].name, "Carcinoma, Non-Small-Cell Lung");
  assert.ok(index.nodes.filter(node => node.sourceId === "D002289").length > 1);
  assert.ok(catalog.searchDiseases("Duchenne", index).some(node => /Muscular Dystrophy, Duchenne/.test(node.name)));
  const aliasRecord = source.terms.find(([, , , aliases]) => aliases.includes("Type 2 Diabetes Mellitus"));
  assert.ok(aliasRecord);
  assert.ok(catalog.searchDiseases("Type 2 Diabetes Mellitus", index).some(node => node.sourceId === aliasRecord[0]));
});

test("legacy manual entries survive population, including orphan and cyclic saved data", () => {
  const saved = catalog.restoreDiseaseEdits([
    { id: "manual-area", name: "My saved area", parentId: null },
    { id: "manual-sub", name: "My saved subtype", parentId: "manual-area" },
    { id: "orphan", name: "Keep orphan", parentId: "missing" },
    { id: "cycle-a", name: "Cycle A", parentId: "cycle-b" },
    { id: "cycle-b", name: "Cycle B", parentId: "cycle-a" },
  ]);
  const index = catalog.buildDiseaseIndex(saved);
  assert.equal(index.unique.length, source.uniqueCount + 5);
  assert.deepEqual(catalog.diseasePath("manual-sub", index).map(node => node.name), ["My saved area", "My saved subtype"]);
  assert.equal(index.byId.get("orphan").parentId, null);
  assert.equal(index.byId.get("orphan").needsReview, true);
  assert.ok(catalog.diseasePath("cycle-a", index).length <= 2);
  assert.ok(catalog.diseasePath("cycle-b", index).length <= 2);
  assert.deepEqual(catalog.restoreDiseaseEdits(JSON.parse(JSON.stringify(saved))), saved);
});

test("renames persist in every placement and preserve source names, source IDs and original-name search", () => {
  let saved = catalog.emptyDiseaseEdits();
  const initial = catalog.buildDiseaseIndex(saved);
  const node = initial.unique.find(node => node.sourceId === "D002289");
  saved = catalog.renameDisease(saved, node, "My lung disease label");
  const index = catalog.buildDiseaseIndex(catalog.restoreDiseaseEdits(JSON.parse(JSON.stringify(saved))));
  const copies = index.nodes.filter(node => node.sourceId === "D002289");
  assert.ok(copies.length > 1);
  assert.ok(copies.every(node => node.name === "My lung disease label" && node.sourceName === "Carcinoma, Non-Small-Cell Lung"));
  assert.equal(index.unique.length, initial.unique.length);
  assert.ok(catalog.searchDiseases("non-small-cell lung", index).some(node => node.sourceId === "D002289"));
});

test("adding beyond the deepest source level retains parent links and only accepts safe source URLs", () => {
  let saved = catalog.emptyDiseaseEdits();
  let index = catalog.buildDiseaseIndex(saved);
  const parent = index.nodes.find(node => node.treeNumber.split(".").length === 10);
  const node = { id: "custom:deep", name: "New deeper subtype", parentId: parent.id, sourceUrl: "https://example.com/evidence" };
  saved = catalog.addDiseaseNode(saved, node, index);
  index = catalog.buildDiseaseIndex(saved);
  assert.equal(catalog.diseasePath(node.id, index).length, 11);
  assert.equal(index.unique.length, source.uniqueCount + 1);
  assert.equal(catalog.addDiseaseNode(saved, { ...node, id: "duplicate" }, index), saved);
  assert.equal(catalog.addDiseaseNode(saved, { ...node, id: "orphan", parentId: "missing" }, index), saved);
  assert.equal(catalog.safeDiseaseSource("javascript:alert(1)"), undefined);
  assert.equal(catalog.safeDiseaseSource("https://user:password@example.com"), undefined);
});

test("the mounted editor migrates manual entries, saves renames and additions, and restores them on remount", async () => {
  const React = require("react");
  const { create, act } = require("react-test-renderer");
  const Component = require("../app/DiseaseRestriction.tsx").default;
  const previousStorage = global.localStorage;
  global.IS_REACT_ACT_ENVIRONMENT = true;
  const stored = new Map([
    [catalog.LEGACY_DISEASE_STORAGE_KEY, JSON.stringify([{ id: "legacy", name: "Saved custom disease", parentId: null }])],
    ["fs-fa-presets", "keep original presets"],
  ]);
  global.localStorage = { getItem: key => stored.get(key) || null, setItem: (key, value) => stored.set(key, value) };
  let tree;
  const buttons = name => tree.root.findAllByType("button").filter(button => button.children.join("") === name);
  const visibleText = node => typeof node === "string" ? node : Array.isArray(node)
    ? node.map(visibleText).join("") : node ? visibleText(node.children) : "";
  const text = () => visibleText(tree.toJSON());
  try {
    await act(async () => { tree = create(React.createElement(Component)); });
    assert.match(text(), /5,169 unique classifications/);
    assert.equal(tree.root.findAllByType("select").length, 5);
    assert.ok(tree.root.findAllByType("select").every(select => select.props.value));
    await act(async () => { buttons("RENAME")[4].props.onClick(); });
    await act(async () => { tree.root.findAllByType("input").find(input => input.props.required).props.onChange({ target: { value: "My lung classification" } }); });
    await act(async () => { tree.root.findByType("form").props.onSubmit({ preventDefault() {} }); });
    await act(async () => { buttons("+ ADD SUBLEVEL")[4].props.onClick(); });
    await act(async () => { tree.root.findAllByType("input").find(input => input.props.required).props.onChange({ target: { value: "My new disease subtype" } }); });
    await act(async () => { tree.root.findByType("form").props.onSubmit({ preventDefault() {} }); });
    assert.equal(tree.root.findAllByType("select").length, 6);
    assert.match(text(), /5,170 unique classifications/);
    assert.match(text(), /My new disease subtype/);
    const edits = JSON.parse(stored.get(catalog.DISEASE_STORAGE_KEY));
    assert.equal(edits.custom.length, 2);
    assert.equal(Object.values(edits.renames)[0], "My lung classification");
    assert.equal(stored.get("fs-fa-presets"), "keep original presets");
    await act(async () => tree.unmount());
    await act(async () => { tree = create(React.createElement(Component)); });
    assert.match(text(), /5,170 unique classifications/);
    assert.match(text(), /My lung classification/);
  } finally {
    if (tree) await act(async () => tree.unmount());
    global.localStorage = previousStorage;
  }
});
