/**
 * Read-only E*TRADE order proposals informed by Alpaca's exact-program research.
 * No brokerage connection, OAuth token, order preview, approval, or place call.
 * This module may suggest a price for manual review only when ALL strict
 * freshness, signal, identity and pre-PDUFA safety gates pass.
 */
export type WtEtradeCandidate = Readonly<{
  ticker:"SVRA"|"CAPR";
  nct:string;
  programId:string;
  drug:string;
}>;

export const WT_ETRADE_CANDIDATES: readonly WtEtradeCandidate[] = [
  {ticker:"SVRA",nct:"NCT04544293",programId:"PDUFA-000165",drug:"MOLBREEVI (molgramostim)"},
  {ticker:"CAPR",nct:"NCT05126758",programId:"PDUFA-000051",drug:"Deramiocel"},
] as const;

export type WtAlpacaEntry = {
  provider?:string;
  ticker?:string;
  programId?:string;
  model?:string;
  status?:string;
  green?:boolean;
  orderExecutionEnabled?:boolean;
  message?:string;
  calculatedAt?:string;
  entryOpen?:string;
  entryClose?:string;
  entryTrigger?:number;
  maximumEntry?:number;
  initialStop?:number;
  checks?:{pass:boolean}[];
  quote?:{bid:number;ask:number;asOf:string;feed:string};
};

export type WtReviewDraft = Readonly<{
  broker:"E*TRADE";
  symbol:string;
  programId:string;
  action:"BUY";
  quantity:1;
  priceType:"LIMIT";
  orderTerm:"GOOD_FOR_DAY";
  marketSession:"REGULAR";
  limitPrice:number|null;
  status:"SOURCE_NOT_VERIFIED"|"PDUFA_DATE_PASSED"|"PDUFA_EXIT_WINDOW"|"NO_FRESH_ENTRY"|"PRICE_SUGGESTED_REVIEW_ONLY";
  reason:string;
  isBrokerPreview:false;
  isApproved:false;
  isSubmitted:false;
}>;

function easternDayMs(date:Date):number {
  const fields=new Intl.DateTimeFormat("en-US",{timeZone:"America/New_York",year:"numeric",month:"2-digit",day:"2-digit"}).formatToParts(date);
  const values=Object.fromEntries(fields.map(x=>[x.type,x.value]));
  return Date.UTC(Number(values.year),Number(values.month)-1,Number(values.day));
}

export function daysUntilPdufa(date:string|null|undefined,nowMs:number):number|null {
  if(!date||!/^\d{4}-\d{2}-\d{2}$/.test(date)||!Number.isFinite(nowMs)||nowMs<=0)return null;
  const when=Date.parse(date+"T00:00:00Z");
  if(!Number.isFinite(when)||new Date(when).toISOString().slice(0,10)!==date)return null;
  return Math.round((when-easternDayMs(new Date(nowMs)))/86400000);
}

function fresh(iso:string|undefined,now:number):boolean {
  if(typeof iso!=="string")return false;
  const stamp=Date.parse(iso);
  return Number.isFinite(stamp)&&now-stamp>=0&&now-stamp<60000;
}

function finitePositive(n:unknown):n is number {
  return typeof n==="number"&&Number.isFinite(n)&&n>0;
}

