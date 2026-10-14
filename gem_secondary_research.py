"""Independent research navigation for GEM potential candidates.

Social posts only generate investigation leads; they can NEVER promote a GEM
benchmark. Source links use exact ticker plus program terms to reduce mistaken
same-ticker attribution. Official investor pages below were checked at authoring;
they may change later and are not a real-time source scan.
"""
from __future__ import annotations

from urllib.parse import quote_plus

# Only confirmed issuer-owned Investor Relations/news destinations belong here.
# All other issuers fall back to a clearly labeled search for their IR page.
CONFIRMED_INVESTOR_NEWS = {
    "NTLA": "https://ir.intelliatx.com/press-releases",
    # AXSM official corporate news is not a dedicated IR press-release page.
    # Leave it unset so the interface clearly requests IR discovery.
    "CAPR": "https://www.capricor.com/investors/news-events/press-releases",
    "CORT": "https://ir.corcept.com/news-releases/",
    "CLDX": "https://ir.celldex.com/press-releases",
    "MLTX": "https://ir.moonlaketx.com/press-releases",
    "PRAX": "https://investors.praxismedicines.com/press-releases",
    "MLYS": "https://ir.mineralystx.com/news-events/press-releases",
    "SVRA": "https://investors.savarapharma.com/news/",
    "ZBIO": "https://investors.zenasbio.com/news-releases",
    "COGT": "https://investors.cogentbio.com/",
}
SEARCH_HOST = "https://www.google.com/search?q="


def _words(value, limit=85):
    return " ".join(str(value or "").split())[:limit]


def _quote(value):
    return quote_plus(value)


def research_search_links(row):
    """Program-specific external search/navigation URLs; no evidence verdicts."""
    ticker = _words(row.get("Ticker"), 15).upper()
    drug = _words(row.get("Drug"), 85)
    indication = _words(row.get("Indication"), 85)
    nct = _words(row.get("NCT ID"), 64)
    if not ticker:
        return {}
    # Include a drug or indication; a bare ticker search can match unrelated
    # programs and must not be used to assert exact-program evidence.
    program_query = " ".join(x for x in (ticker, drug, indication) if x)
    trial_query = " ".join(x for x in (ticker, drug, nct) if x)
    social_query = " ".join(x for x in ("$" + ticker, drug) if x)
    ir_direct = CONFIRMED_INVESTOR_NEWS.get(ticker)
    ir_search = SEARCH_HOST + _quote(program_query + " investor relations press releases")
    return {
        "ticker": ticker,
        "program_query": program_query,
        "confirmed_issuer_news": ir_direct or "",
        "find_issuer_news": ir_search,
        "issuer_program_search": SEARCH_HOST + _quote(
            'site:' + (ir_direct.split('/')[2] if ir_direct else '') +
            ' "' + drug + '" ' + ticker
        ) if ir_direct and drug else ir_search,
        "sec_edgar": "https://www.sec.gov/search-filings",
        "sec_program_search": SEARCH_HOST + _quote(
            'site:sec.gov/Archives/edgar "' + ticker + '" "' + drug + '"'
        ),
        "sec_funding_close_search": SEARCH_HOST + _quote(
            'site:sec.gov/Archives/edgar "' + ticker +
            '" (offering OR private placement OR credit facility) ' +
            '(closed OR completed OR funded) 8-K 10-Q'
        ),
        "issuer_funding_search": SEARCH_HOST + _quote(
            '"' + ticker + '" "' + drug +
            '" (offering OR financing OR placement) (closing OR completed OR funded)'
        ),
        "clinical_trials": "https://clinicaltrials.gov/search?term=" + _quote(trial_query),
        "reddit_program": "https://www.reddit.com/search/?q=" +
            _quote(social_query) + "&sort=new&t=month",
        "stocktwits_ticker": "https://stocktwits.com/symbol/" + _quote(ticker),
        "x_program": "https://x.com/search?q=" + _quote(social_query) + "&f=live",
        "news_program": "https://www.google.com/search?tbm=nws&q=" + _quote(program_query),
    }


def source_research_policy():
    return (
        "SOCIAL / COMMUNITY = unverified investigation lead only. "
        "ISSUER IR/NEWS = company statements to corroborate, not a second financing audit. "
        "SEC / ClinicalTrials.gov = primary records requiring exact-program, "
        "date and two-distinct-post-readout-close verification. "
        "Neither social attention nor an IR link automatically checks a GEM "
        "benchmark or promotes a stock from #2 PIPELINE into verified #1 GEM."
    )

# These mirror the twelve optional GEM due-diligence checks, NOT the two
# required benchmarks. Searching them produces questions, not checked boxes.
OPTIONAL_CHECK_TOPICS = (
    ("clinical_quality", "Clinical endpoints / safety", "Phase 3 primary endpoint safety results"),
    ("clinical_conflict", "Conflicting clinical / FDA reports", "trial conflict adverse events regulatory"),
    ("cash_runway", "Cash runway", "10-Q cash equivalents operating cash runway"),
    ("dilution", "Dilution / new offering", "ATM shelf equity offering dilution"),
    ("price_base", "Post-readout price base", "post Phase 3 readout share price volume"),
    ("market_quote", "Volume / market momentum", "stock volume unusual activity"),
    ("pdufa_source", "FDA PDUFA date source", "FDA accepted NDA BLA PDUFA date"),
    ("pdufa_window", "PDUFA window changes", "PDUFA date extension FDA"),
    ("hedge_funds", "Institutional 13F activity", "13F hedge fund institutional ownership"),
    ("insiders", "Insider Form 4 purchases", "Form 4 insider open market purchase"),
    ("sec_fresh", "Recent SEC filings", "latest 8-K 10-Q SEC filing"),
    ("clinical_fresh", "Latest clinical study updates", "trial ClinicalTrials.gov update results"),
)


def optional_check_search_links(row, check_key):
    """Return search links for one non-benchmark research issue."""
    lookup = {key: (label, phrase) for key, label, phrase in OPTIONAL_CHECK_TOPICS}
    if check_key not in lookup:
        raise ValueError("Only non-benchmark checks can be searched socially")
    links = research_search_links(row)
    if not links:
        return {}
    ticker = links["ticker"]
    drug = _words(row.get("Drug"), 85)
    nct = _words(row.get("NCT ID"), 64)
    label, phrase = lookup[check_key]
    base = " ".join(x for x in (ticker, drug, nct, phrase) if x)
    official_source = "site:sec.gov " + base
    if check_key.startswith("clinical"):
        official_source = "site:clinicaltrials.gov " + base
    elif check_key.startswith("pdufa"):
        official_source = "site:fda.gov " + base
    return {
        "label": label,
        "issuer_ir": links["confirmed_issuer_news"] or links["find_issuer_news"],
        "primary_records": SEARCH_HOST + _quote(official_source),
        "reddit": "https://www.reddit.com/search/?q=" +
            _quote(base) + "&sort=new&t=month",
        "news": "https://www.google.com/search?tbm=nws&q=" + _quote(base),
        "notice": "Unverified social/search results are triage leads, never PASS.",
    }
