"""Synthetic integrity/SQLite fixtures, never historical accuracy evidence."""
import copy
import hashlib
import json
from pathlib import Path
import sqlite3
import stat
import sys
import zipfile

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import ingest_hop_recovered_metadata as m


@pytest.fixture
def package(tmp_path, monkeypatch):
    crl = {"source_record_sha256": "a"*64, "source_record_index": 0, "source_partition": m.CRL_URL,
        "application_numbers": ["NDA 123456"], "company_name_as_published": "SYNTHETIC FIXTURE",
        "file_name_as_published": "fixture.pdf", "letter_type_as_published": "COMPLETE RESPONSE",
        "letter_date_as_published": "01/01/2020", "model_eligible": False, "independently_verified": False,
        "cohort_complete_verified": False, "review_cycle": None, "predecision_evidence_as_of": None,
        "status": "QUARANTINED_PUBLICATION_SELECTED"}
    sub = {"review_priority_as_published": None, "submission_number_as_published": "1",
        "submission_status_as_published": "AP", "submission_status_date_as_published": "20200102", "submission_type_as_published": "ORIG"}
    app = {"record_sha256": "b"*64, "source_record_index": 0, "source_archive_url": m.REGISTRY_URL,
        "application_number_as_published": "NDA123456", "sponsor_name_as_published": "SYNTHETIC FIXTURE",
        "model_eligible": False, "review_cycles_independently_adjudicated": False,
        "complete_application_denominator_verified": False, "point_in_time_features_verified": False,
        "status": "QUARANTINED_APPROVED_PRODUCT_REGISTRY", "submissions_as_published": [sub]}
    work = {"source_record_sha256": crl["source_record_sha256"], "application_ids_as_published": crl["application_numbers"],
        "file_name_as_published": "fixture.pdf", "letter_date_as_published": "01/01/2020", "letter_type_as_published": "COMPLETE RESPONSE"}
    for k in ("model_eligible", "identity_verified", "review_cycle_verified", "independent_review_complete", "complete_denominator_verified",
              "effective_fda_action_date_independently_verified", "original_fda_action_document_verified", "review_cycle_number_verified"):
        work[k] = False
    pdf = {"source_record_sha256": crl["source_record_sha256"], "source_application_ids_as_published": crl["application_numbers"],
        "source_file_name_as_published": "fixture.pdf", "letter_date_as_published": "01/01/2020", "letter_type_as_published": "COMPLETE RESPONSE",
        "document_fetch_status": "OFFICIAL_PDF_BYTES_CONFIRMED", "full_document_sha256_if_confirmed": "c"*64,
        "model_eligible": False, "document_identity_adjudicated": False, "effective_fda_action_date_verified": False, "review_cycle_verified": False}
    def snapshot(status, records):
        return {"schema_version": 1, "status": status, "records": records, "source_export_date": "2020-02-01", "retrieved_on": "2020-02-02"}
    contents = {
        "CRL_SNAPSHOT": {m.CRL_MEMBER: snapshot("QUARANTINED_NOT_A_COMPLETE_APPLICATION_COHORT", [crl]),
            "fda_crl_audit.json": {"archive_sha256_by_url": {m.CRL_URL: m.CRL_SOURCE_SHA}, "published_letter_records": 1,
                "quarantined_records": 1, "letter_types": {"COMPLETE RESPONSE": 1}}},
        "DRUGSFDA_SNAPSHOT": {m.REGISTRY_MEMBER: snapshot("APPROVED_REGISTRY_NOT_COMPLETE_DECISION_COHORT", [app]),
            "drugsfda_approved_registry_audit.json": {"source_archive_sha256": {m.REGISTRY_URL: m.REGISTRY_SOURCE_SHA},
                "source_application_records": 1, "quarantined_application_records": 1, "application_number_prefixes": {"NDA": 1},
                "published_submission_status_counts": {"AP": 1}, "missing_or_invalid_submissions": 0}},
        "ACTION_REVIEW": {name: {} for name in m.MEMBERS["ACTION_REVIEW"]},
    }
    contents["ACTION_REVIEW"].update({m.WORKLIST_MEMBER: snapshot("PUBLISHED_FDA_ACTION_REVIEW_ONLY_NO_VALIDATED_OUTCOMES", [work]),
        m.PDF_MEMBER: snapshot("PDF_FETCH_CHECK_ONLY_NOT_HISTORICAL_OUTCOME_VERIFICATION", [pdf]),
        "fda_shared_pdf_review_worksheet_audit.json": {"published_letter_rows": 0},
        "fda_shared_pdf_independent_review_worksheet.csv": "source_record_sha256,model_eligible,independent_review_complete,first_reviewer,second_reviewer\n"})
    pins = copy.deepcopy(m.PINNED_ARTIFACTS)
    monkeypatch.setattr(m, "PINNED_ARTIFACTS", pins)
    manifest = {"schema_version": 1, "record_type": "RECOVERED_HOP_ARTIFACT_PROVENANCE", "retrieved_on": "2026-10-27", "artifacts": []}
    for role in sorted(pins):
        manifest["artifacts"].append({"role": role, "repository": "pdufa/pdufa-command-center", "relative_path": role + ".zip", **pins[role]})
    path = tmp_path / "manifest.json"
    def save(mutator=None):
        for receipt in manifest["artifacts"]:
            role = receipt["role"]
            with zipfile.ZipFile(tmp_path / (role + ".zip"), "w", zipfile.ZIP_DEFLATED) as archive:
                for name, value in sorted(contents[role].items()):
                    archive.writestr(name, value if isinstance(value, str) else json.dumps(value))
            data = (tmp_path / (role + ".zip")).read_bytes()
            pins[role]["sha256"] = receipt["sha256"] = hashlib.sha256(data).hexdigest()
        if mutator: mutator(manifest)
        path.write_text(json.dumps(manifest))
        return path
    save()
    return path, contents, save, manifest


