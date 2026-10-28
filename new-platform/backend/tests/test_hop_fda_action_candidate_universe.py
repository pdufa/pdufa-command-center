"""Synthetic source-projection tests; no real FDA cohort outcome prediction."""
from copy import deepcopy
from datetime import date
from importlib.util import module_from_spec, spec_from_file_location
from io import BytesIO
import hashlib
import json
from pathlib import Path
import zipfile

import pytest

from app.hop_fda_action_candidate_universe import (
    _letter_identity, build_fda_action_candidate_queue,
)

ROOT = Path(__file__).resolve().parents[1]
BENCHMARKS = json.loads((ROOT / "app" / "research_sources"
                         / "hop_fda_pdufa_filing_benchmarks.json").read_text())
source_spec = spec_from_file_location(
    "candidate_source_cli",
    ROOT / "scripts" / "audit_hop_fda_action_candidate_sources.py")
cli = module_from_spec(source_spec)
source_spec.loader.exec_module(cli)
ASOF = date(2026, 10, 28)


def approved(app="NDA123456", subs=None, *, hash_digit="a"):
    if subs is None:
        subs = [("ORIG", "1", "AP", "20240420")]
    return {
        "application_number_as_published": app,
        "submissions_as_published": [
            {
                "submission_type_as_published": typ,
                "submission_number_as_published": unit,
                "submission_status_as_published": status,
                "submission_status_date_as_published": when,
            }
            for typ, unit, status, when in subs
        ],
        "record_sha256": hash_digit * 64,
        "model_eligible": False,
        "complete_application_denominator_verified": False,
        "review_cycles_independently_adjudicated": False,
        "point_in_time_features_verified": False,
    }


def crl(identifiers=None, *, when="04/21/2024", hash_digit="b",
        letter_type="COMPLETE RESPONSE"):
    return {
        "application_numbers": identifiers or ["BLA 761303/Original 1"],
        "letter_date_as_published": when,
        "letter_type_as_published": letter_type,
        "source_record_sha256": hash_digit * 64,
        "model_eligible": False,
        "independently_verified": False,
        "cohort_complete_verified": False,
    }


def sources():
    registry = {
        "status": "APPROVED_REGISTRY_NOT_COMPLETE_DECISION_COHORT",
        "source_export_date": "2026-10-23",
        "retrieved_on": "2026-10-25",
        "records": [
            approved("NDA123456", [
                ("ORIG", "1", "AP", "20240420"),
                ("SUPPL", "2", "AP", "20250101"),
                ("ORIG", "1", "AP", "20240420"),  # duplicated source action
                ("ORIG", "1", "TA", "20240620"),
            ], hash_digit="a"),
            approved("BLA761303", [("ORIG", "1", "AP", "20250615")], hash_digit="c"),
            approved("ANDA000007", hash_digit="d"),
            approved("NDA999999", [("ORIG", "1", "AP", "20160615")], hash_digit="e"),
        ],
    }
    letters = {
        "status": "QUARANTINED_NOT_A_COMPLETE_APPLICATION_COHORT",
        "source_export_date": "2026-10-21",
        "retrieved_on": "2026-10-25",
        "records": [
            crl(["NDA 123456"], hash_digit="f"),
            crl(["BLA 761303/Original 1"], hash_digit="1"),
            crl(["NDA 123456/S-001"], hash_digit="2"),
            crl(["BL 125701"], hash_digit="3"),
            crl(["BLA 761303/Original 1", "BLA 761303"], hash_digit="4"),
            crl(["NDA 999999"], when="01/20/2025", hash_digit="5"),
            crl(["NDA 999999"], letter_type="TENTATIVE APPROVAL", hash_digit="6"),
        ],
    }
    return registry, letters


def audit(registry=None, letters=None, *, as_of=ASOF):
    r, c = sources()
    return build_fda_action_candidate_queue(
        r if registry is None else registry,
        c if letters is None else letters, BENCHMARKS, as_of=as_of)


def test_multiple_types_original_and_supplement_never_conflate():
    report = audit()
    assert report["status"].endswith("NOT_A_COMPLETE_COHORT")
    assert report["sourceRecordsInspected"] == {
        "approvedProductRegistry": 4,
        "selectedPublishedLetters": 7,
    }
    assert report["researchCandidateRows"] == 9  # 3 orig acts, 6 CRLs
    by_fy = {r["fiscalActionYear"]: r for r in report["selectedFiscalActionYears"]}
    fy24, fy25 = by_fy[2024], by_fy[2025]
    assert fy24["reportedOriginalApplicationFilingsInFY"] == 129
    assert fy25["reportedOriginalApplicationFilingsInFY"] == 157
    assert fy24["sourceRegistryOriginalAPActionCandidates"] == 1
    assert fy24["sourceRegistryTentativeApprovalNonbinaryCandidates"] == 1
    assert fy24["selectedPublishedCRLParentOnly"] == 1
    assert fy24["selectedPublishedCRLExplicitOriginal"] == 1
    assert fy24["selectedPublishedCRLSupplementExcluded"] == 1
    assert fy24["selectedPublishedCRLLegacyOrUnresolved"] == 1
    assert fy24["selectedPublishedCRLMultipleOrMissing"] == 1
    assert fy24["applicationsRepresentedInBothArchivesSameFiscalActionYear"] == 1
    assert fy25["sourceRegistryOriginalAPActionCandidates"] == 1
    assert fy25["selectedPublishedCRLParentOnly"] == 1
    assert fy25["reportedOriginalApplicationFilingsInFY"] == 157
    assert fy24["uniqueFiledApplicationsEnumerated"] is None
    assert fy24["filingDenominatorCoverage"] is None
    assert fy24["actionOutcomeApprovalFraction"] is None
    assert report["applicationLevelFilingDenominatorIndependentlyVerified"] is False
    assert report["allPendingWithdrawnAndUnapprovedCasesRepresented"] is False
    assert report["independentlyVerifiedModelEligibleCycles"] == 0
    assert report["independentRealBacktests"] == 0
    assert report["predictionAccuracy"] is None
    assert report["approvalProbability"] is None
    assert report["trainingAuthorized"] is False
    assert report["tradeAuthorized"] is False
    assert "REPORT_YEAR_FILING_COUNTS_CANNOT_BE_COMPARED_TO_ACTION_YEAR_CANDIDATES" in report["blockers"]
    for row in report["researchCandidates"]:
        assert row["modelEligible"] is False
        assert row["publicOutcomeLabelDateIndependentlyVerified"] is False
        assert row["exactReviewCycleIndependentlyVerified"] is False
        assert row["predecisionEvidenceVerified"] is False


