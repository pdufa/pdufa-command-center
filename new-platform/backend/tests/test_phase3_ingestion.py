"""Synthetic fixtures exercise ingestion logic; live evidence comes from runtime."""
from datetime import date

import pytest
from sqlalchemy import create_engine, text

from app import phase3_ingestion as ingestion


@pytest.fixture
def engine():
    value = create_engine("sqlite+pysqlite:///:memory:")
    ingestion.initialize(value)
    with value.begin() as c:
        c.execute(text("CREATE TABLE original_archive(nct_id TEXT PRIMARY KEY,payload TEXT)"))
        c.execute(text("INSERT INTO original_archive VALUES('NCT00116805','unchanged')"))
    yield value
    value.dispose()


def trial(number=1):
    return {
        "hasResults": True,
        "protocolSection": {
            "identificationModule": {"nctId": "NCT" + str(number).zfill(8), "briefTitle": "Synthetic unit-test trial"},
            "sponsorCollaboratorsModule": {"leadSponsor": {"name": "Synthetic unit-test sponsor"}},
            "designModule": {"phases": ["PHASE2", "PHASE3"]},
            "statusModule": {"overallStatus": "COMPLETED", "completionDateStruct": {"date": "2020-12-01"}},
            "armsInterventionsModule": {"interventions": [{"type": "DRUG", "name": "Synthetic test intervention"}]},
            "conditionsModule": {"conditions": ["Synthetic test condition"]},
        },
        "resultsSection": {"outcomeMeasuresModule": {"outcomeMeasures": [{
            "type": "PRIMARY", "title": "Synthetic measure", "unitOfMeasure": "units",
            "classes": [{"categories": [{"measurements": [{"groupId": "G1", "value": "12"}]}]}],
        }]}},
    }


def proof():
    return {"url": "https://clinicaltrials.gov/api/v2/studies?unit-test-fixture=1", "sha256": "a" * 64,
            "retrieved_at": "2026-10-30T00:00:00+00:00", "verification_status": "VERIFIED", "http_status": 200}


def page(studies, total, token=None):
    value = {"studies": studies, "totalCount": total}
    if token:
        value["nextPageToken"] = token
    return value, proof()


def test_normalization_preserves_posted_values_without_regulatory_inference():
    source = trial()
    normalized = ingestion.normalize_study(source, proof())
    assert normalized["nct_id"] == "NCT00000001"
    assert normalized["drug"] == ["Synthetic test intervention"]
    assert normalized["ticker"] is None
    assert normalized["primary_endpoint_result"]["outcomes"][0]["classes"][0]["categories"][0]["measurements"][0]["value"] == "12"
    assert normalized["source"]["sha256"] == ingestion.sha256(source)
    assert normalized["source"]["hash_scope"] == "canonical-study-json"
    assert normalized["source"]["url"].endswith("/NCT00000001")
    assert not any(key in normalized for key in ["decision", "approval_probability", "scientific_score", "pdufa_date", "assessments_completed"])


@pytest.mark.parametrize("change,code", [
    (lambda value: value.update(hasResults=False), "NO_POSTED_RESULTS"),
    (lambda value: value["protocolSection"]["designModule"].update(phases=["PHASE2"]), "NOT_PHASE3"),
    (lambda value: value["protocolSection"]["identificationModule"].update(nctId="BAD"), "INVALID_NCT"),
    (lambda value: value["protocolSection"]["sponsorCollaboratorsModule"].update(leadSponsor={}), "MISSING_TRIAL_IDENTITY"),
])
def test_critical_missing_or_invalid_data_is_not_ingested(change, code):
    source = trial()
    change(source)
    with pytest.raises(ValueError, match=code):
        ingestion.normalize_study(source, proof())