def test_dry_run_is_deterministic_and_does_not_write_database(package, tmp_path):
    path, _, _, _ = package
    before = sorted(p.name for p in tmp_path.iterdir())
    assert m.ingest(path) == m.ingest(path)
    assert sorted(p.name for p in tmp_path.iterdir()) == before
    r = m.ingest(path)
    assert r["counts"]["crl_source_observations"] == 1
    assert r["counts"]["registry_applications"] == 1
    assert r["counts"]["action_review_observations"] == 1  # same source entity, not a second CRL
    assert r["counts"]["identified_adjudicated_review_cycles"] == 0
    assert r["counts"]["independently_verified_pass"] == r["counts"]["independently_verified_fail"] == 0
    assert r["original_fda_bytes_retained"] is False


def test_sqlite_normalizes_real_rows_and_preserves_null_unknowns(package, tmp_path):
    path, _, _, _ = package
    target = tmp_path / "research.sqlite3"
    m.ingest(path, database=target)
    with sqlite3.connect(target) as db:
        for table, count in [("source_artifacts", 3), ("artifact_members", 14), ("crl_observations", 1),
            ("registry_applications", 1), ("registry_submissions", 1), ("action_review_observations", 1),
            ("pdf_check_observations", 1), ("review_cycles", 0)]:
            assert db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == count
        assert db.execute("SELECT drug,indication,trial_id,pdufa_target_date,source_publication_date,review_cycle,model_eligible FROM crl_observations").fetchone() == (None,)*6 + (0,)
        assert db.execute("SELECT drug,indication,trial_id,pdufa_target_date,source_publication_date FROM registry_applications").fetchone() == (None,)*5
        payload, sha = db.execute("SELECT payload_json,recovered_row_sha256 FROM source_records LIMIT 1").fetchone()
        assert hashlib.sha256(payload.encode()).hexdigest() == sha
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("UPDATE crl_observations SET model_eligible=1")
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("INSERT INTO review_cycles VALUES('NDA123456','ORIG',1,'PASS')")


def test_existing_destination_is_not_opened_or_overwritten(package, tmp_path):
    target = tmp_path / "existing.db"; target.write_bytes(b"leave user data unchanged")
    with pytest.raises(FileExistsError): m.ingest(package[0], database=target)
    assert target.read_bytes() == b"leave user data unchanged"


def test_failed_write_rolls_back_and_removes_only_new_file(package, tmp_path, monkeypatch):
    monkeypatch.setattr(m, "SCHEMA", m.SCHEMA + "CREATE TABLE source_artifacts(x);")
    target = tmp_path / "failed.db"
    with pytest.raises(sqlite3.Error): m.ingest(package[0], database=target)
    assert not target.exists()


