const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const ts=require("typescript");
const React=require("react");
const {act,create}=require("react-test-renderer");
global.IS_REACT_ACT_ENVIRONMENT=true;
for(const ext of [".ts",".tsx"])require.extensions[ext]=(mod,file)=>mod._compile(
  ts.transpileModule(fs.readFileSync(file,"utf8"),{compilerOptions:{
    module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,
    jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true
  }}).outputText,file);
require.extensions[".css"]=mod=>{mod.exports=new Proxy({},{get:(_x,key)=>String(key)});};
const catalog=require("../lib/restriction-catalog.ts");
const {goalRestrictionSummaries}=require("../lib/goal-restrictions.ts");
const GoalDashboard=require("../app/GoalDashboard.tsx").default;

test("GOAL mirrors existing saved Pipeline restrictions, priorities and market-cap limits",()=>{
  const defaults=catalog.defaultCatalogEntries();
  const unchanged=structuredClone(defaults);
  const groups=goalRestrictionSummaries(defaults);
  assert.deepEqual(defaults,unchanged,"GOAL may never mutate stored thresholds");
  assert.ok(groups.PIPELINE.length>=4);
  assert.ok(groups.PIPELINE.some(x=>x.id==="minCap"&&/\$300M/.test(x.valueLabel)));
  assert.ok(groups.PIPELINE.some(x=>x.id==="maxCap"&&/\$10B/.test(x.valueLabel)));
  assert.ok(groups.PIPELINE.some(x=>x.id==="phase"&&/3/.test(x.valueLabel)));
  assert.equal(groups.GEM_JR.length,0);
  assert.equal(groups.GEM.length,0);
  assert.ok(groups.PIPELINE.every(x=>x.priority&&x.title));
});

test("GOAL stage memberships match the original independent priorities and never change GEM FS/FA",()=>{
  const defaults=catalog.defaultCatalogEntries();
  const assocBefore=catalog.RESTRICTION_CATALOG.map(x=>[x.id,x.associations]);
  const gemJr=catalog.insertRestrictionIntoList(defaults,"gem_volume","GEM_JR",0);
  const both=catalog.insertRestrictionIntoList(gemJr,"gem_volume","GEM",0);
  const before=structuredClone(both);
  const all=goalRestrictionSummaries(both);
  assert.deepEqual(both,before);
  assert.ok(all.GEM_JR.some(x=>x.id==="gem_volume"));
  assert.ok(all.GEM.some(x=>x.id==="gem_volume"));
  assert.ok(!all.PIPELINE.some(x=>x.id==="gem_volume"));
  const removeJr=catalog.removeRestrictionFromList(both,"gem_volume","GEM_JR");
  const after=goalRestrictionSummaries(removeJr);
  assert.ok(!after.GEM_JR.some(x=>x.id==="gem_volume"));
  assert.ok(after.GEM.some(x=>x.id==="gem_volume"));
  assert.deepEqual(catalog.RESTRICTION_CATALOG.map(x=>[x.id,x.associations]),assocBefore);
});

test("GOAL shows collapsible per-stage restrictions, saved priorities, and opens central controls",async()=>{
  const entries=catalog.defaultCatalogEntries();
  const groups=goalRestrictionSummaries(entries);
  const navigation=[];
  const originalFetch=global.fetch;
  global.fetch=async()=>({ok:false,status:503,json:async()=>({error:"unavailable"})});
  let tree;
  try{
    await act(async()=>{tree=create(React.createElement(GoalDashboard,{
      records:[],pipelineCount:100,gemJrCount:0,gemCount:0,
      restrictions:groups,onOpen:section=>navigation.push(section)
    }));});
    const pipeline=tree.root.findByProps({"aria-label":"Pipeline saved restriction preview"});
    assert.match(pipeline.findByType("summary").children.join(""),/Active restrictions/);
    assert.ok(pipeline.findAllByType("li").length>=4);
    assert.match(JSON.stringify(tree.toJSON()),/\$300M/);
    assert.match(JSON.stringify(tree.toJSON()),/\$10B/);
    assert.equal(tree.root.findAllByProps({"aria-label":"GEM JR saved restriction preview"}).length,0);
    assert.equal(tree.root.findAllByProps({"aria-label":"GEM saved restriction preview"}).length,0);
    const buttons=tree.root.findAllByType("button").filter(x=>x.props.children==="Open restriction controls →");
    assert.equal(buttons.length,1);
    await act(async()=>{buttons[0].props.onClick();});
    assert.deepEqual(navigation,["RESTRICTIONS"]);
  }finally{
    if(tree)await act(async()=>tree.unmount());
    global.fetch=originalFetch;
  }
});

test("GOAL does not display startup defaults as verified saved preferences until hydration",async()=>{
  const originalFetch=global.fetch;
  global.fetch=async()=>({ok:false,status:503,json:async()=>({})});
  let tree;
  try{
    await act(async()=>{tree=create(React.createElement(GoalDashboard,{
      records:null,pipelineCount:null,gemJrCount:null,gemCount:null,restrictions:null,
      onOpen:()=>{}
    }));});
    assert.match(JSON.stringify(tree.toJSON()),/Loading this browser/);
    assert.equal(tree.root.findAllByType("ol").length,0);
  }finally{if(tree)await act(async()=>tree.unmount());global.fetch=originalFetch;}
});

test("GOAL rule cards are responsive and cannot edit or activate saved rules",()=>{
  const css=fs.readFileSync(path.join(__dirname,"../app/GoalDashboard.module.css"),"utf8");
  assert.match(css,/@media\(max-width:900px\)/);
  assert.match(css,/@media\(max-width:650px\)/);
  assert.match(css,/\.ruleList\{list-style:none/);
  const ws=fs.readFileSync(path.join(__dirname,"../app/Workspace.tsx"),"utf8");
  assert.match(ws,/restrictions=\{masterRestrictionsReady \? goalRestrictionSummaries\(masterRestrictions\) : null\}/);
  const component=fs.readFileSync(path.join(__dirname,"../app/GoalDashboard.tsx"),"utf8");
  assert.doesNotMatch(component,/setMasterRestrictions|localStorage\.setItem|insertRestrictionIntoList|removeRestrictionFromList/);
});
