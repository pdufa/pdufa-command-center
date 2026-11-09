"""Isolated MAIN original-evidence vault: encrypted, append-only public-source bytes.

This module is NOT an automatic source fetcher, medical grader, data-sharing
authorization, or a PHI-approved store. It is usable only by a separately
enabled isolated medical backend with a dedicated role key and encryption key.
Neon branchable object storage is unavailable in the existing west-2 region;
small (<=2 MiB) encrypted original public evidence can instead use PostgreSQL.
No tables are created on import; initialize must be invoked explicitly.
"""
from __future__ import annotations

import base64
import binascii
from datetime import date, datetime, timezone
import hashlib
import json
import os
import re
import secrets
import uuid
from urllib.parse import urlparse
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

EXACT_NCT = "NCT06081894"
MAX_DOCUMENT_BYTES = 2 * 1024 * 1024
ENABLED = ("1", "true", "yes")
REQUEST_TYPES = {
    "LOCKED_PRIMARY_SAP": "STATISTICAL_ANALYSIS_PLAN",
    "PRIMARY_SENSITIVITY_AND_MISSINGNESS": "PRIMARY_ANALYSIS_TABLES",
    "HF_SAE_EVENT_DEFINITION": "HF_ADVERSE_EVENT_TABLE",
    "SAFETY_DENOMINATORS_EXPOSURE": "SAFETY_DENOMINATOR_TABLE",
    "CONSORT_AND_PROTOCOL_VERSIONS": "PROTOCOL_CONSORT",
    "EXACT_NHCM_REGULATORY_STATUS": "REGULATORY_SOURCE",
}
SOURCE_HOSTS = frozenset((
    "clinicaltrials.gov", "ctis.europa.eu", "euclinicaltrials.eu",
    "www.nejm.org", "nejm.org", "pubmed.ncbi.nlm.nih.gov",
    "pmc.ncbi.nlm.nih.gov", "www.ebi.ac.uk", "www.sec.gov", "www.fda.gov",
    "www.accessdata.fda.gov", "accessdata.fda.gov", "ir.cytokinetics.com",
    "cytokinetics.com", "www.cytokinetics.com", "github.com",
))
CONTENT_TYPES = frozenset(("application/pdf", "text/plain"))
META_FIELDS = frozenset((
    "nct", "requestId", "documentType", "documentTitle", "documentVersion",
    "documentDate", "sourceUrl", "claimedSha256", "contentType",
))
ROLE = re.compile(r"^[A-Za-z0-9_.@-]{3,80}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")


class VaultError(ValueError):
    """No raw filenames, source snippets or credentials in error messages."""


def parse_encryption_key(key_b64: str | None) -> bytes:
    if not isinstance(key_b64, str) or not 40 <= len(key_b64) <= 64:
        raise VaultError("Dedicated encryption key not configured")
    try:
        decoded = base64.b64decode(key_b64, validate=True)
    except (ValueError, binascii.Error):
        raise VaultError("Invalid vault encryption key") from None
    if len(decoded) != 32:
        raise VaultError("Vault requires an independently provisioned 256-bit key")
    return decoded


def _allowlisted_url(value: Any) -> bool:
    if not isinstance(value, str) or not 14 <= len(value) <= 320:
        return False
    if re.search(r"[\x00-\x20\x7f]", value):
        return False
    try:
        u = urlparse(value)
    except ValueError:
        return False
    try:
        return (u.scheme == "https" and u.hostname in SOURCE_HOSTS
                and not u.username and not u.password and u.port in (None, 443)
                and not u.query and not u.fragment and bool(u.path)
                and not re.search(r"%2f|%5c|%00|\\", u.path, re.I))
    except ValueError:
        return False


