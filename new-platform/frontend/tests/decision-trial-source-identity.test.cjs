const {test} = require("node:test");
const assert = require("node:assert/strict");
const {readFileSync} = require("node:fs");
const {join} = require("node:path");

// Compile the isolated TS module with the existing TypeScript package,
// without depending on a new runtime or network service.
const ts = require("typescript");
const {Module} = require("node:module");
const source = readFileSync(join(__dirname, "../lib/decision-trial-source-identity.ts"), "utf8");
const js = ts.transpileModule(source, {compilerOptions:{module:ts.ModuleKind.CommonJS, target:ts.ScriptTarget.ES2022}}).outputText;
const m = new Module("decision-trial-source-identity", module);
m.filename = "decision-trial-source-identity.js";
m.paths = module.paths;
m._compile(js, m.filename);
const {validatePrimaryTrialSourceIdentity: validate} = m.exports;
const expected = {trialId:"NCT05535946", protocolId:"ABX464-107"};

test("accept exact ABTECT maintenance identity", () => {
  assert.doesNotThrow(() => validate(expected, {...expected}));
});
test("reject ABTECT-2 induction NCT", () => {
  assert.throws(() => validate(expected, {trialId:"NCT05507216", protocolId:"ABX464-107"}));
});
test("reject induction protocol despite matching NCT", () => {
  assert.throws(() => validate(expected, {trialId:"NCT05535946", protocolId:"ABX464-106"}));
});
test("reject missing, ambiguous, and embedded identifiers", () => {
  for (const source of [
    {trialId:null, protocolId:"ABX464-107"},
    {trialId:"NCT05535946 NCT05507216", protocolId:"ABX464-107"},
    {trialId:"NCT05535946", protocolId:"ABX464-107 / ABX464-106"},
    {trialId:"https://clinicaltrials.gov/study/NCT05535946", protocolId:"ABX464-107"},
  ]) assert.throws(() => validate(expected, source));
});
