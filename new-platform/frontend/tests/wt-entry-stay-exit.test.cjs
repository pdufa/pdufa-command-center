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

test("WT retains original program management controls and research charts",()=>{
 const src=fs.readFileSync(path.join(__dirname,"../app/Workspace.tsx"),"utf8");
 for(const term of ['<WtTopChecklist programs={trackedWtPrograms}/>',
  '<IndicatorParityTables programId={programId} tech={x}',
  '<AlpacaStockChart ticker={ticker} programId={programId} />',
  'MOVE PROGRAM TO TRADING RESEARCH',
  'RETURN PROGRAM TO WATCHLIST',
  'REMOVE PROGRAM TAG',
  'WT INDICATOR ENTRY &amp; EXIT SCORES']){
  assert.ok(src.includes(term),term);
 }
 const checkboxSrc=fs.readFileSync(path.join(__dirname,"../app/WtTradingSections.tsx"),"utf8");
 assert.ok(checkboxSrc.includes('useState<string[]>([])'));
 assert.ok(checkboxSrc.includes('type="checkbox" checked={checked.includes(item.key)}'));
 assert.ok(checkboxSrc.includes("Checking a box"));
 assert.ok(!checkboxSrc.includes("method:\"POST\""));
});

test("Main WT page always renders ENTRY STAY EXIT and 26 unchecked boxes with zero tagged programs",()=>{
 const html=renderToStaticMarkup(React.createElement(WtTopChecklist,{programs:[]}));
 assert.match(html,/WT — ENTRY \/ STAY \/ EXIT CHECKLISTS/);
 assert.match(html,/0 of 26 selected/);
 assert.match(html,/ENTRY — Buy Setup/);
 assert.match(html,/STAY — Hold Monitoring/);
 assert.match(html,/EXIT — Sell \/ Risk Protection/);
 assert.match(html,/No exact programs are saved in your WT Watchlist/);
 assert.equal((html.match(/type="checkbox"/g)||[]).length,0);
 assert.equal((html.match(/aria-expanded="false"/g)||[]).length,3);
 assert.doesNotMatch(html,/checked=""/);
 assert.match(html,/Choose a WT program to display its Alpaca readings/);
});

test("Top-level WT program chooser maps exact program IDs without selecting boxes",()=>{
 const html=renderToStaticMarkup(React.createElement(WtTopChecklist,{programs:[
  {programId:"PDUFA-000001",ticker:"ABCD",drug:"Drug A"},
  {programId:"PDUFA-000002",ticker:"EFGH",drug:"Drug B"}
 ]}));
 assert.match(html,/ABCD · Drug A · PDUFA-000001/);
 assert.match(html,/EFGH · Drug B · PDUFA-000002/);
 assert.match(html,/0 of 26 selected/);
 assert.equal((html.match(/type="checkbox"/g)||[]).length,0);
 assert.equal((html.match(/aria-expanded="false"/g)||[]).length,3);
 const workspace=fs.readFileSync(path.join(__dirname,"../app/Workspace.tsx"),"utf8");
 const top=workspace.indexOf('<WtTopChecklist programs={trackedWtPrograms}/>');
 const list=workspace.indexOf('<div className="wt-panels">');
 assert.ok(top>=0&&list>top,"Top WT checklists must render BEFORE per-program stock panels");
 assert.ok(!workspace.includes('<WtTradingSections key={programId+"|"+ticker}'),"Old nested section must be removed");
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
