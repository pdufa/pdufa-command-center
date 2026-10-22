"""Export all saved trial summaries from the existing PDUFA PostgreSQL archive.

Run inside the backend environment with DATABASE_URL already configured.
Read-only. Does not modify Pipeline/GEM membership or FS/FA presets.
"""
import csv
import json
import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

FIELDS = [
    "nct_id", "study_url", "study_title", "official_title", "sponsor",
    "conditions", "interventions", "phases", "study_type", "status",
    "start_date", "primary_completion_date", "completion_date",
    "last_update_posted", "has_results", "p_value_count", "fetched_at",
]


def display(value):
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return str(value)


def main():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        sys.exit("DATABASE_URL is required; no export performed")
    engine = create_engine(db_url)
    target = Path(os.getenv("TRIAL_EXPORT_PATH", "/tmp/pdufa-master-trials.csv"))
    with engine.connect() as connection:
        count = connection.execute(text("SELECT COUNT(*) FROM full_trial_records")).scalar_one()
        if count == 0:
            sys.exit("Archive is empty; refusing to publish empty master trial export")
        with target.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(FIELDS)
            exported = 0
            for record in connection.execution_options(stream_results=True).execute(
                text("SELECT nct_id, summary, fetched_at FROM full_trial_records ORDER BY nct_id")
            ):
                summary = record.summary
                if isinstance(summary, str):
                    summary = json.loads(summary)
                summary = summary or {}
                values = {**summary, "nct_id": record.nct_id, "fetched_at": record.fetched_at}
                writer.writerow([display(values.get(key)) for key in FIELDS])
                exported += 1
    if exported != count:
        target.unlink(missing_ok=True)
        sys.exit(f"Export count mismatch: expected {count}, got {exported}")
    print(f"Verified {exported} saved trial summaries exported to {target}")


if __name__ == "__main__":
    main()
