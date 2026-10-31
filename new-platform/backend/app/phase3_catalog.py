"""Verified Phase 3 trial catalog, independent of scientific scoring/trading.

All schema changes are additive. Trial source revisions and existing prospective
predictions are append-only. Clinical endpoint results never imply an FDA result.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import date, datetime, timedelta, timezone
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import inspect, text

NCT = re.compile(r"NCT[0-9]{8}\Z")
DECISIONS = ("APPROVED", "CRL", "EXTENDED", "PENDING")
PREDICTED = ("PASS", "CRL", "EXTENSION", "ABSTAIN")
TERMINAL = {"COMPLETED", "TERMINATED", "WITHDRAWN"}
PERIOD_DEFINITION = "CURRENT: ongoing, unknown completion date, or completed within the last 24 months; PREVIOUS: terminal trial completed more than 24 months ago. FDA outcomes require separate verified evidence."
SORT_COLUMNS = {
    "company": "company", "ticker": "ticker", "drug": "drug", "indication": "indication",
    "trial_title": "trial_title", "nct_id": "nct_id", "phase3_status": "phase3_status",
    "last_verified": "last_verified", "completion_date": "completion_date",
    "decision": "actual_decision", "pdufa_date": "pdufa_date", "scientific_readiness": "scientific_readiness",
}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def stamp():
    return datetime.now(timezone.utc).isoformat()


def _time(value):
    if not isinstance(value, str):
        raise ValueError("An evidence timestamp is required")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Evidence timestamps must include a timezone")
    return parsed


def _date(value):
    if not value:
        return None
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}(?:-\d{2})?(?:-\d{2})?", value):
        raise ValueError("Invalid source date")
    # Unknown day/month must not make a trial look more recent: retain partial
    # precision in the source document, conservatively use last possible date.
    if len(value) == 4:
        return value + "-12-31"
    if len(value) == 7:
        year, month = map(int, value.split("-"))
        next_month = date(year + (month == 12), 1 if month == 12 else month + 1, 1)
        return (next_month - timedelta(days=1)).isoformat()
    date.fromisoformat(value)
    return value


def initialize(engine):
    statements = [
        """CREATE TABLE IF NOT EXISTS phase3_companies(company_id TEXT PRIMARY KEY,name TEXT NOT NULL,ticker TEXT,ticker_evidence_id TEXT)""",
        """CREATE TABLE IF NOT EXISTS phase3_drugs(drug_id TEXT PRIMARY KEY,name TEXT NOT NULL)""",
        """CREATE TABLE IF NOT EXISTS phase3_indications(indication_id TEXT PRIMARY KEY,name TEXT NOT NULL)""",
        """CREATE TABLE IF NOT EXISTS phase3_evidence(evidence_id TEXT PRIMARY KEY,url TEXT NOT NULL,retrieved_at TEXT NOT NULL,verification_status TEXT NOT NULL,sha256 VARCHAR(64) NOT NULL,publisher_kind TEXT NOT NULL,document TEXT NOT NULL)""",
        """CREATE TABLE IF NOT EXISTS phase3_dossier_versions(dossier_id TEXT PRIMARY KEY,nct_id VARCHAR(11) NOT NULL,document TEXT NOT NULL,sha256 VARCHAR(64) NOT NULL,created_at TEXT NOT NULL,source_evidence_id TEXT NOT NULL)""",
        """CREATE TABLE IF NOT EXISTS phase3_trials(nct_id VARCHAR(11) PRIMARY KEY,company_id TEXT NOT NULL,company TEXT NOT NULL,ticker TEXT,drug TEXT NOT NULL,indication TEXT NOT NULL,trial_title TEXT NOT NULL,phase3_status TEXT NOT NULL,completion_date TEXT,primary_endpoint_result TEXT NOT NULL,results_available INTEGER NOT NULL,fda_submission_status TEXT NOT NULL DEFAULT 'UNKNOWN',pdufa_date TEXT,actual_decision TEXT NOT NULL DEFAULT 'PENDING',decision_date TEXT,scientific_readiness TEXT NOT NULL DEFAULT 'NOT READY',readiness_reason TEXT NOT NULL,last_verified TEXT NOT NULL,source_url TEXT NOT NULL,latest_dossier_id TEXT NOT NULL,search_text TEXT NOT NULL)""",
        """CREATE TABLE IF NOT EXISTS phase3_trial_drugs(nct_id VARCHAR(11) NOT NULL,drug_id TEXT NOT NULL,PRIMARY KEY(nct_id,drug_id))""",
        """CREATE TABLE IF NOT EXISTS phase3_trial_indications(nct_id VARCHAR(11) NOT NULL,indication_id TEXT NOT NULL,PRIMARY KEY(nct_id,indication_id))""",
        """CREATE TABLE IF NOT EXISTS phase3_results(nct_id VARCHAR(11) PRIMARY KEY,primary_results TEXT NOT NULL,results_available INTEGER NOT NULL,evidence_id TEXT NOT NULL)""",
        """CREATE TABLE IF NOT EXISTS phase3_fda_applications(application_id TEXT PRIMARY KEY,application_number TEXT NOT NULL,sponsor TEXT NOT NULL,drug TEXT NOT NULL,indication TEXT NOT NULL,evidence_id TEXT NOT NULL)""",
        """CREATE TABLE IF NOT EXISTS phase3_trial_applications(nct_id VARCHAR(11) NOT NULL,application_id TEXT NOT NULL,evidence_id TEXT NOT NULL,verification_status TEXT NOT NULL,PRIMARY KEY(nct_id,application_id,evidence_id))""",
        """CREATE TABLE IF NOT EXISTS phase3_fda_decisions(decision_id TEXT PRIMARY KEY,application_id TEXT NOT NULL,decision TEXT NOT NULL,decision_date TEXT,evidence_id TEXT NOT NULL,verification_status TEXT NOT NULL,pdufa_date TEXT,submission_status TEXT NOT NULL,published_at TEXT NOT NULL)""",
        """CREATE TABLE IF NOT EXISTS phase3_predictions(prediction_id TEXT PRIMARY KEY,nct_id VARCHAR(11) NOT NULL,application_id TEXT NOT NULL,decision TEXT NOT NULL,created_at TEXT NOT NULL,evidence_cutoff TEXT NOT NULL,evidence_ids TEXT NOT NULL,confidence REAL,uncertainty TEXT NOT NULL,scientific_readiness TEXT NOT NULL,document TEXT NOT NULL)""",
        "CREATE INDEX IF NOT EXISTS phase3_trial_status_idx ON phase3_trials(phase3_status,completion_date)",
        "CREATE INDEX IF NOT EXISTS phase3_trial_decision_idx ON phase3_trials(actual_decision)",
        "CREATE INDEX IF NOT EXISTS phase3_trial_company_idx ON phase3_trials(company)",
        "CREATE INDEX IF NOT EXISTS phase3_dossier_nct_idx ON phase3_dossier_versions(nct_id)",
        "CREATE INDEX IF NOT EXISTS phase3_application_trial_idx ON phase3_trial_applications(nct_id,application_id)",
    ]
    with engine.begin() as c:
        for sql in statements:
            c.execute(text(sql))
        immutable = ("phase3_evidence", "phase3_dossier_versions", "phase3_predictions", "phase3_fda_decisions", "phase3_trial_applications")
        if engine.dialect.name == "postgresql":
            c.execute(text("""CREATE OR REPLACE FUNCTION phase3_reject_mutation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Phase3 evidence, relationships, dossier revisions and predictions are append-only'; END; $$"""))
            for table in immutable:
                if not c.execute(text("SELECT 1 FROM pg_trigger WHERE tgname=:name AND tgrelid=CAST(:table AS regclass)"), {"name": table + "_immutable", "table": table}).scalar():
                    c.execute(text(f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON {table} FOR EACH STATEMENT EXECUTE FUNCTION phase3_reject_mutation()"))
        else:
            for table in immutable:
                for operation in ("UPDATE", "DELETE"):
                    c.execute(text(f"CREATE TRIGGER IF NOT EXISTS {table}_{operation.lower()} BEFORE {operation} ON {table} BEGIN SELECT RAISE(ABORT, 'Phase3 evidence is append-only'); END"))


def _source(record, nct, document):
    source = record.get("source") or {}
    url = source.get("url") or record.get("source_url")
    sha = source.get("sha256") or record.get("sha256")
    when = source.get("retrieved_at") or source.get("verified_at") or record.get("verified_at")
    if url != "https://clinicaltrials.gov/api/v2/studies/" + nct or not re.fullmatch(r"[a-f0-9]{64}", str(sha or "")):
        raise ValueError("Exact authoritative trial source URL/checksum required")
    if digest(document) != sha:
        raise ValueError("Authoritative trial document checksum mismatch")
    _time(when)
    if source.get("verification_status", "VERIFIED") != "VERIFIED":
        raise ValueError("Unverified trial source")
    return {"id": "ctgov:" + sha, "url": url, "sha256": sha, "retrieved_at": when,
            "verification_status": "VERIFIED", "publisher_kind": "CLINICALTRIALS_GOV", "document": canonical(document)}


def _insert_evidence(c, source):
    c.execute(text("""INSERT INTO phase3_evidence(evidence_id,url,retrieved_at,verification_status,sha256,publisher_kind,document)
        VALUES(:id,:url,:retrieved_at,:verification_status,:sha256,:publisher_kind,:document) ON CONFLICT(evidence_id) DO NOTHING"""), source)


def _strings(values):
    return [v.strip() for v in values if isinstance(v, str) and v.strip()]


def _primary_summary(outcomes):
    if not outcomes:
        return "Results posted; no primary outcome result identified in the posted results."
    summaries = []
    for outcome in outcomes:
        observations = []
        for cls in outcome.get("classes", []):
            for category in cls.get("categories", []):
                for measurement in category.get("measurements", []):
                    if measurement.get("value") is not None:
                        observations.append(str(measurement["value"]))
        title = outcome.get("title") or "Primary endpoint"
        values = ", ".join(observations[:8])
        summaries.append(title + (": " + values if values else ": posted values require review") + (" " + outcome["unitOfMeasure"] if outcome.get("unitOfMeasure") else ""))
    return "; ".join(summaries)[:1600] + " (reported results; endpoint success not adjudicated)"


def upsert_trial(engine, record):
    """Persist a verified CT.gov source revision; never infer regulatory outcomes.

    Call initialize once before ingestion. Identity, sponsors, phase and results
    come from the source JSON, not caller-supplied display strings.
    """
    nct = record.get("nct_id")
    if not isinstance(nct, str) or not NCT.fullmatch(nct):
        raise ValueError("Invalid NCT identifier")
    document = record.get("document")
    if not isinstance(document, dict):
        raise ValueError("Authoritative study JSON required")
    protocol = document.get("protocolSection") or {}
    identity = protocol.get("identificationModule") or {}
    phases = (protocol.get("designModule") or {}).get("phases") or []
    results = document.get("resultsSection")
    if identity.get("nctId") != nct or "PHASE3" not in phases or not isinstance(results, dict) or not results:
        raise ValueError("Only matching Phase 3 trials with posted results are eligible")
    source = _source(record, nct, document)
    sponsor = ((protocol.get("sponsorCollaboratorsModule") or {}).get("leadSponsor") or {}).get("name")
    if not isinstance(sponsor, str) or not sponsor.strip():
        raise ValueError("Verified sponsor identity is missing")
    sponsor = sponsor.strip()
    company_id = digest({"name": sponsor.casefold()})
    products = [v["name"].strip() for v in (protocol.get("armsInterventionsModule") or {}).get("interventions", [])
                if isinstance(v, dict) and v.get("type") in ("DRUG", "BIOLOGICAL") and isinstance(v.get("name"), str) and v["name"].strip()]
    indications = _strings((protocol.get("conditionsModule") or {}).get("conditions") or [])
    status_doc = protocol.get("statusModule") or {}
    overall_status = status_doc.get("overallStatus") or "UNKNOWN"
    completion = _date((status_doc.get("completionDateStruct") or {}).get("date"))
    outcomes = [v for v in (results.get("outcomeMeasuresModule") or {}).get("outcomeMeasures", []) if isinstance(v, dict) and v.get("type") == "PRIMARY"]
    title = identity.get("briefTitle") or identity.get("officialTitle") or nct
    # A source dossier is evidence collection, not a completed scientific dossier.
    dossier_doc = {"nct_id": nct, "sponsor": {"name": sponsor}, "products": [{"name": v} for v in products],
        "indication": indications, "phase": phases, "trial_title": title, "status": status_doc,
        "primary_endpoints": (protocol.get("outcomesModule") or {}).get("primaryOutcomes") or [],
        "primary_endpoint_results": outcomes, "source": {k: source[k] for k in ("url", "sha256", "retrieved_at", "verification_status")},
        "scientific_readiness": "NOT READY", "scientific_assessments_completed": 0,
        "uncertainty": "CT.gov identity/results are verified; regulatory evidence and the existing scientific assessments remain pending."}
    dossier_id = "phase3-catalog:" + source["sha256"] + "/" + nct
    values = {"nct": nct, "company_id": company_id, "company": sponsor, "drug": "; ".join(products) or "Not reported",
        "indication": "; ".join(indications) or "Not reported", "title": title, "status": overall_status,
        "completion": completion, "result": _primary_summary(outcomes), "reason": dossier_doc["uncertainty"],
        "verified": source["retrieved_at"], "url": source["url"], "dossier": dossier_id,
        "search": " ".join([nct, sponsor, title, *products, *indications]).lower()}
    with engine.begin() as c:
        _insert_evidence(c, source)
        c.execute(text("INSERT INTO phase3_companies(company_id,name) VALUES(:id,:name) ON CONFLICT(company_id) DO NOTHING"), {"id": company_id, "name": sponsor})
        c.execute(text("""INSERT INTO phase3_dossier_versions(dossier_id,nct_id,document,sha256,created_at,source_evidence_id)
            VALUES(:id,:nct,:document,:sha,:time,:source) ON CONFLICT(dossier_id) DO NOTHING"""),
            {"id": dossier_id, "nct": nct, "document": canonical(dossier_doc), "sha": digest(dossier_doc), "time": source["retrieved_at"], "source": source["id"]})
        saved_sha = c.execute(text("SELECT sha256 FROM phase3_dossier_versions WHERE dossier_id=:id"), {"id": dossier_id}).scalar_one()
        c.execute(text("""INSERT INTO phase3_trials(nct_id,company_id,company,drug,indication,trial_title,phase3_status,completion_date,primary_endpoint_result,results_available,readiness_reason,last_verified,source_url,latest_dossier_id,search_text)
            VALUES(:nct,:company_id,:company,:drug,:indication,:title,:status,:completion,:result,1,:reason,:verified,:url,:dossier,:search)
            ON CONFLICT(nct_id) DO UPDATE SET company_id=excluded.company_id,company=excluded.company,drug=excluded.drug,
            indication=excluded.indication,trial_title=excluded.trial_title,phase3_status=excluded.phase3_status,
            completion_date=excluded.completion_date,primary_endpoint_result=excluded.primary_endpoint_result,
            results_available=1,last_verified=excluded.last_verified,source_url=excluded.source_url,
            latest_dossier_id=excluded.latest_dossier_id,search_text=excluded.search_text"""), values)
        for product in products:
            product_id = digest({"drug": product.casefold()})
            c.execute(text("INSERT INTO phase3_drugs(drug_id,name) VALUES(:id,:name) ON CONFLICT(drug_id) DO NOTHING"), {"id": product_id, "name": product})
            c.execute(text("INSERT INTO phase3_trial_drugs(nct_id,drug_id) VALUES(:nct,:id) ON CONFLICT(nct_id,drug_id) DO NOTHING"), {"nct": nct, "id": product_id})
        for indication in indications:
            indication_id = digest({"indication": indication.casefold()})
            c.execute(text("INSERT INTO phase3_indications(indication_id,name) VALUES(:id,:name) ON CONFLICT(indication_id) DO NOTHING"), {"id": indication_id, "name": indication})
            c.execute(text("INSERT INTO phase3_trial_indications(nct_id,indication_id) VALUES(:nct,:id) ON CONFLICT(nct_id,indication_id) DO NOTHING"), {"nct": nct, "id": indication_id})
        c.execute(text("""INSERT INTO phase3_results(nct_id,primary_results,results_available,evidence_id) VALUES(:nct,:results,1,:source)
            ON CONFLICT(nct_id) DO UPDATE SET primary_results=excluded.primary_results,evidence_id=excluded.evidence_id"""),
            {"nct": nct, "results": canonical(outcomes), "source": source["id"]})
    return {"nct_id": nct, "dossier_id": dossier_id, "sha256": saved_sha, "verified_at": source["retrieved_at"]}


def saved_catalog_dossier(c, nct, dossier_id=None):
    if not NCT.fullmatch(nct):
        raise ValueError("Invalid NCT identifier")
    if not inspect(c).has_table("phase3_dossier_versions") or not inspect(c).has_table("phase3_trials"):
        raise LookupError("No verified catalog has been initialized")
    if dossier_id is None:
        row = c.execute(text("""SELECT v.dossier_id,v.document,v.sha256 FROM phase3_dossier_versions v
            JOIN phase3_trials t ON t.latest_dossier_id=v.dossier_id WHERE t.nct_id=:nct"""), {"nct": nct}).first()
    else:
        row = c.execute(text("SELECT dossier_id,document,sha256 FROM phase3_dossier_versions WHERE dossier_id=:id AND nct_id=:nct"), {"id": dossier_id, "nct": nct}).first()
    if row is None:
        raise LookupError("No verified saved catalog dossier")
    doc = json.loads(row[1])
    if doc.get("nct_id") != nct or digest(doc) != row[2]:
        raise ValueError("Catalog dossier identity/checksum mismatch")
    return {"id": row[0], "document": doc, "sha256": row[2]}


def _cutoff(as_of=None):
    current = as_of or date.today()
    try:
        return current.replace(year=current.year - 2).isoformat()
    except ValueError:
        return current.replace(year=current.year - 2, day=28).isoformat()


def _period_sql(period):
    previous = "(phase3_status IN ('COMPLETED','TERMINATED','WITHDRAWN') AND completion_date IS NOT NULL AND completion_date < :cutoff)"
    if period == "PREVIOUS":
        return previous
    if period == "CURRENT":
        return "NOT " + previous
    raise ValueError("Invalid search period")


def _latest_run(c, nct, has_streams):
    if not has_streams:
        return None
    return c.execute(text("SELECT run_id FROM nct_stream_runs WHERE nct_id=:nct ORDER BY created_at DESC,run_id DESC LIMIT 1"), {"nct": nct}).scalar()


def _public_evidence(row):
    return {"id": row["evidence_id"], "url": row["url"], "retrieved_at": row["retrieved_at"],
            "verification_status": row["verification_status"], "sha256": row["sha256"]}


def catalog(engine, period="CURRENT", q="", decision="ALL", sort="last_verified", direction="desc", page=1, page_size=50, *, as_of=None):
    if decision not in (*DECISIONS, "ALL") or sort not in SORT_COLUMNS or direction not in ("asc", "desc"):
        raise ValueError("Invalid catalog filter or sort")
    if not isinstance(page, int) or page < 1 or not isinstance(page_size, int) or not 1 <= page_size <= 100 or len(q) > 200:
        raise ValueError("Invalid pagination or search")
    base = _period_sql(period)
    params = {"cutoff": _cutoff(as_of), "limit": page_size, "offset": (page - 1) * page_size}
    if q.strip():
        # Escape SQL LIKE wildcards; every input remains a bound parameter.
        params["query"] = "%" + q.strip().lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        base += " AND (search_text LIKE :query ESCAPE '\\' OR LOWER(COALESCE(ticker,'')) LIKE :query ESCAPE '\\')"
    has_streams = inspect(engine).has_table("nct_stream_runs")
    with engine.connect() as c:
        counts = {value: 0 for value in DECISIONS}
        for value, total in c.execute(text("SELECT actual_decision,COUNT(*) FROM phase3_trials WHERE " + base + " GROUP BY actual_decision"), params):
            counts[value if value in counts else "PENDING"] += total
        where = base
        if decision != "ALL":
            where += " AND actual_decision=:decision"
            params["decision"] = decision
        total = c.execute(text("SELECT COUNT(*) FROM phase3_trials WHERE " + where), params).scalar_one()
        rows = c.execute(text("SELECT * FROM phase3_trials WHERE " + where + " ORDER BY " + SORT_COLUMNS[sort] + " " + direction.upper() + ",nct_id ASC LIMIT :limit OFFSET :offset"), params).mappings().all()
        last_updated = c.execute(text("SELECT MAX(last_verified) FROM phase3_trials")).scalar()
        trials = []
        for raw in rows:
            row = dict(raw)
            evidence = c.execute(text("""SELECT e.* FROM phase3_evidence e JOIN phase3_dossier_versions v ON v.source_evidence_id=e.evidence_id
                WHERE v.dossier_id=:id"""), {"id": row.pop("latest_dossier_id")}).mappings().all()
            row.pop("search_text", None)
            row.pop("company_id", None)
            row["period"] = period
            row["decision"] = row["actual_decision"]
            row["results_available"] = bool(row["results_available"])
            row["last_verified_date"] = row["last_verified"]
            row["scientific_readiness_reason"] = row.pop("readiness_reason")
            row["evidence"] = [_public_evidence(e) for e in evidence]
            regulatory = c.execute(text("""SELECT DISTINCT e.* FROM phase3_evidence e WHERE e.evidence_id IN (
                SELECT l.evidence_id FROM phase3_trial_applications l WHERE l.nct_id=:nct
                UNION SELECT a.evidence_id FROM phase3_fda_applications a JOIN phase3_trial_applications l ON l.application_id=a.application_id WHERE l.nct_id=:nct
                UNION SELECT d.evidence_id FROM phase3_fda_decisions d JOIN phase3_trial_applications l ON l.application_id=d.application_id WHERE l.nct_id=:nct)"""), {"nct": row["nct_id"]}).mappings().all()
            existing_ids = {e["id"] for e in row["evidence"]}
            row["evidence"].extend(_public_evidence(e) for e in regulatory if e["evidence_id"] not in existing_ids)
            row["regulatory_application_ids"] = list(c.execute(text("SELECT DISTINCT application_id FROM phase3_trial_applications WHERE nct_id=:nct AND verification_status='VERIFIED'"), {"nct": row["nct_id"]}).scalars())
            row["latest_run_id"] = _latest_run(c, row["nct_id"], has_streams)
            row["predictions"] = _prediction_rows(c, row["nct_id"], row["actual_decision"], row["decision_date"])
            trials.append(row)
    ingestion = {}
    try:
        from . import phase3_ingestion
        ingestion = phase3_ingestion.status(engine) if inspect(engine).has_table("phase3_ingestion_state") else {"state": "NOT_STARTED", "source_health": {}}
    except (ImportError, ModuleNotFoundError):
        ingestion = {"state": "NOT_STARTED", "source_health": {}}
    source_health = dict(ingestion.get("source_health", {}))
    try:
        from . import phase3_regulatory
        regulatory_status = phase3_regulatory.status(engine) if inspect(engine).has_table("phase3_regulatory_sources") else {"status": "NOT_STARTED"}
    except (ImportError, ModuleNotFoundError):
        regulatory_status = {"status": "NOT_STARTED"}
    source_health["fda"] = regulatory_status
    if "sec" in regulatory_status:
        source_health["sec"] = regulatory_status["sec"]
    if "official_sponsor" in regulatory_status:
        source_health["official_sponsor"] = regulatory_status["official_sponsor"]
    return {"period": period, "trials": trials, "total": total, "page": page, "page_size": page_size,
            "pages": math.ceil(total / page_size), "counts": counts, "source_status": "VERIFIED" if last_updated else "NOT_POPULATED",
            "last_updated": last_updated, "ingestion": ingestion, "source_health": source_health,
            "period_definition": PERIOD_DEFINITION, "historical_cutoff": params["cutoff"]}


def record_regulatory_evidence(engine, *, application, decision, nct_ids, source, published_at, decision_date=None, pdufa_date=None, submission_status="UNKNOWN", application_source=None):
    """Accept explicit, independently reconciled application/NCT evidence only.

    This is not an automatic sponsor/drug-name match. Ambiguous candidates belong
    in an external reconciliation queue; a clinical result can never call this.
    """
    if decision not in DECISIONS or source.get("verification_status") != "VERIFIED":
        raise ValueError("Verified regulatory evidence is required")
    if not nct_ids or any(not NCT.fullmatch(v) for v in nct_ids):
        raise ValueError("Exact trial/application mapping required")
    url = source.get("url", "")
    host = urlsplit(url).hostname or ""
    publisher = source.get("publisher_kind")
    if not url.startswith("https://") or publisher not in ("FDA", "SEC", "OFFICIAL_SPONSOR"):
        raise ValueError("Unacceptable regulatory source")
    if publisher == "FDA" and not (host == "fda.gov" or host.endswith(".fda.gov")):
        raise ValueError("FDA source hostname mismatch")
    if publisher == "SEC" and not (host == "sec.gov" or host.endswith(".sec.gov")):
        raise ValueError("SEC source hostname mismatch")
    if publisher == "OFFICIAL_SPONSOR" and source.get("official_sponsor_domain") != host:
        raise ValueError("Official sponsor identity must be verified")
    required = ("application_id", "application_number", "sponsor", "drug", "indication")
    if any(not isinstance(application.get(k), str) or not application[k].strip() for k in required):
        raise ValueError("Complete application scope required")
    body = source.get("document")
    explicit_ids = set(re.findall(r"(?<![A-Za-z0-9])NCT[0-9]{8}(?![A-Za-z0-9])", body)) if isinstance(body, str) else set()
    if not isinstance(body, str) or not set(nct_ids).issubset(explicit_ids) or any(v.lower() not in body.lower() for v in [application["drug"], application["indication"]]):
        raise ValueError("Source does not explicitly establish the scoped NCT/application mapping")
    application_evidence = None
    if application_source is not None:
        app_body = application_source.get("document")
        app_host = urlsplit(application_source.get("url", "")).hostname or ""
        if not (app_host == "fda.gov" or app_host.endswith(".fda.gov")) or not application_source.get("url", "").startswith("https://") or application_source.get("verification_status") != "VERIFIED":
            raise ValueError("Application identity requires official verified FDA evidence")
        if not isinstance(app_body, str) or any(v.lower() not in app_body.lower() for v in [application["application_number"], application["drug"], application["sponsor"]]):
            raise ValueError("FDA application evidence does not establish sponsor/product/number")
        app_sha = hashlib.sha256(app_body.encode()).hexdigest()
        if app_sha != application_source.get("sha256"):
            raise ValueError("FDA application evidence checksum mismatch")
        _time(application_source.get("retrieved_at"))
        application_evidence = {"id": "application:" + app_sha, "url": application_source["url"], "sha256": app_sha,
            "retrieved_at": application_source["retrieved_at"], "verification_status": "VERIFIED", "publisher_kind": "FDA", "document": app_body}
    elif application["application_number"].lower() not in body.lower():
        raise ValueError("Application number needs independent FDA source support")
    if not re.fullmatch(r"[a-f0-9]{64}", str(source.get("sha256", ""))) or hashlib.sha256(body.encode()).hexdigest() != source["sha256"]:
        raise ValueError("Regulatory evidence checksum mismatch")
    _time(source.get("retrieved_at")); _time(published_at)
    if decision != "PENDING" and not decision_date:
        raise ValueError("A regulatory decision event date is required")
    if decision == "EXTENDED" and (not pdufa_date or not source.get("previous_pdufa_date") or _date(pdufa_date) <= _date(source["previous_pdufa_date"])):
        raise ValueError("An extension needs an evidenced changed future review timeline")
    # Explicit words are supplementary validation, not a substitute for source review.
    terms = {"APPROVED": ("approved", "approval"), "CRL": ("complete response letter",), "EXTENDED": ("extended", "extension"), "PENDING": ("submitted", "accepted", "pending")}
    if not any(term in body.lower() for term in terms[decision]):
        raise ValueError("Source does not establish the claimed regulatory event")
    eid = "regulatory:" + source["sha256"]
    decision_id = digest({"application": application["application_id"], "decision": decision, "date": decision_date, "evidence": eid})
    with engine.begin() as c:
        prior = c.execute(text("SELECT application_number,sponsor,drug,indication FROM phase3_fda_applications WHERE application_id=:app"), {"app": application["application_id"]}).mappings().first()
        if prior and any(prior[k].strip().casefold() != application[k].strip().casefold() for k in ("application_number", "sponsor", "drug", "indication")):
            raise ValueError("Application scope conflicts with an existing regulatory identity")
        count = c.execute(text("SELECT COUNT(*) FROM phase3_trials WHERE nct_id IN (" + ",".join(":n" + str(i) for i in range(len(nct_ids))) + ")"), {"n" + str(i): v for i, v in enumerate(nct_ids)}).scalar_one()
        if count != len(set(nct_ids)):
            raise ValueError("Unknown trial in regulatory relationship")
        _insert_evidence(c, {"id": eid, "url": url, "sha256": source["sha256"], "retrieved_at": source["retrieved_at"], "verification_status": "VERIFIED", "publisher_kind": publisher, "document": body})
        if application_evidence:
            _insert_evidence(c, application_evidence)
        c.execute(text("""INSERT INTO phase3_fda_applications(application_id,application_number,sponsor,drug,indication,evidence_id)
            VALUES(:application_id,:application_number,:sponsor,:drug,:indication,:evidence) ON CONFLICT(application_id) DO NOTHING"""), {**application, "evidence": application_evidence["id"] if application_evidence else eid})
        c.execute(text("""INSERT INTO phase3_fda_decisions(decision_id,application_id,decision,decision_date,evidence_id,verification_status,pdufa_date,submission_status,published_at)
            VALUES(:id,:app,:decision,:date,:evidence,'VERIFIED',:pdufa,:submission,:published) ON CONFLICT(decision_id) DO NOTHING"""),
            {"id": decision_id, "app": application["application_id"], "decision": decision, "date": _date(decision_date), "evidence": eid, "pdufa": _date(pdufa_date), "submission": submission_status, "published": published_at})
        for nct in set(nct_ids):
            c.execute(text("""INSERT INTO phase3_trial_applications(nct_id,application_id,evidence_id,verification_status) VALUES(:nct,:app,:evidence,'VERIFIED')
                ON CONFLICT(nct_id,application_id,evidence_id) DO NOTHING"""), {"nct": nct, "app": application["application_id"], "evidence": eid})
            _reconcile(c, nct)
    return {"decision_id": decision_id, "evidence_id": eid}


def _reconcile(c, nct):
    rows = c.execute(text("""SELECT DISTINCT d.* FROM phase3_fda_decisions d JOIN phase3_trial_applications l ON l.application_id=d.application_id
        WHERE l.nct_id=:nct AND l.verification_status='VERIFIED' AND d.verification_status='VERIFIED' ORDER BY d.decision_date DESC,d.published_at DESC"""), {"nct": nct}).mappings().all()
    if not rows:
        return
    latest = rows[0]
    latest_date = latest["decision_date"]
    # Preserve each application's latest history. An NCT can support several
    # applications; their different outcomes cannot collapse into one approval.
    current_by_app = {}
    conflicting = False
    for row in rows:
        prior = current_by_app.get(row["application_id"])
        if prior is None:
            current_by_app[row["application_id"]] = row
        elif prior["decision_date"] == row["decision_date"] and prior["decision"] != row["decision"]:
            conflicting = True
    conflicting = conflicting or len({r["decision"] for r in current_by_app.values()}) > 1
    selected = "PENDING" if conflicting else latest["decision"]
    c.execute(text("UPDATE phase3_trials SET actual_decision=:decision,decision_date=:date,pdufa_date=:pdufa,fda_submission_status=:submission WHERE nct_id=:nct"),
              {"decision": selected, "date": None if conflicting else latest_date, "pdufa": None if conflicting else latest["pdufa_date"], "submission": "CONFLICTING" if conflicting else latest["submission_status"], "nct": nct})


def record_prediction(engine, prediction):
    """Persist an existing assessment output. This function computes no prediction."""
    for key in ("prediction_id", "nct_id", "application_id", "decision", "created_at", "evidence_cutoff", "evidence_ids"):
        if key not in prediction:
            raise ValueError("Incomplete timestamped prediction")
    if prediction["decision"] not in PREDICTED or not NCT.fullmatch(prediction["nct_id"]):
        raise ValueError("Invalid prediction")
    created, cutoff = _time(prediction["created_at"]), _time(prediction["evidence_cutoff"])
    if cutoff > created:
        raise ValueError("Evidence cutoff cannot follow prediction creation")
    confidence = prediction.get("confidence")
    if confidence is not None and (not prediction.get("calibrated") or isinstance(confidence, bool) or not isinstance(confidence, (float, int)) or not 0 <= confidence <= 1):
        raise ValueError("Only calibrated probabilities may be displayed")
    ids = prediction["evidence_ids"]
    if not isinstance(ids, list) or not ids:
        raise ValueError("Prediction evidence provenance is required")
    with engine.begin() as c:
        links = c.execute(text("""SELECT e.retrieved_at AS relation_at,ae.retrieved_at AS application_at FROM phase3_trial_applications l
            JOIN phase3_fda_applications a ON a.application_id=l.application_id
            JOIN phase3_evidence e ON e.evidence_id=l.evidence_id JOIN phase3_evidence ae ON ae.evidence_id=a.evidence_id
            WHERE l.nct_id=:nct AND l.application_id=:app AND l.verification_status='VERIFIED'
            AND e.verification_status='VERIFIED' AND ae.verification_status='VERIFIED'"""), {"nct": prediction["nct_id"], "app": prediction["application_id"]}).all()
        if not any(_time(link[0]) <= cutoff and _time(link[1]) <= cutoff for link in links):
            raise ValueError("Prediction requires a verified scoped trial/application relationship")
        for eid in ids:
            row = c.execute(text("SELECT retrieved_at FROM phase3_evidence WHERE evidence_id=:id AND verification_status='VERIFIED'"), {"id": eid}).first()
            if row is None or _time(row[0]) > cutoff:
                raise ValueError("Prediction cites missing or later evidence")
        c.execute(text("""INSERT INTO phase3_predictions(prediction_id,nct_id,application_id,decision,created_at,evidence_cutoff,evidence_ids,confidence,uncertainty,scientific_readiness,document)
            VALUES(:id,:nct,:app,:decision,:created,:cutoff,:evidence,:confidence,:uncertainty,:readiness,:document)"""),
            {"id": prediction["prediction_id"], "nct": prediction["nct_id"], "app": prediction["application_id"], "decision": prediction["decision"], "created": prediction["created_at"], "cutoff": prediction["evidence_cutoff"], "evidence": canonical(ids), "confidence": confidence, "uncertainty": prediction.get("uncertainty", "Not calibrated"), "readiness": prediction.get("scientific_readiness", "NOT READY"), "document": canonical(prediction)})


def _application_outcome(c, application_id):
    rows = c.execute(text("SELECT decision,decision_date FROM phase3_fda_decisions WHERE application_id=:app AND verification_status='VERIFIED' ORDER BY decision_date DESC,published_at DESC"), {"app": application_id}).all()
    if not rows:
        return "PENDING", None
    newest_date = rows[0][1]
    newest = {row[0] for row in rows if row[1] == newest_date}
    if len(newest) != 1:
        return "PENDING", None
    return rows[0]


def _prediction_rows(c, nct, actual=None, actual_date=None):
    rows = c.execute(text("SELECT * FROM phase3_predictions WHERE nct_id=:nct ORDER BY created_at DESC"), {"nct": nct}).mappings()
    expected = {"APPROVED": "PASS", "CRL": "CRL", "EXTENDED": "EXTENSION"}
    result = []
    for row in rows:
        # Never evaluate against an aggregated NCT outcome: the NCT may support
        # several scoped applications with different actual decisions.
        actual, actual_date = _application_outcome(c, row["application_id"])
        linked_rows = c.execute(text("""SELECT e.retrieved_at,ae.retrieved_at FROM phase3_trial_applications l
            JOIN phase3_fda_applications a ON a.application_id=l.application_id
            JOIN phase3_evidence e ON e.evidence_id=l.evidence_id JOIN phase3_evidence ae ON ae.evidence_id=a.evidence_id
            WHERE l.nct_id=:nct AND l.application_id=:app AND l.verification_status='VERIFIED'
            AND e.verification_status='VERIFIED' AND ae.verification_status='VERIFIED'"""), {"nct": nct, "app": row["application_id"]}).all()
        linked = any(_time(v[0]) <= _time(row["evidence_cutoff"]) and _time(v[1]) <= _time(row["evidence_cutoff"]) for v in linked_rows)
        timely = bool(linked and actual in expected and actual_date and row["created_at"][:10] < actual_date and _time(row["evidence_cutoff"]) <= _time(row["created_at"]))
        evidence = []
        for eid in json.loads(row["evidence_ids"]):
            source = c.execute(text("SELECT * FROM phase3_evidence WHERE evidence_id=:id AND verification_status='VERIFIED'"), {"id": eid}).mappings().first()
            if source is None or _time(source["retrieved_at"]) > _time(row["evidence_cutoff"]):
                timely = False
            elif source:
                evidence.append(_public_evidence(source))
        correctness = row["decision"] == expected[actual] if timely and row["decision"] != "ABSTAIN" else None
        result.append({"prediction_id": row["prediction_id"], "application_id": row["application_id"], "decision": row["decision"], "created_at": row["created_at"], "evidence_cutoff": row["evidence_cutoff"], "actual_decision": actual, "actual_decision_date": actual_date, "scientific_readiness": row["scientific_readiness"], "confidence": row["confidence"], "uncertainty": row["uncertainty"], "evidence": evidence, "correctness": correctness, "prospective_eligible": timely})
    return result


def historical_validation(engine):
    with engine.connect() as c:
        applications = c.execute(text("SELECT COUNT(*) FROM phase3_fda_applications")).scalar_one()
        apps = c.execute(text("SELECT application_id FROM phase3_fda_applications")).scalars().all()
        known = sum(_application_outcome(c, app)[0] in ("APPROVED", "CRL", "EXTENDED") for app in apps)
        ncts = c.execute(text("SELECT DISTINCT nct_id FROM phase3_predictions")).scalars().all()
        predictions = [p for nct in ncts for p in _prediction_rows(c, nct)]
    eligible = [p for p in predictions if p["prospective_eligible"]]
    # A fixed protocol selects the earliest eligible prospective prediction per
    # application, avoiding multiple counting and retrospective cherry-picking.
    first_by_app = {}
    for prediction in sorted(eligible, key=lambda p: (p["created_at"], p["prediction_id"])):
        first_by_app.setdefault(prediction["application_id"], prediction)
    selected = list(first_by_app.values())
    evaluated = [p for p in selected if p["correctness"] is not None]
    categories = {}
    for decision in ("PASS", "CRL", "EXTENSION"):
        subset = [p for p in evaluated if p["decision"] == decision]
        categories[decision] = {"evaluated": len(subset), "correct": sum(p["correctness"] for p in subset), "accuracy": sum(p["correctness"] for p in subset) / len(subset) if len(subset) >= 10 and len(evaluated) >= 30 else None}
    return {"status": "NOT_VALIDATED" if not evaluated else "REVIEW_REQUIRED", "total_applications": applications, "eligible_applications": len(first_by_app),
            "number_evaluated": len(evaluated), "number_abstained": sum(p["decision"] == "ABSTAIN" for p in selected),
            "number_with_known_outcomes": known, "prediction_records": len(predictions), "temporally_eligible_predictions": len(eligible),
            "excluded_for_lookahead_or_missing_outcome": len(predictions) - len(eligible), "accuracy_by_decision": categories,
            "calibration_metrics": None, "data_completeness": {"applications": applications, "verified_outcomes": known},
            "unresolved_outcomes": max(0, applications - known), "verified_at": stamp(),
            "limitation": "No accuracy claim is validated. Predictions are immutable existing assessment outputs; ingestion generates none. Evaluation excludes evidence or predictions after the outcome."}


def install_routes(app, engine_provider, require_internal_key, require_storage):
    router = APIRouter(prefix="/api/phase3-trials", dependencies=[Depends(require_internal_key), Depends(require_storage)])

    @router.get("")
    def list_trials(period: str = "CURRENT", q: str = Query(default="", max_length=200), search: str | None = Query(default=None, max_length=200), decision: str = "ALL", sort: str = "last_verified", dir: str = "desc", page: int = Query(default=1, ge=1), page_size: int = Query(default=50, ge=1, le=100)):
        try:
            return catalog(engine_provider(), period, q if search is None else search, decision, sort, dir, page, page_size)
        except ValueError as exc:
            raise HTTPException(422, "Invalid catalog period, search, filter or pagination") from exc

    @router.get("/{nct_id}/predictions")
    def trial_predictions(nct_id: str):
        """Read-only, application-scoped saved predictions; never infer a decision."""
        if not NCT.fullmatch(nct_id):
            raise HTTPException(422, "Invalid NCT identifier")
        with engine_provider().connect() as connection:
            records = _prediction_rows(connection, nct_id)
        return {
            "nct_id": nct_id,
            "predictions": records,
            "latest_prediction": records[0] if records else None,
            "status": "RECORDED" if records else "NOT_READY",
            "decision": records[0]["decision"] if records and records[0]["scientific_readiness"] == "READY" else "ABSTAIN",
            "limitation": "Saved predictions are not necessarily calibrated or validated. No prediction is inferred from trial-processing events.",
        }

    @router.get("/validation")
    def validation():
        return historical_validation(engine_provider())

    @router.get("/status")
    def status():
        from . import phase3_ingestion
        return phase3_ingestion.status(engine_provider())

    app.include_router(router)
