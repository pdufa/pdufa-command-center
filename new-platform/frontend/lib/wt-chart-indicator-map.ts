/** Visible Alpaca daily-chart studies controlled only by the existing WT checkboxes.
 * A research checkbox is NOT evidence of a buy, hold, sell, stop, breakout,
 * support confirmation, FDA approval or a verified position.
 */
export const WT_CHART_STUDIES=[
 "sma20","sma50","rsi","volume","atr","range"
] as const;
export type WtChartStudy=typeof WT_CHART_STUDIES[number];
export const WT_CHART_NAMES:Record<WtChartStudy,string>={
 sma20:"SMA20",sma50:"SMA50",rsi:"RSI14",volume:"Daily volume",
 atr:"ATR14",range:"Prior 10-session high/low"
};
export const WT_CHECK_TO_STUDIES:Readonly<Record<string,readonly WtChartStudy[]>>={
 "entry-base":["range"],
 "entry-breakout":["range"],
 "entry-trend":["sma20","sma50"],
 "entry-rvol":["volume"],
 "entry-rsi":["rsi"],
 "entry-atr":["atr"],
 "stay-trend":["sma20","sma50"],
 "stay-support":["range"],
 "stay-rsi":["rsi"],
 "stay-volume":["volume"],
 "exit-two-close":["sma20"],
 "exit-support":["range"],
 "exit-atr-trail":["atr"],
 "exit-rsi":["rsi"],
 "exit-divergence":["volume"]
};
export function chartStudiesForWtChecks(keys:readonly string[]):WtChartStudy[]{
 const selected=new Set(keys);
 return WT_CHART_STUDIES.filter(study=>Object.entries(WT_CHECK_TO_STUDIES)
  .some(([key,studies])=>selected.has(key)&&studies.includes(study)));
}
export function chartDescriptionForWtCheck(key:string):string{
 const visible=WT_CHECK_TO_STUDIES[key];
 if(!visible)return "Research data only — no validated chart overlay";
 if(key==="entry-rvol"||key==="stay-volume"||key==="exit-divergence")
  return "CHART: Daily volume (not a verified RVOL/divergence signal)";
 if(key==="exit-atr-trail")return "CHART: ATR14 only (no trailing stop inferred)";
 if(key==="entry-base"||key==="entry-breakout"||key==="stay-support"||key==="exit-support")
  return "CHART: Prior 10-session range proxy (not confirmed support)";
 if(key==="exit-two-close")return "CHART: SMA20 for manual 2-close review";
 if(key==="exit-rsi")return "CHART: RSI14 (not a validated exhaustion exit)";
 return "CHART: "+visible.map(s=>WT_CHART_NAMES[s]).join(" + ");
}
