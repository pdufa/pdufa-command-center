const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const Module=require("node:module");
const ts=require("typescript");

const source=path.join(__dirname,"..","lib","gem-qualification-checks.ts");
const compiled=ts.transpileModule(fs.readFileSync(source,"utf8"),{
  compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020}
}).outputText;
const m=new Module(source,module);
m.filename=source;
m.paths=module.paths;
m._compile(compiled,source);
const {GEM_CLINICAL_FILTERS,GEM_TRADING_FILTERS,GEM_ALL_FILTERS,gemMatchesCheckedFilters}=m.exports;

test("GEM and GEM JR share nonoverlapping real clinical and Trading checkbox IDs",()=>{
  const clinical=GEM_CLINICAL_FILTERS.map(c=>c.key);
  const trading=GEM_TRADING_FILTERS.map(c=>c.key);
  assert.equal(new Set([...clinical,...trading]).size,clinical.length+trading.length);
  assert.equal(GEM_ALL_FILTERS.length,clinical.length+trading.length);
  assert.ok(clinical.includes("phase3_positive"));
  assert.ok(trading.includes("market_cap"));
  assert.ok(trading.includes("rvol"));
  assert.ok(trading.includes("entry_score"));
});

test("all selected Trading and clinical boxes jointly filter the exact trial program",()=>{
  const passed={id:"PROGRAM-A",ticker:"ABC",phase3Status:"VERIFIED_SUCCESS",
    technical:{benchmarks:{phase3:true,secondFinancing:false},rvol:1.8,
      entry:77,entryCoverage:61,close:18,sma20:16,sma50:15,runwayMonths:20,runwayGate:"PASS"}};
  const failed={id:"PROGRAM-B",ticker:"DEF",phase3Status:"REVIEW",
    technical:{benchmarks:{phase3:false,secondFinancing:false},rvol:2.3,
      entry:79,entryCoverage:67}};
  assert.equal(gemMatchesCheckedFilters(passed,["phase3_positive","rvol","entry_score"]),true);
  assert.equal(gemMatchesCheckedFilters(failed,["phase3_positive","rvol","entry_score"]),false);
  assert.equal(gemMatchesCheckedFilters(passed,["phase3_positive","second_financing"]),false);
});

test("default filters do not impose market cap, and missing evidence never passes",()=>{
  const missing={id:"MISSING",ticker:"TEST",technical:{}};
  assert.equal(gemMatchesCheckedFilters(missing,[]),true);
  assert.equal(gemMatchesCheckedFilters(missing,["market_cap"]),false);
  assert.equal(gemMatchesCheckedFilters(missing,["rvol"]),false);
  assert.equal(gemMatchesCheckedFilters(missing,["bogus_filter"]),false);
});

test("checkbox technical values do not confer clinical qualification by themselves",()=>{
  const strongTech={id:"STRONG",ticker:"TEST",technical:{
    rvol:3.2,sma20:15,sma50:14,close:17,entry:82,entryCoverage:80,
    benchmarks:{phase3:false,secondFinancing:false}}};
  assert.equal(gemMatchesCheckedFilters(strongTech,["rvol","sma_trend"]),true);
  assert.equal(gemMatchesCheckedFilters(strongTech,["rvol","sma_trend","phase3_positive"]),false);
});
