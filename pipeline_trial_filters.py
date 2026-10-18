"""Public-data trial screeners for the existing PIPELINE table.

All lookups are from saved public-source extracts; no hidden live-feed calls.
Issuer-level market data may apply across an issuer's trials, but an SEC
second-financing verification attaches ONLY to its exact application event.
Missing evidence is not a negative clinical or financing finding.
"""
from datetime import date
from pathlib import Path

import pandas as pd

EVIDENCE_FILES = (
    "phase_pipeline_market_caps.csv",
    "step7_market_status.csv",
    "pdufa_candidates.csv",
    "second_financing_status.csv",
)

TRIAL_KEYS = (
    "pipeline_trial_phases_v1",
    "pipeline_trial_statuses_v1",
    "pipeline_trial_indication_v1",
    "pipeline_trial_modalities_v1",
    "pipeline_trial_results_v1",
    "pipeline_trial_financing_v1",
    "pipeline_trial_milestone_v1",
    "pipeline_trial_window_v1",
    "pipeline_trial_market_cap_v1",
    "pipeline_trial_price_v1",
    "pipeline_trial_float_v1",
    "pipeline_trial_cash_v1",
    "pipeline_trial_shares_v1",
    "pipeline_trial_ev_v1",
    "pipeline_trial_runway_v1",
    "pipeline_trial_insider_v1",
)
MULTI_KEYS = {"pipeline_trial_phases_v1", "pipeline_trial_statuses_v1", "pipeline_trial_modalities_v1"}

DEFAULTS = {key: ([] if key in MULTI_KEYS else
                  "" if key == "pipeline_trial_indication_v1" else "Any")
            for key in TRIAL_KEYS}

PHASE_OPTIONS = ("Early Phase 1", "Phase 1", "Phase 1/2", "Phase 2",
                 "Phase 2/3", "Phase 3", "Phase 4", "Not Applicable", "Unknown")
STATUS_OPTIONS = ("RECRUITING", "NOT_YET_RECRUITING", "ACTIVE_NOT_RECRUITING",
                  "COMPLETED", "TERMINATED", "SUSPENDED", "WITHDRAWN",
                  "ENROLLING_BY_INVITATION", "UNKNOWN")
MODALITY_OPTIONS = ("Drug", "Biologic", "Device", "Genetic", "Behavioral",
                    "Radiation", "Dietary supplement", "Other")
RESULT_OPTIONS = ("Any", "Sourced Phase 3 results", "Not confirmed")
FINANCING_OPTIONS = ("Any", "Verified second financing closed", "Not verified")
MILESTONE_OPTIONS = ("Any", "Primary completion", "Study completion",
                     "Results posted", "FDA acceptance", "PDUFA deadline")
WINDOW_OPTIONS = ("Any", "Already passed", "Next 30 days", "Next 90 days",
                  "More than 90 days away", "Date not recorded")
MILESTONE_COLUMNS = {
    "Primary completion": "primary_completion",
    "Study completion": "study_completion",
    "Results posted": "results_posted",
    "FDA acceptance": "fda_acceptance_date",
    "PDUFA deadline": "pdufa_date",
}

