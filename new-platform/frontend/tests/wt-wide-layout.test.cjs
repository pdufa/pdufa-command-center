const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");

const workspace=fs.readFileSync(path.join(__dirname,"../app/Workspace.tsx"),"utf8");
const css=fs.readFileSync(path.join(__dirname,"../app/globals.css"),"utf8");
const layout=css.slice(css.lastIndexOf("/* WT V2 structural layout: NO masonry"));
function rule(selector){
 const start=layout.indexOf(selector+" {");
 assert.ok(start>=0,"Missing WT-scoped selector: "+selector);
 const bodyStart=layout.indexOf("{",start)+1;
 return layout.slice(bodyStart,layout.indexOf("}",bodyStart));
}
test("WT charts are outside old masonry/research-column containers",()=>{
 const chart=workspace.indexOf('<div className="wt-screenwide-chart">');
 const entry=workspace.indexOf('<div className="wt-screenwide-entry">');
 const data=workspace.indexOf('<div className="wt-screenwide-data">');
 assert.ok(entry>=0&&chart>entry&&data>chart,"Chart has a separate full-width block before data");
 const segment=workspace.slice(entry,data);
 assert.match(segment,/<EntrySignal ticker=\{ticker\} programId=\{programId\}\/>/);
 assert.match(segment,/<AlpacaStockChart ticker=\{ticker\} programId=\{programId\} \/>/);
 assert.match(segment,/<\/div>\s*<div className="wt-screenwide-chart">/,"Chart is not inside entry");
 assert.match(workspace,/<\/div>\s*<div className="wt-screenwide-data">/,"Data does not contain chart");
 assert.doesNotMatch(workspace,/<AlpacaStockChart ticker=\{ticker\} programId=\{programId\} compact \/>/);
 const wt=workspace.slice(workspace.indexOf('<div className="wt-screenwide-stages">'));
 assert.doesNotMatch(wt,/className="wt-program-masonry"/);
 assert.doesNotMatch(wt,/className="wt-research-column"/);
 assert.doesNotMatch(wt,/className="wt-stock"/);
});
test("Outer WT stage, list, stock and chart are all full width",()=>{
 assert.match(rule(".wt-page .wt-screenwide-stages"),/display:block/);
 assert.match(rule(".wt-page .wt-screenwide-stages > .wt-screenwide-stage"),/width:100%/);
 assert.match(rule(".wt-page .wt-screenwide-list"),/display:flex/);
 assert.match(rule(".wt-page .wt-screenwide-stock"),/grid-template-columns:minmax\(0,1fr\)/);
 assert.match(rule(".wt-page .wt-screenwide-stock > *"),/grid-column:1\/-1/);
 assert.match(rule(".wt-page .wt-screenwide-chart"),/grid-column:1\/-1/);
 assert.match(rule(".wt-page .wt-screenwide-chart > .alpaca-stock-chart"),/width:100%/);
 assert.match(rule(".wt-page .wt-screenwide-chart .alpaca-plot"),/display:block/);
});
test("WT-only data uses responsive multiple columns without changing GEM",()=>{
 const data=rule(".wt-page .wt-screenwide-data .indicator-tables-separate");
 assert.match(data,/display:grid/);
 assert.match(data,/grid-template-columns:repeat\(auto-fit,minmax\(min\(100%,540px\),1fr\)\)/);
 assert.match(rule(".wt-page .wt-screenwide-data .indicator-tables-separate > header"),/grid-column:1\/-1/);
 assert.match(rule(".wt-page .wt-screenwide-data .indicator-tables-separate > .table-scroll"),/overflow-x:auto/);
 assert.match(rule(".wt-page .wt-screenwide-data .indicator-tables-separate > .entryexit-table-grid"),/grid-template-columns:minmax\(0,1fr\)/);
 assert.match(rule(".wt-page .wt-screenwide-data .indicator-tables-separate > .eight-indicators"),/min-width:0/);
 assert.match(layout,/@media\(max-width:700px\)/);
 assert.match(layout,/\.wt-page \.wt-screenwide-data \.indicator-tables-separate\s*\{\s*grid-template-columns:minmax\(0,1fr\)/);
 assert.ok(!layout.includes(".gem-profile-masonry"),"Only WT layout changed");
});
test("All WT program controls, research indicators and charts remain",()=>{
 for(const term of [
  "<WtTopChecklist programs={trackedWtPrograms}/>",
  '<div className="wt-screenwide-stages">',
  '<div className="wt-screenwide-list">',
  '<article className="wt-screenwide-stock"',
  "<EntrySignal ticker={ticker} programId={programId}/>",
  "<AlpacaStockChart ticker={ticker} programId={programId} />",
  "<WTIndicatorDetails programId={programId} record={selectedRecord} ticker={ticker} />",
  "MOVE PROGRAM TO TRADING RESEARCH",
  "RETURN PROGRAM TO WATCHLIST",
  "REMOVE PROGRAM TAG"
 ])assert.ok(workspace.includes(term),term);
});
