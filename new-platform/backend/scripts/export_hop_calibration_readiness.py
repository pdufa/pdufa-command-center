#!/usr/bin/env python3
"""Export observed HOP calibration blockers; no sources fetched or model fitted."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.hop_probability_calibration import calibration_readiness_status


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.output.parent.is_dir() or args.output.is_symlink():
        raise ValueError("Existing local output directory and non-symlink output required")
    snapshot = calibration_readiness_status()
    snapshot["generatedAtUtc"] = datetime.now(timezone.utc).isoformat()
    snapshot["generationScope"] = "LOCAL_EXISTING_RECEIPT_REPLAY_NOT_NEW_FDA_COLLECTION"
    snapshot["implementation"] = {
        "module": "new-platform/backend/app/hop_probability_calibration.py",
        "tests": "new-platform/backend/tests/test_hop_probability_calibration.py",
        "baseModelTrainingPerformed": False,
        "realCalibrationFitPerformed": False,
        "httpRoutesAdded": False,
    }
    raw = (json.dumps(snapshot, indent=2) + "\n").encode()
    with args.output.open("xb") as file:file.write(raw)
    print(json.dumps({"status": snapshot["modelValidationStatus"],
        "sourceActionLeads": snapshot["sourceActionLeads"], "newHistoricalRecordsObtained": 0,
        "modelEligibleCases": 0, "accuracy": snapshot["accuracy"],
        "outputSha256": hashlib.sha256(raw).hexdigest()}))


if __name__ == "__main__":
    main()