def test_no_primary_result_is_reported_as_missing_instead_of_favorable():
    source = trial()
    source["resultsSection"]["outcomeMeasuresModule"]["outcomeMeasures"] = []
    normalized = ingestion.normalize_study(source, proof())
    assert normalized["primary_endpoint_result"]["status"] == "NOT_REPORTED"
    assert normalized["primary_endpoint_result"]["outcomes"] == []


def test_bounded_checkpoint_resumes_and_preserves_original_archive(engine, monkeypatch):
    imported = []
    monkeypatch.setattr(ingestion, "_upsert_trial", lambda _, value: imported.append(value["nct_id"]))
    first = ingestion.sync(engine, max_pages=1, fetcher=lambda token: page([trial(1)], 2, "next-page"))
    assert first["state"] == "PAUSED" and first["next_page_pending"] is True
    assert first["records_imported"] == 1
    assert "next_page_token" not in first
    received = []

    def second(token):
        received.append(token)
        return page([trial(2)], 2)

    complete = ingestion.sync(engine, max_pages=1, fetcher=second)
    assert received == ["next-page"]
    assert complete["state"] == "COMPLETE" and complete["records_imported"] == 2
    assert complete["pages_completed"] == 2
    assert imported == ["NCT00000001", "NCT00000002"]
    with engine.connect() as c:
        assert c.execute(text("SELECT payload FROM original_archive")).scalar_one() == "unchanged"


def test_fetch_failure_retains_checkpoint_and_error_is_sanitized(engine, monkeypatch):
    monkeypatch.setattr(ingestion, "_upsert_trial", lambda *_: None)
    ingestion.sync(engine, max_pages=1, fetcher=lambda _: page([trial()], 2, "resume-token"))

    def fail(_):
        raise RuntimeError("source request may contain protected data")

    failed = ingestion.sync(engine, max_pages=1, fetcher=fail)
    assert failed["state"] == "FAILED"
    assert failed["error_code"] == "INGESTION_EXECUTION_FAILED"
    assert failed["records_imported"] == 1
    received = []

    def resume(token):
        received.append(token)
        return page([trial(2)], 2)

    assert ingestion.sync(engine, max_pages=1, fetcher=resume)["state"] == "COMPLETE"
    assert received == ["resume-token"]
    with engine.connect() as c:
        logs = c.execute(text("SELECT document FROM phase3_ingestion_history WHERE kind='SYNC_FAILED'")).scalars().all()
    assert logs and "protected data" not in "".join(logs)


def test_duplicates_do_not_inflate_scope_reconciliation(engine, monkeypatch):
    monkeypatch.setattr(ingestion, "_upsert_trial", lambda *_: None)
    ingestion.sync(engine, max_pages=1, fetcher=lambda _: page([trial()], 2, "second"))
    report = ingestion.sync(engine, max_pages=1, fetcher=lambda _: page([trial(), trial(2)], 2))
    assert report["state"] == "COMPLETE"
    assert report["records_seen"] == report["records_imported"] == 2


def test_missing_scope_records_prevent_complete_claim(engine, monkeypatch):
    monkeypatch.setattr(ingestion, "_upsert_trial", lambda *_: None)
    report = ingestion.sync(engine, max_pages=1, fetcher=lambda _: page([trial()], 2))
    assert report["state"] == "REVIEW_REQUIRED"
    assert report["error_code"] == "SCOPE_RECONCILIATION_REQUIRED"


def test_invalid_record_is_persisted_as_rejected_and_advances_checkpoint(engine, monkeypatch):
    monkeypatch.setattr(ingestion, "_upsert_trial", lambda *_: None)
    invalid = trial(2)
    invalid["protocolSection"]["identificationModule"]["nctId"] = "invalid"
    report = ingestion.sync(engine, max_pages=1, fetcher=lambda _: page([trial(), invalid], 2))
    assert report["state"] == "REVIEW_REQUIRED"
    assert report["records_imported"] == 1
    assert report["records_rejected"] == 1


