const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");

const workspace=fs.readFileSync(path.join(__dirname,"../app/Workspace.tsx"),"utf8");
const css=fs.readFileSync(path.join(__dirname,"../app/globals.css"),"utf8");
const layout=css.slice(css.lastIndexOf("/* WT screen-width charts with responsive multiple-column DATA."));
function rule(selector){
 const escaped=selector.replace(/[.*+?^${}()|[\]\\]/g,"\\$&");
 const match=layout.match(new RegExp(escaped+"\\s*\\{([^}]+)\\}"));
 assert.ok(match,"Missing WT scoped rule: "+selector);
 return match[1];
}
test("WT stock charts are full-view charts, not compact masonry thumbnails",()=>{
 assert.match(workspace,/<AlpacaStockChart ticker=\{ticker\} programId=\{programId\} \/>/);
 assert.doesNotMatch(workspace,/<AlpacaStockChart ticker=\{ticker\} programId=\{programId\} compact \/>/);
 assert.match(rule(".wt-page .wt-panels"),/grid-template-columns:\s*minmax\(0,1fr\)/);
 assert.match(rule(".wt-page .wt-program-masonry"),/display:grid/);
 assert.match(rule(".wt-page .wt-program-masonry > .wt-stock"),/width:100%/);
 assert.match(rule(".wt-page .wt-stock .alpaca-stock-chart"),/grid-column:1\/-1/);
});
test("WT-only data tables flow into multiple columns without changing GEM layouts",()=>{
 const data=rule(".wt-page .wt-stock .indicator-tables-separate");
 assert.match(data,/display:grid/);
 assert.match(data,/grid-template-columns:repeat\(auto-fit,minmax\(min\(100%,620px\),1fr\)\)/);
 assert.match(rule(".wt-page .wt-stock .indicator-tables-separate > header"),/grid-column:1\/-1/);
 assert.match(rule(".wt-page .wt-stock .indicator-tables-separate > .table-scroll"),/min-width:0/);
 assert.match(rule(".wt-page .wt-stock .indicator-tables-separate > .entryexit-table-grid"),/grid-template-columns:minmax\(0,1fr\)/);
 assert.match(rule(".wt-page .wt-stock .indicator-tables-separate > .eight-indicators"),/min-width:0/);
 assert.match(layout,/@media \(max-width:700px\)/);
 assert.match(layout,/\.wt-page \.wt-stock \.indicator-tables-separate\s*\{\s*grid-template-columns:minmax\(0,1fr\)/);
 assert.ok(!layout.includes(".gem-profile-masonry"),"New layout rules must not alter GEM/JR");
});
test("Existing WT controls, data providers and entry/stay/exit checklist remain",()=>{
 for(const expected of ["<WtTopChecklist programs={trackedWtPrograms}/>","<EntrySignal ticker={ticker} programId={programId}/>","<WTIndicatorDetails programId={programId} record={selectedRecord} ticker={ticker} />",
  '<div className="wt-panels">','<div className="wt-program-masonry">'])assert.ok(workspace.includes(expected),expected);
});
