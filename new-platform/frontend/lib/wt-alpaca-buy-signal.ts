/**
 * Alpaca EOD-only, read-only technical signal for the exact FOCUS program.
 *
 * This is an unbacktested screening rule, NOT a broker order, live quote,
 * clinical approval forecast, or authorization to bypass the PDUFA blackout.
 * Existing strict entry API and E*TRADE price/order safeguards are independent.
 */
import {sessionSnapshot,type WtMarket,type WtSnapshot} from "./wt-entry-stay-exit";
import {daysUntilPdufa,type WtEtradeCandidate} from "./wt-etrade-order-draft";

export type TechnicalCheck = Readonly<{
  key:string;
  label:string;
  measured:string;
  required:string;
  passed:boolean;
}>;
export type WtAlpacaTechnicalSignal = Readonly<{
  provider:"ALPACA";
  ticker:string;
  programId:string;
  model:"WT_EOD_TECHNICAL_V1_UNBACKTESTED";
  status:"BUY_SETUP"|"WAIT"|"UNAVAILABLE";
  asOf:string|null;
  feed:"IEX"|"SIP"|null;
  checks:readonly TechnicalCheck[];
  passed:number;
  total:number;
  triggerReference:number|null;
  riskStopReference:number|null;
  pdufaDate:string|null;
  pdufaDays:number|null;
  pdufaGate:"NO_VERIFIED_DATE"|"PAST_TARGET"|"PRE_PDUFA_BLACKOUT"|"OUTSIDE_BLACKOUT";
  orderEligible:false;
  brokerOrderEnabled:false;
  reason:string;
}>;

const dayInEastern=(nowMs:number)=>{
  const pieces=new Intl.DateTimeFormat("en-US",{
    timeZone:"America/New_York",year:"numeric",month:"2-digit",day:"2-digit",
  }).formatToParts(new Date(nowMs));
  const parts=Object.fromEntries(pieces.map(p=>[p.type,p.value]));
  return Date.UTC(Number(parts.year),Number(parts.month)-1,Number(parts.day));
};
const money=(n:number)=>"$"+n.toFixed(n<1?4:2);
const fixed=(n:number,places=2)=>n.toFixed(places);
const safeNumber=(n:number)=>Number.isFinite(n)&&n>0;

function buildChecks(data:WtMarket,observed:WtSnapshot):TechnicalCheck[]{
  // Observations already validated by sessionSnapshot; last complete day is signal day.
  const preceding=data.bars.slice(-11,-1);
  const recent=preceding.slice(-5),older=preceding.slice(0,5);
  const baseWidth=observed.baseHigh-observed.baseLow;
  const recentLow=Math.min(...recent.map(b=>b.low));
  const olderLow=Math.min(...older.map(b=>b.low));
  const trigger=observed.baseHigh+0.1*observed.atr14;
  const atrFraction=observed.atr14/observed.close;
  const values=[
    {key:"base",label:"10-session base",measured:money(baseWidth)+" width",required:"Width ≤ 3 × ATR14 ("+money(3*observed.atr14)+")",passed:baseWidth<=3*observed.atr14},
    {key:"lows",label:"Stabilizing lows",measured:money(recentLow)+" vs "+money(olderLow),required:"Recent 5-session low ≥ prior 5-session low",passed:recentLow>=olderLow},
    {key:"breakout",label:"Confirmed close above trigger",measured:money(observed.close),required:"Close > 10-session high + 0.10 × ATR ("+money(trigger)+")",passed:observed.close>trigger},
    {key:"trend",label:"Positive moving-average trend",measured:money(observed.close)+" / "+money(observed.sma20)+" / "+money(observed.sma50),required:"Close > SMA20 > SMA50",passed:observed.close>observed.sma20&&observed.sma20>observed.sma50},
    {key:"volume",label:"Relative volume (RVOL20)",measured:fixed(observed.rvol20)+"×",required:"≥ 1.50× vs prior 20 sessions (same "+observed.feed+" feed)",passed:observed.rvol20>=1.5},
    {key:"momentum",label:"RSI14 momentum",measured:fixed(observed.rsi14,1),required:"Between 50 and 70 inclusive",passed:observed.rsi14>=50&&observed.rsi14<=70},
    {key:"liquidity",label:"20-day average dollar volume",measured:"$"+Math.round(observed.avgDollarVolume20).toLocaleString("en-US"),required:"≥ $1,000,000 in "+observed.feed+" reported bars",passed:observed.avgDollarVolume20>=1000000},
    {key:"risk",label:"ATR14 daily volatility",measured:fixed(atrFraction*100,1)+"% of last close",required:"ATR > 0 and ATR/close ≤ 10%",passed:observed.atr14>0&&atrFraction<=0.10},
  ];
  return values;
}

