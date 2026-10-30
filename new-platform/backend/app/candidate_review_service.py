"""Isolated, append-only scientific evidence review; never mutates trial archives."""
from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from sqlalchemy import text

from .archive_protection import canonical, close_read, digest, inspect_payload, read_connection
from .archive_readiness import study_readiness
from .scientific_candidates import build_dossier, extract_regulatory_identifiers

LOG = logging.getLogger(__name__)
VERSION = "scientific-candidate-review-v1"
EXPECTED = 228
LOCK_ID = 228116223
BASELINE_DATE = date(2026, 10, 30)
_lock = threading.Lock()
_thread = None


def now():
    return datetime.now(timezone.utc).isoformat()


def curated_evidence():
    path = Path(__file__).with_name("regulatory_reconciliation_evidence.json")
    return json.loads(path.read_text()) if path.exists() else {}


def run_key():
    return VERSION + ":" + digest(curated_evidence())[:16]


def initialize(engine):
    with engine.begin() as c:
        c.execute(text("""CREATE TABLE IF NOT EXISTS scientific_review_runs (
            run_id TEXT PRIMARY KEY, verified_at TEXT NOT NULL, summary TEXT NOT NULL)"""))
        c.execute(text("""CREATE TABLE IF NOT EXISTS scientific_candidate_dossiers (
            run_id TEXT NOT NULL, nct_id VARCHAR(11) NOT NULL, document TEXT NOT NULL,
            sha256 VARCHAR(64) NOT NULL CHECK (length(sha256)=64),
            PRIMARY KEY (run_id,nct_id), FOREIGN KEY (run_id) REFERENCES scientific_review_runs(run_id))"""))
        c.execute(text("""CREATE TABLE IF NOT EXISTS regulatory_identifier_reconciliations (
            run_id TEXT NOT NULL, nct_id VARCHAR(11) NOT NULL, identifier TEXT NOT NULL,
            document TEXT NOT NULL, PRIMARY KEY(run_id,nct_id,identifier),
            FOREIGN KEY (run_id) REFERENCES scientific_review_runs(run_id))"""))
        if engine.dialect.name == "postgresql":
            for table in ("scientific_review_runs", "scientific_candidate_dossiers", "regulatory_identifier_reconciliations"):
                exists = c.execute(text("SELECT 1 FROM pg_trigger WHERE tgname=:name AND tgrelid=CAST(:table AS regclass)"), {"name": table + "_immutable", "table": table}).scalar()
                if not exists:
                    c.execute(text(f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON {table} FOR EACH STATEMENT EXECUTE FUNCTION archive_metadata_append_only()"))
                c.execute(text(f"REVOKE ALL ON {table} FROM PUBLIC"))
        else:
            for table in ("scientific_review_runs", "scientific_candidate_dossiers", "regulatory_identifier_reconciliations"):
                for operation in ("UPDATE", "DELETE"):
                    c.execute(text(f"CREATE TRIGGER IF NOT EXISTS {table}_{operation.lower()} BEFORE {operation} ON {table} BEGIN SELECT RAISE(ABORT, 'scientific review metadata is append-only'); END"))


def source_inventory(engine):
    selected, regulators, seen = [], [], set()
    c = read_connection(engine)
    try:
        database = c.execute(text("SELECT current_database()")).scalar_one() if engine.dialect.name == "postgresql" else "sqlite_test"
        manifest = c.execute(text("SELECT document,sha256 FROM archive_manifests WHERE archive_id='pdufa-ctgov-saved-scope-11622-v1'")).one()
        doc = json.loads(manifest[0])
        if digest(doc) != manifest[1]:
            raise ValueError("Manifest checksum failed")
        expected = {r["nct_id"]: r["sha256"] for r in doc["records"]}
        count = c.execute(text("SELECT count(*) FROM full_trial_records")).scalar_one()
        if count != len(expected) or count != 11622:
            raise ValueError("Archive count does not match immutable baseline")
        offset = 0
        while True:
            rows = c.execute(text("SELECT nct_id,payload_gzip,sha256 FROM full_trial_records ORDER BY nct_id LIMIT 100 OFFSET :offset"), {"offset": offset}).all()
            if not rows:
                break
            for nct, packed, sha in rows:
                if nct in seen:
                    raise ValueError("Duplicate archived NCT identifier")
                seen.add(nct)
                errors, study = inspect_payload(nct, packed, sha)
                if any(errors.values()) or expected.get(nct) != sha:
                    raise ValueError("Archive no longer matches verified baseline")
                if study_readiness(study, today=BASELINE_DATE)["scientific_ready"]:
                    selected.append((nct, bytes(packed), sha))
                ids = extract_regulatory_identifiers(study)
                if ids:
                    p = study.get("protocolSection", {})
                    regulators.append({"associated_nct_id": nct,
                                       "sponsor": p.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {}).get("name"),
                                       "products": p.get("armsInterventionsModule", {}).get("interventions", []),
                                       "identifiers": ids, "archive_sha256": sha})
            offset += len(rows)
            if offset % 1000 == 0:
                LOG.warning("PDUFA_CANDIDATE_SOURCE_PROGRESS rows=%d", offset)
        if seen != set(expected):
            raise ValueError("Archive identities differ from immutable baseline")
        if len(selected) != EXPECTED:
            raise ValueError("Candidate selection differs from fixed October 30 baseline")
        return selected, regulators, {"database": database, "manifest_sha256": manifest[1], "archive_count": count}
    finally:
        close_read(c)


def fetch_json(url):
    """Fixed public primary-source URLs only; never follows archive-provided links."""
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "PDUFA-read-only-scientific-review/1.0"})
    try:
        with urlopen(request, timeout=20) as response:
            raw = response.read(20 * 1024 * 1024 + 1)
            if len(raw) > 20 * 1024 * 1024:
                raise ValueError("Primary source exceeds bounded response size")
            return json.loads(raw), {"url": url, "fetched_at": now(), "http_status": response.status,
                                     "sha256": hashlib.sha256(raw).hexdigest(), "status": "FETCHED"}
    except HTTPError as exc:
        return None, {"url": url, "fetched_at": now(), "http_status": exc.code, "status": "UNAVAILABLE", "error_type": type(exc).__name__}
    except Exception as exc:
        return None, {"url": url, "fetched_at": now(), "status": "ERROR", "error_type": type(exc).__name__}


