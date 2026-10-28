"""Fictitious roster contracts; no observed FDA predictive performance."""
import hashlib
import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

from scripts.audit_hop_cohort_manifest import audit_file


def payload():
    return {
        "schema_version": 1,
        "manifest": {
            "cohort_id": "synthetic-roster", "population_definition": "Fictitious test cohort",
            "start_date": "2020-01-01", "end_date": "2020-12-31",
            "source_url": "https://www.fda.gov/example",
            "expected_review_cycles": 1, "observed_review_cycles": 1,
            "independent_reviewer": "FICTITIOUS TEST VALUE",
            "source_retrieved_on": "2021-01-01",
            "independent_review_complete": True,
            "approval_and_crl_ascertainment_complete": True,
        },
        "expected_members": [{"application_id": "NDA000001", "review_cycle": 1}],
        "observed_members": [{"application_id": "NDA000001", "review_cycle": 1,
                              "disposition": "APPROVED"}],
    }


def test_cli_reports_blocked_even_when_metadata_roster_reconciles(tmp_path):
    path = tmp_path / "synthetic.json"
    raw = json.dumps(payload()).encode()
    path.write_bytes(raw)
    before = set(tmp_path.iterdir())
    script = Path(__file__).resolve().parents[1] / "scripts" / "audit_hop_cohort_manifest.py"
    result = subprocess.run([sys.executable, str(script), str(path), "--as-of", "2021-01-02"],
                            check=False, capture_output=True, text=True,
                            env={**os.environ, "PYTHONPATH": str(script.parents[1])})
    assert result.returncode == 1
    assert result.stderr == ""
    report = json.loads(result.stdout)
    assert report["status"] == "BLOCKED" and report["model_eligible"] is False
    assert report["independently_verified"] is False
    assert "external_source_verification_required" in report["blockers"]
    assert report["input_metadata"]["sha256"] == hashlib.sha256(raw).hexdigest()
    assert report["input_metadata"]["hash_scope"] == "EXACT_RESEARCH_INPUT_BYTES_NOT_FDA_DOCUMENT_BYTES"
    assert report["input_metadata"]["audit_as_of"] == "2021-01-02"
    assert "FICTITIOUS TEST VALUE" not in result.stdout
    assert path.read_bytes() == raw and set(tmp_path.iterdir()) == before


@pytest.mark.parametrize("field,value", [("schema_version",True),("schema_version",2),
                                        ("expected_members",{}),("observed_members",None)])
def test_cli_rejects_invalid_envelope(tmp_path,field,value):
    data = payload()
    data[field] = value
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        audit_file(path, as_of=date(2021,1,2))


def test_cli_rejects_duplicate_fields_instead_of_silently_replacing_claims(tmp_path):
    path = tmp_path / "repeated-key.json"
    path.write_text('{"schema_version":1,"schema_version":2}')
    with pytest.raises(ValueError,match="duplicate JSON"):
        audit_file(path,as_of=date(2021,1,2))
