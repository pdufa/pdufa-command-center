const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const ts=require("typescript");
const React=require("react");
const {renderToStaticMarkup}=require("react-dom/server");

for(const extension of [".ts",".tsx"]){
 require.extensions[extension]=(loaded,file)=>{
  const compiled=ts.transpileModule(fs.readFileSync(file,"utf8"),{
   compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,
    jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}
  }).outputText;
  loaded._compile(compiled,file);
 };
}
const base=require("../lib/wt-entry-stay-exit.ts");
const WtSections=require("../app/WtTradingSections.tsx").default;
const WtTopChecklist=require("../app/WtTopChecklist.tsx").default;
const today=new Date("2026-10-18T19:00:00Z");

function data(){
 const days=[];
 for(let ms=Date.parse("2026-10-16T00:00:00Z");days.length<85;ms-=86400000){
  const d=new Date(ms);
  if(d.getUTCDay()!==0&&d.getUTCDay()!==6)days.push(d.toISOString().slice(0,10));
 }
 days.reverse();
 const bars=days.map((d,i)=>{
  const price=18+i*.06;
  return {date:d,open:price,high:price+.3,low:price-.3,close:price,volume:100000+i*30};
 });
 return {provider:"ALPACA",ticker:"ABCD",programId:"PDUFA-000001",status:"OK",
  feed:"IEX",adjustment:"raw",asOf:bars.at(-1).date,bars};
}

test("WT sections use exact three requested titles and every checkbox begins unselected",()=>{
 const page=renderToStaticMarkup(React.createElement(WtSections,{
  programId:"PDUFA-000001",ticker:"ABCD",record:{ticker:"ABCD",id:"APPLICATION|ABCD"}
 }));
 const titles=["ENTRY — Buy Setup","STAY — Hold Monitoring","EXIT — Sell / Risk Protection"];
 for(const title of titles)assert.ok(page.includes(title),title);
 assert.match(page,/0\/10 selected/);
 assert.match(page,/0\/7 selected/);
 assert.match(page,/0\/9 selected/);
 assert.match(page,/0 of 26 selected/);
 assert.equal((page.match(/aria-expanded="false"/g)||[]).length,3);
 assert.doesNotMatch(page,/aria-expanded="true"/);
 assert.deepEqual(base.WT_GROUPS.map(g=>g.items.length),[10,7,9]);
 assert.equal(new Set(base.WT_CHECK_KEYS).size,26);
});

test("Alpaca metrics need 61 valid, dated, complete and recent bars",()=>{
 const bars=data();
 const result=base.sessionSnapshot(bars,today);
 assert.ok(result);
 assert.equal(result.feed,"IEX");
 assert.match(result.coverage,/partial-market volume/);
 assert.equal(result.asOf,"2026-10-16");
 assert.ok(result.sma20>0&&result.sma50>0&&result.atr14>0);
 assert.ok(result.avgDollarVolume20>0);
 assert.equal(result.twoClosesBelowSma20,false);
 assert.equal(base.sessionSnapshot({...bars,status:"RATE_LIMITED"},today),null);
 assert.equal(base.sessionSnapshot({...bars,bars:bars.bars.slice(-50)},today),null);
 assert.equal(base.sessionSnapshot({...bars,asOf:"2026-10-15"},today),null);
 assert.equal(base.sessionSnapshot({...bars,provider:"SAMPLE"},today),null);
 assert.equal(base.sessionSnapshot({...bars,feed:"mock"},today),null);
 assert.equal(base.sessionSnapshot(bars,new Date("2026-11-12T19:00:00Z")),null);
});

test("two complete closes below SMA20 and prior range are explicitly computed",()=>{
 const x=data();
 for(let i=x.bars.length-2;i<x.bars.length;i++){
  x.bars[i].close=x.bars[i].open-(i===x.bars.length-1?6:4);
  x.bars[i].low=x.bars[i].close-.3;
 }
 const result=base.sessionSnapshot(x,today);
 assert.ok(result);
 assert.equal(result.twoClosesBelowSma20,true);
 assert.equal(result.supportHold,false);
 assert.equal(result.breakout,false);
});

test("missing, mixed, or malformed candles fail closed instead of manufacturing values",()=>{
 const x=data();
 x.bars[25]={...x.bars[25],volume:NaN};
 assert.equal(base.sessionSnapshot(x,today),null);
 const y=data();
 y.bars[42].date=y.bars[41].date;
 assert.equal(base.sessionSnapshot(y,today),null);
 const z=data();
 z.bars.at(-1).close=0;
 assert.equal(base.sessionSnapshot(z,today),null);
});

