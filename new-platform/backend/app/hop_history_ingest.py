"""Strict import of curated historical FDA outcomes for HOP research.

This does not fetch, infer, or create historical outcomes. Source reviewers
must provide verifiable, dated cases. Invalid rows fail the entire import.
"""
from __future__ import annotations
import json
from datetime import date
from pathlib import Path
from urllib.parse import urlparse
from .hop_comparators import HistoricalCase, VALID_OUTCOMES

REQUIRED = frozenset({"case_id", "indication", "therapeutic_area", "modality",
                     "phase", "decision_date", "outcome", "evidence_as_of", "source_url"})

def parse_history(text: str) -> list[HistoricalCase]:
    raw = json.loads(text)
    if not isinstance(raw, list):
        raise ValueError("Historical outcomes must be a JSON array")
    cases = []
    seen = set()
    for index, item in enumerate(raw):
        if not isinstance(item, dict) or set(item) != REQUIRED:
            raise ValueError(f"Historical case {index}: missing or unexpected fields")
        if any(not isinstance(item[k], str) or not item[k].strip()
               for k in ("case_id", "indication", "therapeutic_area", "modality", "outcome", "source_url")):
            raise ValueError(f"Historical case {index}: required text is empty")
        if type(item["phase"]) is not int or item["phase"] < 3:
            raise ValueError(f"Historical case {index}: invalid trial phase")
        if item["outcome"] not in VALID_OUTCOMES:
            raise ValueError(f"Historical case {index}: unsupported FDA outcome")
        parsed = urlparse(item["source_url"])
        if parsed.scheme != "https" or parsed.hostname not in {"fda.gov", "www.fda.gov", "accessdata.fda.gov"}:
            raise ValueError(f"Historical case {index}: official FDA source required")
        decision = date.fromisoformat(item["decision_date"])
        evidence = date.fromisoformat(item["evidence_as_of"])
        if evidence >= decision:
            raise ValueError(f"Historical case {index}: evidence must predate FDA decision")
        if decision > date.today() or evidence > date.today():
            raise ValueError(f"Historical case {index}: future evidence/decision")
        if item["case_id"] in seen:
            raise ValueError(f"Historical case {index}: duplicate ID")
        seen.add(item["case_id"])
        cases.append(HistoricalCase(
            case_id=item["case_id"], indication=item["indication"],
            therapeutic_area=item["therapeutic_area"], modality=item["modality"],
            phase=item["phase"], decision_date=decision, outcome=item["outcome"],
            evidence_as_of=evidence, source_url=item["source_url"]))
    return cases

def load_history(path: str | Path) -> list[HistoricalCase]:
    return parse_history(Path(path).read_text(encoding="utf-8"))