export function evaluateWtAlpacaTechnicalSignal(
  candidate:WtEtradeCandidate,
  record:{ticker?:string;nct?:string;recordedPdufaDate?:string|null}|undefined,
  market:WtMarket|null,
  nowMs:number,
):WtAlpacaTechnicalSignal{
  const pdufaDate=record?.recordedPdufaDate||null;
  const days=daysUntilPdufa(pdufaDate,nowMs);
  const pdufaGate:WtAlpacaTechnicalSignal["pdufaGate"]=
    days===null?"NO_VERIFIED_DATE":days<0?"PAST_TARGET":days<=14?"PRE_PDUFA_BLACKOUT":"OUTSIDE_BLACKOUT";
  const base={
    provider:"ALPACA" as const,ticker:candidate.ticker,programId:candidate.programId,
    model:"WT_EOD_TECHNICAL_V1_UNBACKTESTED" as const,
    triggerReference:null,riskStopReference:null,pdufaDate,pdufaDays:days,
    pdufaGate,orderEligible:false as const,brokerOrderEnabled:false as const,
  };
  const unavailable=(reason:string):WtAlpacaTechnicalSignal=>({
    ...base,status:"UNAVAILABLE",asOf:null,feed:null,checks:[],passed:0,total:8,reason,
  });
  if(!Number.isFinite(nowMs)||nowMs<=0)return unavailable("A valid current clock is required.");
  if(!record||record.ticker!==candidate.ticker||record.nct!==candidate.nct)
    return unavailable("FOCUS ticker/NCT membership does not match this permanent program.");
  if(!market||market.programId!==candidate.programId||market.ticker!==candidate.ticker||
    market.provider!=="ALPACA"||market.status!=="OK"||
    !["IEX","SIP"].includes(market.feed)||
    market.adjustment!=="raw")
    return unavailable("No exact-program, verified Alpaca raw daily-bar feed is available.");
  const snapshot=sessionSnapshot(market,new Date(nowMs));
  if(!snapshot)return unavailable("Alpaca bars are missing, invalid or too old to assess.");
  // Explicit E.T. check avoids portraying a Friday chart as a current signal
  // long after an exchange holiday / stale provider response.
  const last=Date.parse(snapshot.asOf+"T00:00:00Z");
  const ageDays=Math.round((dayInEastern(nowMs)-last)/86400000);
  if(!Number.isInteger(ageDays)||ageDays<0||ageDays>4)
    return unavailable("Last complete Alpaca session is too old (over 4 calendar days) or in the future.");
  const checks=buildChecks(market,snapshot);
  const passed=checks.filter(c=>c.passed).length;
  const confirmed=passed===checks.length;
  const trigger=snapshot.baseHigh+0.10*snapshot.atr14;
  const stop=snapshot.baseLow-0.25*snapshot.atr14;
  // No PDUFA override: a technical BUY_SETUP remains non-actionable.
  const riskExplanation=pdufaGate==="PRE_PDUFA_BLACKOUT"?
    " Technical conditions never lift the existing 14-day pre-PDUFA no-new-buy restriction.":
    pdufaGate==="PAST_TARGET"?" Recorded FDA target already passed; verify the official outcome.":
    pdufaGate==="NO_VERIFIED_DATE"?" PDUFA date still requires source verification.":
    " Broker execution additionally requires separate source, cash/dilution and fresh-quote checks.";
  return {
    ...base,status:confirmed?"BUY_SETUP":"WAIT",asOf:snapshot.asOf,feed:snapshot.feed as "IEX"|"SIP",
    checks,passed,total:checks.length,
    triggerReference:safeNumber(trigger)?Math.ceil(trigger*100)/100:null,
    riskStopReference:safeNumber(stop)?Math.floor(stop*100)/100:null,
    reason:(confirmed?
      "All eight completed-session Alpaca technical checks passed (screening BUY setup only).":
      "Technical buy setup not confirmed; "+(checks.length-passed)+" of eight checks did not pass.")+
      riskExplanation,
  };
}
