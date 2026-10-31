const {test} = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const ts = require("typescript");
for (const extension of [".ts", ".tsx"]) {
  require.extensions[extension] = (module, file) => module._compile(
    ts.transpileModule(fs.readFileSync(file, "utf8"), {compilerOptions: {
      module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022,
      jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true,
    }}).outputText, file);
}
const {defaultCatalogEntries, restoreCatalogEntries} = require("../lib/restriction-catalog.ts");
const {detachGemAssociations, poolRuleAllowed, poolRuleDefinition, validatePoolPipeline} =
  require("../lib/pool-pipeline-restrictions.ts");

test("Pool->Pipeline preserves exact active baseline without GEM links or lost values", () => {
  const original = defaultCatalogEntries();
  const before = JSON.stringify(original);
  const active = detachGemAssociations(original);
  assert.equal(original.length, 41);
  assert.equal(active.length, 40);
  assert.ok(!active.some(e => e.id === "gem_jr_source"));
  assert.ok(validatePoolPipeline(active));
  assert.deepEqual(active.filter(e => e.stage === "PIPELINE").map(e => e.id),
    ["public", "minCap", "maxCap", "fdaPath", "phase"]);
  assert.equal(active.find(e => e.id === "minCap").value, "300");
  assert.equal(active.find(e => e.id === "maxCap").value, "10000");
  assert.equal(JSON.stringify(original), before, "Legacy settings remain untouched");
  assert.equal(poolRuleAllowed("gem_jr_source"), false);
});

test("Remove every GEM JR and GEM stage association even from mixed and saved settings", () => {
  const original = restoreCatalogEntries(defaultCatalogEntries().map(e =>
    e.id === "minCap" ? {...e,stage:"GEM",priority:"9",additionalStages:["GEM_JR","PIPELINE"],
      stagePriorities:{GEM:"9",GEM_JR:"8",PIPELINE:"3"},enabled:true,value:"350"}
    : e.id === "runway" ? {...e,stage:"GEM_JR",priority:"2",stagePriorities:{GEM_JR:"2"},
      enabled:true,value:"18"}
    : e));
  const snapshot = JSON.stringify(original);
  const active = detachGemAssociations(original);
  assert.ok(validatePoolPipeline(active));
  const min = active.find(e => e.id === "minCap");
  assert.deepEqual([min.stage,min.priority,min.value,min.enabled],["PIPELINE","3","350",true]);
  assert.deepEqual(min.stagePriorities,{PIPELINE:"3"});
  assert.deepEqual(min.additionalStages,[]);
  const cash = active.find(e => e.id === "runway");
  assert.deepEqual([cash.stage,cash.enabled,cash.value],["",false,"18"]);
  assert.deepEqual(cash.stagePriorities,{});
  assert.equal(JSON.stringify(original),snapshot,"No destructive legacy data changes");
  assert.deepEqual(detachGemAssociations(active),active,"idempotent on saved active Pool data");
});

test("GEM/FS/FA descriptor associations do not leak into active Pool definitions", () => {
  const active = detachGemAssociations(defaultCatalogEntries());
  assert.ok(active.every(entry => poolRuleDefinition(entry).associations.length === 0));
  assert.ok(active.every(entry => !/(GEM JR|GEM|FS\\s*\\/\\s*FA)/i.test(poolRuleDefinition(entry).help)));
  assert.ok(active.every(entry => ["Pipeline restriction","Pool: available restriction"].includes(poolRuleDefinition(entry).category)));
});
