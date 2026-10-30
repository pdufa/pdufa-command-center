"""Synthetic fixtures exercise source gates; they are never imported as live data."""
import hashlib
import json

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from app import phase3_regulatory as regulatory


@pytest.fixture
def engine():
    value = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    regulatory.initialize(value)
    return value


def article(nct="NCT00000001", words="approved", drug="Fixturemab", indication="lung cancer"):
    return regulatory._document("<html><body><p>On January 2, 2025, the Food and Drug Administration " + words + " " + drug + " (Fixturebrand, Fixture Corp) for " + indication + ".</p><p>Trial " + nct + " evaluated " + drug + ".</p><a href='/drugs/resources-information-approved-drugs/example'>more</a></body></html>", "https://www.fda.gov/drugs/resources-information-approved-drugs/fixture")


def test_approval_needs_explicit_affirmative_statement_and_date():
    value = article()
    parsed = regulatory._announcement(value)
    assert parsed["decision_date"] == "2025-01-02"
    assert parsed["indication"] == "lung cancer"
    assert parsed["published_at"] == value["retrieved_at"]
    assert regulatory._announcement(article(words="has not approved")) is None
    assert regulatory._announcement(regulatory._document("<html><p>FDA approved something for lung cancer.</p></html>", regulatory.INDEX)) is None


def test_official_url_validation_blocks_external_queue_and_protocols():
    assert regulatory._allowed_index(regulatory.INDEX + "?page=1")
    assert regulatory._allowed_article("https://www.fda.gov/drugs/resources-information-approved-drugs/fda-approves-fixture")
    assert not regulatory._allowed_article("https://www.fda.gov.evil.test/drugs/resources-information-approved-drugs/fda-approves-fixture")
    assert not regulatory._allowed_article("http://www.fda.gov/drugs/resources-information-approved-drugs/fda-approves-fixture")
    with pytest.raises(ValueError, match="HOST_NOT_ALLOWED"):
        regulatory.fetch("https://sponsor.example.test/statement")


def test_no_nct_no_decision_even_when_endpoint_success_is_reported(engine):
    value = article(nct="No identifier", words="approved")
    assert regulatory.reconcile_document(engine, "https://www.fda.gov/drugs/resources-information-approved-drugs/fixture", value)["reconciled"] == 0
    value = article(words="announced positive Phase 3 results for")
    assert regulatory.reconcile_document(engine, "https://www.fda.gov/drugs/resources-information-approved-drugs/fixture", value)["reconciled"] == 0


def test_unknown_trials_are_deferred_not_fabricated(engine, monkeypatch):
    monkeypatch.setattr(regulatory, "_catalog_trial", lambda *_: None)
    value = regulatory.reconcile_document(engine, "https://www.fda.gov/drugs/resources-information-approved-drugs/fixture", article())
    assert value == {"reconciled": 0, "deferred": 1, "reason": None}


def test_no_drug_or_indication_match_never_calls_application_lookup(engine, monkeypatch):
    monkeypatch.setattr(regulatory, "_catalog_trial", lambda *_: {"nct_id": "NCT00000001", "company": "Fixture Corp", "drugs": ["Othermab"], "indication": "lung cancer"})
    monkeypatch.setattr(regulatory, "_lookup_application", lambda *_: pytest.fail("unmatched drug cannot reach FDA application lookup"))
    result = regulatory.reconcile_document(engine, "https://www.fda.gov/drugs/resources-information-approved-drugs/fixture", article())
    assert result["reconciled"] == 0
    assert result["reason"] == "DRUG_OR_INDICATION_NOT_RECONCILED"


def test_application_ambiguity_fails_closed(monkeypatch):
    def application(number):
        return {"application_number": number, "sponsor_name": "Fixture Corp", "products": [{"brand_name": "Fixturebrand", "active_ingredients": [{"name": "Fixturemab"}]}]}
    values = {"results": [application("BLA000001"), application("BLA000002")]}
    monkeypatch.setattr(regulatory, "fetch", lambda *_args, **_kw: (json.dumps(values), values))
    matched, source = regulatory._lookup_application("Fixturemab", article(), {"company": "Fixture Corp"})
    assert matched is None and source is None


def test_verified_application_requires_sponsor_product_and_brand(monkeypatch):
    value = {"results": [{"application_number": "BLA000001", "sponsor_name": "Fixture Corp", "products": [{"brand_name": "Fixturebrand", "active_ingredients": [{"name": "Fixturemab"}]}]}]}
    raw = json.dumps(value)
    monkeypatch.setattr(regulatory, "fetch", lambda *_args, **_kw: (raw, value))
    matched, source = regulatory._lookup_application("Fixturemab", article(), {"company": "Fixture Corp"})
    assert matched["application_number"] == "BLA000001"
    assert source["sha256"] == hashlib.sha256(raw.encode()).hexdigest()
    assert regulatory._lookup_application("Fixturemab", article(), {"company": "Different Company"}) == (None, None)


