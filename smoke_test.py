import csv
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent

REQUIRED = {
    "data/company_registry.csv": {
        "ticker","company","cik10","exchange","sic","sic_description","status",
    },
    "data/discovery_events.csv": {
        "discovery_key","discovered_at_utc","source_type","event_type","ticker","company",
        "cik10","drug","indication","nct_id","application_type","pdufa_date",
        "source_date","source_url","evidence","company_status","match_confidence","pipeline_status",
    },
    "data/discovery_backfill_queue.csv": {
        "discovery_key","ticker","company","cik10","event_type","drug","indication","nct_id",
        "application_type","pdufa_date","source_url","evidence","company_status",
        "match_confidence","backfill_status","first_seen_utc","last_seen_utc",
    },
    "data/second_financing_status.csv": {
        "event_key","second_financing_status","second_financing_announced",
        "second_financing_running","second_financing_closed",
        "first_financing_date","first_financing_source",
        "second_financing_date","second_financing_source",
        "second_financing_audit_status","second_financing_evidence_note","verified_as_of",
    },
    "data/pdufa_candidates.csv": {
        "event_key", "ticker", "company", "drug", "indication", "pdufa_date",
        "approval_probability", "public_approval_probability", "biopharmawatch_probability",
    },
    "data/recheck_status.csv": {
        "event_key","ticker","run_status","last_successful_recheck_utc","change_count","error_count",
        "pdufa_date_status","phase3_status","financing_status","cash_runway_status",
        "market_data_status","ownership_insiders_status",
    },
    "data/fda_review_engine.csv": {
        "event_key","ticker","drug","pdufa_date","fda_application_identity",
        "fda_clinical_score","fda_statistics_score","fda_safety_score","fda_cmc_score",
        "fda_inspection_status","fda_regulatory_score","fda_benefit_risk_score",
        "fda_hard_gate","fda_probability","fda_prediction","fda_confidence",
        "fda_model_version","decision_date","actual_fda_decision","fda_match_result",
    },
    "data/fda_prediction_freezes.csv": {
        "freeze_id","event_key","ticker","drug","pdufa_date","fda_probability",
        "fda_prediction","frozen_at","model_version","decision_date",
        "actual_fda_decision","match_result",
    },
    "data/fda_review_backfill_queue.csv": {
        "event_key","ticker","drug","pdufa_date","priority","days_to_pdufa",
        "missing_components","backfill_status","source_targets","decision_date",
        "actual_fda_decision","notes",
    },
    "data/fda_v3_historical_backtest.csv": {
        "event_key","ticker","pdufa_date","actual_outcome","model_class","p_approval",
        "correct","validation_period","independence_status","public_model_class",
        "v3_phase_a_status","v3_phase_a_match","historical_v3_backfill_needed",
        "v3_backfill_priority","diagnostic_miss_class",
    },
    "data/fda_v3_historical_backfill_queue.csv": {
        "event_key","ticker","pdufa_date","actual_outcome","validation_period",
        "independence_status","v3_backfill_priority","diagnostic_miss_class",
    },
    "data/prediction_engine_history.csv": {
        "event_key", "ticker", "pdufa_date", "p_approval", "actual_outcome",
        "public_approval_probability", "biopharmawatch_probability",
    },
    "data/prediction_engine_audit.csv": {"event_key", "audit_status", "count_in_audited_accuracy"},
    "data/prediction_engine_rescore_queue.csv": {"original_event_key", "ticker", "audit_status", "needs_rescore"},
    "data/prediction_engine_pvalues.csv": {
        "event_key","ticker","pdufa_date","reported_p_values",
        "p_value_audit_status","p_value_source_url","p_value_evidence_note",
    },
    "data/prediction_engine_designations.csv": {
        "event_key","ticker","pdufa_date","orphan_drug","no_available_therapy",
        "serious_condition","life_threatening","fast_track","breakthrough_therapy",
        "priority_review","accelerated_approval","rmat","qidp",
        "rare_pediatric_disease","priority_review_voucher","rolling_review",
        "rtor","project_orbis","spa","designation_audit_status",
        "designation_source_url","designation_evidence_note",
    },
}

MINIMUM_LIVE_EVENT_COUNT = 38
REQUIRED_LIVE_EVENTS = {
    "SVRA|MOLBREEVI_PAP_20261122",
    "COGT|BEZUCLASTINIB_GIST_20261130",
}