def live_registry(ids):
    """Fresh exact-ID batch, with exact membership/duplicate and pagination checks."""
    url = "https://clinicaltrials.gov/api/v2/studies?" + urlencode({"filter.ids": ",".join(ids), "pageSize": 100, "format": "json"})
    payload, proof = fetch_json(url)
    found = {}
    if payload is not None:
        if not isinstance(payload.get("studies"), list) or payload.get("nextPageToken"):
            proof = {**proof, "status": "ERROR", "error_type": "UnexpectedRegistryPagination"}
        else:
            for study in payload["studies"]:
                nct = study.get("protocolSection", {}).get("identificationModule", {}).get("nctId")
                if nct not in ids or nct in found:
                    return {}, {**proof, "status": "ERROR", "error_type": "UnexpectedRegistryIdentity"}
                found[nct] = study
    return found, proof


def fda_lookup(study):
    interventions = study.get("protocolSection", {}).get("armsInterventionsModule", {}).get("interventions", [])
    names = [i.get("name", "").strip() for i in interventions if i.get("type") in ("DRUG", "BIOLOGICAL") and i.get("name", "").strip().lower() not in ("", "placebo", "saline", "normal saline")]
    # One exact ingredient-name search per study. It is a search result, never a
    # claim that an application supports this indication or clinical trial.
    if not names:
        return {"status": "NOT_SEARCHABLE", "reason": "No named active drug/biological intervention"}
    name = names[0].replace('"', '')[:180]
    url = "https://api.fda.gov/drug/drugsfda.json?" + urlencode({"search": 'products.active_ingredients.name:"' + name + '"', "limit": 5})
    payload, proof = fetch_json(url)
    if proof.get("http_status") == 404:
        proof["status"] = "NO_MATCH"
    applications = []
    if payload is not None:
        for row in payload.get("results", []):
            applications.append({"application_number": row.get("application_number"), "sponsor_name": row.get("sponsor_name"),
                                 "products": [{"brand_name": p.get("brand_name"), "active_ingredients": p.get("active_ingredients", [])} for p in row.get("products", [])]})
    return {**proof, "query_product": name, "applications": applications,
            "caveat": "Product-level application search does not establish this trial's FDA pathway, indication, submission, designations or PDUFA date. No hit is not evidence of no application."}