# Each interval is lower inclusive and upper exclusive; None = unbounded.
NUMERIC_SPECS = (
    ("Market cap", "pipeline_trial_market_cap_v1", "filter_market_cap_usd", {
        "Any": None, "Under $300M": (None, 300e6),
        "$300M–$10B": (300e6, 10e9), "$10B+": (10e9, None),
    }),
    ("Stock price (recent EOD)", "pipeline_trial_price_v1", "filter_price_usd", {
        "Any": None, "Under $1": (None, 1), "$1–$5": (1, 5),
        "$5–$20": (5, 20), "$20–$100": (20, 100), "$100+": (100, None),
    }),
    ("Public float (saved)", "pipeline_trial_float_v1", "filter_float_shares", {
        "Any": None, "Under 20M": (None, 20e6),
        "20M–100M": (20e6, 100e6), "100M+": (100e6, None),
    }),
    ("Cash (saved USD)", "pipeline_trial_cash_v1", "filter_cash_usd", {
        "Any": None, "Under $50M": (None, 50e6),
        "$50M–$200M": (50e6, 200e6), "$200M+": (200e6, None),
    }),
    ("Shares outstanding", "pipeline_trial_shares_v1", "filter_shares_outstanding", {
        "Any": None, "Under 20M": (None, 20e6),
        "20M–100M": (20e6, 100e6), "100M+": (100e6, None),
    }),
    ("Enterprise value", "pipeline_trial_ev_v1", "filter_enterprise_value_usd", {
        "Any": None, "Under $300M": (None, 300e6),
        "$300M–$10B": (300e6, 10e9), "$10B+": (10e9, None),
    }),
    ("Cash runway", "pipeline_trial_runway_v1", "filter_runway_months", {
        "Any": None, "Under 6 months": (None, 6),
        "6–12 months": (6, 12), "12–24 months": (12, 24),
        "24+ months": (24, None),
    }),
    ("Insider ownership", "pipeline_trial_insider_v1", "filter_insider_pct", {
        "Any": None, "Under 5%": (None, 5),
        "5–20%": (5, 20), "20%+": (20, None),
    }),
)
NUMERIC_COLUMNS = tuple(spec[2] for spec in NUMERIC_SPECS)
UNSUPPORTED_REASONS = {
    "filter_shares_outstanding": "No validated shares-outstanding series linked to PIPELINE.",
    "filter_enterprise_value_usd": "Debt and comparable cash inputs are not yet validated.",
    "filter_runway_months": "A consistent verified cash-burn time series is not yet linked.",
    "filter_insider_pct": "Form 4 trades do not establish insider ownership percentage.",
}

def selection_signature(state):
    """Stable immutable selection to synchronize automatic update callbacks."""
    return tuple(
        (key, tuple(state.get(key, [])) if key in MULTI_KEYS
         else str(state.get(key, DEFAULTS[key]) or DEFAULTS[key]).strip())
        for key in TRIAL_KEYS
    )

def selections(state):
    return {key: state.get(key, DEFAULTS[key]) for key in TRIAL_KEYS}

def has_active_filter(settings):
    return any(
        (bool(value) if key in MULTI_KEYS or key == "pipeline_trial_indication_v1"
         else value not in ("Any", "", None))
        for key, value in settings.items() if key in DEFAULTS
    )

def _read_csv(root, name):
    path = Path(root) / name
    if not path.is_file():
        return pd.DataFrame()
    try:
        return pd.read_csv(path, dtype=str, keep_default_na=False, low_memory=False)
    except (OSError, UnicodeError, ValueError, pd.errors.ParserError):
        return pd.DataFrame()

def _ticker_map(rows, value_column, eligible=None):
    if rows.empty or "ticker" not in rows or value_column not in rows:
        return {}
    data = rows.copy()
    if eligible is not None:
        data = data.loc[eligible(data)].copy()
    if data.empty:
        return {}
    data["_ticker"] = data["ticker"].astype(str).str.strip().str.upper()
    data = data.loc[data["_ticker"].ne("") & data[value_column].astype(str).str.strip().ne("")]
    return dict(zip(data["_ticker"], data[value_column]))

def _numeric(series):
    return pd.to_numeric(series, errors="coerce")