def test_legacy_original_and_supplement_are_not_parent_only():
    assert _letter_identity(["BLA 761303/Original 2"]) == (
        "EXPLICIT_ORIGINAL", "BLA761303", "2")
    assert _letter_identity(["NDA 217225/S-001"]) == (
        "SUPPLEMENT_NOT_ORIGINAL", "NDA217225", "S-001")
    assert _letter_identity(["BL 125806"]) == (
        "LEGACY_OR_UNRESOLVED_IDENTIFIER", None, None)
    assert _letter_identity(["NDA 217724/Original 1", "NDA 217724"]) == (
        "MULTIPLE_OR_MISSING_IDENTIFIERS", None, None)
    assert _letter_identity([]) == (
        "MULTIPLE_OR_MISSING_IDENTIFIERS", None, None)


def test_duplicate_original_actions_do_not_double_count():
    report = audit()
    original_rows = [r for r in report["researchCandidates"]
                     if r["source"] == "DRUGSFDA_APPROVED_PRODUCT_REGISTRY"]
    assert len(original_rows) == 3
    assert len([r for r in original_rows if r["sourceAction"] == "AP"]) == 2
    assert len([r for r in original_rows if r["sourceAction"] == "TA"]) == 1


@pytest.mark.parametrize("mutator", [
    lambda r, c: r.update(status="COMPLETE_FDA_FILING_ROSTER"),
    lambda r, c: c.update(status="ALL_FDA_CRL_LETTERS"),
    lambda r, c: r.update(source_export_date="2026-10-29"),
    lambda r, c: c.update(retrieved_on="2026-10-30"),
    lambda r, c: r["records"][0].update(model_eligible=True),
    lambda r, c: r["records"][0].update(complete_application_denominator_verified=True),
    lambda r, c: r["records"][0].update(point_in_time_features_verified=True),
    lambda r, c: r["records"][0].update(review_cycles_independently_adjudicated=True),
    lambda r, c: c["records"][0].update(model_eligible=True),
    lambda r, c: c["records"][0].update(cohort_complete_verified=True),
    lambda r, c: c["records"][0].update(independently_verified=True),
    lambda r, c: r["records"][0].update(record_sha256="bad"),
    lambda r, c: c["records"][0].update(source_record_sha256="bad"),
    lambda r, c: c["records"][1].update(source_record_sha256=c["records"][0]["source_record_sha256"]),
    lambda r, c: r["records"].append(deepcopy(r["records"][0])),
    lambda r, c: c.update(records=[]),
    lambda r, c: r.update(records=[]),
])
def test_forged_sample_completeness_or_corrupt_record_blocks(mutator):
    r, c = sources()
    mutator(r, c)
    with pytest.raises(ValueError):
        audit(r, c)


@pytest.mark.parametrize("fys", [(), (2025, 2024), (2024, 2024),
                                      (2023,), (2024, 2026), (2024, True)])
def test_bad_fiscal_scope_refused(fys):
    r, c = sources()
    with pytest.raises(ValueError):
        build_fda_action_candidate_queue(
            r, c, BENCHMARKS, as_of=ASOF, fiscal_years=fys)


def test_publisher_observation_is_not_2020_historical_knowledge():
    r, c = sources()
    with pytest.raises(ValueError, match="chronology"):
        build_fda_action_candidate_queue(
            r, c, BENCHMARKS, as_of=date(2020, 1, 1))


def _synthetic_zip(name, payload):
    io = BytesIO()
    with zipfile.ZipFile(io, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr(name, payload)
    return io.getvalue()


def test_cli_pin_sha_refuses_wrong_artifact_bytes(tmp_path):
    app_zip = tmp_path/"registry.zip"
    app_zip.write_bytes(_synthetic_zip(
        "drugsfda_approved_registry_quarantined.json", b'{"records":[]}'))
    with pytest.raises(ValueError, match="hash"):
        cli._quarantined_json(app_zip,
            name="drugsfda_approved_registry_quarantined.json",
            expected_sha256="0"*64)


def test_cli_real_source_shape_with_test_digest(monkeypatch, tmp_path):
    r, _ = sources()
    blob = json.dumps(r).encode()
    digest = hashlib.sha256(blob).hexdigest()
    file = tmp_path/"registry.zip"
    file.write_bytes(_synthetic_zip(
        "drugsfda_approved_registry_quarantined.json", blob))
    assert cli._quarantined_json(
        file, name="drugsfda_approved_registry_quarantined.json",
        expected_sha256=digest)["status"] == r["status"]
    monkeypatch.setattr(cli, "_MAX_BYTES", 1)
    with pytest.raises(ValueError, match="missing or oversized"):
        cli._quarantined_json(
            file, name="drugsfda_approved_registry_quarantined.json",
            expected_sha256=digest)