def test_scope_is_not_limited_to_228_candidates(engine, monkeypatch):
    monkeypatch.setattr(ingestion, "_upsert_trial", lambda *_: None)

    def fetch(token):
        offset = int(token or 0)
        next_offset = offset + 25
        return page([trial(i) for i in range(offset + 1, min(next_offset, 300) + 1)], 300,
                    str(next_offset) if next_offset < 300 else None)

    report = ingestion.sync(engine, max_pages=20, fetcher=fetch)
    assert report["state"] == "COMPLETE"
    assert report["records_imported"] == 300 and report["pages_completed"] == 12


def test_scheduling_execution_is_claimed_only_after_automatic_page_execution(engine, monkeypatch):
    monkeypatch.setattr(ingestion, "_upsert_trial", lambda *_: None)
    assert ingestion.status(engine)["scheduling"]["verified_execution"] is False
    report = ingestion.sync(engine, max_pages=1, automatic=True, fetcher=lambda _: page([trial()], 1))
    assert report["scheduling"]["verified_execution"] is True
    assert report["scheduling"]["last_automatic_execution_at"] == proof()["retrieved_at"]
    assert report["scheduling"]["next_due_at"] is not None


def test_repeated_source_checkpoint_fails_without_skipping_records(engine, monkeypatch):
    monkeypatch.setattr(ingestion, "_upsert_trial", lambda *_: None)
    ingestion.sync(engine, max_pages=1, fetcher=lambda _: page([trial()], 2, "same"))
    report = ingestion.sync(engine, max_pages=1, fetcher=lambda _: page([trial(2)], 2, "same"))
    assert report["state"] == "FAILED"
    assert report["error_code"] == "INVALID_SOURCE_CHECKPOINT"
    assert report["next_page_pending"] is True


def test_upsert_storage_error_does_not_advance_page_checkpoint(engine, monkeypatch):
    def fail(*_):
        raise RuntimeError("storage interruption")
    monkeypatch.setattr(ingestion, "_upsert_trial", fail)
    report = ingestion.sync(engine, max_pages=1, fetcher=lambda _: page([trial()], 1, "would-skip"))
    assert report["state"] == "FAILED"
    assert report["pages_completed"] == 0
    assert report["next_page_pending"] is False


def test_complete_scope_waits_until_next_due_sync(engine, monkeypatch):
    monkeypatch.setattr(ingestion, "_upsert_trial", lambda *_: None)
    report = ingestion.sync(engine, max_pages=1, fetcher=lambda _: page([trial()], 1))
    original_sync = report["sync_id"]

    def should_not_fetch(_):
        raise AssertionError("should not redownload completed scope before due time")

    report = ingestion.sync(engine, max_pages=1, fetcher=should_not_fetch)
    assert report["state"] == "COMPLETE" and report["sync_id"] == original_sync


def test_real_catalog_integration_persists_verified_dossier_and_unknown_fda_outcome(engine):
    from app import phase3_catalog
    phase3_catalog.initialize(engine)
    report = ingestion.sync(engine, max_pages=1, fetcher=lambda _: page([trial()], 1))
    assert report["state"] == "COMPLETE" and report["records_imported"] == 1
    saved = phase3_catalog.catalog(engine, period="PREVIOUS", as_of=date(2026, 10, 30))
    assert saved["total"] == 1
    row = saved["trials"][0]
    assert row["nct_id"] == "NCT00000001"
    assert row["decision"] == "PENDING" and row["ticker"] is None
    assert row["evidence"][0]["sha256"] == ingestion.sha256(trial())
    with engine.connect() as c:
        dossier = phase3_catalog.saved_catalog_dossier(c, "NCT00000001")
        assert dossier["document"]["nct_id"] == "NCT00000001"
        assert dossier["sha256"] == phase3_catalog.digest(dossier["document"])
        assert c.execute(text("SELECT payload FROM original_archive")).scalar_one() == "unchanged"
