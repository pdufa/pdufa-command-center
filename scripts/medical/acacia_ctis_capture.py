#!/usr/bin/env python3
"""Single-study, public-source CTIS protocol receipt. No secrets, no scoring or DB writes."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import urllib.error
import urllib.request

TRIAL = "2023-505797-15-00"
PROTOCOL = "CY 6033"
NAME = f"D1_{TRIAL}_Protocol_FP"
ROOT = "https://euclinicaltrials.eu/ctis-public-api"
PORTAL = f"https://euclinicaltrials.eu/ctis-public/view/{TRIAL}?lang=en"
OUTPUT = Path("acacia-ctis-source-receipt")
MAX_JSON = 12_000_000
MAX_DOC = 25_000_000
USER_AGENT = "PDUFA-MAIN-open-source-research/1.0 (single trial, public protocol; no credential)"
UUID = re.compile(r"^[A-Za-z0-9-]{16,80}$")

def request(url: str, max_bytes: int, accept: str, expected_host: str = "euclinicaltrials.eu") -> tuple[bytes, dict]:
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": accept,
        "Referer": PORTAL,
    })
    with urllib.request.urlopen(req, timeout=30) as rsp:
        code = rsp.status
        mime = rsp.headers.get("content-type", "")
        raw = rsp.read(max_bytes + 1)
        final_url = rsp.url
    if len(raw) > max_bytes:
        raise ValueError("SOURCE_TOO_LARGE")
    if code != 200:
        raise ValueError(f"HTTP_{code}")
    from urllib.parse import urlsplit
    location = urlsplit(final_url)
    if location.scheme != "https" or location.hostname != expected_host or location.username or location.password:
        raise ValueError("UNEXPECTED_REDIRECT_DOMAIN")
    return raw, {"http_status": code, "content_type": mime, "returned_url": final_url}

def gather_documents(root: object) -> list[dict]:
    """Look for the documented CTIS .documents[] entries at any nesting depth."""
    found, stack, steps = [], [root], 0
    while stack and steps < 40000:
        node = stack.pop()
        steps += 1
        if isinstance(node, dict):
            if isinstance(node.get("title"), str) and isinstance(node.get("uuid"), str):
                found.append(node)
            stack.extend(node.values())
        elif isinstance(node, list):
            stack.extend(node)
    return found

def run() -> dict:
    payload, response = request(f"{ROOT}/retrieve/{TRIAL}", MAX_JSON, "application/json")
    result = json.loads(payload)
    if not isinstance(result, dict):
        raise ValueError("INVALID_CTIS_OBJECT")
    if result.get("ctNumber") != TRIAL:
        raise ValueError("EXACT_EU_TRIAL_ID_MISMATCH")
    docs = gather_documents(result)
    related = [v for v in docs if any(t in str(v.get("title","")).lower() for t in
                ("statist", "analysis plan", "sap", "protocol"))]
    print("CTIS_INFO potential SAP/protocol document titles: " +
          json.dumps([{"title":d["title"],"version":d.get("version") or d.get("versionNumber")}
                      for d in related][:18], ensure_ascii=True))
    print("CTIS_INFO retrieved trial keys: " + ", ".join(sorted(result.keys())[:20]))
    print("CTIS_INFO public document records in retrieved trial: " + str(len(docs)))
    print("CTIS_INFO exact published protocol title matches: " + str(sum(1 for v in docs if v["title"] == NAME)))
    candidates = [v for v in docs if v["title"] == NAME and UUID.fullmatch(v["uuid"])]
    if len(candidates) != 1:
        raise ValueError(f"AM4_PROTOCOL_UNRESOLVED_MATCH_COUNT_{len(candidates)}")
    doc = candidates[0]
    identifier = str(doc["uuid"])
    file_type = str(doc.get("fileType", "")).lower()
    if file_type not in ("pdf", "application/pdf", ""):
        raise ValueError("UNEXPECTED_DOCUMENT_FORMAT")
    data, doc_response = request(f"{ROOT}/documents/{TRIAL}/{identifier}/download",
                                 MAX_DOC, "application/pdf,application/octet-stream")
    if "application/json" in str(doc_response.get("content_type", "")):
        from urllib.parse import urlsplit
        handoff = json.loads(data)
        if not isinstance(handoff, dict) or not isinstance(handoff.get("url"), str):
            raise ValueError("CTIS_DOCUMENT_HANDOFF_MISSING_URL")
        signed = handoff["url"]
        parsed = urlsplit(signed)
        trusted_host = "ctis-publication-engine-doc-storage-prod.s3.eu-central-1.amazonaws.com"
        if parsed.scheme != "https" or parsed.hostname != trusted_host or parsed.username or parsed.password:
            raise ValueError("CTIS_DOCUMENT_HANDOFF_UNTRUSTED_HOST")
        # The presigned S3 URL is ephemeral and never logged, stored, or emitted as evidence.
        data, doc_response = request(signed, MAX_DOC, "application/pdf,application/octet-stream",
                                     expected_host=trusted_host)
    if not data.startswith(b"%PDF-"):
        mime = str(doc_response.get("content_type", ""))[:64].replace(" ", "_")
        magic = data[:12].hex()
        raise ValueError(f"DOCUMENT_NOT_PDF_mime={mime}_magic={magic}_bytes={len(data)}")
    file = OUTPUT / "D1_2023-505797-15-00_Protocol_FP_AM4.pdf"
    file.write_bytes(data)
    details = {
        "status": "PUBLIC_ORIGINAL_PROTOCOL_DOWNLOADED_FOR_SOURCE_INSPECTION",
        "trial_id": TRIAL, "protocol_code": PROTOCOL,
        "document_title": NAME, "listed_version": doc.get("version") or doc.get("versionNumber") or "VERIFY_IN_DOCUMENT",
        "document_uuid": identifier,
        "document_type": doc.get("documentTypeLabel"),
        "source_trial_portal": PORTAL,
        "document_endpoint": f"{ROOT}/documents/{TRIAL}/{identifier}/download",
        "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
        "response": doc_response,
        "number_of_documents_in_response": len(docs),
        "phase_independently_verified": False, "clinical_signoff": False,
        "graded_methods": 0,
        "fda_predictions": {"APPROVAL":"ABSTAIN","CRL":"ABSTAIN","REVIEW_DELAY":"ABSTAIN"},
    }
    print("CTIS_PDF_TOOLS pdfinfo=" + str(bool(shutil.which("pdfinfo"))) +
          " pdftotext=" + str(bool(shutil.which("pdftotext"))))
    if shutil.which("pdfinfo"):
        p = subprocess.run(["pdfinfo",str(file)],capture_output=True,text=True,timeout=12)
        if p.returncode == 0:
            m = re.search(r"(?im)^Pages:\s*(\d+)",p.stdout)
            if m: details["pdf_pages"] = int(m.group(1))
    # Fallback to a pinned pure-Python PDF reader when poppler is not available.
    text_file = OUTPUT / "_private_protocol_extracted.txt"
    if shutil.which("pdftotext"):
        p = subprocess.run(["pdftotext",str(file),str(text_file)],capture_output=True,text=True,timeout=18)
        if p.returncode != 0:
            details["text_extraction_status"] = "SYSTEM_PDFTOTEXT_FAILED"
    else:
        try:
            from pypdf import PdfReader
            pdf = PdfReader(str(file))
            details["pdf_pages"] = len(pdf.pages)
            details["pdf_encrypted"] = bool(pdf.is_encrypted)
            if not pdf.is_encrypted:
                parts = [p.extract_text(extraction_mode="plain") or "" for p in pdf.pages[:180]]
                text_file.write_text("\n".join(parts),encoding="utf-8")
        except (ImportError, ValueError, OSError, Exception) as exc:
            details["text_extraction_status"] = "PYTHON_PDF_READER_UNAVAILABLE_OR_FAILED"
            print("CTIS_PDF_TEXT_READER error_class=" + type(exc).__name__)
    if text_file.exists() and text_file.stat().st_size:
        text = text_file.read_text(encoding="utf-8",errors="replace").lower()
        details["term_presence_only"] = {
            term:term.lower() in text for term in (
                "statistical analysis plan", "intercurrent event", "randomization",
                "missing data", "peak oxygen uptake", "kansas city",
            )
        }
        details["machine_readable_text_bytes"] = text_file.stat().st_size
        normalized = " ".join(text.split())
        details["first_page_identity_preview"] = normalized[:360]
        terms = (
            "statistical analysis plan", "protocol amendment", "amendment 4", "amendment no",
            "analysis populations", "estimand", "intercurrent event",
            "missing data", "randomization", "multiplicity", "sample size",
            "kansas city cardiomyopathy", "peak oxygen uptake", "pvo2", "36 weeks",
            "heart failure", "ejection fraction", "primary efficacy",
        )
        details["protocol_topic_locations"] = []
        for term in terms:
            position = normalized.find(term)
            details["protocol_topic_locations"].append({
                "topic":term,
                "found":position>=0,
                "context_excerpt":normalized[max(0,position-60):position+130] if position>=0 else None,
            })
        print("CTIS_PDF_INFO pages=" + str(details.get("pdf_pages")) +
              " readable_text_bytes=" + str(details["machine_readable_text_bytes"]))
        print("CTIS_PDF_INFO identity_excerpt=" + repr(details["first_page_identity_preview"]))
        for entry in details["protocol_topic_locations"]:
            if entry["found"]:
                print("CTIS_PDF_TOPIC " + entry["topic"] + " = " + repr(entry["context_excerpt"][:170]))
        # Do not upload extracted copyrighted text as an artifact.
        text_file.unlink()
    elif text_file.exists():
        text_file.unlink()
        details["text_extraction_status"] = "NO_MACHINE_READABLE_TEXT"
    return details

def main():
    OUTPUT.mkdir(exist_ok=True)
    receipt = {
        "schema": "ONE_SHOT_PUBLIC_CTIS_PROTOCOL_CAPTURE_V1",
        "target_ct_number":TRIAL, "source_portal":PORTAL,
        "independent_clinical_review":False, "method_grades":0,
    }
    try:
        receipt.update(run())
        print("CTIS source retrieval SUCCESS; validate source bytes and protocol version before reviewer grading.")
        print(f"SHA256: {receipt['sha256']}  PDF bytes: {receipt['bytes']}")
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError, OSError,
            json.JSONDecodeError, subprocess.SubprocessError) as ex:
        receipt["status"] = "NOT_RETRIEVED_OR_NOT_VERIFIED"
        name = type(ex).__name__
        receipt["error_category"] = name
        if isinstance(ex, urllib.error.HTTPError): receipt["http_status"]=ex.code
        if isinstance(ex, ValueError):
            receipt["safe_diagnostic"] = str(ex)[:180]
        print(f"CTIS public protocol capture not completed: {name}: {receipt.get('safe_diagnostic','see status')}. No clinical grades or phase status were changed.")
    (OUTPUT/"source_receipt.json").write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf-8")
    (OUTPUT/"README.txt").write_text(
        "Research-only CTIS protocol capture for EU CT 2023-505797-15-00.\n"
        "A stored original protocol is not a signed clinical review, final SAP or FDA prediction.\n"
        "Do not import this artifact as an approved method grade or phase event.\n",encoding="utf-8")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