def _check_document(meta: dict, raw: bytes, uploader: str) -> None:
    if not isinstance(meta, dict) or frozenset(meta) != META_FIELDS:
        raise VaultError("Incorrect exact research metadata fields")
    if meta["nct"] != EXACT_NCT:
        raise VaultError("Only the named Phase III pilot is authorized")
    if (meta["requestId"] not in REQUEST_TYPES
            or meta["documentType"] != REQUEST_TYPES[meta["requestId"]]):
        raise VaultError("Evidence requirement or document type mismatch")
    title, version, d = meta["documentTitle"], meta["documentVersion"], meta["documentDate"]
    if (not isinstance(title, str) or not 8 <= len(title) <= 160
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 .,():_+/\-–—]*", title)):
        raise VaultError("Invalid source document title")
    if (not isinstance(version, str) or not 1 <= len(version) <= 48
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._ /\-]*", version)):
        raise VaultError("Invalid immutable source version")
    try:
        if not isinstance(d, str) or len(d) != 10 or date.fromisoformat(d).isoformat() != d:
            raise ValueError()
    except ValueError:
        raise VaultError("Invalid document date") from None
    if not _allowlisted_url(meta["sourceUrl"]):
        raise VaultError("Document source domain or URL not allowed")
    if meta["contentType"] not in CONTENT_TYPES:
        raise VaultError("Only public PDF or UTF-8 original text is supported")
    if not isinstance(raw, bytes) or not 40 <= len(raw) <= MAX_DOCUMENT_BYTES:
        raise VaultError("Original source byte size is outside allowed range")
    if meta["contentType"] == "application/pdf" and not raw.startswith(b"%PDF-"):
        raise VaultError("Original PDF signature missing")
    if meta["contentType"] == "text/plain":
        try:
            clear = raw.decode("utf-8", "strict")
        except UnicodeDecodeError:
            raise VaultError("Original text must be valid UTF-8") from None
        if "\x00" in clear:
            raise VaultError("Binary data not permitted as original text")
    sha = hashlib.sha256(raw).hexdigest()
    if not isinstance(meta["claimedSha256"], str) or not HEX64.fullmatch(meta["claimedSha256"]):
        raise VaultError("Source digest must be exact SHA-256")
    if not secrets.compare_digest(sha, meta["claimedSha256"]):
        raise VaultError("Original bytes do not match the claimed digest")
    if not isinstance(uploader, str) or not ROLE.fullmatch(uploader):
        raise VaultError("A named authorized intake officer is required")


def _canonical(payload: dict) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def _receipt_hash(fields: dict) -> str:
    return hashlib.sha256(_canonical(fields)).hexdigest()


def initialize(engine, *, test_only: bool = False) -> None:
    """Additive, isolated tables only. PostgreSQL mandatory except unit tests."""
    if engine.dialect.name != "postgresql" and not test_only:
        raise VaultError("Durable PostgreSQL is required for original evidence")
    binary_type = "BYTEA" if engine.dialect.name == "postgresql" else "BLOB"
    with engine.begin() as c:
        c.execute(text(f"""CREATE TABLE IF NOT EXISTS medical_original_evidence_vault (
            receipt_id TEXT PRIMARY KEY,
            nct_id TEXT NOT NULL CHECK(nct_id = 'NCT06081894'),
            request_id TEXT NOT NULL,
            content_sha256 TEXT NOT NULL,
            metadata_json TEXT NOT NULL,
            encrypted_data {binary_type} NOT NULL,
            nonce {binary_type} NOT NULL,
            aad_sha256 TEXT NOT NULL,
            byte_count INTEGER NOT NULL CHECK(byte_count BETWEEN 40 AND 2097152),
            uploaded_by TEXT NOT NULL,
            deposited_at TEXT NOT NULL,
            previous_receipt_sha256 TEXT,
            receipt_sha256 TEXT NOT NULL UNIQUE,
            UNIQUE(nct_id,request_id,content_sha256)
        )"""))
        c.execute(text("""CREATE INDEX IF NOT EXISTS medical_evidence_vault_nct_request
          ON medical_original_evidence_vault(nct_id,request_id,deposited_at)"""))
        if engine.dialect.name == "postgresql":
            c.execute(text("""CREATE OR REPLACE FUNCTION medical_evidence_vault_reject_change()
                RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN RAISE EXCEPTION 'Original evidence vault records are append-only';
                END; $$"""))
            exists = c.execute(text("""SELECT 1 FROM pg_trigger WHERE tgname=:name
                AND tgrelid=CAST(:table AS regclass)"""),
                {"name":"medical_original_evidence_vault_immutable",
                 "table":"medical_original_evidence_vault"}).scalar()
            if not exists:
                c.execute(text("""CREATE TRIGGER medical_original_evidence_vault_immutable
                    BEFORE UPDATE OR DELETE OR TRUNCATE ON medical_original_evidence_vault
                    FOR EACH STATEMENT EXECUTE FUNCTION medical_evidence_vault_reject_change()"""))
        else:
            for operation in ("UPDATE", "DELETE"):
                c.execute(text(f"""CREATE TRIGGER IF NOT EXISTS
                    medical_original_evidence_vault_{operation.lower()}
                    BEFORE {operation} ON medical_original_evidence_vault BEGIN
                    SELECT RAISE(ABORT,'Original evidence vault records are append-only');
                    END"""))