def reconcile_regulators(regulators, live, proofs, evidence):
    results, seen = [], set()
    for record in regulators:
        nct = record["associated_nct_id"]
        for item in record["identifiers"]:
            identifier = item.get("identifier") or item.get("matched_identifier") or item.get("value")
            if not identifier:
                raise ValueError("Regulatory identifier extractor must preserve exact identifier")
            if (nct, identifier) in seen:
                continue
            seen.add((nct, identifier))
            curated = evidence.get(nct + "|" + identifier, {})
            row = {**record, "identifier": identifier, "raw_identifier": item, "status": "UNRESOLVED",
                   "archived_interventions": record["products"],
                   "products": [p.get("name", "") for p in record["products"] if p.get("type") in ("DRUG", "BIOLOGICAL")],
                   "verified_at": now(), "registry_checked": nct in live, "registry_source": proofs.get(nct),
                   "evidence": [], "conflicts": [],
                   "explanation": "Archive secondary identifier requires independent FDA and sponsor evidence. A registry assertion alone does not verify the regulatory identifier."}
            if curated:
                # Curated citations are reviewed primary sources, not inferred
                # from openFDA product-name matches or trial phase.
                if curated.get("status") not in ("VERIFIED", "CONFLICTING", "UNRESOLVED"):
                    raise ValueError("Invalid curated reconciliation classification")
                sources = curated.get("evidence", [])
                if not isinstance(sources, list) or not sources:
                    raise ValueError("Curated reconciliation requires source provenance")
                from urllib.parse import urlsplit
                for source in sources:
                    if not source.get("url", "").startswith("https://") or not source.get("checked_at") or not source.get("supports"):
                        raise ValueError("Incomplete reconciliation source provenance")
                if curated["status"] == "VERIFIED" and not any((urlsplit(s["url"]).hostname or "") == "fda.gov" or (urlsplit(s["url"]).hostname or "").endswith(".fda.gov") or (s.get("source_type") == "SPONSOR_REGULATORY_DISCLOSURE" and s.get("sponsor_domain_verified") is True) for s in sources):
                    raise ValueError("Verified identifier requires independent FDA or sponsor evidence")
                for field in ("status", "evidence", "conflicts", "explanation", "next_action"):
                    if field in curated:
                        row[field] = curated[field]
                row["verified_at"] = now()
            results.append(row)
    return results


