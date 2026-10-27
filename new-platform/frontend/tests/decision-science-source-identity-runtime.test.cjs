const { test } = require("node:test");
const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { join } = require("node:path");
const { Module } = require("node:module");
const ts = require("typescript");
const cache = new Map();
function load(name) {
  if (cache.has(name)) return cache.get(name).exports;
  const filename = join(__dirname, "../lib", name + ".ts");
  const source = readFileSync(filename, "utf8");
  const compiled = ts.transpileModule(source, {compilerOptions: {module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022}}).outputText;
  const mod = new Module(filename, module);
  mod.filename = filename;
  mod.paths = module.paths;
  cache.set(name, mod);
  mod.require = id => id.startsWith("./decision-") ? load(id.slice(2)) : require(id);
  mod._compile(compiled, filename);
  return mod.exports;
}
const { parseScienceInvestigation } = load("decision-science-investigation");
const identity = {exactKey:"ABVX",programId:"ABX464",trialId:"NCT05535946",ticker:"ABVX",stage:"PIPELINE"};
const source = {url:"https://clinicaltrials.gov",publishedAt:"2026-06-01T00:00:00Z",observedAt:"2026-10-26T00:00:00Z",independentlyReviewed:false};
function input(primaryTrial) {
  const s = {...source};
  if (primaryTrial !== undefined) s.primaryTrial = primaryTrial;
  return {identity,asOf:"2026-10-27T00:00:00Z",drug:"obefazimod",indication:"UC",companyCik:"0000000001",fdaApplication:null,layers:[],levels:[{id:"L1",label:"L1",layerId:"S1",assessments:[{id:"A1",status:"PARTIAL",reviewer:"",criticalEvaluation:"",uncertainty:"",unresolvedCriticalFindings:1,sources:[s]}]}]};
}
test("accept matching primary trial identity", () => {
  assert.doesNotThrow(() => parseScienceInvestigation(input({trialId:"NCT05535946",protocolId:"ABX464-107"})));
});
test("reject cross-trial NCT identity", () => {
  assert.throws(() => parseScienceInvestigation(input({trialId:"NCT05507216",protocolId:"ABX464-107"})), /mismatch/);
});
test("reject malformed primary metadata", () => {
  assert.throws(() => parseScienceInvestigation(input({trialId:"NCT05535946"})));
});
test("accept legacy source without optional metadata", () => {
  assert.doesNotThrow(() => parseScienceInvestigation(input()));
});