def deposit(engine, *, metadata: dict, original_bytes: bytes,
            uploaded_by: str, encryption_key: bytes) -> dict:
    """Persist exactly one versioned, ciphertext-only, SHA-256-verified object."""
    if engine.dialect.name != "postgresql" and engine.dialect.name != "sqlite":
        raise VaultError("Unsupported database engine")
    if not isinstance(encryption_key, bytes) or len(encryption_key) != 32:
        raise VaultError("Invalid independently provisioned encryption key")
    _check_document(metadata, original_bytes, uploaded_by)
    rid = str(uuid.uuid4())
    deposited_at = datetime.now(timezone.utc).isoformat()
    canonical_metadata = _canonical(metadata).decode("ascii")
    source_sha = metadata["claimedSha256"]
    aad = _canonical({"nct":EXACT_NCT,"requestId":metadata["requestId"],
                      "receiptId":rid,"sourceSha256":source_sha,
                      "metadataSha256":hashlib.sha256(canonical_metadata.encode()).hexdigest()})
    nonce = os.urandom(12)
    ciphertext = AESGCM(encryption_key).encrypt(nonce, original_bytes, aad)
    with engine.begin() as c:
        if engine.dialect.name == "postgresql":
            c.execute(text("SELECT pg_advisory_xact_lock(hashtext(:id))"),
                      {"id":EXACT_NCT+":"+metadata["requestId"]})
        prior = c.execute(text("""SELECT receipt_sha256 FROM medical_original_evidence_vault
          WHERE nct_id=:nct AND request_id=:request ORDER BY deposited_at DESC,receipt_id DESC LIMIT 1"""),
          {"nct":EXACT_NCT,"request":metadata["requestId"]}).scalar()
        fields = {
            "receiptId":rid,"nct":EXACT_NCT,"requestId":metadata["requestId"],
            "sourceSha256":source_sha,"metadataSha256":hashlib.sha256(canonical_metadata.encode()).hexdigest(),
            "aadSha256":hashlib.sha256(aad).hexdigest(),"byteCount":len(original_bytes),
            "uploadedBy":uploaded_by,"depositedAt":deposited_at,
            "previousReceiptSha256":prior,
        }
        receipt = _receipt_hash(fields)
        try:
            c.execute(text("""INSERT INTO medical_original_evidence_vault
                (receipt_id,nct_id,request_id,content_sha256,metadata_json,
                encrypted_data,nonce,aad_sha256,byte_count,uploaded_by,
                deposited_at,previous_receipt_sha256,receipt_sha256)
                VALUES (:rid,:nct,:request,:sha,:metadata,:encrypted,:nonce,
                :aad,:size,:uploader,:at,:previous,:receipt)"""),
                {"rid":rid,"nct":EXACT_NCT,"request":metadata["requestId"],
                 "sha":source_sha,"metadata":canonical_metadata,
                 "encrypted":ciphertext,"nonce":nonce,
                 "aad":hashlib.sha256(aad).hexdigest(),
                 "size":len(original_bytes),"uploader":uploaded_by,
                 "at":deposited_at,"previous":prior,"receipt":receipt})
        except IntegrityError:
            raise VaultError("An identical source version is already archived") from None
    # No plaintext or decryption key is included in a response or log.
    return {**fields,"receiptSha256":receipt,"encrypted":True,
            "receivedOriginalBytes":len(original_bytes),
            "sourceHashComputedFromOriginalBytes":True,
            "issuerAndClinicalContentIndependentlyVerified":False,
            "sponsorAuthorizationVerified":False,
            "clinicalReviewerSigned":False,"medicalGradesWritten":0,
            "fdaPrediction":"ABSTAIN"}


def list_receipts(engine, *, nct: str) -> list[dict]:
    if nct != EXACT_NCT:
        raise VaultError("Wrong trial")
    with engine.connect() as c:
        rows = c.execute(text("""SELECT receipt_id,request_id,content_sha256,
             metadata_json,byte_count,uploaded_by,deposited_at,
             previous_receipt_sha256,receipt_sha256 FROM medical_original_evidence_vault
             WHERE nct_id=:nct ORDER BY request_id,deposited_at,receipt_id"""),
             {"nct":nct}).mappings().all()
    out=[]
    for row in rows:
        r=dict(row)
        out.append({"receiptId":r["receipt_id"],"requestId":r["request_id"],
                    "sourceSha256":r["content_sha256"],"byteCount":r["byte_count"],
                    "uploadedBy":r["uploaded_by"],"depositedAt":r["deposited_at"],
                    "previousReceiptSha256":r["previous_receipt_sha256"],
                    "receiptSha256":r["receipt_sha256"],
                    "metadata":json.loads(r["metadata_json"]),
                    "clinicalReviewerSigned":False,"medicalGrade":None})
    return out