def add_public_filter_columns(frame, root="data", today=None):
    """Enrich without changing record count, trial identity or clinical stages."""
    result = frame.copy()
    for col in NUMERIC_COLUMNS:
        result[col] = pd.Series(float("nan"), index=result.index, dtype="float64")
    result["filter_second_financing_verified"] = False
    result["filter_phase3_result_sourced"] = False
    result["filter_price_last_session"] = ""
    if result.empty:
        return result

    today = today or date.today()
    ticker = result["ticker"].fillna("").astype(str).str.strip().str.upper()
    caps = _read_csv(root, "phase_pipeline_market_caps.csv")
    cap_map = _ticker_map(caps, "market_cap", lambda x:
                          x["market_cap_status"].eq("VERIFIED")
                          if "market_cap_status" in x else pd.Series(False, index=x.index))
    result["filter_market_cap_usd"] = _numeric(ticker.map(cap_map)).where(
        lambda x: x.gt(0)
    )

    prices = _read_csv(root, "step7_market_status.csv")
    if not prices.empty and "last_session" in prices:
        last = pd.to_datetime(prices["last_session"], errors="coerce")
        recent = (pd.Timestamp(today) - last).dt.days.between(0, 10)
        good = (prices.get("market_status", pd.Series("", index=prices.index))
                .eq("MARKET_UPDATED") & recent)
        prices = prices.loc[good].copy()
    price_map = _ticker_map(prices, "last_close_usd")
    day_map = _ticker_map(prices, "last_session")
    result["filter_price_usd"] = _numeric(ticker.map(price_map)).where(
        lambda x: x.gt(0)
    )
    result["filter_price_last_session"] = ticker.map(day_map).fillna("")

    # Candidate cash/float figures are historical saved inputs, not verified
    # current market fundamentals. Never propagate them by ticker alone.
    candidates = _read_csv(root, "pdufa_candidates.csv")
    if not candidates.empty and "event_key" in candidates:
        exact = candidates.drop_duplicates("event_key", keep="last").set_index("event_key")
        keys = result["record_id"].astype(str).str.removeprefix("APPLICATION|")
        is_application = result["record_id"].astype(str).str.startswith("APPLICATION|")
        for input_col, target_col in (
            ("shares_float", "filter_float_shares"),
            ("cash", "filter_cash_usd"),
        ):
            if input_col in exact:
                numeric = _numeric(keys.map(exact[input_col])).where(is_application)
                result[target_col] = numeric.where(numeric.gt(0))

    financing = _read_csv(root, "second_financing_status.csv")
    if not financing.empty and "event_key" in financing:
        required = {"second_financing_closed", "second_financing_audit_status",
                    "second_financing_source"}
        if required.issubset(financing.columns):
            confirmed = financing.loc[
                financing["second_financing_closed"].str.upper().eq("YES")
                & financing["second_financing_audit_status"].str.upper()
                  .eq("VERIFIED_SECOND_POST_PHASE3_FINANCING")
                & financing["second_financing_source"].str.startswith(("https://", "http://")),
                "event_key",
            ].astype(str)
            result["filter_second_financing_verified"] = (
                result["record_id"].astype(str).isin(
                    set("APPLICATION|" + key for key in confirmed)
                )
            )

    def sourced(row):
        tags = row.get("stage_tags", ())
        if isinstance(tags, (list, tuple, set)):
            return "Phase 3 Results" in tags
        return "Phase 3 Results" in str(tags)
    result["filter_phase3_result_sourced"] = result.apply(sourced, axis=1)
    return result

def filter_public_trials(frame, settings, today=None):
    """Every selected criterion is ANDed. Missing numbers never pass a band."""
    if frame.empty or not has_active_filter(settings):
        return frame.copy()
    selected = frame
    phases = settings.get("pipeline_trial_phases_v1") or []
    if phases:
        selected = selected.loc[selected["registered_phase"].isin(phases)]
    statuses = settings.get("pipeline_trial_statuses_v1") or []
    if statuses:
        selected = selected.loc[selected["status"].fillna("").str.upper().isin(statuses)]
    indication = str(settings.get("pipeline_trial_indication_v1") or "").strip()
    if indication:
        selected = selected.loc[selected["indication"].fillna("")
                                .str.contains(indication, case=False, regex=False)]
    modalities = settings.get("pipeline_trial_modalities_v1") or []
    if modalities:
        text = selected["drug_modality"].fillna("").astype(str).str.lower()
        selected = selected.loc[
            pd.concat([text.str.contains(word.lower(), regex=False)
                       for word in modalities], axis=1).any(axis=1)]
    results = settings.get("pipeline_trial_results_v1", "Any")
    if results != "Any":
        yes = results == "Sourced Phase 3 results"
        selected = selected.loc[selected["filter_phase3_result_sourced"].eq(yes)]
    financing = settings.get("pipeline_trial_financing_v1", "Any")
    if financing != "Any":
        yes = financing == "Verified second financing closed"
        selected = selected.loc[selected["filter_second_financing_verified"].eq(yes)]

    milestone = settings.get("pipeline_trial_milestone_v1", "Any")
    window = settings.get("pipeline_trial_window_v1", "Any")
    if milestone in MILESTONE_COLUMNS and window != "Any":
        days = (pd.to_datetime(selected[MILESTONE_COLUMNS[milestone]].astype(str).str[:10],
                               errors="coerce") - pd.Timestamp(today or date.today())).dt.days
        mask = {
            "Already passed": days.lt(0),
            "Next 30 days": days.between(0, 30),
            "Next 90 days": days.between(0, 90),
            "More than 90 days away": days.gt(90),
            "Date not recorded": days.isna(),
        }[window]
        selected = selected.loc[mask]
    for _, key, column, bands in NUMERIC_SPECS:
        bound = bands.get(settings.get(key, "Any"))
        if bound is None:
            continue
        nums = _numeric(selected[column])
        lower, upper = bound
        mask = nums.notna()
        if lower is not None:
            mask &= nums.ge(lower)
        if upper is not None:
            mask &= nums.lt(upper)
        selected = selected.loc[mask]
    return selected.copy()