/** Never creates an executable broker order, even when its price is populated. */
export function prepareWtEtradeDraft(
  candidate:WtEtradeCandidate,
  focusRecord:{ticker?:string;nct?:string;recordedPdufaDate?:string|null}|undefined,
  signal:WtAlpacaEntry|null,
  nowMs:number,
):WtReviewDraft {
  const base={
    broker:"E*TRADE" as const,symbol:candidate.ticker,programId:candidate.programId,
    action:"BUY" as const,quantity:1 as const,priceType:"LIMIT" as const,
    orderTerm:"GOOD_FOR_DAY" as const,marketSession:"REGULAR" as const,
    isBrokerPreview:false as const,isApproved:false as const,isSubmitted:false as const,
  };
  const stop=(status:WtReviewDraft["status"],reason:string):WtReviewDraft=>({...base,limitPrice:null,status,reason});
  if(!focusRecord||focusRecord.nct!==candidate.nct||focusRecord.ticker!==candidate.ticker)
    return stop("SOURCE_NOT_VERIFIED","Exact current FOCUS NCT/ticker membership could not be verified.");
  const days=daysUntilPdufa(focusRecord.recordedPdufaDate,nowMs);
  if(days===null)return stop("SOURCE_NOT_VERIFIED","No correctly dated PDUFA target is present in the current FOCUS record.");
  if(days<0)return stop("PDUFA_DATE_PASSED","Recorded FDA target has passed. Review the source outcome; do not construct a new entry.");
  if(days<=14)return stop("PDUFA_EXIT_WINDOW","Within the existing 14-calendar-day pre-PDUFA no-new-buy window ("+days+" days remaining).");

  if(!signal)return stop("NO_FRESH_ENTRY","Waiting for the exact-program Alpaca entry analysis.");
  if(signal.provider!=="ALPACA"||signal.programId!==candidate.programId||
    signal.ticker!==candidate.ticker||signal.model!=="BASE_BREAKOUT_V1_UNVALIDATED"||
    signal.orderExecutionEnabled!==false)
    return stop("NO_FRESH_ENTRY","Alpaca source, program identity, model, or execution safety contract did not match.");
  if(signal.status!=="BUY"||signal.green!==true||
    !Array.isArray(signal.checks)||signal.checks.length===0||signal.checks.some(x=>x.pass!==true))
    return stop("NO_FRESH_ENTRY",signal.message||"No validated entry-window confirmation; do not chase the price.");
  if(!fresh(signal.calculatedAt,nowMs)||!fresh(signal.quote?.asOf,nowMs))
    return stop("NO_FRESH_ENTRY","Alpaca calculation or quote is stale (60-second maximum).");
  const start=Date.parse(signal.entryOpen||""),end=Date.parse(signal.entryClose||"");
  if(!Number.isFinite(start)||!Number.isFinite(end)||nowMs<start||nowMs>=end)
    return stop("NO_FRESH_ENTRY","Not inside the regular NYSE entry session.");
  const q=signal.quote;
  if(!q||!["IEX","SIP"].includes(q.feed)||
    !finitePositive(q.bid)||!finitePositive(q.ask)||q.bid>q.ask||
    !finitePositive(signal.entryTrigger)||!finitePositive(signal.maximumEntry)||
    q.bid<signal.entryTrigger||q.ask>signal.maximumEntry||signal.maximumEntry<=signal.entryTrigger)
    return stop("NO_FRESH_ENTRY","Fresh quote is missing, crossed, outside the entry range, or lacks verified bounds.");
  // These two candidates are dollar stocks. Avoid silently changing a quote
  // into an invalid E*TRADE tick or rounding an ask below the executable quote.
  const price=Math.round(q.ask*100)/100;
  if(price<1||Math.abs(price-q.ask)>0.000001)
    return stop("NO_FRESH_ENTRY","Price precision is not suitable for a US-dollar stock limit draft.");
  return {...base,limitPrice:price,status:"PRICE_SUGGESTED_REVIEW_ONLY",
    reason:"Fresh Alpaca ask is within the research entry band. Verify current E*TRADE quote, risks, account, limit and disclosures before approving an order."};
}

export function formatWtEtradeDraft(draft:WtReviewDraft,pdufaDate:string|null|undefined):string {
  return [
    "DRAFT FOR MANUAL REVIEW — NOT AN E*TRADE ORDER",
    "Broker: E*TRADE (not connected)",
    "Symbol: "+draft.symbol,
    "Program ID: "+draft.programId,
    "Action: BUY",
    "Quantity: 1 whole share",
    "Order type: LIMIT",
    "Limit price: "+(draft.limitPrice===null?"PENDING — do not submit":"$"+draft.limitPrice.toFixed(2)+" (Alpaca research, recheck at E*TRADE)"),
    "Term: GOOD_FOR_DAY / regular market session",
    "Recorded PDUFA: "+(pdufaDate||"not verified"),
    "Entry status: "+draft.status,
    "Reason: "+draft.reason,
    "E*TRADE preview: NOT PERFORMED",
    "User approval: NOT GIVEN",
    "Order submission: DISABLED",
  ].join("\n");
}