@pytest.mark.parametrize("where", ["manifest", "artifact", "database"])
def test_symlink_paths_refused(package, tmp_path, where):
    path, _, _, _ = package
    if where == "manifest":
        alias = tmp_path / "alias.json"; alias.symlink_to(path)
        with pytest.raises(ValueError, match="symlink"): m.ingest(alias)
    elif where == "artifact":
        file = tmp_path / "CRL_SNAPSHOT.zip"; moved = tmp_path / "original.zip"; file.rename(moved); file.symlink_to(moved)
        with pytest.raises(ValueError, match="symlink"): m.ingest(path)
    else:
        original = tmp_path / "original.db"; original.write_bytes(b"safe")
        alias = tmp_path / "alias.db"; alias.symlink_to(original)
        with pytest.raises(ValueError, match="symlink"): m.ingest(path, database=alias)
        assert original.read_bytes() == b"safe"


@pytest.mark.parametrize("mutation", ["bad_sha", "bad_run", "bad_path", "extra_receipt", "duplicate_role", "future_receipt"])
def test_manifest_receipts_are_pinned(package, mutation):
    path, _, _, manifest = package
    if mutation == "bad_sha": manifest["artifacts"][0]["sha256"] = "f"*64
    elif mutation == "bad_run": manifest["artifacts"][0]["run_id"] += 1
    elif mutation == "bad_path": manifest["artifacts"][0]["relative_path"] = "../escape.zip"
    elif mutation == "extra_receipt": manifest["artifacts"][0]["independently_verified"] = True
    elif mutation == "duplicate_role": manifest["artifacts"][0] = manifest["artifacts"][1]
    else: manifest["retrieved_on"] = "2020-01-01"
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError): m.ingest(path)


def test_modified_zip_is_rejected_before_parsing(package):
    path, _, _, manifest = package
    file = path.parent / manifest["artifacts"][0]["relative_path"]
    file.write_bytes(file.read_bytes() + b"tampering")
    with pytest.raises(ValueError, match="digest mismatch"): m.ingest(path)


@pytest.mark.parametrize("content", ['{"schema_version":1,"schema_version":1}', '{broken', '{"value":NaN}'])
def test_malformed_or_duplicate_json_rejected(package, content):
    path, values, save, _ = package
    values["CRL_SNAPSHOT"][m.CRL_MEMBER] = content; save()
    with pytest.raises(ValueError): m.ingest(path)


@pytest.mark.parametrize("kind", ["extra", "missing", "symlink", "duplicate"])
def test_zip_members_must_be_exact_safe_regular_files(package, kind):
    path, values, save, manifest = package
    if kind == "extra":
        values["CRL_SNAPSHOT"]["../escape.json"] = {}; save()
    elif kind == "missing":
        del values["CRL_SNAPSHOT"]["fda_crl_audit.json"]; save()
    else:
        receipt = next(r for r in manifest["artifacts"] if r["role"] == "CRL_SNAPSHOT")
        file = path.parent / receipt["relative_path"]
        with zipfile.ZipFile(file, "a") as archive:
            if kind == "duplicate":
                with pytest.warns(UserWarning): archive.writestr(m.CRL_MEMBER, "{}")
        if kind == "symlink":
            with zipfile.ZipFile(file) as original:
                copied = [(info, original.read(info)) for info in original.infolist()]
            with zipfile.ZipFile(file, "w") as changed:
                for info, content in copied:
                    if info.filename == m.CRL_MEMBER:
                        info.external_attr = (stat.S_IFLNK | 0o777) << 16
                    changed.writestr(info, content)
        receipt["sha256"] = m.PINNED_ARTIFACTS["CRL_SNAPSHOT"]["sha256"] = hashlib.sha256(file.read_bytes()).hexdigest()
        path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError): m.ingest(path)