def execute_review(engine):
    if not _lock.acquire(blocking=False):
        return {"status": "SKIPPED_OVERLAP"}
    connection = None
    acquired = False
    phase = "initialize"
    try:
        initialize(engine)
        key = run_key()
        connection = engine.connect()
        if engine.dialect.name == "postgresql":
            acquired = bool(connection.execute(text("SELECT pg_try_advisory_lock(:id)"), {"id": LOCK_ID}).scalar_one())
            connection.commit()
            if not acquired:
                return {"status": "SKIPPED_OVERLAP"}
        if connection.execute(text("SELECT 1 FROM scientific_review_runs WHERE run_id=:id"), {"id": key}).scalar():
            connection.rollback()
            return {"status": "ALREADY_COMPLETED"}
        connection.rollback()
        phase = "archive_source_inventory"
        selected, regulators, baseline = source_inventory(engine)
        LOG.warning("PDUFA_CANDIDATE_IDENTIFIERS %s", canonical({"nct_ids": [r[0] for r in selected], "regulatory_records": regulators, **baseline}))
        all_ids = sorted({r[0] for r in selected} | {r["associated_nct_id"] for r in regulators})
        phase = "fresh_registry_sources"
        live, proofs = {}, {}
        batches = [all_ids[i:i + 40] for i in range(0, len(all_ids), 40)]
        with ThreadPoolExecutor(max_workers=2) as pool:
            for ids, (studies, proof) in zip(batches, pool.map(live_registry, batches)):
                live.update(studies)
                proofs.update({nct: proof for nct in ids})
                LOG.warning("PDUFA_CANDIDATE_REGISTRY_BATCH requested=%d retrieved=%d status=%s", len(ids), len(studies), proof["status"])
        import gzip
        archived = {nct: (json.loads(gzip.decompress(packed)), sha) for nct, packed, sha in selected}
        phase = "fda_product_searches"
        with ThreadPoolExecutor(max_workers=3) as pool:
            fda_results = dict(zip(archived, pool.map(fda_lookup, [live.get(nct, archived[nct][0]) for nct in archived])))
        phase = "dossier_classification"
        dossiers = []
        for index, (nct, (study, sha)) in enumerate(archived.items(), 1):
            proof = proofs.get(nct, {})
            dossier = build_dossier(study, live.get(nct), archived_sha256=sha, verified_at=now(),
                                    source_status=proof.get("status", "UNAVAILABLE"),
                                    external_evidence={"registry_sourceproof": proof, "fda_lookup": fda_results[nct]})
            dossiers.append(dossier)
            if index % 25 == 0:
                LOG.warning("PDUFA_CANDIDATE_REVIEW_PROGRESS dossiers=%d target=228", index)
        phase = "regulatory_reconciliation"
        reconciled = reconcile_regulators(regulators, live, proofs, curated_evidence())
        verified_at = now()
        counts = {category: sum(d["readiness"] == category for d in dossiers) for category in ("READY", "RELUCTANT", "NOT READY")}
        checked = sum(bool(d.get("independently_checked")) for d in dossiers)
        summary = {"run_id": key, "status": "COMPLETE" if checked == EXPECTED else "REVIEW_REQUIRED",
                   "candidates_identified": EXPECTED, "candidates_independently_checked": checked,
                   "ready": counts["READY"], "reluctant": counts["RELUCTANT"], "not_ready": counts["NOT READY"],
                   "requiring_additional_external_evidence": sum(bool(d["additional_external_evidence_required"]) for d in dossiers),
                   "regulatory_identifiers_verified": sum(r["status"] == "VERIFIED" for r in reconciled),
                   "regulatory_identifiers_unresolved": sum(r["status"] == "UNRESOLVED" for r in reconciled),
                   "regulatory_identifiers_conflicting": sum(r["status"] == "CONFLICTING" for r in reconciled),
                   "scientific_dossiers_created": len(dossiers), "full_scientific_investigations_completed": 0,
                   "last_verified": verified_at, "source_manifest_sha256": baseline["manifest_sha256"],
                   "database": baseline["database"], "source_archive_count": baseline["archive_count"],
                   "fda_lookups_attempted": len(fda_results),
                   "fda_lookups_with_product_candidates": sum(bool(r.get("applications")) for r in fda_results.values()),
                   "fda_lookups_no_matches": sum(r.get("status") == "NO_MATCH" for r in fda_results.values()),
                   "fda_lookups_unavailable": sum(r.get("status") not in ("FETCHED", "NO_MATCH") for r in fda_results.values()),
                   "scope": "Independent registry checks and structured evidence-readiness screening; not completed scientific investigations or regulatory outcome predictions",
                   "trade_authorized": False}
        if len(dossiers) != EXPECTED or sum(counts.values()) != EXPECTED or len({d["nct_id"] for d in dossiers}) != EXPECTED:
            raise ValueError("Dossier count/identity reconciliation failed")
        phase = "persist_review_metadata"
        connection.execute(text("INSERT INTO scientific_review_runs(run_id,verified_at,summary) VALUES(:id,:time,:summary)"), {"id": key, "time": verified_at, "summary": canonical(summary)})
        for d in dossiers:
            connection.execute(text("INSERT INTO scientific_candidate_dossiers(run_id,nct_id,document,sha256) VALUES(:id,:nct,:doc,:sha)"), {"id": key, "nct": d["nct_id"], "doc": canonical(d), "sha": digest(d)})
        for r in reconciled:
            connection.execute(text("INSERT INTO regulatory_identifier_reconciliations(run_id,nct_id,identifier,document) VALUES(:id,:nct,:identifier,:doc)"), {"id": key, "nct": r["associated_nct_id"], "identifier": r["identifier"], "doc": canonical(r)})
        connection.commit()
        LOG.warning("PDUFA_REGULATORY_RECONCILIATION_RESULT %s", canonical(reconciled))
        LOG.warning("PDUFA_CANDIDATE_REVIEW_RESULT %s", canonical(summary))
        verify_http()
        return summary
    except Exception as exc:
        if connection is not None:
            connection.rollback()
        LOG.error("PDUFA_CANDIDATE_REVIEW_FAILED phase=%s error_type=%s sqlstate=%s", phase, type(exc).__name__, getattr(getattr(exc, "orig", None), "sqlstate", "none"))
        return {"status": "REVIEW_REQUIRED", "error_type": type(exc).__name__}
    finally:
        try:
            if connection is not None:
                try:
                    if acquired:
                        connection.execute(text("SELECT pg_advisory_unlock(:id)"), {"id": LOCK_ID})
                        connection.commit()
                finally:
                    connection.close()
        finally:
            _lock.release()