def read_csv(path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

for rel, required in REQUIRED.items():
    path = ROOT / rel
    if not path.exists():
        raise SystemExit(f"missing required file: {rel}")
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = set(reader.fieldnames or [])
    missing = required - headers
    if missing:
        raise SystemExit(f"{rel}: missing columns {sorted(missing)}")

registry = read_csv(ROOT / "data/company_registry.csv")
registry_tickers = [(r.get("ticker") or "").strip().upper() for r in registry]
if len(registry) < 716:
    raise SystemExit(f"company_registry.csv: registry shrank below original 716 companies: {len(registry)}")
if any(not t for t in registry_tickers):
    raise SystemExit("company_registry.csv: blank ticker")
if len(registry_tickers) != len(set(registry_tickers)):
    raise SystemExit("company_registry.csv: duplicate ticker")

discovery_events = read_csv(ROOT / "data/discovery_events.csv")
discovery_keys = [(r.get("discovery_key") or "").strip() for r in discovery_events]
if any(not k for k in discovery_keys):
    raise SystemExit("discovery_events.csv: blank discovery_key")
if len(discovery_keys) != len(set(discovery_keys)):
    raise SystemExit("discovery_events.csv: duplicate discovery_key")

discovery_queue = read_csv(ROOT / "data/discovery_backfill_queue.csv")
queue_keys = [(r.get("discovery_key") or "").strip() for r in discovery_queue]
if any(not k for k in queue_keys):
    raise SystemExit("discovery_backfill_queue.csv: blank discovery_key")
if len(queue_keys) != len(set(queue_keys)):
    raise SystemExit("discovery_backfill_queue.csv: duplicate discovery_key")

candidates = read_csv(ROOT / "data/pdufa_candidates.csv")
keys = [r["event_key"].strip() for r in candidates]
if any(not k for k in keys):
    raise SystemExit("pdufa_candidates.csv: blank event_key")
if len(keys) != len(set(keys)):
    raise SystemExit("pdufa_candidates.csv: duplicate event_key")
if len(candidates) < MINIMUM_LIVE_EVENT_COUNT:
    raise SystemExit(
        f"pdufa_candidates.csv: live feed shrank below baseline {MINIMUM_LIVE_EVENT_COUNT}; found {len(candidates)}"
    )
missing_required_events = REQUIRED_LIVE_EVENTS - set(keys)
if missing_required_events:
    raise SystemExit(
        "pdufa_candidates.csv: missing reconciled authoritative event(s): "
        + ", ".join(sorted(missing_required_events))
    )

for r in candidates:
    d = r["pdufa_date"].strip()
    if d:
        datetime.strptime(d, "%Y-%m-%d")

recheck = read_csv(ROOT / "data/recheck_status.csv")
recheck_keys = [(r.get("event_key") or "").strip() for r in recheck]
if len(recheck_keys) != len(set(recheck_keys)):
    raise SystemExit("recheck_status.csv: duplicate event_key")
unknown_recheck_keys = set(recheck_keys) - set(keys)
if unknown_recheck_keys:
    raise SystemExit(
        "recheck_status.csv: contains event_key(s) not present in live candidates: "
        + ", ".join(sorted(unknown_recheck_keys)[:5])
    )
if not (ROOT / "scripts/recheck_events.py").exists():
    raise SystemExit("missing scripts/recheck_events.py")
if not (ROOT / "scripts/fda_decision_engine.py").exists():
    raise SystemExit("missing scripts/fda_decision_engine.py")
if not (ROOT / "data/fda_engine_config.json").exists():
    raise SystemExit("missing data/fda_engine_config.json")
if not (ROOT / "scripts/fda_v3_historical_backtest.py").exists():
    raise SystemExit("missing scripts/fda_v3_historical_backtest.py")
if not (ROOT / "scripts/complete_fda_v3_historical_review.py").exists():
    raise SystemExit("missing scripts/complete_fda_v3_historical_review.py")
if not (ROOT / "data/fda_v3_historical_summary.json").exists():
    raise SystemExit("missing data/fda_v3_historical_summary.json")

second_financing = read_csv(ROOT / "data/second_financing_status.csv")
sf_keys = [(r.get("event_key") or "").strip() for r in second_financing]
if len(sf_keys) != len(set(sf_keys)):
    raise SystemExit("second_financing_status.csv: duplicate event_key")
unknown_sf_keys = set(sf_keys) - set(keys)
if unknown_sf_keys:
    raise SystemExit(
        "second_financing_status.csv: contains event_key(s) not present in live candidates: "
        + ", ".join(sorted(unknown_sf_keys)[:5])
    )

verified_second_financing = 0
for r in second_financing:
    status = (r.get("second_financing_audit_status") or "").strip()
    if status == "VERIFIED_SECOND_POST_PHASE3_FINANCING":
        verified_second_financing += 1
        if (r.get("second_financing_status") or "").strip() != "CLOSED":
            raise SystemExit(f"second_financing_status.csv: verified row is not CLOSED: {r['event_key']}")
        for field in ("second_financing_announced","second_financing_running","second_financing_closed"):
            if (r.get(field) or "").strip().upper() != "YES":
                raise SystemExit(f"second_financing_status.csv: verified row missing {field}: {r['event_key']}")
        if not (r.get("second_financing_source") or "").strip():
            raise SystemExit(f"second_financing_status.csv: verified row missing source: {r['event_key']}")
        if not (r.get("second_financing_evidence_note") or "").strip():
            raise SystemExit(f"second_financing_status.csv: verified row missing evidence note: {r['event_key']}")
if verified_second_financing < 17:
    raise SystemExit(
        f"second_financing_status.csv: expected at least 17 verified second-financing rows, found {verified_second_financing}"
    )
unresearched_financing = [
    r["event_key"] for r in second_financing
    if not (r.get("second_financing_audit_status") or "").strip()
    or (r.get("second_financing_audit_status") or "").strip() == "NOT_VERIFIED"
]
if unresearched_financing:
    raise SystemExit(
        "second_financing_status.csv: live events remain unresearched: "
        + ", ".join(unresearched_financing[:5])
    )

history = read_csv(ROOT / "data/prediction_engine_history.csv")
hkeys = [r["event_key"].strip() for r in history]
if len(hkeys) != len(set(hkeys)):
    raise SystemExit("prediction_engine_history.csv: duplicate event_key")

pvalues = read_csv(ROOT / "data/prediction_engine_pvalues.csv")
pkeys = [r["event_key"].strip() for r in pvalues]
if len(pkeys) != len(set(pkeys)):
    raise SystemExit("prediction_engine_pvalues.csv: duplicate event_key")
# The p-value file is a provenance/evidence ledger and intentionally preserves
# superseded source event keys after canonical audit repairs. It may therefore
# contain more rows than the current canonical history and is not required to
# match history event_key-for-event_key.
verified_pvalues = sum(
    1 for r in pvalues
    if (r.get("reported_p_values") or "").strip()
    and (r.get("p_value_audit_status") or "").strip() == "VERIFIED_PRIMARY_OR_PIVOTAL"
)
if verified_pvalues < 1:
    raise SystemExit("prediction_engine_pvalues.csv: no verified historical P values found")
for r in pvalues:
    if (r.get("reported_p_values") or "").strip() and not (r.get("p_value_source_url") or "").strip():
        raise SystemExit(f"prediction_engine_pvalues.csv: populated P without source: {r['event_key']}")

designations = read_csv(ROOT / "data/prediction_engine_designations.csv")
dkeys = [r["event_key"].strip() for r in designations]
if len(dkeys) != len(set(dkeys)):
    raise SystemExit("prediction_engine_designations.csv: duplicate event_key")
# The designation file is also a provenance/evidence ledger. Canonical audit
# repairs can leave valid historical source keys that no longer equal the
# current prediction_engine_history event_key set.

designation_fields = [
    "orphan_drug","no_available_therapy","serious_condition","life_threatening",
    "fast_track","breakthrough_therapy","priority_review","accelerated_approval",
    "rmat","qidp","rare_pediatric_disease","priority_review_voucher",
    "rolling_review","rtor","project_orbis","spa",
]
bad_values = []
verified_checks = 0
for r in designations:
    for field in designation_fields:
        v = (r.get(field) or "").strip()
        if v not in {"", "YES"}:
            bad_values.append((r["event_key"], field, v))
        if v == "YES":
            verified_checks += 1
if bad_values:
    raise SystemExit(f"prediction_engine_designations.csv: invalid designation values {bad_values[:5]}")
if verified_checks < 1:
    raise SystemExit("prediction_engine_designations.csv: no verified positive designations found")

for year, expected in ((2020, 20), (2021, 24), (2022, 22)):
    year_rows = [r for r in history if (r.get("pdufa_date") or "").startswith(f"{year}-")]
    if len(year_rows) != expected:
        raise SystemExit(f"prediction_engine_history.csv: expected {expected} audited {year} rows, found {len(year_rows)}")
    for r in year_rows:
        cap = float(r["historical_market_cap_billions"])
        if not (0.3 <= cap <= 10.0):
            raise SystemExit(f"{year} history row outside $300M-$10B gate: {r['event_key']} cap={cap}")
        if (r.get("public_approval_probability") or "").strip() or (r.get("biopharmawatch_probability") or "").strip():
            raise SystemExit(f"{year} row fabricates unavailable historical public/vendor probability: {r['event_key']}")

history_2023 = [r for r in history if (r.get("pdufa_date") or "").startswith("2023-")]
if len(history_2023) != 24:
    raise SystemExit(f"prediction_engine_history.csv: expected 24 audited 2023 rows, found {len(history_2023)}")
for r in history_2023:
    cap = float(r["historical_market_cap_billions"])
    if not (0.3 <= cap <= 10.0):
        raise SystemExit(f"2023 history row outside $300M-$10B gate: {r['event_key']} cap={cap}")
    if (r.get("public_approval_probability") or "").strip() or (r.get("biopharmawatch_probability") or "").strip():
        raise SystemExit(f"2023 row fabricates unavailable historical public/vendor probability: {r['event_key']}")

history_2024 = [r for r in history if (r.get("pdufa_date") or "").startswith("2024-")]
if len(history_2024) != 26:
    raise SystemExit(f"prediction_engine_history.csv: expected 26 audited 2024 rows, found {len(history_2024)}")
for r in history_2024:
    cap = float(r["historical_market_cap_billions"])
    if not (0.3 <= cap <= 10.0):
        raise SystemExit(f"2024 history row outside $300M-$10B gate: {r['event_key']} cap={cap}")

app = (ROOT / "app.py").read_text(encoding="utf-8")
required_ui_contracts = [
    "Probability of Approval % — Public",
    "Probability of Approval % — All Sources",
    "Direction / FDA Match",
    "calendar-event-link",
    "color:#17211a !important",
    'return "Not scored"',
    'def _merged_table_sort_series',
    'def _sort_header_button',
    'def _merged_sort_payload',
    'components.html(table_html',
    "btn.addEventListener('click'",
    "icon.textContent = idx === activeIndex ? (ascending ? '▲' : '▼') : '⇅'",
    'Click the boxed ⇅ icon',
    'def load_second_financing_backfill',
    'second-fin-verified',
    'Verified second-financing closes:',
    'Financing research coverage:',
    'FINANCING CACHE FIX',
    '"2F Announced"',
    '"2F Running"',
    '"2F Closed"',
    'SECOND_FINANCING_COLUMNS = ["Announced", "Running", "Closed"]',
    'colspan="3">2nd Financing',
    'APPLICATION_COLUMNS = ["N", "B"]',
    'colspan="2">Application',
    '"PDUFA"',
    '"NEW COMPANY / EVENT DISCOVERY"',
    '"data/second_financing_status.csv"',
    '"Company Registry"',
    '"Needs Backfill"',
    '"7. RECHECK"',
    'RUN RECHECK — SELECTED EVENT',
    'RUN RECHECK — ALL EVENTS',
    '"PDUFA date / FDA decision"',
    '"Phase 3 results / p-value"',
    '"Financing closure"',
    '"Cash runway"',
    '"Market data"',
    '"Options / ownership / insiders"',
    'no current PDUFA event in the saved event feed',
    'def run_recheck_worker',
    '"data/recheck_status.csv"',
    '"8. FDA ENGINE"',
    '"FDA MODEL %"',
    '"FDA CALL"',
    '"FDA GATE"',
    'def load_fda_review_engine',
    '"data/fda_review_engine.csv"',
    '"data/fda_prediction_freezes.csv"',
    '"data/fda_review_backfill_queue.csv"',
    'def load_fda_review_backfill_queue',
    'FDA Discipline Backfill Queue',
    'FDA-V3 decision-safe benchmark',
    'Review Complete',
    'FDA-V3 Match',
    'Directional Coverage',
    'Backfill Remaining',
    'FDA-V3 historical backfill queue',
    '"1. DECISION"',
    'Year scroller',
    'Month scroller',
    'Month-by-month result',
    'OPEN FULL PDUFA DATA',
    'def load_fda_v3_historical_backtest',
    '### FDA-V3 Review',
    'V3 Evidence Summary',
    'INSTALL DECISION ON IPHONE',
    'Open as Web App',
    '@media (max-width: 768px)',
]
for label in required_ui_contracts:
    if label not in app:
        raise SystemExit(f"app.py missing required audit/UI contract: {label}")

# Missing probabilities must remain missing/not-scored rather than being silently
# coerced into a misleading literal 0% display.
for row in candidates:
    confidence = (row.get("confidence") or "").strip().upper()
    for field in ("approval_probability", "public_approval_probability", "biopharmawatch_probability"):
        raw = (row.get(field) or "").strip()
        if not raw and confidence in {"", "NOT SCORED", "UNSCORED"}:
            continue

print(
    f"smoke test passed: {len(registry)} company registry rows, {len(candidates)} live events, "
    f"{verified_second_financing} verified second-financing rows, "
    f"{len(history)} historical rows, {verified_checks} verified designation checks, {verified_pvalues} verified P values, authoritative event reconciliation locked"
)