def evaluate_public_trial_screen(frame, settings, today=None):
    """Audit selected criteria without mistaking absent evidence for failure.

    PASS requires every selected check to pass. FAIL means a supported check
    contradicts the requested setting. NEEDS VERIFICATION means one or more
    selected checks lack evidence, with no known failure. No filters means all
    records are PASS (unrestricted), not zero results.
    """
    result = frame.copy()
    if result.empty:
        result["Screen status"] = pd.Series(dtype="str")
        return result
    if not has_active_filter(settings):
        result["Screen status"] = "PASS"
        return result

    failures = pd.Series(False, index=result.index)
    unknown = pd.Series(False, index=result.index)

    def test(values, acceptable, known=None):
        nonlocal failures, unknown
        known = values.notna() if known is None else known
        known = known.fillna(False).astype(bool)
        failures |= known & ~acceptable.fillna(False).astype(bool)
        unknown |= ~known

    for key, col in (("pipeline_trial_phases_v1", "registered_phase"),
                     ("pipeline_trial_statuses_v1", "status")):
        chosen = settings.get(key) or []
        if chosen:
            values = result[col].fillna("").astype(str).str.strip()
            test(values, values.str.upper().isin([str(x).upper() for x in chosen]),
                 values.ne("") & values.str.upper().ne("UNKNOWN"))
    indication = str(settings.get("pipeline_trial_indication_v1") or "").strip()
    if indication:
        values = result["indication"].fillna("").astype(str).str.strip()
        test(values, values.str.contains(indication, case=False, regex=False),
             values.ne(""))
    modalities = settings.get("pipeline_trial_modalities_v1") or []
    if modalities:
        values = result["drug_modality"].fillna("").astype(str).str.strip()
        matched = pd.concat([
            values.str.contains(str(word), case=False, regex=False)
            for word in modalities
        ], axis=1).any(axis=1)
        test(values, matched, values.ne(""))
    for key, col, affirmative, negative in (
        ("pipeline_trial_results_v1", "filter_phase3_result_sourced",
         "Sourced Phase 3 results", "Not confirmed"),
        ("pipeline_trial_financing_v1", "filter_second_financing_verified",
         "Verified second financing closed", "Not verified"),
    ):
        choice = settings.get(key, "Any")
        if choice == affirmative:
            # The False cache state means no verification, not a proven failure.
            values = result[col].fillna(False).astype(bool)
            test(values, values, values)
        elif choice == negative:
            # A sourced positive contradicts an explicitly negative selection;
            # absence of a positive is not proof of a negative.
            values = result[col].fillna(False).astype(bool)
            test(values, ~values, values)

    milestone = settings.get("pipeline_trial_milestone_v1", "Any")
    window = settings.get("pipeline_trial_window_v1", "Any")
    if milestone in MILESTONE_COLUMNS and window != "Any":
        values = pd.to_datetime(
            result[MILESTONE_COLUMNS[milestone]].astype(str).str[:10],
            errors="coerce",
        )
        days = (values - pd.Timestamp(today or date.today())).dt.days
        choices = {
            "Already passed": days.lt(0),
            "Next 30 days": days.between(0, 30),
            "Next 90 days": days.between(0, 90),
            "More than 90 days away": days.gt(90),
            "Date not recorded": values.isna(),
        }
        if window == "Date not recorded":
            # Explicitly searching for missing dates is a valid positive match.
            test(values, choices[window], pd.Series(True, index=result.index))
        elif window in choices:
            test(values, choices[window], values.notna())
    for _, key, col, bands in NUMERIC_SPECS:
        bound = bands.get(settings.get(key, "Any"))
        if bound is None:
            continue
        values = _numeric(result[col])
        lower, upper = bound
        matched = pd.Series(True, index=result.index)
        if lower is not None:
            matched &= values.ge(lower)
        if upper is not None:
            matched &= values.lt(upper)
        test(values, matched, values.notna())

    result["Screen status"] = "PASS"
    result.loc[unknown, "Screen status"] = "NEEDS VERIFICATION"
    result.loc[failures, "Screen status"] = "FAIL"
    return result
