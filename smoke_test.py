import csv
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent

REQUIRED = {
    "data/pdufa_candidates.csv": {
        "event_key", "ticker", "company", "drug", "indication", "pdufa_date",
        "approval_probability", "public_approval_probability", "biopharmawatch_probability",
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

EXPECTED_LIVE_EVENT_COUNT = 38
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

candidates = read_csv(ROOT / "data/pdufa_candidates.csv")
keys = [r["event_key"].strip() for r in candidates]
if any(not k for k in keys):
    raise SystemExit("pdufa_candidates.csv: blank event_key")
if len(keys) != len(set(keys)):
    raise SystemExit("pdufa_candidates.csv: duplicate event_key")
if len(candidates) != EXPECTED_LIVE_EVENT_COUNT:
    raise SystemExit(
        f"pdufa_candidates.csv: expected {EXPECTED_LIVE_EVENT_COUNT} live events, found {len(candidates)}"
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

history = read_csv(ROOT / "data/prediction_engine_history.csv")
hkeys = [r["event_key"].strip() for r in history]
if len(hkeys) != len(set(hkeys)):
    raise SystemExit("prediction_engine_history.csv: duplicate event_key")

pvalues = read_csv(ROOT / "data/prediction_engine_pvalues.csv")
pkeys = [r["event_key"].strip() for r in pvalues]
if len(pkeys) != len(set(pkeys)):
    raise SystemExit("prediction_engine_pvalues.csv: duplicate event_key")
if len(pvalues) != len(history):
    raise SystemExit(
        f"prediction_engine_pvalues.csv: expected {len(history)} rows, found {len(pvalues)}"
    )
if set(pkeys) != set(hkeys):
    raise SystemExit("prediction_engine_pvalues.csv: event_key set does not exactly match history")
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
if len(designations) != len(history):
    raise SystemExit(
        f"prediction_engine_designations.csv: expected {len(history)} rows, found {len(designations)}"
    )
if set(dkeys) != set(hkeys):
    raise SystemExit("prediction_engine_designations.csv: event_key set does not exactly match history")

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
    '"Sort column"',
    '"Ascending", "Descending"',
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
    f"smoke test passed: {len(candidates)} live events, "
    f"{len(history)} historical rows, {verified_checks} verified designation checks, {verified_pvalues} verified P values, authoritative event reconciliation locked"
)
