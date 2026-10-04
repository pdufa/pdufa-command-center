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

for r in candidates:
    d = r["pdufa_date"].strip()
    if d:
        datetime.strptime(d, "%Y-%m-%d")

history = read_csv(ROOT / "data/prediction_engine_history.csv")
hkeys = [r["event_key"].strip() for r in history]
if len(hkeys) != len(set(hkeys)):
    raise SystemExit("prediction_engine_history.csv: duplicate event_key")

app = (ROOT / "app.py").read_text(encoding="utf-8")
for label in [
    "Probability of Approval % — Public",
    "Probability of Approval % — All Sources",
]:
    if label not in app:
        raise SystemExit(f"app.py missing visible score label: {label}")

print(f"smoke test passed: {len(candidates)} live events, {len(history)} historical rows")