def list_reviews(engine):
    with engine.connect() as c:
        raw = c.execute(text("SELECT run_id,summary FROM scientific_review_runs ORDER BY verified_at DESC LIMIT 1")).first()
        if raw is None:
            return {"status": "PENDING", "candidates_identified": EXPECTED, "candidates_independently_checked": None,
                    **{k: None for k in ("ready", "reluctant", "not_ready", "regulatory_identifiers_verified", "regulatory_identifiers_unresolved", "full_scientific_investigations_completed", "scientific_dossiers_created", "last_verified")},
                    "candidates": [], "regulatory_identifiers": []}
        summary = json.loads(raw[1])
        candidates = []
        for doc, sha in c.execute(text("SELECT document,sha256 FROM scientific_candidate_dossiers WHERE run_id=:id ORDER BY nct_id"), {"id": raw[0]}):
            d = json.loads(doc)
            if digest(d) != sha:
                raise ValueError("Dossier checksum mismatch")
            candidates.append({"nct_id": d["nct_id"], "sponsor": d.get("sponsor", {}).get("name", ""), "products": [p.get("name", "") for p in d.get("products", [])],
                               "indications": d.get("indication", []), "readiness": d["readiness"],
                               "explanation": " ".join(d.get("reasons", [])), "last_verified": d.get("verified_at", summary["last_verified"])})
        regulators = [json.loads(r) for r in c.execute(text("SELECT document FROM regulatory_identifier_reconciliations WHERE run_id=:id ORDER BY nct_id,identifier"), {"id": raw[0]}).scalars()]
    if len(candidates) != summary["scientific_dossiers_created"]:
        raise ValueError("Persisted dossier counts do not reconcile")
    return {**summary, "candidates": candidates, "regulatory_identifiers": regulators}


def detail(engine, nct):
    with engine.connect() as c:
        row = c.execute(text("SELECT d.document,d.sha256 FROM scientific_candidate_dossiers d JOIN scientific_review_runs r ON r.run_id=d.run_id WHERE d.nct_id=:nct ORDER BY r.verified_at DESC LIMIT 1"), {"nct": nct}).first()
    if row is None:
        return None
    document = json.loads(row[0])
    if digest(document) != row[1]:
        raise ValueError("Dossier checksum mismatch")
    return document


def start(engine):
    global _thread
    if engine.dialect.name != "postgresql":
        return
    if _thread is not None and _thread.is_alive():
        return
    # Wait for existing archive initialization/audit; do not compete for its lock.
    def worker():
        import time
        from .archive_protection import dashboard
        for _ in range(40):
            try:
                if dashboard(engine)["status"] == "PASS":
                    execute_review(engine)
                    return
            except Exception:
                pass
            time.sleep(10)
        LOG.error("PDUFA_CANDIDATE_REVIEW_FAILED error_type=ArchiveBaselineNotReady")
    _thread = threading.Thread(target=worker, daemon=True, name="scientific-candidate-review")
    _thread.start()


def verify_http():
    try:
        headers = {"X-Pdufa-Internal-Key": os.environ["PDUFA_INTERNAL_API_KEY"]}
        with urlopen(Request("http://127.0.0.1:8000/api/scientific-candidates", headers=headers), timeout=20) as response:
            result = json.load(response)
        first = result["candidates"][0]["nct_id"]
        with urlopen(Request("http://127.0.0.1:8000/api/scientific-candidates/" + first, headers=headers), timeout=20) as response:
            dossier = json.load(response)
        ok = (result["candidates_identified"] == len(result["candidates"]) == EXPECTED
              and result["ready"] + result["reluctant"] + result["not_ready"] == EXPECTED
              and dossier["nct_id"] == first and result["full_scientific_investigations_completed"] == 0)
        LOG.warning("PDUFA_CANDIDATE_HTTP_SELFTEST status=%s http=200 dossiers=%d checked=%d", "PASS" if ok else "FAIL", len(result["candidates"]), result["candidates_independently_checked"])
    except Exception as exc:
        LOG.error("PDUFA_CANDIDATE_HTTP_SELFTEST status=FAIL error_type=%s", type(exc).__name__)
