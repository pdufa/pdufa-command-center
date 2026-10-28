"""SCIENCE 40-question evidence readiness dossier, without FDA prediction.

Preserves a separate 8-layer/40-question research contract. Submitted
evidence is never considered *independently reviewed* on its own; only a
separately maintained, server-side adjudication register can attest it.
The register starts empty for every real trial. No scoring or trade decisions.
"""
from __future__ import annotations

from datetime import date
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlsplit


QUESTION_CATALOG = Path(__file__).with_name("science_40_question_catalog.json")
ADJUDICATION_REGISTER = Path(__file__).with_name("science_40_adjudication_register.json")
INTERPRETATIONS = frozenset({"SUPPORTS", "CHALLENGES", "MIXED", "INCONCLUSIVE"})
SOURCE_SHA = re.compile(r"[a-f0-9]{64}\Z")
DEPTH_LEVELS = tuple(range(1, 21))


def _date(value: object) -> date | None:
    if not isinstance(value, str) or len(value) != 10:
        return None
    try:
        parsed = date.fromisoformat(value)
        return parsed if parsed.isoformat() == value else None
    except ValueError:
        return None


def _valid_https(value: object) -> bool:
    if not isinstance(value, str) or any(c.isspace() for c in value):
        return False
    try:
        parsed = urlsplit(value)
        host = parsed.hostname or ""
        return (
            parsed.scheme == "https"
            and parsed.netloc != ""
            and parsed.username is None and parsed.password is None
            and parsed.fragment == "" and "." in host
            and parsed.port in (None, 443)
            and host not in ("localhost", "127.0.0.1")
        )
    except ValueError:
        return False


@lru_cache(maxsize=1)
def _catalog() -> tuple[dict, ...]:
    raw = json.loads(QUESTION_CATALOG.read_text(encoding="utf-8"))
    questions = raw.get("questions")
    if (raw.get("schemaVersion") != "science-40-question-catalog-v1"
            or raw.get("status") != "RESEARCH_ONLY_NOT_CERTIFIED"
            or not isinstance(questions, list) or len(questions) != 40):
        raise ValueError("40-question SCIENCE source catalog missing or inconsistent")
    for i, q in enumerate(questions):
        if (q.get("id") != f"S{i + 1:02d}"
                or q.get("layer") != 1 + i // 5
                or not all(isinstance(q.get(k), str) and q[k].strip()
                           for k in ("layerName", "question", "requiredEvidence"))):
            raise ValueError("SCIENCE question identity or layer mismatch")
    if len({q["id"] for q in questions}) != 40:
        raise ValueError("Duplicate SCIENCE question IDs")
    return tuple(questions)


@lru_cache(maxsize=1)
def _trusted_register() -> dict:
    register = json.loads(ADJUDICATION_REGISTER.read_text(encoding="utf-8"))
    if (register.get("schemaVersion") != "science40-adjudication-register-v1"
            or not isinstance(register.get("cases"), dict)):
        raise ValueError("Invalid SCIENCE independent review register")
    return register


def _source_submission(record: object, cutoff: date) -> tuple[str, dict | None]:
    """Separate source-report metadata from an independently certified finding."""
    if not isinstance(record, dict):
        return ("NOT_SUBMITTED", None) if record is None else ("REJECTED", None)
    if not record:
        return "NOT_SUBMITTED", None
    pub = _date(record.get("published_at"))
    examined = _date(record.get("examined_at"))
    kind = record.get("source_kind")
    finding = record.get("finding")
    interpretation = record.get("interpretation")
    sha = record.get("source_sha256")
    depth = record.get("depth_level")
    if not (
        pub and examined and pub <= examined <= cutoff
        and _valid_https(record.get("source_url"))
        and kind in {"ISSUER_DISCLOSURE", "TRIAL_REGISTRY", "PROTOCOL",
                     "PEER_REVIEWED_PUBLICATION", "FDA_DOCUMENT", "STATISTICAL_PLAN",
                     "CLINICAL_STUDY_REPORT", "MANUFACTURING_DOCUMENT", "OTHER"}
        and isinstance(finding, str) and 0 < len(finding.strip()) <= 4000
        and interpretation in INTERPRETATIONS
        and isinstance(sha, str) and SOURCE_SHA.fullmatch(sha)
        and type(depth) is int and depth in DEPTH_LEVELS
    ):
        return "REJECTED", None
    return "SOURCE_REPORTED_UNADJUDICATED", {
        "sourceUrl": record["source_url"],
        "publishedAt": pub.isoformat(),
        "examinedAt": examined.isoformat(),
        "sourceKind": kind,
        "finding": finding.strip(),
        "interpretation": interpretation,
        "sourceSha256": sha,
        "depthLevel": depth,
    }