def audit_version_chain(engine, *, request_id: str) -> dict:
    """Verify linked, append-only metadata receipts for a source request.

    A database administrator may still change/drop SQL triggers; the receipt
    chain is an audit aid, not tamper-proof protection against a DB owner.
    """
    if request_id not in REQUEST_TYPES:
        raise VaultError("Unknown source evidence requirement")
    with engine.connect() as c:
        rows=c.execute(text("""SELECT receipt_id,nct_id,request_id,content_sha256,
            metadata_json,aad_sha256,byte_count,uploaded_by,deposited_at,
            previous_receipt_sha256,receipt_sha256
            FROM medical_original_evidence_vault WHERE nct_id=:nct AND request_id=:id
            ORDER BY deposited_at,receipt_id"""),
            {"nct":EXACT_NCT,"id":request_id}).mappings().all()
    previous=None
    for row in rows:
        if row["previous_receipt_sha256"] != previous:
            raise VaultError("Evidence version history has an invalid previous receipt")
        h=_receipt_hash({
            "receiptId":row["receipt_id"],"nct":row["nct_id"],
            "requestId":row["request_id"],"sourceSha256":row["content_sha256"],
            "metadataSha256":hashlib.sha256(row["metadata_json"].encode()).hexdigest(),
            "aadSha256":row["aad_sha256"],"byteCount":row["byte_count"],
            "uploadedBy":row["uploaded_by"],"depositedAt":row["deposited_at"],
            "previousReceiptSha256":row["previous_receipt_sha256"],
        })
        if not secrets.compare_digest(h,row["receipt_sha256"]):
            raise VaultError("Evidence version history receipt digest invalid")
        previous=row["receipt_sha256"]
    return {"nct":EXACT_NCT,"requestId":request_id,"immutableReceiptCount":len(rows),
            "lastReceiptSha256":previous,"receiptChainVerified":True,
            "clinicalGradesWritten":0,"fdaPrediction":"ABSTAIN"}


def verify_at_rest(engine, *, receipt_id: str, encryption_key: bytes) -> dict:
    """Internal audit only. Never return decrypted original document bytes."""
    if not isinstance(receipt_id, str) or not re.fullmatch(r"[0-9a-f-]{36}",receipt_id):
        raise VaultError("Invalid receipt id")
    if not isinstance(encryption_key, bytes) or len(encryption_key) != 32:
        raise VaultError("Encryption key not configured")
    with engine.connect() as c:
        row=c.execute(text("""SELECT * FROM medical_original_evidence_vault
            WHERE receipt_id=:receipt"""),{"receipt":receipt_id}).mappings().first()
    if not row:
        raise VaultError("Unknown evidence receipt")
    meta=json.loads(row["metadata_json"])
    expected_receipt = _receipt_hash({
        "receiptId":row["receipt_id"],"nct":EXACT_NCT,
        "requestId":row["request_id"],"sourceSha256":row["content_sha256"],
        "metadataSha256":hashlib.sha256(row["metadata_json"].encode()).hexdigest(),
        "aadSha256":row["aad_sha256"],"byteCount":row["byte_count"],
        "uploadedBy":row["uploaded_by"],"depositedAt":row["deposited_at"],
        "previousReceiptSha256":row["previous_receipt_sha256"],
    })
    if not secrets.compare_digest(expected_receipt,row["receipt_sha256"]):
        raise VaultError("Evidence receipt manifest integrity failed")
    aad=_canonical({"nct":EXACT_NCT,"requestId":row["request_id"],
                    "receiptId":row["receipt_id"],
                    "sourceSha256":row["content_sha256"],
                    "metadataSha256":hashlib.sha256(row["metadata_json"].encode()).hexdigest()})
    if hashlib.sha256(aad).hexdigest()!=row["aad_sha256"]:
        raise VaultError("Evidence authenticated-data binding invalid")
    try:
        raw=AESGCM(encryption_key).decrypt(bytes(row["nonce"]),bytes(row["encrypted_data"]),aad)
    except Exception:
        raise VaultError("Encrypted original evidence authentication failed") from None
    if hashlib.sha256(raw).hexdigest()!=row["content_sha256"] or len(raw)!=row["byte_count"]:
        raise VaultError("Original evidence source digest verification failed")
    _check_document(meta,raw,row["uploaded_by"])
    return {"receiptId":receipt_id,"sha256Verified":True,
            "aesGcmAuthenticationVerified":True,
            "originalBytesVerified":len(raw),
            "clinicalReviewerSigned":False,
            "medicalGradesWritten":0,"fdaPrediction":"ABSTAIN"}
