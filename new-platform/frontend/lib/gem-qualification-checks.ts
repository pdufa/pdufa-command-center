import type { Candidate } from "../app/Workspace";

export type GemCriterion = {
  key: string;
  label: string;
  help: string;
  passes: (row: Candidate) => boolean;
};
const number = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);
const positive = (v: unknown): v is number => number(v) && v > 0;
const recorded = (v: unknown) => typeof v === "string" && v.trim().length > 0 &&
  !/^(unverified|unknown|not verified|not recorded|missing|unavailable)$/i.test(v.trim());

function dayInPacific(): string {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: "America/Los_Angeles", year: "numeric", month: "2-digit", day: "2-digit",
  }).formatToParts(new Date());
  const values = Object.fromEntries(parts.filter(x => x.type !== "literal").map(x => [x.type, x.value]));
  return values.year + "-" + values.month + "-" + values.day;
}

export const GEM_CLINICAL_FILTERS: readonly GemCriterion[] = [
  {
    key: "phase3_status", label: "Phase 3 trial status recorded",
    help: "An observed trial/readout status, not proof of successful endpoints.",
    passes: row => recorded(row.phase3Status) || recorded(row.phase3Date),
  },
  {
    key: "phase3_positive", label: "Successful Phase 3 verified",
    help: "Exact-program independently source-verified positive Phase 3 result.",
    passes: row => row.technical?.benchmarks?.phase3 === true,
  },
  {
    key: "second_financing", label: "Second financing verified (optional)",
    help: "Optional cash/dilution context; not a mandatory GEM qualification gate.",
    passes: row => row.technical?.benchmarks?.secondFinancing === true,
  },
  {
    key: "fda_date_source", label: "PDUFA date and source URL recorded",
    help: "A dated source exists. This checkbox does not itself verify an FDA decision date.",
    passes: row => /^\d{4}-\d{2}-\d{2}$/.test((row.pdufaDate || "").slice(0,10)) &&
      /^https:\/\/[^\s]+$/.test(row.fdaSource || ""),
  },
];

export const GEM_TRADING_FILTERS: readonly GemCriterion[] = [
  {
    key: "market_cap", label: "Market cap $300M–$10B (optional)",
    help: "Disabled by default. Only the saved verified in-range flag can satisfy it.",
    passes: row => row.capInRange === true,
  },
  {
    key: "runway", label: "Cash runway at least 12 months",
    help: "Requires a saved source-gated runway estimate; not a stock-price indicator.",
    passes: row => number(row.technical?.runwayMonths) &&
      row.technical.runwayMonths >= 12 && row.technical.runwayGate?.startsWith("PASS") === true,
  },
  {
    key: "daily_close", label: "Daily closing price recorded",
    help: "Only requires a saved market-price observation, not an entry signal.",
    passes: row => positive(row.technical?.close),
  },
  {
    key: "sma_trend", label: "Close ≥ SMA20 ≥ SMA50",
    help: "Positive saved moving-average alignment. Missing averages do not pass.",
    passes: row => positive(row.technical?.close) && positive(row.technical?.sma20) &&
      positive(row.technical?.sma50) &&
      row.technical.close >= row.technical.sma20 &&
      row.technical.sma20 >= row.technical.sma50,
  },
  {
    key: "rvol", label: "Relative volume ≥1.5×",
    help: "Saved volume observation; Alpaca IEX-only volume is not consolidated.",
    passes: row => number(row.technical?.rvol) && row.technical.rvol >= 1.5,
  },
  {
    key: "rsi", label: "RSI14 between 45 and 65",
    help: "Provisional momentum range, not a backtested BUY threshold.",
    passes: row => number(row.technical?.rsi14) &&
      row.technical.rsi14 >= 45 && row.technical.rsi14 <= 65,
  },
  {
    key: "dollar_volume", label: "20-day dollar volume ≥$5M/day",
    help: "Only passes if liquidity observation is available and adequate.",
    passes: row => number(row.technical?.avgDollarVolume20) &&
      row.technical.avgDollarVolume20 >= 5_000_000,
  },
  {
    key: "support", label: "Closing support level recorded",
    help: "Records that a support estimate exists; it is not an executable stop.",
    passes: row => positive(row.technical?.closingSupport20),
  },
  {
    key: "base", label: "Price-base assessment recorded",
    help: "Records an affirmative, reviewed base observation, not a BUY signal.",
    passes: row => /^(confirmed|verified|base forming|support established|tight base)/i.test(
      String(row.technical?.base?.status || "")),
  },
  {
    key: "entry_score", label: "Entry score ≥70 with ≥50 coverage",
    help: "Provisional research score; does not authorize buying.",
    passes: row => number(row.technical?.entry) && row.technical.entry >= 70 &&
      number(row.technical.entryCoverage) && row.technical.entryCoverage >= 50,
  },
  {
    key: "exit_coverage", label: "Exit-risk evidence coverage ≥50",
    help: "Measures availability of exit observations, not a low-risk status.",
    passes: row => number(row.technical?.exitRisk) &&
      number(row.technical.exitCoverage) && row.technical.exitCoverage >= 50,
  },
  {
    key: "pdufa_window", label: "PDUFA 30–90 days (source recorded)",
    help: "Optional trading timing window; date/source recorded, not independently reverified.",
    passes: row => {
      const value=(row.pdufaDate || "").slice(0,10);
      if(!/^\d{4}-\d{2}-\d{2}$/.test(value) || !/^https:\/\/[^\s]+$/.test(row.fdaSource || ""))return false;
      const gap=(Date.parse(value+"T00:00:00Z")-Date.parse(dayInPacific()+"T00:00:00Z"))/86_400_000;
      return Number.isFinite(gap) && gap>=30 && gap<=90;
    },
  },
];

export const GEM_ALL_FILTERS = [...GEM_CLINICAL_FILTERS, ...GEM_TRADING_FILTERS];
if(new Set(GEM_ALL_FILTERS.map(x=>x.key)).size!==GEM_ALL_FILTERS.length){
  throw Error("Duplicate GEM qualification checkbox IDs");
}

export function gemMatchesCheckedFilters(row: Candidate, checked: readonly string[]): boolean {
  const wanted=new Set(checked);
  // Unknown keys never silently pass a scan.
  if([...wanted].some(key=>!GEM_ALL_FILTERS.some(c=>c.key===key)))return false;
  return GEM_ALL_FILTERS.every(c=>!wanted.has(c.key) || c.passes(row));
}
