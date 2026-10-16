"""Explicit reference levels for every indicator in the PDUFA research sheet.

Labels distinguish project selection gates, preferred screening heuristics,
non-numeric diligence requirements, and manual trade-plan controls. These
are NOT empirically validated purchase/sale thresholds.
"""
from __future__ import annotations

# Display order mirrors the complete investment analysis: facts and finance
# first, then chart signals, ownership/squeeze overlays, and trading controls.
EXTRA_FIELDS = (
    "CLINICAL — Phase 3 primary endpoint",
    "CLINICAL — Statistical significance",
    "CLINICAL — Clinical efficacy",
    "CLINICAL — Safety / adverse events",
    "CLINICAL — FDA approval probability",
    "CLINICAL — Regulatory / CMC risk",
    "FINANCIAL — Second post-Phase 3 financing",
    "FINANCIAL — Cash runway (months)",
    "FINANCIAL — Dilution / ATM / warrants",
    "FINANCIAL — Catalyst window (days)",
    "FINANCIAL — Valuation / opportunity",
    "FINANCIAL — Trading liquidity (20D $)",
    "PARTICIPATION — Short interest (%)",
    "PARTICIPATION — Free float",
    "PARTICIPATION — Short days to cover",
    "PARTICIPATION — Institutional accumulation",
    "PARTICIPATION — Insider open-market buying",
    "PARTICIPATION — Buyout evidence",
    "DECISION — Candidate eligibility",
    "DECISION — Entry score (/100)",
    "DECISION — Exit risk score (/100)",
    "DECISION — Hard stop / invalidation",
    "DECISION — Profit objective",
    "DECISION — Catalyst exit rule",
)

# Reference levels are displayed in an adjacent column for EACH metric.
# Do not turn preferred ranges into automated GEM promotion gates.
TARGETS = {
    "Market cap $": "[PROJECT FILTER] $300,000,000 to $10,000,000,000 inclusive; source verified",
    "Market-cap gate": "[PROJECT FILTER] WITHIN $300M–$10B, verified",
    "CLINICAL — Phase 3 primary endpoint": "[GEM GATE] Positive primary Phase 3 readout for this exact program; primary-source verified",
    "CLINICAL — Statistical significance": "[DILIGENCE] Meets prespecified alpha/multiplicity plan (often p < 0.05); inspect confidence intervals",
    "CLINICAL — Clinical efficacy": "[DILIGENCE] Clinically meaningful benefit; comparator and endpoint relevance verified",
    "CLINICAL — Safety / adverse events": "[DILIGENCE] Acceptable benefit-risk; review SAEs, discontinuations and warnings",
    "CLINICAL — FDA approval probability": "[PROJECT PREFERENCE] >=75% independently assessed; estimate is not an FDA statistic",
    "CLINICAL — Regulatory / CMC risk": "[DILIGENCE] No unresolved material FDA/CMC/inspection/CRL problems",
    "FINANCIAL — Second post-Phase 3 financing": "[GEM GATE] Two distinct post-readout financings closed, SEC/source verified",
    "FINANCIAL — Cash runway (months)": "[PROJECT PREFERENCE] >=12 months; prefer covering catalyst plus buffer",
    "FINANCIAL — Dilution / ATM / warrants": "[RISK GATE] No imminent thesis-invalidating raise; assess ATM, warrants and convertibles",
    "FINANCIAL — Catalyst window (days)": "[PROJECT PREFERENCE] 30–90 days; focus 30–60; do not assume FDA date is verified",
    "FINANCIAL — Valuation / opportunity": "[DILIGENCE] Favorable enterprise value and probability-weighted upside/downside; no universal multiple",
    "FINANCIAL — Trading liquidity (20D $)": "[TRADING PREFERENCE] >=$5,000,000 average daily dollar volume; spread check also required",
    "Priority 1 — Price base / support / resistance": "[ILLUSTRATIVE TEST] 2+ separated support tests, tight base, volume contraction; breakout through resistance",
    "Base support $": "[SETUP] Verified structural support below planned entry; no fixed price target",
    "Base resistance $": "[SETUP] Verified resistance; breakout or retest plan required",
    "Base support tests": "[ILLUSTRATIVE TEST] >=2 separated tests, preferably >=3 sessions apart",
    "Priority 2 — Latest volume": "[SETUP] Rising participation at breakout vs prior 20-session average; no fixed share count",
    "RVOL": "[ILLUSTRATIVE TEST] >=1.5x previous 20-session average during breakout",
    "Priority 3 — SMA20 $": "[TREND PREFERENCE] Closing price above rising 20-day SMA",
    "SMA50 $": "[TREND PREFERENCE] Closing price above rising 50-day SMA",
    "Priority 4 — ATR(14)": "[RISK INPUT] 14-period true range from OHLC; no universal ATR threshold",
    "Priority 5 — Entry $": "[MANUAL PLAN] Price at validated breakout/retest, before order",
    "Stop $": "[MANUAL RISK] Predefined structure-based invalidation and tolerable position risk",
    "Target $": "[MANUAL PLAN] Realistic resistance/price objective with >=2R to first target preferred",
    "Reward / risk": "[ILLUSTRATIVE TEST] >=2.0:1 to first realistic target",
    "Priority 6 — VWAP / anchored VWAP": "[CONFIRMATION] Price holds above meaningful event-anchored VWAP; no universal dollar level",
    "Priority 7 — Strength vs XBI": "[CONFIRMATION] Rising 20–60-session relative-performance line vs XBI",
    "Priority 8 — PDUFA / catalyst": "[PROJECT PREFERENCE] Source-verified date 30–90 days out; exit before decision per policy",
    "Priority 9 — RSI(14)": "[OPTIONAL / UNVALIDATED] Roughly 45–65 for constructive momentum; not mandatory",
    "Priority 10 — MACD": "[OPTIONAL] MACD above signal and improving; not an independent mandatory gate",
    "PARTICIPATION — Short interest (%)": "[OPTIONAL SQUEEZE] >=15% of float, verified settlement-date short interest",
    "PARTICIPATION — Free float": "[OPTIONAL SQUEEZE] Prefer smaller verified float; no universal absolute threshold",
    "PARTICIPATION — Short days to cover": "[OPTIONAL SQUEEZE] >=3 days is exploratory, not validated",
    "PARTICIPATION — Institutional accumulation": "[SECONDARY] Net increases in comparable 13F positions, adjusted for reporting lag",
    "PARTICIPATION — Insider open-market buying": "[SECONDARY] Recent material verified Form 4 open-market buys; no fixed dollar cutoff",
    "PARTICIPATION — Buyout evidence": "[SUPPLEMENTAL] Strategic rationale supported by sources; speculation earns no automatic pass",
    "DECISION — Candidate eligibility": "[HARD OVERRIDE] All required clinical / financing / regulatory-source gates verified",
    "DECISION — Entry score (/100)": "[PROVISIONAL] 0–100 measured with source coverage; no buy cutoff until backtested",
    "DECISION — Exit risk score (/100)": "[PROVISIONAL] 0–100 watch signal; hard exit triggers override score",
    "DECISION — Hard stop / invalidation": "[HARD OVERRIDE] Exit under predefined stop or thesis-invalidating development",
    "DECISION — Profit objective": "[MANUAL PLAN] 2R first target preferred; 3R subsequent target optional",
    "DECISION — Catalyst exit rule": "[PROJECT POLICY] Exit before FDA decision; existing GEM default PDUFA -3 calendar days; FDA may act earlier",
}

assert set(EXTRA_FIELDS).issubset(TARGETS)