def _certified(source: dict, claim: object, cutoff: date) -> bool:
    """Only a *server-stored* independently signed-off source may count.

    This validates metadata consistency. It does not verify scientific truth
    independently: the attestor must actually review the underlying document.
    """
    if not isinstance(claim, dict) or claim.get("reviewStatus") != "INDEPENDENTLY_ADJUDICATED":
        return False
    when = _date(claim.get("reviewedAt"))
    reviewer = claim.get("reviewerId")
    if (not when or not _date(source["examinedAt"]) <= when <= cutoff
            or not isinstance(reviewer, str) or len(reviewer.strip()) < 3):
        return False
    for src, dest in [
        ("sourceUrl", "sourceUrl"),
        ("sourceSha256", "sourceSha256"),
        ("publishedAt", "publishedAt"),
        ("finding", "finding"),
        ("interpretation", "interpretation"),
    ]:
        if claim.get(dest) != source[src]:
            return False
    digest = hashlib.sha256(source["finding"].encode("utf-8")).hexdigest()
    return claim.get("findingSha256") == digest


def evaluate_science_40(
    *, exact_key: str, evidence: dict, as_of: str,
    trusted_register: dict | None = None,
) -> dict:
    """Create immutable presentation output, independent of trading scores.

    The HTTP API never provides trusted_register; test injection supports
    isolated validation without producing real certified evidence.
    """
    if not isinstance(exact_key, str) or not exact_key.strip():
        raise ValueError("Exact trial/program identity required")
    if not isinstance(evidence, dict):
        raise ValueError("SCIENCE evidence must be a mapping")
    cutoff = _date(as_of)
    if cutoff is None:
        raise ValueError("Valid SCIENCE snapshot date required")
    catalog = _catalog()
    register = trusted_register if trusted_register is not None else _trusted_register()
    if (not isinstance(register, dict)
            or register.get("schemaVersion") != "science40-adjudication-register-v1"
            or not isinstance(register.get("cases"), dict)):
        raise ValueError("Invalid independent SCIENCE register")
    entry = register["cases"].get(exact_key, {})
    if not isinstance(entry, dict):
        raise ValueError("Invalid exact-case independent SCIENCE register")

    rows = []
    submitted_count = reviewed_count = rejected_count = 0
    depth_covered = set()
    critical_questions = []
    for q in catalog:
        question_id = q["id"]
        status, source = _source_submission(evidence.get(question_id), cutoff)
        certified = (source is not None
                     and _certified(source, entry.get(question_id), cutoff))
        if source is not None:
            submitted_count += 1
        elif status == "REJECTED":
            rejected_count += 1
        if certified:
            status = "INDEPENDENTLY_REVIEWED"
            reviewed_count += 1
            depth_covered.add(source["depthLevel"])
            if source["interpretation"] in {"CHALLENGES", "MIXED"}:
                critical_questions.append(question_id)
        rows.append({
            "id": question_id,
            "layer": q["layer"],
            "layerName": q["layerName"],
            "question": q["question"],
            "requiredEvidence": q["requiredEvidence"],
            "status": status,
            "independentlyReviewed": certified,
            # Source assertions are clearly labeled; no calculated score.
            "sourceObservation": source,
            "scientificScore": None,
        })
    unexpected_keys = sorted(k for k in evidence if k not in {q["id"] for q in catalog})
    ready = reviewed_count == 40 and len(depth_covered) == 20
    return {
        "schemaVersion": "science40-evidence-readiness-v1",
        "catalogStatus": "RESEARCH_ONLY_NOT_CERTIFIED",
        "exactKey": exact_key,
        "asOf": cutoff.isoformat(),
        "layers": 8,
        "questionsPerLayer": 5,
        "totalAssessments": 40,
        "maximumInvestigationDepth": 20,
        "submittedSourceObservations": submitted_count,
        "rejectedSourceSubmissions": rejected_count,
        "independentlyReviewedAssessments": reviewed_count,
        "independentEvidenceCoveragePercent": round(100 * reviewed_count / 40, 1),
        "reviewedDepthLevels": sorted(depth_covered),
        "missingDepthLevels": [n for n in DEPTH_LEVELS if n not in depth_covered],
        "criticalQuestions": critical_questions,
        "unmappedEvidenceKeys": unexpected_keys,
        "readinessGrade": "READY_FOR_ANALYSIS" if ready else "RELUCTANT",
        "readinessMeaning": "STRUCTURAL_EVIDENCE_READINESS_NOT_FDA_OUTCOME",
        "records": rows,
        "independentScientificConclusion": None,
        "approvalProbability": None,
        "tradeAuthorized": False,
        "researchOnly": True,
    }