test("PDUFA T-minus calculations are labeled reported and based on Pacific calendar",()=>{
 assert.equal(base.pdufaDays("2026-11-20",today),33);
 assert.equal(base.pdufaDays("",today),null);
 assert.equal(base.pdufaDays("UNKNOWN",today),null);
});

test("WT keeps program management, scoped indicator checkboxes and full-width charts",()=>{
 const src=fs.readFileSync(path.join(__dirname,"../app/Workspace.tsx"),"utf8");
 for(const term of [
  '<AlpacaStockChart ticker={ticker} programId={programId} wtIndicatorKeys={chartIndicatorKeys} />',
  'MOVE PROGRAM TO TRADING RESEARCH',
  'RETURN PROGRAM TO WATCHLIST',
  'REMOVE PROGRAM TAG',
  'WT INDICATOR ENTRY &amp; EXIT SCORES',
  'Chart indicator stage for ',
  '<WtTradingSections key={programId+"|"+selectedStage}'
 ])assert.ok(src.includes(term),term);
 assert.ok(!src.includes('<WtTopChecklist programs='),"Shared top checklist should be removed");
 const checkboxSrc=fs.readFileSync(path.join(__dirname,"../app/WtTradingSections.tsx"),"utf8");
 assert.ok(checkboxSrc.includes('type="checkbox" checked={checked.includes(item.key)}'));
 assert.ok(checkboxSrc.includes("shownGroups.map"),"Only selected stage checkboxes render");
 assert.ok(checkboxSrc.includes('activeGroup?:GroupId'));
 assert.ok(!checkboxSrc.includes("method:\"POST\""));
});