@pytest.mark.parametrize("mutation", ["promotion", "wrong_count", "duplicate_crl", "duplicate_app", "bad_join", "missing_review", "bad_snapshot_chronology"])
def test_quarantine_counts_uniqueness_and_cross_artifact_join(package, mutation):
    path, values, save, _ = package
    if mutation == "promotion": values["CRL_SNAPSHOT"][m.CRL_MEMBER]["records"][0]["model_eligible"] = True
    elif mutation == "wrong_count": values["CRL_SNAPSHOT"]["fda_crl_audit.json"]["published_letter_records"] = 2
    elif mutation == "duplicate_crl": values["CRL_SNAPSHOT"][m.CRL_MEMBER]["records"] *= 2
    elif mutation == "duplicate_app": values["DRUGSFDA_SNAPSHOT"][m.REGISTRY_MEMBER]["records"] *= 2
    elif mutation == "bad_join": values["ACTION_REVIEW"][m.WORKLIST_MEMBER]["records"][0]["source_record_sha256"] = "d"*64
    elif mutation == "missing_review": values["ACTION_REVIEW"][m.PDF_MEMBER]["records"] = []
    else: values["CRL_SNAPSHOT"][m.CRL_MEMBER]["retrieved_on"] = "2019-01-01"
    save()
    with pytest.raises(ValueError): m.ingest(path)


def test_raw_unknown_status_and_bad_date_are_preserved_without_labels(package, tmp_path):
    path, values, save, _ = package
    sub = values["DRUGSFDA_SNAPSHOT"][m.REGISTRY_MEMBER]["records"][0]["submissions_as_published"][0]
    sub.update(submission_status_as_published=None, submission_status_date_as_published="20200230")
    values["DRUGSFDA_SNAPSHOT"]["drugsfda_approved_registry_audit.json"]["published_submission_status_counts"] = {}
    save(); target = tmp_path / "unknown.db"
    report = m.ingest(path, database=target)
    assert report["counts"]["registry_submissions_without_status"] == 1
    assert report["published_submission_status_date_range"]["unknown_or_invalid_dates"] == 1
    with sqlite3.connect(target) as db:
        assert db.execute("SELECT published_status,published_status_date,published_status_date_raw FROM registry_submissions").fetchone() == (None, None, "20200230")


def test_application_format_normalization_is_candidate_only(package, tmp_path):
    path, values, save, _ = package
    values["DRUGSFDA_SNAPSHOT"][m.REGISTRY_MEMBER]["records"][0]["application_number_as_published"] = "NDA12345"
    save(); target = tmp_path / "normalized.db"; m.ingest(path, database=target)
    with sqlite3.connect(target) as db:
        assert db.execute("SELECT application_id_candidate,application_id_as_published,independently_verified FROM registry_applications").fetchone() == ("NDA012345", "NDA12345", 0)


def test_member_size_limit_applies_even_to_pinned_zip(package, monkeypatch):
    monkeypatch.setattr(m, "MAX_MEMBER_BYTES", 10)
    with pytest.raises(ValueError, match="unsafe ZIP member"): m.ingest(package[0])


def test_zip_encryption_flag_refused_before_member_read(package):
    path, _, _, manifest = package
    receipt = next(r for r in manifest["artifacts"] if r["role"] == "CRL_SNAPSHOT")
    file = path.parent / receipt["relative_path"]
    data = bytearray(file.read_bytes())
    central = data.index(b"PK\x01\x02")
    data[central + 8] |= 1
    file.write_bytes(data)
    receipt["sha256"] = m.PINNED_ARTIFACTS["CRL_SNAPSHOT"]["sha256"] = hashlib.sha256(data).hexdigest()
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="unsafe ZIP member"):
        m.ingest(path)


def test_sqlite_never_opens_destination_path(package, tmp_path, monkeypatch):
    original_connect = m.sqlite3.connect
    calls = []
    def capture(path, *args, **kwargs):
        calls.append(path)
        return original_connect(path, *args, **kwargs)
    monkeypatch.setattr(m.sqlite3, "connect", capture)
    target = tmp_path / "safe.db"
    m.ingest(package[0], database=target)
    assert calls == [":memory:"]
    assert target.is_file()


def test_replacement_created_before_exclusive_publish_is_preserved(package, tmp_path, monkeypatch):
    target = tmp_path / "race.db"
    original_publish = m._publish_new
    def concurrent_create(path, content):
        target.write_bytes(b"other writer data")
        return original_publish(path, content)
    monkeypatch.setattr(m, "_publish_new", concurrent_create)
    with pytest.raises(FileExistsError):
        m.ingest(package[0], database=target)
    assert target.read_bytes() == b"other writer data"
