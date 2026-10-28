"""Fictitious intake fixtures; these tests establish no FDA source truth."""
import csv
import json
from datetime import date, datetime
import pytest
from app.hop_history_ingest import parse_history
from app.hop_comparators import TargetCase, match_historical_cases, prediction_status
from app.hop_outcomes_import import REQUIRED_COLUMNS, validate_csv

AS_OF = date(2021, 1, 1)

def example():
    return dict(case_id="SYNTHETIC-fda-example-1", application_id="nda-000001", review_cycle=1,
                drug_name="Fictitious drug", sponsor="Fictitious sponsor", indication="lung cancer",
                therapeutic_area="oncology", modality="antibody", phase=3,
                decision_date="2020-01-02", outcome="APPROVED",
                evidence_as_of="2020-01-03", public_features_as_of="2019-12-01",
                source_title="Fictitious FDA source",
                source_url="https://www.fda.gov/drugs")

def test_empty_inventory_is_explicit():
    assert parse_history("[]") == []

def test_valid_curated_record():
    case = parse_history(json.dumps([example()]), as_of=AS_OF)[0]
    assert case.case_id == "SYNTHETIC-fda-example-1"
    assert (case.application_id, case.review_cycle) == ("NDA000001", 1)
    assert case.public_features_as_of == date(2019,12,1)
    assert case.evidence_as_of == date(2020,1,3)
    assert case.source_title == "Fictitious FDA source"
    assert case.drug_name == "Fictitious drug" and case.sponsor == "Fictitious sponsor"
    assert case.independently_adjudicated is False
    # Schema success cannot authorize comparison or a numerical prediction.
    target = TargetCase("lung cancer", "oncology", "antibody", 3, AS_OF)
    assert match_historical_cases(target, [case]) == []
    assert prediction_status([])["probability"] is None

@pytest.mark.parametrize("field,value", [
    ("source_url", "https://example.com/fda"),
    ("outcome", "PENDING"),
    ("phase", 0),
    ("decision_date", "2099-01-01"),
    ("case_id", ""),
])
def test_rejects_invalid_evidence(field, value):
    row = example()
    row[field] = value
    with pytest.raises(ValueError):
        parse_history(json.dumps([row]))

def test_duplicate_case_rejected():
    with pytest.raises(ValueError, match="duplicate"):
        parse_history(json.dumps([example(), example()]))

def test_rejects_predecision_outcome_evidence():
    row = example()
    row["evidence_as_of"] = "2020-01-01"
    with pytest.raises(ValueError, match="outcome_evidence_predates_decision"):
        parse_history(json.dumps([row]))

@pytest.mark.parametrize("cutoff", ["2020-01-02", "2020-01-03"])
def test_rejects_decision_day_or_postdecision_clinical_features(cutoff):
    row = dict(example(), public_features_as_of=cutoff)
    with pytest.raises(ValueError, match="features_not_predecision"):
        parse_history(json.dumps([row]))

@pytest.mark.parametrize("field,value", [
    ("decision_date", None), ("evidence_as_of", None),
    ("decision_date", 20200102), ("evidence_as_of", []),
    ("decision_date", ""), ("evidence_as_of", ""),
])
def test_rejects_missing_or_nontext_dates(field, value):
    record = example()
    record[field] = value
    with pytest.raises(ValueError):
        parse_history(json.dumps([record]))


def test_legacy_single_clock_inventory_requires_explicit_source_review():
    legacy = {k:v for k,v in example().items() if k in (
        "case_id", "indication", "therapeutic_area", "modality", "phase",
        "decision_date", "outcome", "evidence_as_of", "source_url")}
    legacy["evidence_as_of"] = "2020-01-01"
    with pytest.raises(ValueError, match="legacy single-clock"):
        parse_history(json.dumps([legacy]))


def test_duplicate_exact_cycle_rejected_across_local_ids_and_application_aliases():
    rows = [example(), dict(example(), case_id="SYNTHETIC-other", application_id="NDA000001")]
    with pytest.raises(ValueError, match="duplicate case/application review cycle"):
        parse_history(json.dumps(rows))


@pytest.mark.parametrize("field,value", [("phase", True), ("review_cycle", True),
                                        ("phase", "3"), ("review_cycle", "1")])
def test_json_numeric_identity_fields_are_strict_integers(field,value):
    row = dict(example(), **{field:value})
    with pytest.raises(ValueError, match="must be integers"):
        parse_history(json.dumps([row]))


@pytest.mark.parametrize("value", ["2021-01-01", datetime(2021,1,1)])
def test_explicit_replay_cutoff_requires_date(value):
    with pytest.raises(ValueError, match="as_of must be a date"):
        parse_history("[]", as_of=value)


def test_replay_uses_given_snapshot_instead_of_the_wall_clock():
    with pytest.raises(ValueError, match="outcome_evidence_after_import_as_of"):
        parse_history(json.dumps([example()]), as_of=date(2020,1,2))


def test_json_and_csv_preserve_the_same_identity_and_distinct_evidence_clocks(tmp_path):
    path = tmp_path / "synthetic.csv"
    with path.open("w",newline="",encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=REQUIRED_COLUMNS)
        writer.writeheader()
        writer.writerow(example())
    csv_result = validate_csv(path, as_of=AS_OF)
    csv_case = csv_result["records"][0]
    json_case = parse_history(json.dumps([example()]), as_of=AS_OF)[0]
    for field in REQUIRED_COLUMNS:
        assert getattr(json_case,field) == getattr(csv_case,field)
    assert csv_result["model_eligible_records"] == 0
    assert csv_result["independently_verified"] is False
    assert json_case.independently_adjudicated is False


@pytest.mark.parametrize("url", ["https://user@www.fda.gov/drugs", "https://www.fda.gov:8443/drugs",
                                  "https://www.fda.gov/drugs#claim", "https://www.fda.gov/"])
def test_json_reuses_the_strict_official_source_url_contract(url):
    with pytest.raises(ValueError, match="source_not_official_fda_https"):
        parse_history(json.dumps([dict(example(),source_url=url)]))


def test_client_supplied_adjudication_flag_cannot_certify_a_case():
    with pytest.raises(ValueError, match="complete historical metadata required"):
        parse_history(json.dumps([dict(example(),independently_adjudicated=True)]))


@pytest.mark.parametrize("key,value", [("application_id","NDA000002"),("outcome","COMPLETE_RESPONSE"),
                                       ("review_cycle",2),("public_features_as_of","2020-01-03")])
def test_duplicate_json_keys_cannot_silently_replace_identity_or_evidence(key,value):
    # Construct JSON with a repeated key; a Python dict would hide this defect.
    original = json.dumps(example())
    payload = "[" + original[:-1] + "," + json.dumps(key) + ":" + json.dumps(value) + "}]"
    with pytest.raises(ValueError, match="Duplicate JSON field"):
        parse_history(payload, as_of=AS_OF)