test("Each trial can select ENTRY STAY EXIT or NONE beside its ticker",()=>{
 const src=fs.readFileSync(path.join(__dirname,"../app/Workspace.tsx"),"utf8");
 for(const stage of ['<option value="">NONE — price only</option>',
  '<option value="entry">ENTRY — Buy setup</option>',
  '<option value="stay">STAY — Hold monitoring</option>',
  '<option value="exit">EXIT — Risk protection</option>']){
  assert.ok(src.includes(stage),stage);
 }
 const ticker=src.indexOf('<h3>{ticker||"SOURCE NOT CURRENT"}</h3>');
 const dropdown=src.indexOf('className="wt-stage-selector"',ticker);
 const chart=src.indexOf('<div className="wt-screenwide-chart"',dropdown);
 assert.ok(ticker>=0&&dropdown>ticker&&chart>dropdown,
  "Stage dropdown must be beside the ticker, before the independent chart");
 assert.match(src,/keys:\{\.\.\.prior\.keys,\[stage\]:manual\}/);
 assert.match(src,/manualKeys:\{\.\.\.prior\.manualKeys,\[stage\]:manual\}/);
 assert.match(src,/return \{\.\.\.current,\[programId\]:\{\.\.\.prior,stage\}\}/);
 assert.doesNotMatch(src,/WT_STAGE_PRESETS|firstUse/);
 assert.match(src,/window\.localStorage\.setItem\(/);
 assert.match(src,/\^PDUFA-\\d\{6,\}\$/);
});

test("Choosing EXIT beside a ticker immediately reveals nine independent checkboxes",()=>{
 const html=renderToStaticMarkup(React.createElement(WtSections,{
  programId:"PDUFA-000001",ticker:"ABCD",activeGroup:"exit",compact:true,
  checkedKeys:["exit-rsi","exit-support"]
 }));
 assert.match(html,/EXIT — Sell \/ Risk Protection — SELECT INDICATORS/);
 assert.doesNotMatch(html,/ENTRY — Buy Setup|STAY — Hold Monitoring/);
 assert.match(html,/2\/9 selected/);
 assert.equal((html.match(/type="checkbox"/g)||[]).length,9);
 assert.equal((html.match(/checked=""/g)||[]).length,2);
 assert.doesNotMatch(html,/aria-expanded="false"/);
 assert.match(html,/FA is an independent switch with no indicators assigned/);
});

test("Selecting ENTRY or STAY immediately shows only that category's available options",()=>{
 for(const [stage,count] of [["entry",10],["stay",7]]){
  const html=renderToStaticMarkup(React.createElement(WtSections,{
   programId:"PDUFA-000002",ticker:"EFGH",activeGroup:stage,compact:true,
   checkedKeys:[]
  }));
  assert.equal((html.match(/type="checkbox"/g)||[]).length,count);
  assert.equal((html.match(/checked=""/g)||[]).length,0);
  assert.match(html,new RegExp("0/"+count+" selected"));
  assert.doesNotMatch(html,/aria-expanded="false"/);
 }
});
 
test("WT entry/stay/exit sections always start collapsed and leave all 26 choices off",()=>{
 const html=renderToStaticMarkup(React.createElement(WtTopChecklist,{programs:[]}));
 assert.match(html,/ENTRY — Buy Setup/);
 assert.match(html,/STAY — Hold Monitoring/);
 assert.match(html,/EXIT — Sell \/ Risk Protection/);
 assert.match(html,/0 of 26 selected/);
 assert.equal((html.match(/aria-expanded="false"/g)||[]).length,3);
 assert.equal((html.match(/type="checkbox"/g)||[]).length,0);
 assert.equal(base.WT_CHECK_KEYS.length,26);
});


test("FS and FA buttons display side by side with separate states and selections",()=>{
 const {nextWtPresetSelection,nextWtPresetFlags,wtEffectivePresetKeys}=require("../app/WtTradingSections.tsx");
 for(const [stage,count] of [["entry",10],["stay",7],["exit",9]]){
  const blank={fs:false,fa:false};
  const fsFlags=nextWtPresetFlags(blank,"FS");
  const faFlags=nextWtPresetFlags(blank,"FA");
  assert.deepEqual(fsFlags,{fs:true,fa:false},"FS activates only FS");
  assert.deepEqual(faFlags,{fs:false,fa:true},"FA activates only FA");
  const fsKeys=wtEffectivePresetKeys([],stage,fsFlags);
  const faKeys=wtEffectivePresetKeys([],stage,faFlags);
  assert.ok(fsKeys.length>0&&fsKeys.length<count);
  assert.equal(faKeys.length,0,"FA is unassigned");
  assert.deepEqual(nextWtPresetSelection([],stage,"FA"),[],"Unassigned FA fallback must not check indicators");
  assert.deepEqual(wtEffectivePresetKeys([],stage,nextWtPresetFlags(fsFlags,"FS")),[]);
  assert.deepEqual(wtEffectivePresetKeys([],stage,nextWtPresetFlags(faFlags,"FA")),[]);
  const both=nextWtPresetFlags(fsFlags,"FA");
  assert.deepEqual(both,{fs:true,fa:true});
  assert.deepEqual(wtEffectivePresetKeys([],stage,nextWtPresetFlags(both,"FA")),fsKeys,
   "Turning off FA preserves FS");
  assert.deepEqual(wtEffectivePresetKeys([],stage,nextWtPresetFlags(both,"FS")),[],
   "Turning off FS leaves no chart indicators from FA");
  const manual=["other-stage",fsKeys[0]];
  assert.deepEqual(wtEffectivePresetKeys(manual,stage,blank),[fsKeys[0]],"Manual checks remain independent");
  const rendered=renderToStaticMarkup(React.createElement(WtSections,{
   programId:"PDUFA-000005",ticker:"TEST",activeGroup:stage,compact:true,
   checkedKeys:fsKeys,presetFlags:fsFlags,onPresetToggle:()=>{}
  }));
  assert.match(rendered,/>FS<\/button>/);
  assert.match(rendered,/>FA<\/button>/);
  assert.equal((rendered.match(/type="checkbox"/g)||[]).length,count);
  const controls=rendered.match(/<div class="wt-checklist-preset-buttons"[^>]*>([\s\S]*?)<\/div>/);
  assert.ok(controls,"Both controls appear in same nonwrapping group");
  const individual=controls[1].match(/<button[^>]*>FS<\/button>|<button[^>]*>FA<\/button>/g)||[];
  assert.equal(individual.length,2);
  assert.match(individual[0],/aria-pressed="true"/);
  assert.match(individual[1],/aria-pressed="false"/);
  assert.match(rendered,/FA — no indicators assigned/);
  assert.equal(faKeys.length,0);
 }
 const source=fs.readFileSync(path.join(__dirname,"../app/Workspace.tsx"),"utf8");
 assert.match(source,/presetFlags=\{preference\.presets\[selectedStage\]\}/);
 assert.match(source,/function toggleWtTrialPreset\(programId:string,stage:WtTrialStage,mode:"FS"\|"FA"\)/);
 assert.match(source,/:nextWtPresetFlags\(prior\.presets\[stage\],"FA"\)/);
 const css=fs.readFileSync(path.join(__dirname,"../app/globals.css"),"utf8");
 assert.match(css,/\.wt-checklist-preset-button:first-child \{\s*border-right:0/);
 assert.match(css,/display:inline-flex;flex:0 0 auto;flex-wrap:nowrap/);
});

test("ENTRY FS preset is exactly the five requested signal and trade-risk indicators",()=>{
 const {suggestedWtIndicators,areWtSuggestedIndicatorsChecked,wtEffectivePresetKeys}=require("../app/WtTradingSections.tsx");
 const chosen=["entry-score","entry-breakout","entry-dollar","entry-trigger","entry-stop"];
 assert.deepEqual(suggestedWtIndicators.entry,chosen);
 assert.deepEqual(wtEffectivePresetKeys([],"entry",{fs:true,fa:false}),chosen);
 assert.equal(areWtSuggestedIndicatorsChecked(chosen,"entry"),true);
 assert.equal(areWtSuggestedIndicatorsChecked(chosen.slice(0,4),"entry"),false);
 assert.equal(areWtSuggestedIndicatorsChecked(["entry-base","entry-trend","entry-rvol","entry-rsi","entry-atr"],"entry"),false);
 // Different trading stages retain their existing, independent FS presets.
 assert.deepEqual(suggestedWtIndicators.stay,["stay-trend","stay-support","stay-rsi","stay-volume"]);
 assert.deepEqual(suggestedWtIndicators.exit,["exit-two-close","exit-support","exit-atr-trail","exit-rsi"]);
});

test("ENTRY FS illuminates when the five checkboxes are selected manually and goes dark if one unchecks",()=>{
 const {suggestedWtIndicators}=require("../app/WtTradingSections.tsx");
 for(const [keys,expected] of [
  [suggestedWtIndicators.entry,"true"],
  [suggestedWtIndicators.entry.slice(1),"false"]
 ]){
  // Even when the persisted FS flag is false, selection drives active state.
  const html=renderToStaticMarkup(React.createElement(WtSections,{
   programId:"PDUFA-000333",ticker:"TEST",activeGroup:"entry",compact:true,
   checkedKeys:keys,presetFlags:{fs:false,fa:false},onPresetToggle:()=>{}
  }));
  const button=html.match(/<button[^>]*aria-label="FS — toggle suggested ENTRY[^>]*>FS<\/button>/);
  assert.ok(button,"FS button must always remain visible");
  assert.match(button[0],new RegExp('aria-pressed="'+expected+'"'));
  assert.match(html,/>FA<\/button>/,"FA button stays independently available");
 }
 const workspace=fs.readFileSync(path.join(__dirname,"../app/Workspace.tsx"),"utf8");
 assert.match(workspace,/const turnFsOff=mode==="FS"&&areWtSuggestedIndicatorsChecked\(prior\.keys\[stage\],stage\)/);
 assert.match(workspace,/manualKeys:\{\.\.\.prior\.manualKeys,\[stage\]:manual\}/);
 assert.match(workspace,/presets:\{\.\.\.prior\.presets,\[stage\]:\{\.\.\.prior\.presets\[stage\],fs:false\}\}/);
});

test("Legacy Streamlit reference indicator and eight-signal tables are absent from all pages",()=>{
 const workspace=fs.readFileSync(path.join(__dirname,"../app/Workspace.tsx"),"utf8");
 assert.doesNotMatch(workspace,/IndicatorParityTables|STREAMLIT REFERENCE|STREAMLIT WATCHLIST/);
 assert.match(workspace,/WT INDICATOR ENTRY &amp; EXIT SCORES/);
 assert.match(workspace,/<WTIndicatorDetails programId=\{programId\}/);
 assert.match(workspace,/<PriorityIndicators record=\{r\}/);
 assert.match(workspace,/<TechnicalPanel record=\{r\}/);
});

test("Every ENTRY STAY EXIT checklist item explicitly marks its information location in red",()=>{
 const {WT_INFO_LOCATIONS}=require("../app/WtTradingSections.tsx");
 assert.deepEqual(Object.keys(WT_INFO_LOCATIONS).sort(),base.WT_CHECK_KEYS.slice().sort(),
  "No WT indicator lacks an info location");
 const targetCounts={entry:10,stay:7,exit:9};
 for(const stage of ["entry","stay","exit"]){
  const html=renderToStaticMarkup(React.createElement(WtSections,{
   programId:"PDUFA-000111",ticker:"TEST",activeGroup:stage,compact:true,
   checkedKeys:[]
  }));
  assert.equal((html.match(/class="wt-where-info"/g)||[]).length,targetCounts[stage]);
  assert.equal((html.match(/WHERE TO SEE INFO:/g)||[]).length,targetCounts[stage]);
  assert.equal((html.match(/class="wt-where-link"/g)||[]).length,targetCounts[stage]);
  assert.equal((html.match(/class="wt-where-reading"/g)||[]).length,targetCounts[stage]);
  assert.equal((html.match(/type="checkbox"/g)||[]).length,targetCounts[stage]);
  assert.match(html,/ACTUAL:/);
 }
 const entry=renderToStaticMarkup(React.createElement(WtSections,{
  programId:"PDUFA-000111",ticker:"TEST",activeGroup:"entry",compact:true
 }));
 assert.match(entry,/href="#wt-entry-info-PDUFA-000111"/);
 assert.match(entry,/href="#wt-chart-PDUFA-000111"/);
 assert.match(entry,/id="wt-reading-PDUFA-000111-entry-dollar"/);
 assert.match(entry,/REFRESH ALPACA \/ ENTRY DATA/);
 const exit=renderToStaticMarkup(React.createElement(WtSections,{
  programId:"PDUFA-000111",ticker:"TEST",activeGroup:"exit",compact:true
 }));
 assert.match(exit,/href="#wt-score-info-PDUFA-000111"/);
 assert.match(exit,/No backtested price plateau detector exists/);
 const workspace=fs.readFileSync(path.join(__dirname,"../app/Workspace.tsx"),"utf8");
 assert.match(workspace,/id=\{"wt-entry-info-"\+programId\}/);
 assert.match(workspace,/id=\{"wt-score-info-"\+programId\}/);
 const styles=fs.readFileSync(path.join(__dirname,"../app/globals.css"),"utf8");
 assert.match(styles,/\.wt-where-info \{[\s\S]*?border-left:4px solid #bb2026/);
 assert.match(styles,/\.wt-where-link \{[\s\S]*?color:#aa1620/);
 assert.match(styles,/\.wt-where-reading \{/);
});

test("Numeric WT indicator values are bold black while source labels and unavailable statuses stay red",()=>{
 const {wtNumericReadingParts}=require("../app/WtTradingSections.tsx");
 for(const [sample,expected] of [
  ["$23.45 close vs prior high $24.61 · ABOVE",["$23.45","$24.61"]],
  ["1.53× (IEX partial volume)",["1.53×"]],
  ["Trigger $10.24 · Max $10.87 · API snapshot",["$10.24","$10.87"]],
  ["82/100 · Entry API WAIT",["82/100"]],
  ["-$0.45 · trigger-to-stop 2.36%",["-$0.45","2.36%"]],
  ["Close $12.75 · SMA20 $11.90 · SMA50 $10.08",["$12.75","$11.90","$10.08"]],
  ["2026-10-18 · 30 calendar days",["2026","30"]]
 ]){
  assert.deepEqual(wtNumericReadingParts(sample).filter(p=>p.numeric).map(p=>p.text),expected);
  assert.equal(wtNumericReadingParts(sample).map(p=>p.text).join(""),sample);
 }
 for(const text of ["UNSCORED · Entry API UNAVAILABLE","NOT VERIFIED — No confirmed stop",
  "SMA20 RSI14 20d average and 10-session base"]){
  assert.equal(wtNumericReadingParts(text).filter(p=>p.numeric).length,0);
  assert.equal(wtNumericReadingParts(text).map(p=>p.text).join(""),text);
 }
 const rendered=renderToStaticMarkup(React.createElement(WtSections,{
  programId:"PDUFA-000111",ticker:"TEST",activeGroup:"entry",compact:true,
  tech:{indicatorEntry:82}
 }));
 assert.match(rendered,/class="wt-indicator-number">82\/100<\/strong>/);
 assert.match(rendered,/WHERE TO SEE INFO:/);
 assert.match(rendered,/ACTUAL:/);
 assert.match(rendered,/NOT VERIFIED/);
 const styles=fs.readFileSync(path.join(__dirname,"../app/globals.css"),"utf8");
 assert.match(styles,/\.wt-where-reading \.wt-indicator-number \{\s*color:#111111/);
 assert.match(styles,/\.wt-where-heading[\s\S]*?color:#aa1620/);
});
