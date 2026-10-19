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
  '<IndicatorParityTables programId={programId} tech={x}',
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
 assert.match(html,/The two buttons operate independently/);
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

test("FS and FA buttons are visible as soon as an individual WT stage checklist opens",()=>{
 const {nextWtPresetSelection}=require("../app/WtTradingSections.tsx");
 for(const [stage,count] of [["entry",10],["stay",7],["exit",9]]){
  const html=renderToStaticMarkup(React.createElement(WtSections,{
   programId:"PDUFA-000005",ticker:"TEST",activeGroup:stage,compact:true,checkedKeys:[]
  }));
  assert.match(html,/role="group"/);
  assert.match(html,/>FS<\/button>/);
  assert.match(html,/>FA<\/button>/);
  assert.match(html,/aria-pressed="false"/);
  assert.match(html, new RegExp('FS — toggle suggested '+stage.toUpperCase()));
  assert.match(html, new RegExp('FA — toggle all available '+stage.toUpperCase()));
  assert.equal((html.match(/type="checkbox"/g)||[]).length,count);
  const suggested=nextWtPresetSelection([],stage,"FS");
  assert.ok(suggested.length>0&&suggested.length<count,"FS chooses a curated subset");
  assert.deepEqual(nextWtPresetSelection(suggested,stage,"FS"),[],"FS toggles back off");
  const all=nextWtPresetSelection([],stage,"FA");
  assert.equal(all.length,count,"FA checks all options");
  assert.deepEqual(nextWtPresetSelection(all,stage,"FA"),[],"FA toggles back off");
  assert.deepEqual(nextWtPresetSelection(["unrelated"],stage,"FA").filter(x=>x==="unrelated"),["unrelated"]);
 }
 const old=renderToStaticMarkup(React.createElement(WtSections,{
  programId:"PDUFA-000005",ticker:"TEST"
 }));
 assert.doesNotMatch(old,/>FS<\/button>|>FA<\/button>/,"Non-WT checklists are unchanged");
});

test("FS and FA are one adjacent nonwrapping button pair in WT checklist heading",()=>{
 const html=renderToStaticMarkup(React.createElement(WtSections,{
  programId:"PDUFA-000009",ticker:"TEST",activeGroup:"entry",compact:true,checkedKeys:[]
 }));
 assert.match(html,/<div class="wt-checklist-heading-text">/);
 assert.match(html,/<div class="wt-checklist-preset-buttons" role="group" aria-label="FS and FA together/);
 assert.match(html, /<div class="wt-checklist-preset-buttons"[^>]*>\s*<button[^>]*>FS<\/button>\s*<button[^>]*>FA<\/button>\s*<\/div>/);
 const css=fs.readFileSync(path.join(__dirname,"../app/globals.css"),"utf8");
 assert.match(css,/\.wt-page \.wt-trial-indicator-panel \.wt-checklist-preset-buttons \{\s*display:inline-flex;flex:0 0 auto;flex-wrap:nowrap;/);
 assert.match(css,/\.wt-checklist-preset-button:first-child \{\s*border-right:0;/);
 assert.match(css,/@media\(max-width:700px\) \{\s*\.wt-page \.wt-trial-indicator-panel \.wt-checklist-preset-buttons \{\s*flex-wrap:nowrap;/);
});

test("FS and FA preset states operate independently even when checklist options overlap",()=>{
 const {nextWtPresetFlags,wtEffectivePresetKeys}=require("../app/WtTradingSections.tsx");
 for(const [stage,count] of [["entry",10],["stay",7],["exit",9]]){
  const off={fs:false,fa:false};
  const fs=nextWtPresetFlags(off,"FS");
  assert.deepEqual(fs,{fs:true,fa:false},"FS must not trigger FA");
  const fa=nextWtPresetFlags(off,"FA");
  assert.deepEqual(fa,{fs:false,fa:true},"FA must not trigger FS");
  assert.equal(wtEffectivePresetKeys([],stage,fa).length,count);
  const both=nextWtPresetFlags(fs,"FA");
  assert.deepEqual(both,{fs:true,fa:true});
  assert.equal(wtEffectivePresetKeys([],stage,both).length,count);
  assert.deepEqual(wtEffectivePresetKeys([],stage,nextWtPresetFlags(both,"FA")),
    wtEffectivePresetKeys([],stage,fs),"Turning off FA leaves FS choices");
  assert.deepEqual(wtEffectivePresetKeys([],stage,nextWtPresetFlags(both,"FS")),
    wtEffectivePresetKeys([],stage,fa),"Turning off FS leaves FA choices");
  assert.equal(wtEffectivePresetKeys([],stage,nextWtPresetFlags(fa,"FA")).length,0);
  for(const [flags,expectedFs,expectedFa] of [
   [fa,"false","true"],[fs,"true","false"],[both,"true","true"]
  ]){
   const html=renderToStaticMarkup(React.createElement(WtSections,{
    programId:"PDUFA-000009",ticker:"TEST",activeGroup:stage,compact:true,
    checkedKeys:wtEffectivePresetKeys([],stage,flags),presetFlags:flags,
    onPresetToggle:()=>{}
   }));
   const buttons=html.match(/<div class="wt-checklist-preset-buttons"[^>]*>(.*?)<\/div>/s);
   assert.ok(buttons,"Joined FS / FA control must exist");
   const rendered=buttons[1].match(/<button[^>]*aria-pressed="(true|false)"[^>]*>(FS|FA)<\/button>/g);
   assert.equal(rendered.length,2,"Both buttons remain independently clickable");
   assert.match(rendered[0],new RegExp('aria-pressed="'+expectedFs+'"'));
   assert.match(rendered[1],new RegExp('aria-pressed="'+expectedFa+'"'));
  }
 }
});

test("WT saves explicit per-stage preset flags rather than deriving both buttons from selected checkboxes",()=>{
 const source=fs.readFileSync(path.join(__dirname,"../app/Workspace.tsx"),"utf8");
 assert.match(source,/presetFlags=\{preference\.presets\[selectedStage\]\}/);
 assert.match(source,/onPresetToggle=\{mode=>toggleWtTrialPreset\(programId,selectedStage,mode\)\}/);
 assert.match(source,/const flags=nextWtPresetFlags\(prior\.presets\[stage\],mode\)/);
 assert.match(source,/keys:\{\.\.\.prior\.keys,\[stage\]:wtEffectivePresetKeys\(prior\.manualKeys\[stage\],stage,flags\)\}/);
 assert.match(source,/presets:\{\.\.\.prior\.presets,\[stage\]:\{fs:false,fa:false\}\}/);
 assert.match(source,/manualKeys/);
});
