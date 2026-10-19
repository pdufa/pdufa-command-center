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
 const chart=workspace.indexOf('<div className="wt-screenwide-chart" id={"wt-chart-"+programId}>');
 const entry=workspace.indexOf('<div className="wt-screenwide-entry" id={"wt-entry-info-"+programId}>');
 const data=workspace.indexOf('<div className="wt-screenwide-data" id={"wt-score-info-"+programId}>');
 assert.ok(entry>=0&&chart>entry&&data>chart,"Chart has a separate full-width block before data");
 const segment=workspace.slice(entry,data);
 assert.match(segment,/<EntrySignal ticker=\{ticker\} programId=\{programId\}\/>/);
 assert.match(segment,/<AlpacaStockChart ticker=\{ticker\} programId=\{programId\} wtIndicatorKeys=/);
 assert.match(segment,/<\/div>\s*<div className="wt-screenwide-chart"/,"Chart is not inside entry");
 assert.match(workspace,/<\/div>\s*<div className="wt-screenwide-data" id=\{"wt-score-info-"\+programId\}/,"Data does not contain chart");
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
test("WT keeps current score panels while removing all Streamlit reference tables",()=>{
 assert.match(rule(".wt-page .wt-screenwide-data > .wt-score-details"),/width:100%/);
 assert.match(rule(".wt-page .wt-screenwide-data .wt-score-details .research-score-cards"),
   /grid-template-columns:repeat\(auto-fit,minmax\(min\(100%,190px\),1fr\)\)/);
 assert.match(workspace,/WT INDICATOR ENTRY &amp; EXIT SCORES/);
 assert.match(workspace,/<WTIndicatorDetails programId=\{programId\}/);
 assert.match(workspace,/<TechnicalPanel record=\{r\}\/>/);
 assert.match(workspace,/<PriorityIndicators record=\{r\}\/>/);
 assert.doesNotMatch(workspace,/IndicatorParityTables|STREAMLIT REFERENCE|STREAMLIT WATCHLIST/);
 assert.ok(!layout.includes(".gem-profile-masonry"),"GEM layout remains unchanged");
});
test("All WT program controls, research indicators and charts remain",()=>{
 for(const term of [
  '<WtTradingSections key={programId+"|"+selectedStage}',
  '<div className="wt-screenwide-stages">',
  '<div className="wt-screenwide-list">',
  '<article className="wt-screenwide-stock"',
  "<EntrySignal ticker={ticker} programId={programId}/>",
  "<AlpacaStockChart ticker={ticker} programId={programId} wtIndicatorKeys=",
  "<WTIndicatorDetails programId={programId} record={selectedRecord} ticker={ticker} />",
  "MOVE PROGRAM TO TRADING RESEARCH",
  "RETURN PROGRAM TO WATCHLIST",
  "REMOVE PROGRAM TAG"
 ])assert.ok(workspace.includes(term),term);
});