def test_reconciliation_calls_catalog_only_after_all_primary_source_gates(engine, monkeypatch):
    from app import phase3_catalog
    calls = []
    monkeypatch.setattr(regulatory, "_catalog_trial", lambda *_: {"nct_id": "NCT00000001", "company": "Fixture Corp", "drugs": ["Fixturemab"], "indication": "Lung Neoplasms"})
    app = {"application_number": "BLA000001", "sponsor_name": "Fixture Corp"}
    monkeypatch.setattr(regulatory, "_lookup_application", lambda *_: (app, {"verified": True}))
    monkeypatch.setattr(phase3_catalog, "record_regulatory_evidence", lambda *args, **kwargs: calls.append(kwargs))
    value = article()
    result = regulatory.reconcile_document(engine, "https://www.fda.gov/drugs/resources-information-approved-drugs/fixture", value)
    assert result["reconciled"] == 1
    assert len(calls) == 1
    saved = calls[0]
    assert saved["nct_ids"] == ["NCT00000001"]
    assert saved["decision"] == "APPROVED"
    assert saved["source"]["document"] == value["body"]
    assert saved["source"]["sha256"] == hashlib.sha256(value["body"].encode()).hexdigest()
    assert saved["application_source"] == {"verified": True}


def test_incremental_index_discovery_checkpoint_and_dedup(engine, monkeypatch):
    target = "https://www.fda.gov/drugs/resources-information-approved-drugs/fda-approves-fixture"
    raw = "<html><a href='" + target + "'>real-source fixture</a><a href='https://example.test/never'>offsite</a></html>"
    monkeypatch.setattr(regulatory, "fetch", lambda url: (raw, regulatory._document(raw, url)))
    first = regulatory.sync(engine, max_pages=1)
    assert first["sources"]["PENDING"] == 1
    assert first["sources"]["COMPLETE"] == 1
    second = regulatory.sync(engine, max_pages=1)
    assert second["sources"]["COMPLETE"] == 2
    with engine.connect() as c:
        assert c.execute(text("SELECT COUNT(*) FROM phase3_regulatory_sources")).scalar_one() == 2
        assert c.execute(text("SELECT COUNT(*) FROM phase3_regulatory_history")).scalar_one() == 2


def test_http_failures_persist_source_health_and_retry_without_false_decisions(engine, monkeypatch):
    def failed(_url):
        raise ValueError("HTTP_403")
    monkeypatch.setattr(regulatory, "fetch", failed)
    state = regulatory.sync(engine, max_pages=1)
    assert state["status"] == "ERROR"
    assert state["last_error_code"] == "HTTP_403"
    assert state["reconciled_trial_application_links"] == 0
    assert state["ready_sources"] == 0
    with engine.connect() as c:
        row = c.execute(text("SELECT state,attempts,next_retry_at FROM phase3_regulatory_sources")).first()
    assert row[0] == "RETRY" and row[1] == 1 and row[2]


def test_deferred_primary_evidence_is_replayed_after_catalog_population_without_redownload(engine, monkeypatch):
    target = "https://www.fda.gov/drugs/resources-information-approved-drugs/fda-approves-fixture"
    with engine.begin() as c:
        c.execute(text("UPDATE phase3_regulatory_sources SET state='COMPLETE',last_checked_at=:now WHERE kind='INDEX'"), {"now": regulatory.stamp()})
        c.execute(text("INSERT INTO phase3_regulatory_sources(url,kind,state) VALUES(:url,'ARTICLE','PENDING')"), {"url": target})
    fetch_calls = []
    document = article()
    def fetched(url):
        fetch_calls.append(url)
        return "unused", document
    monkeypatch.setattr(regulatory, "fetch", fetched)
    results = iter([{"reconciled": 0, "deferred": 1, "reason": None}, {"reconciled": 1, "deferred": 0, "reason": None}])
    monkeypatch.setattr(regulatory, "reconcile_document", lambda *_: next(results))
    regulatory.sync(engine, max_pages=1)
    with engine.begin() as c:
        c.execute(text("UPDATE phase3_regulatory_sources SET next_retry_at='2000-01-01T00:00:00+00:00' WHERE url=:url"), {"url": target})
    complete = regulatory.sync(engine, max_pages=1)
    assert complete["reconciled_trial_application_links"] == 1
    assert complete["sources"]["COMPLETE"] == 2
    assert fetch_calls == [target]


def test_scope_size_and_source_health_are_honest(engine):
    value = regulatory.status(engine)
    assert value["status"] == "PENDING"
    assert value["reconciled_trial_application_links"] == 0
    assert value["sec"]["status"] in {"USER_AGENT_CONFIGURATION_REQUIRED", "CONFIGURED_NOT_EXECUTED"}
    assert value["official_sponsor"]["status"] == "EXPLICIT_PRIMARY_EVIDENCE_REQUIRED"
    with pytest.raises(ValueError):
        regulatory.sync(engine, max_pages=0)
