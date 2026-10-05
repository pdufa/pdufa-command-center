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
    f"{len(history)} historical rows, authoritative event reconciliation locked"
)
