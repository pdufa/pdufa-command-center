/** Read-only WT technical observations. Never turns a research checkbox into a trade. */
export type WtBar={date:string;open:number;high:number;low:number;close:number;volume:number};
export type WtMarket={programId:string;ticker:string;provider:string;status:string;feed:string;asOf:string|null;adjustment:string;bars:WtBar[];message?:string};
export type WtObservation={text:string;source:"ALPACA DAILY"|"SAVED RESEARCH"|"PROGRAM RECORD"|"UNAVAILABLE"};
export type WtSnapshot={
  asOf:string;feed:string;coverage:string;close:number;sma20:number;sma50:number;
  rvol20:number;rsi14:number;atr14:number;avgDollarVolume20:number;
  baseLow:number;baseHigh:number;supportHold:boolean;breakout:boolean;
  twoClosesBelowSma20:boolean;changePct:number;
};
export type WtCheck={key:string;label:string;note:string};
export type WtGroup={id:"entry"|"stay"|"exit";title:string;items:readonly WtCheck[]};
export const WT_GROUPS:readonly WtGroup[]=[
 {id:"entry",title:"ENTRY — Buy Setup",items:[
  {key:"entry-score",label:"Entry Signal / Entry Score",note:"Observed research score and current entry API status are not executed orders"},
  {key:"entry-base",label:"Base Formation",note:"10-session observed range, not a confirmed pattern"},
  {key:"entry-breakout",label:"Breakout Above Resistance",note:"Close relative to the preceding 10-session high"},
  {key:"entry-trend",label:"Closing Price vs. SMA20 / SMA50",note:"Completed Alpaca daily price observations"},
  {key:"entry-rvol",label:"Relative Volume (RVOL20)",note:"IEX-only volume cannot certify consolidated volume"},
  {key:"entry-rsi",label:"RSI14 — Momentum",note:"Wilder's 14-session momentum reading"},
  {key:"entry-dollar",label:"20-Day Average Dollar Volume",note:"Average of daily closing price × exchange-reported volume"},
  {key:"entry-atr",label:"ATR14 — Volatility",note:"Wilder's 14-session true range"},
  {key:"entry-trigger",label:"Entry Trigger / Maximum Buy Price",note:"Only when explicitly returned by the Alpaca entry research API"},
  {key:"entry-stop",label:"Initial Stop-Loss / Entry Risk",note:"Illustrative initial stop only; actual risk requires executed entry"},
 ]},
 {id:"stay",title:"STAY — Hold Monitoring",items:[
  {key:"stay-trend",label:"Price Trend — SMA20 / SMA50",note:"Alpaca daily closing-price trend, not a hold instruction"},
  {key:"stay-support",label:"Support Level Holding",note:"Close vs. preceding 10-session low; not verified multi-touch support"},
  {key:"stay-rsi",label:"RSI14 — Momentum Strength",note:"Wilder's RSI14"},
  {key:"stay-volume",label:"Relative Volume Trend",note:"Current relative volume, with feed scope disclosed"},
  {key:"stay-trailing",label:"Trailing Stop Monitoring",note:"Requires verified dated fills and a specific trail policy"},
  {key:"stay-pdufa",label:"Days Remaining to PDUFA",note:"Reported program date, not re-verified FDA action"},
  {key:"stay-signal",label:"STAY / HOLD Signal",note:"Requires actual position and tested exit rules; not inferred from a Watchlist tag"},
 ]},
 {id:"exit",title:"EXIT — Sell / Risk Protection",items:[
  {key:"exit-score",label:"EXIT Signal / Exit Risk Score",note:"Saved GEM exit-risk research, not an order"},
  {key:"exit-two-close",label:"Two Consecutive Closes Below SMA20",note:"Calculated from separate completed daily sessions"},
  {key:"exit-support",label:"Support Breakdown",note:"Close vs. preceding 10-session low; preliminary only"},
  {key:"exit-atr-trail",label:"ATR Trailing Stop",note:"Requires dated entry and a stop ledger; ATR itself is observable"},
  {key:"exit-rsi",label:"RSI / Momentum Exhaustion",note:"RSI observed; a plateau/exhaustion exit rule is not validated"},
  {key:"exit-plateau",label:"Price Plateau Detection",note:"No backtested plateau detector is deployed"},
  {key:"exit-divergence",label:"Volume–Price Divergence",note:"Price/volume observations are not a validated divergence signal"},
  {key:"exit-pdufa",label:"PDUFA Exit Deadline",note:"Provisional reported-date minus 3 days, not source-verified deadline"},
  {key:"exit-action",label:"FDA Action / Dilution Risk Warning",note:"Only published research status and alerts, never inferred approval"},
 ]},
];
export const WT_CHECK_KEYS=WT_GROUPS.flatMap(g=>g.items.map(x=>x.key));
if(new Set(WT_CHECK_KEYS).size!==WT_CHECK_KEYS.length)throw Error("WT checkbox keys must be distinct");

