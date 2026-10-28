"""Synthetic intake fixtures verify chronology and quarantine, not FDA accuracy."""
from dataclasses import replace
from datetime import date, datetime
import json

import pytest

from app.hop_comparators import TargetCase, match_historical_cases
from app.hop_history_ingest import load_history, parse_history

AS_OF = date(2026, 10, 27)


def example():
    return dict(case_id="fda-example-1", application_id="BLA-125807", review_cycle=1,
                drug_name="Synthetic drug", sponsor="Synthetic sponsor", indication="lung cancer",
                therapeutic_area="oncology", modality="antibody", phase=3,
                decision_date="2020-01-02", outcome="APPROVED",
                evidence_as_of="2020-01-03", public_features_as_of="2020-01-01",
                source_title="Synthetic source fixture",
                source_url="https://www.fda.gov/example-letter")


def encode(*records):
    return json.dumps({"schema_version": 2, "records": list(records)})


def parse(*records):
    return parse_history(encode(*records), as_of=AS_OF)


def test_empty_inventory_is_explicit():
    assert parse() == []


def test_preserves_separate_chronology_and_exact_cycle_in_quarantine():
    case = parse(example())[0]
    assert case.application_id == "BLA125807"
    assert case.review_cycle == 1
    assert case.public_features_as_of < case.decision_date <= case.evidence_as_of
    assert case.independently_adjudicated is False
    target = TargetCase("lung cancer", "oncology", "antibody", 3, AS_OF)
    assert match_historical_cases(target, [case]) == []
    # Simulate separate adjudication only inside the test: accepted chronology
    # now agrees with the comparator instead of being structurally impossible.
    reviewed_fixture = replace(case, independently_adjudicated=True)
    assert [row.case_id for row in match_historical_cases(target, [reviewed_fixture])] == [case.case_id]


@pytest.mark.parametrize("legacy", [[], [example()], {"schema_version": 1, "records": []}])
def test_legacy_schema_requires_explicit_migration(legacy):
    with pytest.raises(ValueError, match="migrate legacy chronology"):
        parse_history(json.dumps(legacy), as_of=AS_OF)


@pytest.mark.parametrize("field,value", [
    ("source_url", "https://example.com/fda"),
    ("source_url", "https://user@www.fda.gov/example"),
    ("source_url", "https://www.fda.gov:8443/example"),
    ("source_url", "https://www.fda.gov/example#fragment"),
    ("source_url", "https://www.fda.gov/"),
    ("outcome", "PENDING"), ("outcome", "WITHDRAWN"),
    ("phase", 2), ("phase", 5), ("phase", True), ("phase", "3"),
    ("review_cycle", 0), ("review_cycle", True), ("review_cycle", "1"),
    ("application_id", "BL 125807/0"), ("application_id", "NDA123"),
    ("decision_date", "2099-01-01"), ("case_id", ""),
    ("decision_date", "20200102"), ("decision_date", "2020-02-30"),
    ("decision_date", "2020-01-02T00:00:00Z"),
    ("evidence_as_of", "2020-01-01"),
    ("evidence_as_of", "2099-01-01"),
    ("public_features_as_of", "2020-01-02"),
    ("public_features_as_of", "2020-01-03"),
])
def test_rejects_invalid_or_leaking_evidence(field, value):
    row = example()
    row[field] = value
    with pytest.raises(ValueError):
        parse(row)


@pytest.mark.parametrize("evidence_date", ["2020-01-02", "2020-01-03"])
def test_accepts_outcome_evidence_on_or_after_decision(evidence_date):
    row = example()
    row["evidence_as_of"] = evidence_date
    assert parse(row)[0].evidence_as_of == date.fromisoformat(evidence_date)


@pytest.mark.parametrize("field,value", [
    ("decision_date", None), ("evidence_as_of", None),
    ("decision_date", 20200102), ("evidence_as_of", []),
    ("decision_date", ""), ("evidence_as_of", ""),
    ("public_features_as_of", None), ("public_features_as_of", {}),
])
def test_rejects_missing_or_nontext_dates(field, value):
    record = example()
    record[field] = value
    with pytest.raises(ValueError, match="required text"):
        parse(record)


def test_rejects_duplicate_normalized_case_or_application_cycle():
    first = example()
    same_case = {**first, "case_id": " fda-example-1 ", "review_cycle": 2}
    same_cycle = {**first, "case_id": "other-case", "application_id": "bla125807"}
    for duplicate in (same_case, same_cycle):
        with pytest.raises(ValueError, match="duplicate"):
            parse(first, duplicate)


def test_preserves_crl_and_approval_in_distinct_explicit_cycles():
    first = {**example(), "outcome": "COMPLETE_RESPONSE"}
    second = {**example(), "case_id": "later-cycle", "review_cycle": 2,
              "decision_date": "2021-01-02", "evidence_as_of": "2021-01-03",
              "public_features_as_of": "2021-01-01"}
    cases = parse(first, second)
    assert [(c.application_id, c.review_cycle, c.outcome) for c in cases] == [
        ("BLA125807", 1, "COMPLETE_RESPONSE"), ("BLA125807", 2, "APPROVED")]
    assert all(c.independently_adjudicated is False for c in cases)


@pytest.mark.parametrize("field", ["independently_adjudicated", "model_eligible", "probability"])
def test_cannot_self_promote_through_json(field):
    with pytest.raises(ValueError, match="unexpected fields"):
        parse({**example(), field: True})


def test_rejects_duplicate_json_fields_and_invalid_envelope():
    with pytest.raises(ValueError, match="duplicate JSON field"):
        parse_history('{"schema_version":2,"schema_version":2,"records":[]}', as_of=AS_OF)
    for raw in ({"schema_version": True, "records": []}, {"schema_version": 2, "records": {}},
                {"schema_version": 2, "records": [], "verified": True}):
        with pytest.raises(ValueError):
            parse_history(json.dumps(raw), as_of=AS_OF)


def test_import_cutoff_is_explicit_and_load_uses_same_contract(tmp_path):
    with pytest.raises(ValueError, match="after_import_as_of"):
        parse_history(encode(example()), as_of=date(2020, 1, 2))
    with pytest.raises(ValueError, match="as_of must be a date"):
        parse_history(encode(), as_of=datetime(2020, 1, 2))
    path = tmp_path / "history.json"
    path.write_text(encode(example()), encoding="utf-8")
    assert load_history(path, as_of=AS_OF)[0].application_id == "BLA125807"


def test_rejects_oversized_inventory_before_parsing():
    with pytest.raises(ValueError, match="bounded text size"):
        parse_history(" " * (2 * 1024 * 1024 + 1), as_of=AS_OF)
