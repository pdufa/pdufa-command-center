#!/usr/bin/env python3
"""Research-only exact registered drug/condition term locators in SEC text.

ClinicalTrials.gov registered terms may appear in unrelated business discussions.
Exact lexical mentions do NOT establish drug identity, ownership, indication,
current licensing, territory, FDA review or approval probability.
"""
from __future__ import annotations

import re
from collections import defaultdict

TOTAL_TRIALS = 741
NCT_ID = re.compile(r"^NCT[0-9]{8}$")
SHA256 = re.compile(r"^[a-fA-F0-9]{64}$")
REGISTRY_URL = "https://clinicaltrials.gov/api/v2/studies/"
MAX_DOC_CHARS = 8_000_000
MAX_CANDIDATES_PER_KIND = 12
MAX_MENTIONS_PER_DOCUMENT = 120
EXCERPT_CHARS = 160
EXCLUDE = {
    "placebo", "saline", "vehicle", "sham", "observation",
    "no intervention", "standard of care", "usual care",
    "best supportive care", "study drug", "drug", "treatment",
    "experimental drug", "active treatment",
}


def prepare_program_terms(program, casebook):
    """Enforce complete exact NCT, issuer and immutable source associations."""
    entries = program.get("items") if isinstance(program, dict) else None
    originals = casebook.get("items") if isinstance(casebook, dict) else None
    if (program.get("report_type") != "MAIN_PHASE3_ORIGINAL_DRUG_INDICATION_TERMS_RESEARCH_ONLY"
        or program.get("total_trials") != TOTAL_TRIALS
        or program.get("independently_verified_program_identities") != 0
        or program.get("independently_verified_commercial_rights") != 0
        or program.get("qualified_pipeline_total") is not None
        or casebook.get("total_trials") != TOTAL_TRIALS
        or casebook.get("qualified_pipeline_total") is not None
        or not isinstance(entries, list) or len(entries) != TOTAL_TRIALS
        or not isinstance(originals, list) or len(originals) != TOTAL_TRIALS):
        raise ValueError("Exact unqualified 741-study original program report required")
    originals_by_nct = {}
    for original in originals:
        if not isinstance(original, dict):
            raise ValueError("Malformed original casebook")
        nct = original.get("nct_id")
        if not isinstance(nct, str) or not NCT_ID.fullmatch(nct) or nct in originals_by_nct:
            raise ValueError("Invalid/duplicate casebook identity")
        originals_by_nct[nct] = original
    prepared = defaultdict(list)
    seen = set()
    for row in entries:
        if not isinstance(row, dict):
            raise ValueError("Malformed original program row")
        nct, ticker = row.get("nct_id"), row.get("ticker")
        if nct not in originals_by_nct or nct in seen:
            raise ValueError("Unknown or duplicated program NCT")
        seen.add(nct)
        original = originals_by_nct[nct]
        if (ticker != original.get("ticker") or not isinstance(ticker, str)
            or row.get("original_registry_source_url") != REGISTRY_URL + nct
            or row.get("original_registry_source_url") != original.get("original_registry_api_url")
            or row.get("original_registry_source_sha256") != original.get("original_registry_sha256")
            or not isinstance(row.get("original_registry_source_sha256"), str)
            or not SHA256.fullmatch(row["original_registry_source_sha256"])
            or row.get("commercial_rights_verified") is not False
            or row.get("drug_indication_qualified") is not False
            or row.get("qualified_pipeline") is not None
            or row.get("identity_review_status") != "REGISTRY_TERMS_REQUIRE_INDEPENDENT_REVIEW"):
            raise ValueError("Registry/issuer provenance or qualification boundary violated")
        interventions = row.get("registry_interventions")
        drug_names = row.get("provisional_drug_or_biologic_names")
        conditions = row.get("registry_conditions")
        if (not isinstance(interventions, list) or not isinstance(drug_names, list)
            or not isinstance(conditions, list)):
            raise ValueError("Original program intervention/condition lists missing")
        accepted = {
            x.get("name") for x in interventions if isinstance(x, dict)
            and x.get("type") in ("DRUG", "BIOLOGICAL")
            and isinstance(x.get("name"), str)
        }
        if any(not isinstance(x, str) or x not in accepted for x in drug_names):
            raise ValueError("Reported provisional drug must be exact original intervention")
        for kind, values in (("REGISTERED_DRUG_OR_BIOLOGIC", drug_names[:MAX_CANDIDATES_PER_KIND]),
                             ("REGISTERED_CONDITION", conditions[:MAX_CANDIDATES_PER_KIND])):
            for value in values:
                if not isinstance(value, str) or len(value) > 400 or not value.strip():
                    raise ValueError("Malformed registered program term")
                term = " ".join(value.strip().split())
                if len(term) < 4 or term.casefold() in EXCLUDE or term.isdecimal():
                    continue
                prepared[ticker].append((nct, kind, term))
    if seen != set(originals_by_nct):
        raise ValueError("Incomplete original NCT program association")
    return dict(prepared)


def exact_text_mentions(text, terms):
    """Find bounded source-offset excerpts for exact terms, without legal inference."""
    if not isinstance(text, str) or len(text) > MAX_DOC_CHARS:
        raise ValueError("Invalid or unbounded SEC plain text")
    if not isinstance(terms, list):
        raise ValueError("Malformed issuer-specific terms")
    output = []
    for term in terms:
        if (not isinstance(term, tuple) or len(term) != 3
            or not isinstance(term[0], str) or not NCT_ID.fullmatch(term[0])
            or term[1] not in ("REGISTERED_DRUG_OR_BIOLOGIC", "REGISTERED_CONDITION")
            or not isinstance(term[2], str) or not 4 <= len(term[2]) <= 400):
            raise ValueError("Malformed term association")
        nct, kind, phrase = term
        # Distinguish e.g. AXB-1 from AXB-12. Registered exact text is
        # only a literal lexical hit, never confirmation of molecular alias.
        pattern = re.compile(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", re.I)
        match = pattern.search(text)
        if match is None:
            continue
        offset = match.start()
        left = max(0, offset - 65)
        right = min(len(text), match.end() + 65)
        output.append({
            "nct_id": nct,
            "term_kind": kind,
            "registered_term": phrase,
            "normalized_text_offset": offset,
            "context_excerpt": text[left:right][:EXCERPT_CHARS],
            "status": "EXACT_LEXICAL_MENTION_RESEARCH_ONLY_NO_RIGHTS_VERIFIED",
        })
        if len(output) == MAX_MENTIONS_PER_DOCUMENT:
            break
    output.sort(key=lambda x: (x["nct_id"], x["normalized_text_offset"], x["term_kind"]))
    return output