const valid=(v:unknown):v is number=>typeof v==="number"&&Number.isFinite(v);
const avg=(rows:WtBar[],f:(v:WtBar)=>number)=>rows.reduce((a,x)=>a+f(x),0)/rows.length;
const round=(x:number,n=2)=>Math.round(x*10**n)/10**n;
export const numeric=(n:number|null|undefined,d=2)=>valid(n)?n.toFixed(d):"NOT VERIFIED";
export const dollars=(n:number|null|undefined)=>valid(n)?"$"+n.toFixed(n<1?4:2):"NOT VERIFIED";
export function sessionSnapshot(data:WtMarket|null, today=new Date()):WtSnapshot|null{
 if(!data||data.provider!=="ALPACA"||data.status!=="OK"||!["IEX","SIP"].includes(data.feed.toUpperCase())||!Array.isArray(data.bars))return null;
 const bars=[...data.bars];
 if(bars.length<61)return null;
 for(let i=0;i<bars.length;i++){
  const b=bars[i];
  if(!/^\d{4}-\d{2}-\d{2}$/.test(b.date)||[b.open,b.high,b.low,b.close,b.volume].some(x=>!valid(x))
     ||Math.min(b.open,b.high,b.low,b.close)<=0||b.volume<0||b.high<Math.max(b.open,b.close,b.low)
     ||b.low>Math.min(b.open,b.close,b.high)
     ||(i>0&&bars[i-1].date>=b.date))return null;
 }
 const last=bars.at(-1)!,prior=bars.at(-2)!;
 // Do not show indicators from an old, unbounded or future chart.
 const age=Math.floor((Date.UTC(today.getUTCFullYear(),today.getUTCMonth(),today.getUTCDate())-Date.parse(last.date+"T00:00:00Z"))/86400000);
 if(!Number.isFinite(age)||age<0||age>7||last.date!==data.asOf?.slice(0,10))return null;
 const sma20=avg(bars.slice(-20),r=>r.close);
 const sma50=avg(bars.slice(-50),r=>r.close);
 const prevSma20=avg(bars.slice(-21,-1),r=>r.close);
 const avgVolume=avg(bars.slice(-21,-1),r=>r.volume);
 if(avgVolume<=0)return null;
 const changes=bars.slice(1).map((b,i)=>b.close-bars[i].close);
 let gain=changes.slice(0,14).reduce((s,x)=>s+Math.max(0,x),0)/14;
 let loss=changes.slice(0,14).reduce((s,x)=>s+Math.max(0,-x),0)/14;
 for(const delta of changes.slice(14)){
  gain=(gain*13+Math.max(0,delta))/14;
  loss=(loss*13+Math.max(0,-delta))/14;
 }
 const rsi=loss===0?(gain===0?50:100):100-100/(1+gain/loss);
 const ranges=bars.slice(1).map((b,i)=>Math.max(b.high-b.low,Math.abs(b.high-bars[i].close),Math.abs(b.low-bars[i].close)));
 let atr=avg(ranges.slice(0,14).map((v,i)=>({...bars[i+1],_trueRange:v})),r=>(r as WtBar&{_trueRange:number})._trueRange);
 for(const r of ranges.slice(14))atr=(atr*13+r)/14;
 const base=bars.slice(-11,-1),baseHigh=Math.max(...base.map(b=>b.high)),baseLow=Math.min(...base.map(b=>b.low));
 return {asOf:last.date,feed:data.feed.toUpperCase(),coverage:data.feed.toUpperCase()==="IEX"?"IEX single exchange; partial-market volume":"SIP consolidated",
  close:last.close,sma20:round(sma20,4),sma50:round(sma50,4),
  rvol20:round(last.volume/avgVolume),rsi14:round(rsi,1),atr14:round(atr,4),
  avgDollarVolume20:round(avg(bars.slice(-20),b=>b.close*b.volume),0),
  baseLow:round(baseLow,4),baseHigh:round(baseHigh,4),
  supportHold:last.close>=baseLow,breakout:last.close>baseHigh,
  twoClosesBelowSma20:prior.close<prevSma20&&last.close<sma20,
  changePct:round((last.close/prior.close-1)*100,2)};
}
export function pdufaDays(reported?:string,today=new Date()):number|null{
 if(!reported||!/^\d{4}-\d{2}-\d{2}$/.test(reported.slice(0,10)))return null;
 const day=reported.slice(0,10);
 const parts=new Intl.DateTimeFormat("en-US",{timeZone:"America/Los_Angeles",year:"numeric",month:"2-digit",day:"2-digit"}).formatToParts(today);
 const m=Object.fromEntries(parts.filter(x=>x.type!=="literal").map(x=>[x.type,x.value]));
 const current=m.year+"-"+m.month+"-"+m.day;
 const n=(Date.parse(day+"T00:00:00Z")-Date.parse(current+"T00:00:00Z"))/86400000;
 return Number.isFinite(n)?n:null;
}
