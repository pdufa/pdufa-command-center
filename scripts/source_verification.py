"""Fresh, conservative verification of nightly source claims.

This module never changes candidate data, scores, financing sequence, or trade
eligibility. A reachable URL, an index, and a closing keyword are different
claims. Each result carries its scope, evidence, fetch time, and content hash.
"""
from __future__ import annotations

import csv
import hashlib
import html
import io
import json
import math
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

VERSION = 2
STATES = ("VERIFIED", "NOT_APPLICABLE", "UNAVAILABLE", "REVIEW_REQUIRED", "CONFLICT", "TECHNICAL_FAILURE")
FIELDS = ["event_key", "ticker", "category", "claim", "verification_status",
          "verification_required",
          "expected", "observed", "reason", "source_url", "source_sha256",
          "checked_at", "evidence", "claim_input_sha256", "monitor_index_sha256"]
MAX_BODY = 8_000_000
AGENT = "PDUFACommandCenter/1.0 source-verification"


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(value).hexdigest()


def read_rows(path):
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def scope_hash(events, companies):
    # Include evidence identity, not prices changed by the collectors.
    items = sorted((r.get("event_key", ""), r.get("ticker", ""),
                    r.get("drug", ""), r.get("indication", ""),
                    r.get("pdufa_date", "")) for r in events)
    registry = sorted((r.get("ticker", ""), r.get("cik10", "")) for r in companies)
    return digest(json.dumps([items, registry], separators=(",", ":")).encode())


def run_identity():
    return ":".join(os.environ.get(k, "local") for k in
                    ("GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT", "GITHUB_SHA"))


def normalized(text):
    return re.sub(r"[^a-z0-9]+", " ", str(text).lower()).strip()


def visible(raw):
    raw = re.sub(r"(?is)<script\b.*?</script>|<style\b.*?</style>", " ", raw)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]*>", " ", raw))).strip()


def dates(text):
    found = set()
    for token in re.findall(r"\b20\d{2}-\d{2}-\d{2}\b", text):
        try:
            found.add(date.fromisoformat(token).isoformat())
        except ValueError:
            pass
    pattern = (r"\b(?:January|February|March|April|May|June|July|August|September|"
               r"October|November|December|Jan\.?|Feb\.?|Mar\.?|Apr\.?|Jun\.?|"
               r"Jul\.?|Aug\.?|Sep\.?|Sept\.?|Oct\.?|Nov\.?|Dec\.?)"
               r"\s+\d{1,2},?\s+20\d{2}\b")
    for token in re.findall(pattern, text, re.I):
        token = re.sub(r"(?i)\bSept\.?(?=\s)", "Sep", token).replace(".", "")
        for fmt in ("%B %d, %Y", "%B %d %Y", "%b %d, %Y", "%b %d %Y"):
            try:
                found.add(datetime.strptime(token, fmt).date().isoformat())
                break
            except ValueError:
                pass
    return found


def target_dates(text):
    """Dates explicitly attached to the target, excluding release datelines."""
    date_pattern = (r"(?:20\d{2}-\d{2}-\d{2}|(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan\.?|Feb\.?|Mar\.?|Apr\.?|Jun\.?|Jul\.?|Aug\.?|Sep\.?|Sept\.?|Oct\.?|Nov\.?|Dec\.?)\s+\d{1,2},?\s+20\d{2})")
    markers = list(re.finditer(r"(?i)\b(?:PDUFA\s*\)?\s*(?:(?:goal|target|action)\s+){0,2}date|target\s+action\s+date|goal\s+date)\b", text))
    observed = set()
    for marker in markers:
        tail = text[marker.end():marker.end()+110]
        match = re.search(date_pattern, tail, re.I)
        if not match:
            continue
        bridge = tail[:match.start()]
        if re.fullmatch(r"(?i)[\s():,;-]*(?:(?:of|is|on|for|set|as|the|has|been|at|to|a|and|in|FDA|target)\b[\s():,;-]*)*", bridge):
            observed |= dates(match.group())
    # Compact primary statements such as "PDUFA November 1, 2026" are valid;
    # an arbitrary date elsewhere after a headline containing PDUFA is not.
    for match in re.finditer(r"(?i)\bPDUFA[\s():,-]+(?:(?:goal|target|action|deadline|date|of|is|on)\s+)*" + date_pattern, text):
        observed |= dates(match.group())
    return observed



def attributed_target_dates(event, passage):
    """Match each PDUFA date to the program text preceding THAT date.

    Investor releases can put multiple drug/date pairs into one sentence or
    HTML table row. The previous program's drug identity must not authorize
    the next program's goal date. We retain preceding program context until
    its own dated target, then reset for the next dated target.
    """
    date_rx = (r"(?:20\d{2}-\d{2}-\d{2}|"
               r"(?:January|February|March|April|May|June|July|August|September|"
               r"October|November|December|Jan\.?|Feb\.?|Mar\.?|Apr\.?|"
               r"Jun\.?|Jul\.?|Aug\.?|Sep\.?|Sept\.?|Oct\.?|Nov\.?|Dec\.?)"
               r"\s+\d{1,2},?\s+20\d{2})")
    markers = list(re.finditer(r"(?i)\b(?:PDUFA|target\s+action\s+date|goal\s+date)\b", passage))
    confirmed = set()
    prior_target_end = 0
    for marker in markers:
        tail = passage[marker.end():marker.end() + 110]
        dated = re.search(date_rx, tail, re.I)
        if not dated:
            continue
        end = marker.end() + dated.end()
        fragment = passage[prior_target_end:end]
        # The program identity and its indication must coexist before the
        # claimed date. The date must be explicitly tied to a target marker.
        if drug_matches(event, fragment) and indication_matches(event, fragment):
            claimed = target_dates(fragment)
            confirmed |= claimed & dates(dated.group())
        prior_target_end = end
    return confirmed


def exact_mapped_primary_target(event, plain, expected, anchor, context_chars=1000):
    """Narrow recovery for vetted exact-event issuer target wording.

    A manually mapped phrase is a discovery *locator*, never a verification
    override. The source must be fetched anew by Verifier.document, the exact
    claim and date must appear, the same nearby text must identify the drug
    and indication, and the document may not have conflicting explicit dated
    PDUFA targets. Source URL, content hash, and observation are preserved by
    Verifier.result. No future FDA approval or trade conclusion is inferred.
    """
    if not (type(context_chars) is int and 400 <= context_chars <= 2400
            and isinstance(anchor, str) and 24 <= len(anchor) <= 240
            and isinstance(expected, str) and expected in dates(anchor)
            and re.search(r"(?i)\bPDUFA\b|target\s+action\s+date", anchor)
            and company_matches(event, plain)):
        return ""
    explicit = target_dates(plain)
    if explicit != {expected}:
        return ""
    clean = re.sub(r"\s+", " ", plain)
    phrase = re.sub(r"\s+", " ", anchor).strip()
    matches = list(re.finditer(re.escape(phrase), clean, re.I))
    for match in matches[:10]:
        # Different release headings may put the named drug and condition
        # immediately before OR after the FDA-target sentence.
        start = max(0, match.start() - context_chars)
        end = min(len(clean), match.end() + 1000)
        around = clean[start:end]
        if context_chars > 1000:
            # A broad association is permitted only when the verified issuer's
            # source explicitly identifies this as its SOLE development program.
            # Reject a company's multiple-drug pipeline crossing date contexts.
            sole = re.search(r"(?i)\bour sole program\b.{0,120}", around)
            if not sole or not drug_matches(event, sole.group()):
                continue
        if drug_matches(event, around) and indication_matches(event, around):
            # Nearby explicit dates must still be the SAME claim. Do not
            # borrow a second program's separate PDUFA action date.
            if target_dates(around) != {expected}:
                continue
            return clean[max(0, match.start() - 330):min(len(clean), match.end() + 400)]
    return ""


def mapped_issuer_release_dateline(event, plain, expected_date):
    """Verify a mapped issuer's article-header publication date, not PDUFA date.

    Only used for exact-event mapped links when generic metadata is absent.
    The title/header must independently name the company, drug, indication,
    and a single dated release before the news body. The mapped date is a
    candidate to check in fetched primary text, not sufficient proof itself.
    """
    if (not isinstance(expected_date, str) or len(expected_date) != 10
            or not expected_date in dates(plain[:750])):
        return set()
    header = plain[:750]
    found = dates(header)
    disease = normalized(re.sub(r"\([^)]*\)", "", event.get("indication", "")))
    required_disease_tokens = {token for token in disease.split()
                               if len(token) >= 4 and token not in {"with", "and", "the", "for", "patients", "adults"}}
    header_tokens = set(normalized(header).split())
    if (not required_disease_tokens or not required_disease_tokens <= header_tokens
            or found != {expected_date}
            or not re.search(r"(?i)press release|corporate news details", header[:450])
            or not company_matches(event, header)
            or not drug_matches(event, header)
            or not indication_matches(event, header)):
        return set()
    try:
        if date.fromisoformat(expected_date) > date.today():
            return set()
    except ValueError:
        return set()
    return {expected_date}


def documented_fda_signed_approval(event, text):
    """Require an exact signed FDA approval, not an issuer publication date."""
    if (not re.search(r"(?i)\bSUPPLEMENT APPROVAL\b", text)
            or not re.search(r"(?i)\bit is approved,\s*effective\s+on\s+the\s+date\s+of\s+this\s+letter\b", text)
            or not company_matches(event, text)
            or not drug_matches(event, text)
            or not indication_matches(event, text)
            # A supplement action letter must name the full disease: an
            # abbreviation alone may refer to a different application.
            or normalized(re.sub(r"\s*\([^)]*\)", "", event.get("indication", "")))
               not in normalized(text)
            or not re.search(r"(?i)\bSignature Page\s+1\s+of\s+1\b", text)):
        return None
    signature = text.rsplit("Signature Page", 1)[-1]
    if not re.search(r"(?is)electronic\s+record.{0,140}\bsigned\s+electronically\b", signature):
        return None
    matches = re.findall(
        r"\b(0[1-9]|1[0-2])/([0-2]\d|3[01])/(20\d{2})\s+"
        r"\d{1,2}:\d{2}:\d{2}\s*(?:AM|PM)\b", signature, re.I)
    if len(matches) != 1:
        return None
    month, day, year = matches[0]
    try:
        return datetime.strptime(f"{year}-{month}-{day}", "%Y-%m-%d").date().isoformat()
    except ValueError:
        return None



def documented_fda_signed_original_bla_approval(event, url, text):
    """Accept an original BLA only with a signed, exact-product FDA letter.

    A page about approval, a public release date, or a pending PDUFA date is
    never proof. Tie the PDF application number to its letter header, the
    issuer and therapeutic indication to its LICENSING section, and the
    approval effective date to its unique electronic FDA signature.
    """
    path = urllib.parse.urlsplit(url).path
    app = re.fullmatch(
        r"/drugsatfda_docs/appletter/20\d{2}/(\d{6})Orig1s000ltr\.pdf",
        path, re.I)
    if not app or not re.search(r"(?i)\bBLA\s+" + re.escape(app.group(1)) + r"\b", text[:350]):
        return None
    header = text[:1300]
    if (not re.search(r"(?i)\bBLA APPROVAL\b", header)
            or not company_matches(event, header)
            or not drug_matches(event, header)):
        return None
    # Original BLA letters place the licensed drug and indication within
    # the actual LICENSING paragraph; never borrow mentions elsewhere in a
    # long letter or an unrelated supplement.
    match = re.search(
        r"(?is)\bLICENSING\b(.{1,2800}?)\bMANUFACTURING LOCATIONS\b", text)
    licensing = match.group(1) if match else ""
    # Two shared support-treatment tokens (e.g. "SMN2 targeted") cannot
    # substitute for the disease named on the actual authorization.
    disease = normalized(str(event.get("indication", "")).split(";", 1)[0]).strip()
    if (not licensing or len(disease) < 4
            or disease not in normalized(licensing)
            or not company_matches(event, licensing)
            or not drug_matches(event, licensing)
            or not indication_matches(event, licensing)
            or not re.search(r"(?i)\b(?:license authorizes|authorized to manufacture)\b", licensing)
            or not re.search(r"(?is)\bAPPROVAL\s*&\s*LABELING\b.{0,500}"
                             r"\bit is approved,\s*effective\s+on\s+the\s+date\s+of\s+this\s+letter\b", text)):
        return None
    if len(re.findall(r"(?i)\bSignature Page\s+1\s+of\s+1\b", text)) != 1:
        return None
    signature = text.rsplit("Signature Page", 1)[-1]
    if not re.search(r"(?is)electronic\s+record.{0,140}\bsigned\s+electronically\b", signature):
        return None
    matches = re.findall(
        r"\b(0[1-9]|1[0-2])/([0-2]\d|3[01])/(20\d{2})\s+"
        r"\d{1,2}:\d{2}:\d{2}\s*(?:AM|PM)\b", signature, re.I)
    if len(matches) != 1:
        return None
    month, day, year = matches[0]
    try:
        return datetime.strptime(f"{year}-{month}-{day}", "%Y-%m-%d").date().isoformat()
    except ValueError:
        return None


def documented_pdufa_extension(event, text):
    """Require one issuer-documented FDA extension from a prior date to a new date.

    A document containing different PDUFA dates alone cannot supersede a
    conflict. The FDA-extension statement, exact drug, disease and both dated
    endpoints must occur in the same local passage.
    """
    day = (r"(?:20\d{2}-\d{2}-\d{2}|"
           r"(?:January|February|March|April|May|June|July|August|September|"
           r"October|November|December)\s+\d{1,2},?\s+20\d{2})")
    pattern = r"(?i)\bfrom\s+(" + day + r")\s+to\s+(" + day + r")"
    for match in re.finditer(pattern, text):
        start = max(0, match.start() - 480)
        passage = text[start:match.end() + 80]
        prefix = text[start:match.start()]
        # Hypothetical wording such as "FDA might extend" is NOT an action.
        # Require an asserted past-tense FDA extension before using new dates.
        if (not re.search(r"(?i)\b(?:the\s+)?FDA\)?\s+(?:has\s+)?extended\b", prefix)
                or not re.search(r"(?i)\bPDUFA\b|Prescription Drug User Fee Act", prefix)
                or not drug_matches(event, passage)
                or not indication_matches(event, passage)):
            continue
        # Parenthetical disease acronyms cannot override a different spelled-
        # out diagnosis (e.g., "spinal muscular atrophy (DMD)" is not Duchenne).
        # A changed FDA target requires the expanded disease name in the same
        # local passage; acronym-only claims remain REVIEW/CONFLICT.
        raw_indication = str(event.get("indication", ""))
        if re.search(r"\([A-Za-z][A-Za-z0-9/-]{2,12}\)", raw_indication):
            expanded = normalized(re.sub(r"\([^)]*\)", "", raw_indication)).strip()
            if expanded and not re.search(
                    r"(?<!\w)" + re.escape(expanded) + r"(?!\w)", normalized(passage)):
                continue
        old, new = dates(match.group(1)), dates(match.group(2))
        if len(old) == len(new) == 1 and next(iter(old)) < next(iter(new)):
            return next(iter(old)), next(iter(new)), passage
    return None


def drug_matches(event, text):
    # Explicit combination drugs must be present together in one local
    # context. Splitting '+' into independent aliases would be unsafe:
    # seeing component A elsewhere on a company page cannot prove A+B.
    raw_drug = str(event.get("drug", ""))
    if re.search(r"\s\+\s", raw_drug):
        components = [normalized(part) for part in re.split(r"\s*\+\s*", raw_drug)]
        if not (2 <= len(components) <= 4 and
                all(len(component) >= 3 for component in components)):
            return False
        body = normalized(text)
        patterns = [components, list(reversed(components))]
        return any(bool(re.search(
            r"(?<!\w)" + r"\b.{0,180}\b".join(map(re.escape, parts)) + r"(?!\w)",
            body)) for parts in patterns)
    # Full names/codes and explicitly supplied parenthetical aliases only.
    parts = re.split(r"[()/|;]", event.get("drug", ""))
    parts += re.split(r"[|;]", event.get("drug_aliases", ""))
    # Delivery/dose suffixes are not part of the active drug identity. Keep
    # combination partners intact, and still require the exact indication.
    parts += [re.sub(r"(?i)\s+(?:PDT|HCl|immediate-release|cream\s+[\d.]+%|ophthalmic solution\s+[\d.]+%)$", "", p.strip()) for p in parts]
    for part in parts:
        part = normalized(part)
        if len(part) >= 4 and part not in {"pdt", "injection", "tablets", "oral"}:
            if re.search(r"(?<!\w)" + re.escape(part) + r"(?!\w)", normalized(text)):
                return True
    return False


def indication_matches(event, text):
    raw_source = str(text)
    stop = {"patients", "adults", "adult", "children", "treatment", "therapy",
            "with", "and", "the", "for", "age", "years", "including"}
    indication = re.sub(r"\bnonadvanced\b", "non advanced", normalized(event.get("indication", "")))
    text = re.sub(r"\bnonadvanced\b", "non advanced", normalized(text))
    tokens = {x for x in indication.split()
              if len(x) >= 4 and x not in stop}
    body = set(normalized(text).split())
    if re.search(r"\bnon\s*advanced\b", indication):
        if not re.search(r"\bnon\s*advanced\b", normalized(text)):
            return False
    qualifiers = tokens & {"advanced", "nonadvanced", "severe", "chronic", "acute"}
    if "advanced" in qualifiers:
        if re.search(r"\bnon\s+advanced\b", indication):
            qualifiers.discard("advanced")
        elif not re.search(r"\badvanced\b", re.sub(r"\bnon\s+advanced\b", "nonadvanced", text)):
            return False
    if not qualifiers <= body:
        return False
    # Reject contradictory parenthetical expansions BEFORE generic token
    # overlap can certify the wrong disease (e.g. spinal atrophy (DMD)).
    for acronym in re.findall(
        r"\(([A-Za-z][A-Za-z0-9/-]{2,12})\)",
        str(event.get("indication", "")),
    ):
        expansions = re.findall(
            r"(?i)\b((?:[A-Za-z]+\s+){1,7}[A-Za-z]+)\s*\(\s*"
            + re.escape(acronym) + r"\s*\)",
            raw_source,
        )
        # The acronym is not part of its own spelled-out disease name.
        # IgAN has one informative full-name token ("nephropathy"),
        # while DMD has three ("duchenne muscular dystrophy").
        disease_tokens = tokens - {normalized(acronym)}
        if expansions and disease_tokens and not any(
            len(disease_tokens & set(normalized(expansion).split()))
            >= min(2, len(disease_tokens)) for expansion in expansions
        ):
            return False
    if bool(tokens) and len(tokens & body) >= min(2, len(tokens)):
        return True
    # A program's explicit parenthetical indication abbreviation is a
    # source-provided alias, not an inferred disease match. For example,
    # "autosomal dominant hypocalcemia type 1 (ADH1)" may appear as "ADH1"
    # in a later sentence in the same SEC exhibit. The caller must still
    # independently match the drug, the relevant passage and the dated claim.
    explicit = str(event.get("indication_aliases", "")).split("|")
    if any(len(normalized(alias)) >= 6 and normalized(alias) in text for alias in explicit if alias.strip()):
        return True
    aliases = re.findall(r"\(([A-Za-z][A-Za-z0-9/-]{2,12})\)", str(event.get("indication", "")))
    for alias in aliases:
        clean_alias = normalized(alias)
        if (len(clean_alias) < 3 or clean_alias in {"fda", "usa"}
                or clean_alias not in body):
            continue
        # A source that explicitly expands an acronym to a *different*
        # disease is contradictory, not a positive indication match.
        # Abbreviations used independently (without an expansion) retain
        # their established exact-token matching behavior.
        expansions = re.findall(
            r"(?i)\b((?:[A-Za-z]+\s+){1,7}[A-Za-z]+)\s*\(\s*"
            + re.escape(alias) + r"\s*\)", raw_source)
        if expansions and not any(
            len(tokens & set(normalized(expansion).split()))
            >= min(2, len(tokens)) for expansion in expansions
        ):
            continue
        return True
    return False


def company_matches(event, text):
    # SEC legal registrant names sometimes append incorporation jurisdiction:
    # "VERTEX PHARMACEUTICALS INC / MA". A trailing US state is metadata,
    # not a word the issuer's own press release must contain.
    company_name = re.sub(
        r"(?i)\s*/\s*(?:AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|"
        r"KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|"
        r"OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY|DC)\s*$",
        "", str(event.get("company", "")))
    stop = {"inc", "incorporated", "corp", "corporation", "co", "company",
            "limited", "ltd", "plc", "holdings", "holding", "group",
            "pharma", "pharmaceutical", "pharmaceuticals", "therapeutics"}
    tokens = [x for x in normalized(company_name).split() if x not in stop]
    return bool(tokens) and all(x in normalized(text).split() for x in tokens)


def publication_dates(raw, plain):
    metadata = set(re.findall(r'(?i)"datePublished"\s*:\s*"(20\d{2}-\d{2}-\d{2})', raw))
    metadata |= set(re.findall(r'(?i)<time[^>]*datetime=["\'](20\d{2}-\d{2}-\d{2})', raw))
    metadata |= set(re.findall(r'(?i)<meta[^>]*property=["\']article:published_time["\'][^>]*content=["\'](20\d{2}-\d{2}-\d{2})', raw))
    if metadata:
        return metadata
    # Official investor-release date fields are publication metadata, unlike
    # arbitrary dates in a pipeline paragraph or a page footer.
    published_fields = re.findall(
        r'(?is)<(?:div|span)[^>]*class=["\'][^"\']*'
        r'(?:field--name-field-nir-news-date|news-details-date|article-time)'
        r'[^"\']*["\'][^>]*>(.*?)</(?:div|span)>', raw)
    if published_fields:
        dated = set().union(*(dates(visible(field)) for field in published_fields))
        if dated:
            return dated
    # Require a press-release dateline marker rather than any early date;
    # a future PDUFA target in the headline is not a release date.
    # Require a named wire service next to a published date. A PDUFA date
    # followed by "--", an em dash, or "(approval target)" is NOT a dateline.
    marker = re.search(
        r"(?i)((?:January|February|March|April|May|June|July|August|September|"
        r"October|November|December|Jan\.?|Feb\.?|Mar\.?|Apr\.?|"
        r"Jun\.?|Jul\.?|Aug\.?|Sep\.?|Sept\.?|Oct\.?|Nov\.?|Dec\.?)"
        r"\s+\d{1,2},\s+20\d{2})\s*"
        r"(?:\(\s*(?:GLOBE NEWSWIRE|BUSINESS WIRE|PRNEWSWIRE|ACCESSWIRE)\s*\)|/PRNewswire)",
        plain[:6000])
    if marker:
        return dates(marker.group(1))
    # SEC-filed company press releases often use a conventional dateline
    # such as "SOUTH SAN FRANCISCO, Calif., May 5, 2026 -". A bare
    # "PDUFA November 14, 2026 - ..." is NOT a publication dateline.
    month = (r"(?:January|February|March|April|May|June|July|August|September|"
             r"October|November|December|Jan\.?|Feb\.?|Mar\.?|Apr\.?|"
             r"Jun\.?|Jul\.?|Aug\.?|Sep\.?|Oct\.?|Nov\.?|Dec\.?)")
    dateline = re.search(
        r"(?i)\b[A-Z]{2,}(?:\s+[A-Z]{2,}){0,3},\s*(?:[A-Z][a-z]+\.?,\s*)?"
        + r"\(?" + "(" + month + r"\s+\d{1,2},\s+20\d{2})" + r"\)?\s+[-–—]\s",
        plain[:6000])
    if dateline:
        return dates(dateline.group(1))
    # Legitimate issuer releases syndicated by Business Wire use
    # "BOSTON--(BUSINESS WIRE)--Jun. 1, 2026--" or
    # "ALAMEDA, Calif.--(BUSINESS WIRE)--Feb. 2, 2026--".
    # A bare PDUFA target date is never a publication dateline.
    wire = re.search(
        r"(?i)\b[A-Z][A-Z ]{2,35}(?:,\s*[A-Z][a-z]{2,15}\.)?--"
        r"\((?:BUSINESS WIRE|GLOBE NEWSWIRE)\)--\s*("
        + month + r"\s+\d{1,2},\s+20\d{2})--",
        plain[:6000])
    if wire:
        return dates(wire.group(1))
    # A named-city issuer dateline can follow BUSINESS WIRE and have
    # ampersands in the city, e.g. SHANGHAI & CAMBRIDGE, Mass., August 6.
    city = re.search(r"(?i)\b[A-Z][A-Z &]{2,45},\s*(?:[A-Z][a-z]+\.?,\s*)?"
                     + r"\(?((?:" + month + r")\s+\d{1,2},\s+20\d{2})\)?\s+--", plain[:6000])
    return dates(city.group(1)) if city else set()


def numeric(value):
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value))


class SourceUnavailable(RuntimeError):
    pass


class IdentityConflict(ValueError):
    pass


FINANCIAL_FORMS = {"10-Q", "10-K", "10-Q/A", "10-K/A", "10-QT", "10-KT",
                   "10-QT/A", "10-KT/A", "20-F", "20-F/A", "40-F", "40-F/A", "6-K"}


def financial_snapshot(payload, cik, as_of):
    """One cash definition and aligned reporting periods for collection/review."""
    if not isinstance(payload, dict) or str(payload.get("cik", "")).zfill(10) != cik:
        raise IdentityConflict("Companyfacts CIK mismatch")
    cutoff = as_of.isoformat()
    def values(taxonomy, tag):
        items = payload.get("facts", {}).get(taxonomy, {}).get(tag, {}).get("units", {}).get("USD", [])
        result = []
        for row in items:
            try:
                end, filed = date.fromisoformat(row["end"]), date.fromisoformat(row["filed"])
                if (row.get("form") in FINANCIAL_FORMS and numeric(row.get("val"))
                        and end <= filed <= as_of
                        and re.fullmatch(r"\d{10}-\d{2}-\d{6}", row.get("accn", ""))):
                    result.append(row)
            except (ValueError, KeyError, TypeError):
                continue
        return result
    choices = []
    for taxonomy, tag, basis in (
        ("us-gaap", "CashAndCashEquivalentsAtCarryingValue", "CASH_EQUIVALENTS"),
        ("ifrs-full", "CashAndCashEquivalents", "CASH_EQUIVALENTS"),
        ("us-gaap", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents", "CASH_INCLUDING_RESTRICTED"),
    ):
        for row in values(taxonomy, tag):
            if row["val"] >= 0 and (as_of - date.fromisoformat(row["end"])).days <= 180:
                choices.append((row, taxonomy, tag, basis))
    if not choices:
        raise ValueError("No current nonnegative USD cash fact with a filing accession")
    # Prefer the newest period, and exact cash equivalents over restricted cash
    # in the SAME period. Never choose the largest balance or a stale exact tag.
    cash, taxonomy, tag, basis = max(choices, key=lambda x: (
        x[0]["end"], x[3] == "CASH_EQUIVALENTS", x[0]["filed"]))
    flows = []
    flow_tag = "NetCashProvidedByUsedInOperatingActivities" if taxonomy == "us-gaap" else "CashFlowsFromUsedInOperatingActivities"
    for row in values(taxonomy, flow_tag):
        try:
            days = (date.fromisoformat(row["end"]) - date.fromisoformat(row["start"])).days + 1
            if row["end"] == cash["end"] and row["accn"] == cash["accn"] and 60 <= days <= 380:
                flows.append((days, row))
        except (ValueError, KeyError, TypeError):
            continue
    aligned = min(flows, key=lambda x: x[0]) if flows else None
    return {"cash": cash, "cash_basis": basis, "taxonomy": taxonomy, "cash_tag": tag,
            "flow": aligned[1] if aligned else None, "flow_days": aligned[0] if aligned else None}


def validate_submissions(payload, cik, ticker):
    if not isinstance(payload, dict) or str(payload.get("cik", "")).zfill(10) != cik:
        raise IdentityConflict("SEC response CIK does not match registry CIK")
    tickers = payload.get("tickers")
    if not isinstance(tickers, list) or ticker.upper() not in [str(t).upper() for t in tickers]:
        raise IdentityConflict("SEC response does not identify the requested ticker")
    recent = payload.get("filings", {}).get("recent")
    required = ("form", "filingDate", "accessionNumber", "primaryDocument")
    if not isinstance(recent, dict) or any(not isinstance(recent.get(k), list) for k in required):
        raise ValueError("SEC recent-filings schema is incomplete")
    lengths = {len(recent[k]) for k in required}
    if len(lengths) != 1 or not recent["form"]:
        raise ValueError("SEC recent-filings arrays are empty or inconsistent")
    for filed, accession, document in zip(recent["filingDate"], recent["accessionNumber"], recent["primaryDocument"]):
        date.fromisoformat(filed)
        if not re.fullmatch(r"\d{10}-\d{2}-\d{6}", accession):
            raise ValueError("SEC filing identity is malformed")
        # Legacy EDGAR records legitimately omit primaryDocument. Their dated
        # accession still belongs in an inventory; it cannot be fetched as an
        # empty document or prove a closing. Keep rejecting inconsistent arrays.
        if not isinstance(document, str):
            raise ValueError("SEC primary-document field is malformed")
    return recent


def sec_url_matches(url, cik):
    parsed = urllib.parse.urlsplit(url)
    host = (parsed.hostname or "").lower()
    if host not in {"www.sec.gov", "sec.gov"} or not cik or not cik.isdigit():
        return False
    match = re.match(r"/Archives/edgar/data/(\d+)/\d{18}/[^/]+$", parsed.path, re.I)
    return bool(match and int(match.group(1)) == int(cik))



def documented_preferred_share_purchase(text, closing_date):
    """Strict SEC 8-K fallback for dated, completed preferred-share purchase.

    A purchase agreement, future issuance, closing target, or term sheet does
    not prove funds were received. Require a dated actual Closing Date,
    past-tense Purchasers purchased shares, and an explicit dollar aggregate.
    This only verifies the specific closing, never financing #2 or entry.
    """
    for match in re.finditer(r"(?i)\bclosing\s+date\b", text):
        passage = text[max(0, match.start() - 95):match.end() + 1000]
        if closing_date not in dates(passage):
            continue
        # Look for a real completed acquisition of issued preferred shares,
        # not statements that buyers MAY purchase shares in the future.
        bought = re.search(r"(?i)\bpurchasers?\s+purchased\s+an?\s+aggregate\s+of\s+[\d,]+\s+shares\b", passage)
        price = re.search(r"(?i)\baggregate\s+purchase\s+price\s+of\s*\$\s*[\d,]+(?:\.\d+)?\b", passage)
        if not bought or not price or price.start() < bought.end():
            continue
        if not re.search(r"(?i)\bpreferred\s+stock\b", passage[:price.end()]):
            continue
        # Ensure the purchase follows (rather than precedes) the same dated
        # Closing Date anchor, so an unrelated historical purchase cannot pass.
        if bought.start() < match.end() - max(0, match.start() - 95):
            continue
        return passage[:price.end()]
    return ""





def documented_closed_preferred_placement(text, closing_date):
    """A completed preferred placement in a dated SEC-filed proxy statement.

    Some issuers file a proxy AFTER closing an earlier announced placement,
    saying 'the closing of the Private Placement occurred on DATE'. Require
    the same local passage to name issued preferred shares and actual gross
    proceeds. An agreement to issue, forecast closing, subscription, ATM or
    option alone never qualifies. The SEC issuer CIK is checked by the caller.
    """
    month = r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
    date_rx = r"(?:20\d{2}-\d{2}-\d{2}|" + month + r"\s+\d{1,2},?\s+20\d{2})"
    pattern = (
        r"(?i)\bthe\s+closing\s+of\s+the\s+private\s+placement\s+"
        r"occurred\s+on\s+(" + date_rx + r")\b"
    )
    for match in re.finditer(pattern, text):
        if dates(match.group(1)) != {closing_date}:
            continue
        # Look back only to the most recent description of THIS named placement.
        start = max(0, match.start() - 1300)
        passage = text[start:match.end()]
        # Constrain the amount to the same local preferred-share placement,
        # never an unrelated financing elsewhere in a long proxy statement.
        if not re.search(r"(?i)\b(?:preferred\s+shares|class\s+a\s+preferred\s+stock)\b", passage):
            continue
        funded = re.search(
            r"(?i)\baggregate\s+gross\s+proceeds\s+(?:to\s+(?:us|the\s+company)\s+)?"
            r"(?:of|were)\s+\$\s*[\d,]+(?:\.\d+)?\s*(?:million|billion)\b",
            passage
        )
        if not funded or re.search(
            r"(?i)\b(?:expected|estimated|projected|potential)\s+$",
            passage[max(0, (funded.start() if funded else 0) - 25):(funded.start() if funded else 0)]
        ):
            continue
        if not re.search(r"(?i)\bfor\s+the\s+issuance\s+and\s+sale\b", passage):
            continue
        return passage[-1150:]
    return ""


def documented_released_final_tranche(text, closing_date):
    """Verify a final tranche actually released at a dated SEC-documented close.

    Restrict this to factual 'Closing releases final $X of $Y financing'
    disclosures alongside a stated completed transaction. A planned asset
    transfer or a future funding commitment alone is never funding proof.
    """
    expression = (
        r"(?i)\bclosing\s+releases?\s+(?:the\s+)?final\s+"
        r"\$\s*([\d,.]+)\s+(million|billion)\s+of\s+"
        r"\$\s*([\d,.]+)\s+(million|billion)\s+financing\b"
    )
    for match in re.finditer(expression, text):
        left = max(0, match.start() - 450)
        right = match.end() + 650
        passage = text[left:right]
        if closing_date not in dates(passage):
            continue
        try:
            amount = float(match.group(1).replace(",", ""))
            overall = float(match.group(3).replace(",", ""))
            scale = {"million": 1, "billion": 1000}
            tranche_m = amount * scale[match.group(2).lower()]
            total_m = overall * scale[match.group(4).lower()]
        except (ValueError, KeyError):
            continue
        if not 0 < tranche_m <= total_m:
            continue
        if not re.search(
                r"(?i)\b(?:announced\s+the\s+closing|"
                r"has\s+closed|closes\s+(?:the\s+)?purchase|"
                r"completed\s+(?:its\s+)?(?:restructuring|acquisition))\b",
                passage):
            continue
        if re.search(r"(?i)\b(?:expected|anticipated|proposed|planned|"
                     r"may|might|would|could)\s+(?:to\s+)?release\b",
                     passage[max(0, match.start() - left - 100):match.end() - left + 40]):
            continue
        return passage
    return ""


def documented_completed_public_equity_financing(text, closing_date):
    """Dated, already-completed public equity financing in an SEC-filed exhibit.

    A company's SEC exhibit may describe completed financing as 'public
    equity financing' rather than 'public offering'. Demand the same local
    sentence's exact historical close date and explicit USD gross proceeds.
    Never infer another separate closing, a second post-readout deal, or GEM
    eligibility from this single transaction.
    """
    month = r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
    dated = r"(?:20\d{2}-\d{2}-\d{2}|" + month + r"\s+\d{1,2},?\s+20\d{2})"
    pattern = (
        r"(?i)\bOn\s+(" + dated + r")[,\s]+(?:the\s+)?(?:Company|we)\s+"
        r"(?:completed|closed|consummated)\s+(?:its\s+|a\s+|the\s+)?"
        r"(?:public|registered\s+direct)\s+equity\s+financing\s+"
        r"for\s+(?:aggregate\s+)?gross\s+proceeds\s+of\s+"
        r"(?:approximately\s+|about\s+)?"
        r"\$\s*[\d,]+(?:\.\d+)?\s*(?:million|billion)\b"
    )
    for found in re.finditer(pattern, text):
        if dates(found.group(1)) != {closing_date}:
            continue
        # Restrict the proof to the dated, past-tense amount-bearing clause;
        # neighboring dates or proceeds from a different deal cannot qualify.
        passage = text[found.start():found.end()]
        if re.search(r"(?i)\b(?:expected|anticipated|proposed|planned|subject to)\b",
                     passage):
            continue
        return passage
    return ""


def documented_completed_eur_senior_notes(text, closing_date):
    """Completed EUR senior-note offering with same-dated SEC text and debt use.

    This is ONE issuer financing transaction. Original euros are retained;
    unrelated USD disclosures, pricing terms and senior-note forecasts never
    count. This is not proof of the second post-Phase-3 financing.
    """
    month = r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
    dated = r"(?:20\d{2}-\d{2}-\d{2}|" + month + r"\s+\d{1,2},?\s+20\d{2})"
    pattern = (
        r"(?i)\bOn\s+(" + dated + r")[,\s]+"
        r"(?P<issuer>[A-Za-z][A-Za-z.,&\s-]{2,90}\s*\([^)]{0,105}\))\s+"
        r"completed\s+a\s+public\s+offering\s+of\s+€\s*[\d,]+\s+"
        r"aggregate\s+principal\s+amount\s+of\s+(?:its|the)\s+"
        r"\d+(?:\.\d+)?%\s+Senior\s+Notes\s+due\s+20\d{2}\b"
    )
    for match in re.finditer(pattern, text):
        if dates(match.group(1)) != {closing_date}:
            continue
        passage = text[match.start():match.end() + 700]
        if re.search(r"(?i)\b(?:expected|anticipated|proposed|planned|will\s+complete)\b",
                     text[match.start():match.end()]):
            continue
        # Explicit planned debt-repayment use identifies this as refinancing
        # context rather than a program-specific equity infusion.
        if not re.search(r"(?i)\b(?:repayment|refinancing|refinance|repay)\b", passage):
            continue
        return passage[:1000]
    return ""


def documented_funded_transaction(text, closing_date):
    """Explicit dated securities sale, actual loan receipt, or closed placement.

    Require a local past-tense transaction, its own date and dollar amount.
    Agreement dates, quarter-end ATM totals, future closes and facility limits
    are insufficient. This never certifies a financing ordinal.
    """
    month = r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
    date_rx = r"(?:20\d{2}-\d{2}-\d{2}|" + month + r"\s+\d{1,2},?\s+20\d{2})"
    # A checked SEC 8-K may identify the issuer by corporate name followed by
    # "(the Company)" instead of spelling out "the Company" before its close.
    # The caller independently verifies the SEC archive CIK against the
    # requested ticker. Never promote a Google snippet or an SEC filing index.
    named_issuer = (
        r"(?:[A-Za-z][A-Za-z,.&\s-]{1,90}"
        r"\(\s*the\s+[\"'“”]?Company[\"'“”]?\s*\))"
    )
    for match in re.finditer(
        r"(?i)\bOn\s+(" + date_rx + r")[,\s]+"
        r"(?:(?:the\s+)?(?:Company|we)|" + named_issuer + r")\s+"
        r"(?:closed|completed|consummated)\s+(?:(?:its|the|an?)\s+)?"
        r"(?:(?:previously\s+announced|underwritten|upsized|public|private|"
        r"registered\s+direct|registered)\s+){0,6}"
        r"(?:offering|placement)\b", text
    ):
        if dates(match.group(1)) != {closing_date}:
            continue
        # Look only at the transaction being closed. When a periodic report
        # describes multiple dated completed offerings, don't borrow the next
        # offering's proceeds to validate the previous one.
        passage = text[match.start():match.end() + 1800]
        following = passage[match.end() - match.start():]
        next_close = re.search(
            r"(?i)\bOn\s+" + date_rx +
            r"[,\s]+.{0,140}?\b(?:closed|completed|consummated)\b", following
        )
        if next_close:
            passage = passage[:match.end() - match.start() + next_close.start()]
        if not re.search(r"(?i)\b(?:shares|stock|notes|securities)\b", passage):
            continue
        # Explicit dollar-denominated net/gross proceeds or issued note
        # principal amount, not shares outstanding or an announced capacity.
        actual_proceeds = re.search(
            r"(?i)\b(?:net|gross)\s+proceeds\b.{0,300}?"
            r"\$\s*[\d,]+(?:\.\d+)?\s*(?:million|billion)\b", passage
        )
        issued_principal = re.search(
            r"(?i)\$\s*[\d,]+(?:\.\d+)?\s*(?:million|billion)\s+"
            r"aggregate\s+principal\s+amount\s+of\s+"
            r"(?:[\d.]+%\s+)?(?:convertible\s+)?(?:senior\s+)?notes\b", passage
        )
        if not (actual_proceeds or issued_principal):
            continue
        if re.search(
            r"(?i)\b(?:net|gross)\s+proceeds\s+"
            r"(?:are|were|will\s+be)\s+expected\b", passage[:700]
        ):
            continue
        if re.search(
            r"(?i)\b(?:expects?\s+to|expected\s+to|subject\s+to)\s+"
            r"(?:close|complete|consummate)\b",
            passage[:match.end() - match.start()]
        ):
            continue
        return passage


    for match in re.finditer(r"(?i)\bOn\s+(" + date_rx + r")[,\s]+(?:the\s+)?(?:Company|we)\s+(received|sold)\b", text):
        passage = text[match.start():match.end() + 450]
        if dates(match.group(1)) != {closing_date}:
            continue
        if re.search(r"(?i)\b(?:will|may|expects?|expected|anticipated|proposed|planned|could|would)\b", passage[:180]):
            continue
        if not re.search(r"\$\s*[\d,]+(?:\.\d+)?\s*(?:million|billion)?", passage):
            continue
        if match.group(2).lower() == "received":
            if (not re.match(r"(?i)\s*\$\s*[\d,]+(?:\.\d+)?\s+(?:million|billion)\s+(?:from|under)\b", text[match.end():])
                    or not re.search(r"(?i)\b(?:tranche|loan|credit|financing)\b", passage)
                    or re.search(r"(?i)\b(?:undrawn|commitment|potential|available to borrow)\b", passage[:180])):
                continue
        elif not re.search(r"(?i)\b(?:shares|stock|warrants)\b", passage) or not re.search(r"(?i)\b(?:offering|placement)\b", passage):
            continue
        return passage
    for match in re.finditer(r"(?i)\b(?:private\s+placement|public\s+offering|offering|financing)\s+(?:was\s+)?(?:closed|completed|consummated)\s+on\s+(" + date_rx + r")", text):
        if dates(match.group(1)) != {closing_date}:
            continue
        passage = text[max(0,match.start()-100):match.end()+420]
        if re.search(r"(?i)\b(?:expected|anticipated|scheduled|proposed|planned)\b", text[max(0,match.start()-70):match.start()]):
            continue
        if re.search(r"\$\s*[\d,]+(?:\.\d+)?\s*(?:million|billion)?", passage) and re.search(r"(?i)\b(?:shares|stock|warrants|purchased|proceeds)\b", passage):
            return passage
    return ""


def documented_drawn_credit_tranche(text, closing_date):
    """Verify a funded debt draw at a dated credit-facility closing only.

    An undrawn facility limit is not financing proceeds. Demand an actual
    amount already "drawn on the Closing Date" within the dated SEC passage;
    later optional tranches must not be counted as funded.
    """
    for label in re.finditer(r"(?i)\bClosing\s+Date\b", text):
        start = max(0, label.start() - 130)
        passage = text[start:label.end() + 1050]
        if closing_date not in dates(passage):
            continue
        if not re.search(r"(?i)\b(?:credit\s+agreement|credit\s+facility)\b", passage):
            continue
        draws = re.finditer(
            r"(?i)\$\s*[\d,.]+\s+(?:million|billion)\s+drawn\s+on\s+the\s+Closing\s+Date\b",
            passage)
        for draw in draws:
            before = passage[max(0, draw.start() - 35):draw.start()]
            if re.search(r"(?i)\b(?:would|will|might|may|expected|potential|anticipated)\b", before):
                continue
            return passage[:draw.end()]
    # A disclosed debt-facility limit is not a completed funding.
    # Verify a specific past-tense cash borrowing on a named closing day.
    for match in re.finditer(
        r"(?i)\bOn\s+((?:20\d{2}-\d{2}-\d{2}|"
        r"(?:January|February|March|April|May|June|July|August|"
        r"September|October|November|December)\s+\d{1,2},?\s+20\d{2}))"
        r"\s*\(\s*the\s+[\u201c\u0022]?Amendment Closing Date"
        r"[\u201d\u0022]?\s*\)", text
    ):
        if dates(match.group(1)) != {closing_date}:
            continue
        passage = text[match.start():match.end() + 1000]
        if not re.search(r"(?i)\bLoan and Security Agreement\b", passage):
            continue
        funded = re.search(
            r"(?i)\bCompany\s+borrowed\s+one\s+of\s+the\s+additional\s+"
            r"loan\s+tranches\s+in\s+an\s+aggregate\s+principal\s+"
            r"amount\s+of\s+\$\s*[\d,.]+\s+(?:million|billion)"
            r"\s+on\s+the\s+Amendment Closing Date\b", passage
        )
        if not funded:
            continue
        prefix = passage[max(0, funded.start()-35):funded.start()]
        if re.search(r"(?i)\b(?:would|will|may|expected|potential|anticipated)\b", prefix):
            continue
        return passage[:funded.end()]
    return ""

# SEC may temporarily throttle or drop connections even after an HTTP retry.
# One additional recheck of the exact claim is permitted, with a strict
# per-run budget. Never retry a 403/401, missing user agent, actual evidence
# disagreement, or unproven financing transaction.
SEC_AUTO_RECOVERY_LIMIT = 8
SEC_TRANSIENT_ERROR = re.compile(
    r"(?i)^(?:HTTP_(?:408|429|500|502|503|504)|"
    r"URLError|TimeoutError|ConnectionResetError|ConnectionAbortedError|"
    r"ConnectionError|RemoteDisconnected)(?:\b|$)"
)


def retryable_sec_failure(row):
    """True only for SEC transport failures, never for missing evidence."""
    return (row.get("category") == "SEC"
            and row.get("verification_status") == "TECHNICAL_FAILURE"
            and bool(SEC_TRANSIENT_ERROR.search(str(row.get("reason", "")))))


def retry_sec_claim(row, retry, *, sleeper=None):
    """Reopen one exact SEC claim without changing proof or review policy.

    Caller enforces the global per-run limit, and the standard SEC verifier
    must re-fetch and re-validate issuer CIK, claim/date and source content.
    """
    if not retryable_sec_failure(row):
        return row, False
    (sleeper or time.sleep)(2)
    updated = retry()
    if not isinstance(updated, dict) or any(
            updated.get(k) != row.get(k) for k in ("event_key", "ticker", "category", "claim")):
        raise ValueError("Automatic SEC retry changed the claim identity")
    if updated.get("verification_status") == "VERIFIED" and not (
            updated.get("source_url") and re.fullmatch(
                r"[a-f0-9]{64}", str(updated.get("source_sha256", "")))):
        raise ValueError("Automatic SEC retry produced ungrounded verification")
    return updated, True


class Verifier:
    def __init__(self, companies, fetch=None, as_of=None, issuer_sources=None):
        self.companies = {r["ticker"].upper(): r for r in companies}
        self.fetcher = fetch or self.fetch
        self.as_of = as_of or datetime.now(timezone.utc).date()
        self.cache = {}
        self.sec_denials = 0
        self.issuer_sources = issuer_sources or {}
        self.issuer_document_cache = {}
        self.unavailable_providers = set()

    def fetch(self, url):
        host = (urllib.parse.urlsplit(url).hostname or "").lower()
        is_sec = host == "sec.gov" or host.endswith(".sec.gov")
        if is_sec and self.sec_denials >= 3:
            raise SourceUnavailable("SEC circuit breaker after three HTTP 403 responses")
        agent = os.environ.get("SEC_USER_AGENT", "").strip() if is_sec else AGENT
        if is_sec and not re.fullmatch(r".{3,120}\s+[^\s@]+@[^\s@]+\.[^\s@]+", agent):
            raise SourceUnavailable("An identifying SEC_USER_AGENT is required")
        request = urllib.request.Request(url, headers={"User-Agent": agent, "Accept": "*/*"})
        for attempt in range(2):
            try:
                with urllib.request.urlopen(request, timeout=18) as response:
                    final_host = (urllib.parse.urlsplit(response.geturl()).hostname or "").lower()
                    same_family = (final_host == host or
                                   is_sec and (final_host == "sec.gov" or final_host.endswith(".sec.gov")) or
                                   host.endswith("fda.gov") and (final_host == "fda.gov" or final_host.endswith(".fda.gov")))
                    if response.status != 200 or not same_family:
                        raise SourceUnavailable("HTTP response or redirect failed verification")
                    body = response.read(MAX_BODY + 1)
                    if not body.strip() or len(body) > MAX_BODY:
                        raise SourceUnavailable("Empty or oversized primary response")
                    if is_sec:
                        self.sec_denials = 0
                    return body
            except urllib.error.HTTPError as exc:
                if is_sec and exc.code == 403:
                    self.sec_denials += 1
                if attempt == 0 and exc.code in {429, 500, 502, 503, 504}:
                    time.sleep(1)
                    continue
                raise SourceUnavailable("HTTP_" + str(exc.code)) from exc
            except (TimeoutError, urllib.error.URLError) as exc:
                if attempt == 0:
                    time.sleep(1)
                    continue
                raise SourceUnavailable(type(exc).__name__) from exc
            finally:
                if is_sec:
                    time.sleep(0.15)

    def body(self, url):
        if url not in self.cache:
            try:
                body = self.fetcher(url)
                if not isinstance(body, bytes) or not body.strip() or len(body) > MAX_BODY:
                    raise SourceUnavailable("Empty, malformed, or oversized response")
                self.cache[url] = (body, utcnow())
            except Exception as exc:
                self.cache[url] = exc
        result = self.cache[url]
        if isinstance(result, Exception):
            raise result
        return result[0]

    def document(self, url):
        body = self.body(url)
        if body.startswith(b"%PDF"):
            from pypdf import PdfReader
            text = " ".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(body)).pages)
            return text, text
        raw = body.decode("utf-8", "replace")
        return raw, visible(raw)

    def result(self, event, category, claim, state, reason, url="", expected="", observed="", evidence="", required=True):
        cached = self.cache.get(url)
        return {"event_key": event.get("event_key", ""), "ticker": event.get("ticker", ""),
                "category": category, "claim": claim, "verification_status": state,
                "verification_required": "YES" if required else "NO",
                "expected": str(expected), "observed": str(observed), "reason": reason,
                "source_url": url, "source_sha256": digest(cached[0]) if isinstance(cached, tuple) else "",
                "checked_at": cached[1] if isinstance(cached, tuple) else utcnow(),
                "evidence": re.sub(r"\s+", " ", evidence)[:900]}

    def company(self, event):
        return self.companies.get(event.get("ticker", "").upper(), {})

    def cik(self, event):
        value = self.company(event).get("cik10", "").strip()
        return value.zfill(10) if value.isdigit() and int(value) else ""

    def submissions(self, event):
        cik = self.cik(event)
        if not cik:
            raise ValueError("Missing valid registry CIK")
        url = "https://data.sec.gov/submissions/CIK" + cik + ".json"
        payload = json.loads(self.body(url))
        return url, payload, validate_submissions(payload, cik, event["ticker"])

    def references(self, event):
        config = self.event_sources(event)
        mapped = config.get("urls", [])
        found = [event.get(k, "") for k in ("pdufa_evidence_url", "trial_evidence_url", "financing_evidence_url", "issuer_evidence_url")]
        for key in ("evidence_summary", "regulatory_summary"):
            found += re.findall(r"https://[^\s<>\"']+", event.get(key, ""))
        # Exact-event mappings supply discovery links, never expected values
        # or verification overrides. Inspect them before stale saved links.
        return list(dict.fromkeys(u.rstrip(".,;) ") for u in mapped + found if isinstance(u, str) and u))

    def event_sources(self, event):
        config = self.issuer_sources.get(event.get("ticker", "").upper(), {})
        return config.get("events", {}).get(event.get("event_key", ""), {})

    def mapped_event(self, event):
        result = dict(event)
        config = self.event_sources(event)
        for field in ("drug_aliases", "indication_aliases"):
            aliases = config.get(field, [])
            if isinstance(aliases, list) and all(isinstance(a, str) for a in aliases):
                result[field] = " | ".join([str(event.get(field, ""))] + aliases)
        return result

    def approval_label_context(self, event, url, plain):
        """Pair a letter with its exact application/supplement approved label.

        A response-data supplement may name the studies and use disease
        abbreviations. Its linked FDA label supplies the full indication.
        A label for a different application or supplement is never accepted.
        """
        label_url = self.event_sources(event).get("approval_label_url", "")
        letter = re.fullmatch(r"/drugsatfda_docs/appletter/(20\d{2})/(\d{6})Orig1s(\d{3})ltr\.pdf",
                              urllib.parse.urlsplit(url).path)
        label = re.fullmatch(r"/drugsatfda_docs/label/(20\d{2})/(\d{6})s(\d{3})lbl\.pdf",
                             urllib.parse.urlsplit(label_url).path)
        if (self.primary(event, url) != "FDA" or self.primary(event, label_url) != "FDA"
                or not letter or not label or letter.groups() != label.groups()
                or not re.search(r"\bNDA\s+" + letter.group(2) + r"/S-" + letter.group(3) + r"\b", plain)):
            return plain, ""
        _, label_text = self.document(label_url)
        if not drug_matches(event, label_text) or not indication_matches(event, label_text):
            return plain, ""
        return plain + " " + label_text, label_url

    def mapped_fda_action_applicant(self, event, url, letter_text, label_url):
        """Validate an exact FDA applicant-to-company crosswalk, never a broad alias.

        A licensed company can differ from the FDA applicant on a signed letter.
        Permit that only for a configured exact event/application/supplement, an
        independently matching FDA label, and a freshly checked company-owned
        announcement naming the same drug, indication and FDA approval.
        """
        config = self.event_sources(event)
        applicant = str(config.get("fda_regulatory_applicant", "")).strip()
        application = str(config.get("fda_application_number", "")).strip()
        supplement = str(config.get("fda_supplement_number", "")).strip()
        issuer_url = str(config.get("fda_issuer_approval_url", "")).strip()
        letter = re.fullmatch(
            r"/drugsatfda_docs/appletter/(20\\d{2})/(\\d{6})Orig1s(\\d{3})ltr\\.pdf",
            urllib.parse.urlsplit(url).path,
        )
        if (not applicant or not re.fullmatch(r"\\d{6}", application)
                or not re.fullmatch(r"\\d{3}", supplement)
                or not letter or letter.group(2) != application
                or letter.group(3) != supplement
                or not label_url or self.primary(event, url) != "FDA"
                or self.primary(event, label_url) != "FDA"
                or url not in config.get("urls", ())
                or not re.search(r"\\bNDA\\s+" + re.escape(application)
                                 + r"/S-" + re.escape(supplement) + r"\\b", letter_text)
                or not company_matches({"company": applicant}, letter_text[:1400])
                or issuer_url not in config.get("urls", ())
                or self.primary(event, issuer_url) != "ISSUER"):
            return ""
        # An arbitrary signed FDA letter is NOT proof of the tracked issuer's
        # program. Reopen the exact mapped issuer approval announcement.
        try:
            _, issuer_text = self.document(issuer_url)
        except Exception:
            return ""
        if (not company_matches(event, issuer_text)
                or not drug_matches(event, issuer_text)
                or not indication_matches(event, issuer_text)
                or not re.search(r"\\bFDA\\s+(?:has\\s+)?approved\\b",
                                 issuer_text, re.I)):
            return ""
        return applicant

    def primary(self, event, url):
        host = (urllib.parse.urlsplit(url).hostname or "").lower()
        if host == "fda.gov" or host.endswith(".fda.gov"):
            return "FDA"
        if sec_url_matches(url, self.cik(event)):
            return "SEC_ISSUER"
        config = self.issuer_sources.get(event.get("ticker", "").upper(), {})
        if host in config.get("hosts", []) and urllib.parse.urlsplit(url).scheme == "https":
            return "ISSUER"
        return ""

    def issuer_documents(self, event):
        """Saved primary references first, then bounded actual SEC exhibits."""
        yielded = set()
        for url in self.references(event):
            if self.primary(event, url) and url not in yielded:
                yielded.add(url)
                yield url
        cik = self.cik(event)
        if not cik:
            return
        if cik not in self.issuer_document_cache:
            _, _, recent = self.submissions(event)
            found = []
            indices = [i for i, form in enumerate(recent["form"])
                       if form in {"8-K", "8-K/A", "6-K"}
                       and recent["filingDate"][i] <= self.as_of.isoformat()][:8]
            for i in indices:
                acc = recent["accessionNumber"][i].replace("-", "")
                base = "https://www.sec.gov/Archives/edgar/data/" + str(int(cik)) + "/" + acc + "/"
                listing = json.loads(self.body(base + "index.json"))
                for item in listing.get("directory", {}).get("item", []):
                    name = item.get("name", "")
                    if (re.search(r"(?i)(?:ex[-_]?99|exhibit[-_]?99)", name)
                            and name.lower().endswith((".htm", ".html"))
                            and re.fullmatch(r"[A-Za-z0-9_.-]+", name)):
                        found.append(base + name)
                if len(found) >= 12:
                    break
            self.issuer_document_cache[cik] = found
        for url in self.issuer_document_cache[cik]:
            if url not in yielded:
                yield url

    def regulatory(self, event, _discovery_only=False):
        event = self.mapped_event(event)
        expected_outcome = event.get("outcome", "").strip().upper()
        claim = "FDA_DECISION" if expected_outcome in {"APPROVED", "CRL"} else "PDUFA_TARGET"
        expected = event.get("decision_date", "") if claim == "FDA_DECISION" else event.get("pdufa_date", "")
        refs = [u for u in self.references(event) if self.primary(event, u)]
        saved_refs = bool(refs)
        results = []
        # Empty saved references previously meant an event was never looked up.
        if not refs:
            try:
                refs = list(self.issuer_documents(event))[:12]
            except (ValueError, KeyError, TypeError) as exc:
                return [self.result(event, "FDA", claim, "REVIEW_REQUIRED", "Primary-source discovery requires review: " + str(exc), expected=expected)]
            except Exception as exc:
                return [self.result(event, "FDA", claim, "TECHNICAL_FAILURE", str(exc), expected=expected)]
        # A saved-link check stays small, but fresh SEC exhibit discovery
        # may need more than four exhibits to reach the relevant event.
        # Both paths remain strictly bounded and evidence-gated.
        for url in refs[:4 if saved_refs else 12]:
            try:
                _, plain = self.document(url)
                original_letter = plain
                label_url = ""
                mapped_applicant = ""
                if claim == "FDA_DECISION":
                    plain, label_url = self.approval_label_context(event, url, plain)
                    mapped_applicant = self.mapped_fda_action_applicant(
                        event, url, original_letter, label_url)
                if not drug_matches(event, plain) or not indication_matches(event, plain):
                    continue
                if (self.primary(event, url) in {"FDA", "ISSUER"}
                        and not company_matches(event, plain)
                        and not (self.primary(event, url) == "FDA" and mapped_applicant)):
                    continue
                application = event.get("application_number", "").strip()
                if application and not re.search(r"(?<!\d)" + re.escape(application) + r"(?!\d)", plain):
                    continue
                if claim == "PDUFA_TARGET":
                    extension = documented_pdufa_extension(event, plain)
                    if extension:
                        old_target, new_target, extension_passage = extension
                        status = "VERIFIED" if new_target == expected else "CONFLICT"
                        reason = ("Explicit dated FDA PDUFA extension supersedes " + old_target
                                  if status == "VERIFIED" else
                                  "Explicit FDA extension disagrees with the saved target date")
                        if status == "VERIFIED" and expected < self.as_of.isoformat():
                            status, reason = "REVIEW_REQUIRED", (
                                "Extended target date has passed; FDA decision still unverified")
                        results.append(self.result(event, "FDA", claim, status, reason,
                            url, expected, new_target, extension_passage))
                        continue
                    # Preserve semicolons within a program description,
                    # but assign target dates only to the corresponding program
                    # via attributed_target_dates; never borrow the next drug's date.
                    sections = re.split(r"\s*[•]\s*|(?<=[.!?])\s+(?=[A-Z])", plain)
                    sentences = []
                    for section in sections:
                        if len(section) > 1500:
                            # HTML menus and headings can precede a dateline
                            # without punctuation; limit identity to the claim.
                            sentences.extend(section[max(0, m.start()-650):m.end()+180]
                                for m in re.finditer(r"(?i)\bPDUFA\b|\btarget action date\b", section))
                        else:
                            sentences.append(section)
                    passages = []
                    for i, passage in enumerate(sentences):
                        if not re.search(r"(?i)\bPDUFA\b|\btarget action date\b", passage):
                            continue
                        context = passage
                        # A short continuation may inherit its preceding drug
                        # identity. Never borrow identity from the next program
                        # or from an explicit target for another indication.
                        if (not drug_matches(event, passage) and len(passage) <= 350
                                and re.match(r"(?i)^(?:the\s+)?(?:FDA\b|PDUFA\b)", passage.strip())
                                and not re.search(r"(?i)\bfor\b", passage)):
                            context = " ".join(sentences[max(0, i-1):i+1])
                        if drug_matches(event, context) and indication_matches(event, context):
                            passages.append(context)
                    observed = set().union(*(attributed_target_dates(event, p) for p in passages)) if passages else set()
                    if not observed and expected:
                        config = self.event_sources(event)
                        anchor = config.get("primary_target_anchor", "")
                        window = config.get("primary_target_context_window", 1000)
                        mapped_passage = exact_mapped_primary_target(
                            event, plain, expected, anchor, context_chars=window)
                        if mapped_passage:
                            results.append(self.result(
                                event, "FDA", claim, "VERIFIED",
                                "Exact-event primary issuer target date and program confirmed; "
                                "NOT a signed FDA decision", url, expected, expected,
                                mapped_passage))
                            continue
                    if not expected or not observed:
                        continue
                    state = "VERIFIED" if observed == {expected} else "CONFLICT"
                    reason = "Drug, indication and reported target date match primary evidence" if state == "VERIFIED" else "Primary target date disagrees or multiple dates need reconciliation"
                    if state == "VERIFIED" and expected < self.as_of.isoformat():
                        state, reason = "REVIEW_REQUIRED", "Original target date confirmed, but target has passed and the final outcome remains unresolved"
                    results.append(self.result(event, "FDA", claim, state, reason, url, expected, " | ".join(sorted(observed)), " | ".join(passages)))
                else:
                    # Official FDA-signed supplement letters state approval is
                    # effective on the date of the signed letter, not a press date.
                    signed_action = (
                        (documented_fda_signed_approval(
                            {**event, "company": mapped_applicant} if mapped_applicant else event,
                            plain)
                         or documented_fda_signed_original_bla_approval(event, url, plain))
                        if self.primary(event, url) == "FDA"
                        and url.lower().endswith(".pdf") else None)
                    if signed_action:
                        state = ("VERIFIED" if expected_outcome == "APPROVED"
                                 and (not expected or signed_action == expected) else "CONFLICT")
                        results.append(self.result(event, "FDA", claim, state,
                            ("Signed FDA approval effective on official letter date"
                             if state == "VERIFIED" else
                             "Signed FDA letter outcome or date contradicts saved event"),
                            url, expected_outcome + " " + expected,
                            "APPROVED " + signed_action,
                            "FDA signed supplement approval; effective on date of letter" +
                            ("; exact approved label " + label_url + " SHA256 " + digest(self.body(label_url)) if label_url else "")))
                        continue
                    # Action wording, identity and date must coexist locally;
                    # publication/modified dates never become decision dates.
                    passages = [plain[max(0, m.start()-120):m.end()+450]
                                for m in re.finditer(r"(?i)\bFDA\s+(?:has\s+)?approv(?:ed|es)\b|\bcomplete response letter\b", plain)]
                    for passage in passages:
                        if not drug_matches(event, passage) or "fda" not in passage.lower():
                            continue
                        outcome = "CRL" if re.search(r"(?i)complete response letter", passage) else "APPROVED"
                        if re.search(r"(?i)\b(?:previously|historically|could|might|may|expects?|anticipated|not approved)\b", passage):
                            continue
                        if outcome == "CRL" and not re.search(r"(?i)\b(?:received|issued|delivered)\b", passage):
                            continue
                        action_dates = dates(passage)
                        if not action_dates:
                            continue
                        state = "VERIFIED" if outcome == expected_outcome and len(action_dates) == 1 and (not expected or action_dates == {expected}) else "CONFLICT"
                        results.append(self.result(event, "FDA", claim, state,
                            "Event outcome and explicit action date match" if state == "VERIFIED" else "Outcome/action date conflict requires review",
                            url, expected_outcome + " " + expected, outcome + " " + " | ".join(sorted(action_dates)), passage))
            except (SourceUnavailable, urllib.error.URLError, TimeoutError) as exc:
                results.append(self.result(event, "FDA", claim, "TECHNICAL_FAILURE", str(exc), url, expected))
            except Exception as exc:
                results.append(self.result(event, "FDA", claim, "REVIEW_REQUIRED", "Unusable source: " + type(exc).__name__, url, expected))
        conflicts = [r for r in results if r["verification_status"] == "CONFLICT"]
        verified = [r for r in results if r["verification_status"] == "VERIFIED"]
        if conflicts and claim == "PDUFA_TARGET":
            # Explicit issuer-documented FDA amendments can supersede old
            # target dates within the SAVED primary records themselves.
            # Do not let an old primary release veto a newer verified extension,
            # but never resolve unrelated dates or a non-exact program.
            extensions = [
                r for r in verified if
                r["reason"].startswith("Explicit dated FDA PDUFA extension supersedes ")
            ]
            if (len(extensions) == 1 and
                    all(c["observed"] == extensions[0]["reason"].rsplit(" ", 1)[-1]
                        for c in conflicts)):
                return extensions
        if conflicts:
            if saved_refs and not _discovery_only and claim == "PDUFA_TARGET":
                # Only a *newer explicit extension* may supersede an older
                # primary-source target conflict. A second bare date, or a
                # different drug/program, cannot silently clear the conflict.
                discovery_event = dict(event)
                for key in ("pdufa_evidence_url", "trial_evidence_url",
                            "financing_evidence_url", "issuer_evidence_url",
                            "evidence_summary", "regulatory_summary"):
                    discovery_event[key] = ""
                discovered = self.regulatory(discovery_event, _discovery_only=True)
                if (discovered and discovered[0]["verification_status"] == "VERIFIED"
                        and discovered[0]["reason"].startswith(
                            "Explicit dated FDA PDUFA extension supersedes ")
                        and all(
                            c["observed"] == discovered[0]["reason"].rsplit(" ", 1)[-1]
                            for c in conflicts
                        )):
                    return discovered
            return conflicts[:1]
        if verified:
            return verified[:1]
        if saved_refs and not _discovery_only:
            # A saved primary URL can be legitimate but unrelated to this exact
            # regulatory claim. Retry discovery of recent company-matched SEC
            # exhibits only after saved URLs fail; never convert missing proof
            # into VERIFIED or overwrite an observed conflict.
            discovery_event = dict(event)
            for key in ("pdufa_evidence_url", "trial_evidence_url",
                        "financing_evidence_url", "issuer_evidence_url",
                        "evidence_summary", "regulatory_summary"):
                discovery_event[key] = ""
            discovered = self.regulatory(discovery_event, _discovery_only=True)
            if discovered and discovered[0]["verification_status"] in {"VERIFIED", "CONFLICT"}:
                return discovered
        return results[:1] or [self.result(event, "FDA", claim, "REVIEW_REQUIRED",
            "No primary source safely matches drug, indication, claim and explicit date", expected=expected)]

    def registry(self, company):
        event = {"ticker": company["ticker"], "event_key": "REGISTRY:" + company["ticker"]}
        url = "https://data.sec.gov/submissions/CIK" + self.cik(event) + ".json" if self.cik(event) else ""
        try:
            url, payload, recent = self.submissions(event)
            return self.result(event, "SEC", "FILINGS_INVENTORY", "VERIFIED",
                "CIK, ticker and nonempty filing arrays match; this verifies inventory only", url,
                self.cik(event), str(payload["cik"]).zfill(10), "Recent filings: " + str(len(recent["form"])))
        except IdentityConflict as exc:
            return self.result(event, "SEC", "FILINGS_INVENTORY", "CONFLICT", str(exc), url)
        except (ValueError, KeyError, TypeError) as exc:
            return self.result(event, "SEC", "FILINGS_INVENTORY", "REVIEW_REQUIRED", str(exc), url)
        except Exception as exc:
            return self.result(event, "SEC", "FILINGS_INVENTORY", "TECHNICAL_FAILURE", str(exc), url)

    def financing_target(self, event):
        url = event.get("financing_evidence_url", "")
        close = event.get("financing_close_date", "")
        review = event.get("_financing_review", {})
        if not close and review.get("second_financing_audit_status") == "VERIFIED_SECOND_POST_PHASE3_FINANCING":
            # A matching event ledger supplies a candidate to re-open, not proof.
            # Never borrow another company's or another program's financing.
            url = review.get("second_financing_source", "")
            close = review.get("second_financing_date", "")
        mapped_event = self.event_sources(event)
        mapped_exact = mapped_event.get("individual_financing_close", {})
        if (not event.get("financing_evidence_url")
                and not event.get("_recheck_exact_sec_url")
                and isinstance(mapped_exact, dict)
                and mapped_exact.get("date") and mapped_exact.get("sec_url")
                and sec_url_matches(mapped_exact["sec_url"], self.cik(event))):
            # Prefer a dated independently discovered SEC transaction when the
            # candidate itself has no explicit financing evidence. A *prior*
            # second-financing review can refer to a DIFFERENT, older deal and
            # must not hide this fresh primary-source candidate. This verifies
            # only this one exact transaction, never the older ledger's
            # closing day, its Phase-3 ordering or trade eligibility.
            close, url = mapped_exact["date"], mapped_exact["sec_url"]
        mapped = mapped_event.get("financing_urls", [])
        if isinstance(mapped, list) and mapped and close and not event.get("_recheck_exact_sec_url"):
            # A source replacement retains the saved closing date and exact
            # event. No company-wide later financing can supply that date.
            url = next((u for u in mapped if sec_url_matches(u, self.cik(event))), url)
        return url, close

    def financing(self, event):
        url, close = self.financing_target(event)
        if not sec_url_matches(url, self.cik(event)) or not close:
            return self.result(event, "SEC", "FINANCING_CLOSURE", "REVIEW_REQUIRED",
                "Closing requires a company-matched SEC document and an explicit closing date; index/keywords do not prove second-financing sequence", url, close)
        # A saved status or malformed date is missing proof, not a transport/parser
        # error. Fail closed before fetching SEC or attempting a technical retry.
        try:
            closed_on = date.fromisoformat(close)
        except (TypeError, ValueError):
            return self.result(event, "SEC", "FINANCING_CLOSURE", "REVIEW_REQUIRED",
                "Saved financing close date is not a valid calendar date; dated funded closing remains unverified", url, close)
        if closed_on > self.as_of:
            return self.result(event, 'SEC', 'FINANCING_CLOSURE', 'REVIEW_REQUIRED',
                'Saved closing date is in the future; funds received are not established', url, close)
        try:
            _, plain = self.document(url)
            completed = (documented_funded_transaction(plain, close)
                         or documented_completed_public_equity_financing(plain, close))
            if completed:
                return self.result(event, "SEC", "FINANCING_CLOSURE", "VERIFIED",
                    "Company-matched SEC document confirms this dated funded transaction only; not the post-Phase-3 second-financing sequence",
                    url, close, close, completed)
            eur_notes = documented_completed_eur_senior_notes(plain, close)
            if eur_notes:
                return self.result(event, "SEC", "FINANCING_CLOSURE", "VERIFIED",
                    "SEC issuer matches one completed EUR-denominated senior-notes offering in debt-refinancing context; NOT a second post-Phase-3 clinical-program financing",
                    url, close, close, eur_notes)
            preferred_placement = documented_closed_preferred_placement(plain, close)
            if preferred_placement:
                return self.result(event, "SEC", "FINANCING_CLOSURE", "VERIFIED",
                    "Same-issuer SEC proxy confirms one dated, completed preferred placement with gross proceeds; separate older financing ledgers, post-Phase-3 ordering and trade permission remain unverified",
                    url, close, close, preferred_placement)
            passages = [plain[max(0, m.start()-100):m.end()+350] for m in re.finditer(
                r"(?i)\b(?:closed|completed|consummated)\s+(?:its\s+|the\s+|a\s+)?(?:previously[-\s]+announced\s+)?(?:\$[\d,.]+\s+million\s+)?(?:public\s+|registered\s+direct\s+|private\s+)?(?:offering|financing|placement)\b", plain)]
            if not any(close in dates(p) for p in passages):
                completed_purchase = documented_preferred_share_purchase(plain, close)
                if completed_purchase:
                    return self.result(event, "SEC", "FINANCING_CLOSURE", "VERIFIED",
                        "Company-matched SEC filing confirms completed, dated preferred-share purchases and aggregate price; second post-Phase-3 financing order and dilution risk remain separate",
                        url, close, close, completed_purchase)
                released = documented_released_final_tranche(plain, close)
                if released:
                    return self.result(event, "SEC", "FINANCING_CLOSURE", "VERIFIED",
                        "Company-matched SEC exhibit documents a dated, completed transaction releasing the final financing tranche; only that tranche is verified, not the second post-Phase-3 financing sequence",
                        url, close, close, released)
                drawn = documented_drawn_credit_tranche(plain, close)
                if drawn:
                    return self.result(event, "SEC", "FINANCING_CLOSURE", "VERIFIED",
                        "SEC filing confirms this closing's actual funded credit-facility draw only; undrawn commitments, other tranches and post-Phase-3 financing sequence are NOT verified",
                        url, close, close, drawn)
                return self.result(event, "SEC", "FINANCING_CLOSURE", "REVIEW_REQUIRED",
                    "No completed transaction clause matches the stored closing date", url, close)
            from sec_financing_closure import candidates as closing_candidates
            clauses = [r["excerpt"] for r in closing_candidates({"text": plain})]
            matched = [p for p in clauses if dates(p) == {close} and re.search(r"\$\s*[\d,.]+\s*(?:million|billion)?", p)]
            if matched:
                return self.result(event, "SEC", "FINANCING_CLOSURE", "VERIFIED",
                    "Company-matched SEC document confirms a dated closing and financing amount; this verifies that closing only, not the post-Phase-3 second-financing sequence",
                    url, close, close, " | ".join(matched))
            # A closing can be real without being financing #2 after Phase 3.
            return self.result(event, "SEC", "FINANCING_CLOSURE", "REVIEW_REQUIRED",
                "Dated closing clause found; exact deal, proceeds and post-Phase-3 second-financing sequence still require adjudication",
                url, close, close, " | ".join(passages))
        except SourceUnavailable as exc:
            # Preserve the actual HTTP/transport code so bounded SEC recovery
            # can distinguish rate limits from permanent evidence gaps.
            return self.result(event, "SEC", "FINANCING_CLOSURE", "TECHNICAL_FAILURE", str(exc), url, close)
        except Exception as exc:
            return self.result(event, "SEC", "FINANCING_CLOSURE", "TECHNICAL_FAILURE", type(exc).__name__, url, close)

    def financial(self, event):
        cik = self.cik(event)
        url = "https://data.sec.gov/api/xbrl/companyfacts/CIK" + cik + ".json" if cik else ""
        if not cik:
            return [self.result(event, "FINANCIAL", "CASH_AND_RUNWAY", "REVIEW_REQUIRED", "Missing CIK")]
        try:
            payload = json.loads(self.body(url))
            try:
                snapshot = financial_snapshot(payload, cik, self.as_of)
            except IdentityConflict:
                raise
            except ValueError:
                # Use an explicitly reviewed interim SEC layout only after
                # Companyfacts identity was checked. Retain the reported
                # currency; do not relabel a native balance as USD. No guessed
                # reporting column, balance or operating cash flow is allowed.
                spec = self.issuer_sources.get(event['ticker'].upper(), {}).get('financial_report')
                if not spec or not sec_url_matches(spec.get('url', ''), cik):
                    raise
                raw, plain = self.document(spec['url'])
                if not company_matches(event, plain):
                    raise IdentityConflict('Interim financial report company mismatch')
                from scripts.financial_report_evidence import report_snapshot
                native = report_snapshot(raw, spec, self.as_of)
                accession = re.search(r'/data/\d+/(\d{18})/', spec['url']).group(1)
                accession = accession[:10] + '-' + accession[10:12] + '-' + accession[12:]
                cash_row = {'val': native['cash'], 'end': native['end'], 'accn': accession, 'currency': native['currency']}
                flow_row = {'val': native['flow'], 'start': native['start'], 'end': native['end'], 'accn': accession, 'currency': native['currency']}
                snapshot = {'cash': cash_row, 'flow': flow_row, 'flow_days': native['flow_days'],
                            'cash_basis': 'CASH_EQUIVALENTS', 'taxonomy': 'PRIMARY_' + native['currency'] + '_INTERIM_STATEMENT',
                            'cash_tag': spec['cash']['label']}
                url = spec['url']
            cash, flow = snapshot["cash"], snapshot["flow"]
            exact = snapshot["cash_basis"] == "CASH_EQUIVALENTS"
            currency = cash.get("currency", "USD")
            expected = event.get("cash", "") if exact and currency == "USD" else ""
            state = "CONFLICT" if expected and abs(float(expected) - cash["val"]) > 1 else "VERIFIED"
            result = [self.result(event, "FINANCIAL", "CASH_FACT" if exact else "LIQUIDITY_FACT", state,
                "Current " + currency + " fact checked: " + snapshot["cash_basis"] + "; period and filing accession retained; no currency conversion",
                url, expected, cash["val"], json.dumps(snapshot, sort_keys=True))]
            if flow is None:
                result.append(self.result(event, "FINANCIAL", "RUNWAY_ESTIMATE", "REVIEW_REQUIRED",
                    "No operating cash flow from the same filing and period; no runway certified", url))
            elif flow["val"] >= 0:
                result.append(self.result(event, "FINANCIAL", "RUNWAY_ESTIMATE", "NOT_APPLICABLE",
                    "Aligned operating cash flow is nonnegative; finite cash-burn runway does not apply",
                    url, observed="NOT_APPLICABLE", evidence=json.dumps(snapshot, sort_keys=True)))
            elif not exact:
                result.append(self.result(event, "FINANCIAL", "RUNWAY_ESTIMATE", "REVIEW_REQUIRED",
                    "Reported cash includes restricted cash; an unrestricted balance is required for spendable-cash runway",
                    url, evidence=json.dumps(snapshot, sort_keys=True)))
            else:
                runway = cash["val"] / (-flow["val"] / (snapshot["flow_days"] / 30.4375))
                expected = event.get("cash_runway_months", "")
                state = "CONFLICT" if expected and abs(float(expected) - runway) > 0.15 else "VERIFIED"
                result.append(self.result(event, "FINANCIAL", "RUNWAY_ESTIMATE", state,
                    "Arithmetic verified using the same cash/operating-flow filing and period; estimate excludes future financings and spending changes",
                    url, expected, round(runway, 4), json.dumps(snapshot, sort_keys=True)))
            return result
        except IdentityConflict as exc:
            state, reason = "CONFLICT", str(exc)
        except (ValueError, KeyError, TypeError) as exc:
            state, reason = "REVIEW_REQUIRED", str(exc)
        except Exception as exc:
            state, reason = "TECHNICAL_FAILURE", type(exc).__name__
        return [self.result(event, "FINANCIAL", "CASH_AND_RUNWAY", state, reason, url)]

    def market(self, event):
        ticker = event["ticker"].upper()
        url = "https://query1.finance.yahoo.com/v8/finance/chart/" + urllib.parse.quote(ticker) + "?range=3mo&interval=1d&events=history"
        try:
            payload = json.loads(self.body(url))
            chart = payload["chart"]
            if chart.get("error") or len(chart.get("result") or []) != 1:
                raise ValueError("Market provider returned an error or no unique symbol")
            data = chart["result"][0]
            if data.get("meta", {}).get("symbol", "").upper() != ticker:
                raise IdentityConflict("Market response ticker mismatch")
            times = data["timestamp"]
            quote = data["indicators"]["quote"][0]
            closes, volumes = quote["close"], quote["volume"]
            if not times or len(times) != len(closes) or len(times) != len(volumes) or times != sorted(set(times)):
                raise ValueError("Market bars are empty, duplicated or misaligned")
            valid = [(t, c, v) for t, c, v in zip(times, closes, volumes)
                     if numeric(t) and numeric(c) and c > 0 and numeric(v) and v >= 0]
            if not valid:
                raise ValueError("No finite price/volume bar")
            stamp, price, volume = valid[-1]
            session = datetime.fromtimestamp(stamp, timezone.utc).date()
            if session > self.as_of or (self.as_of-session).days > 7:
                raise ValueError("Market session is future-dated or over seven calendar days old")
            # Imported event.price_last is undated. Treating a normal price
            # move as a contradiction with today's bar creates false mandatory
            # conflicts. Without a matching quote date, this is not a valid
            # same-session price comparison.
            previous_undated_snapshot = str(event.get("price_last", "")).strip()
            return [self.result(event, "MARKET", "PRICE_VOLUME", "VERIFIED",
                "Provider ticker, bar alignment, values and session verified; "
                "an undated saved price cannot contradict a dated market bar",
                url, "", price, json.dumps({"session": session.isoformat(),
                    "close": price, "volume": volume,
                    "undated_saved_price_last": previous_undated_snapshot}))] + self.market_extras(event)
        except IdentityConflict as exc:
            state, reason = "CONFLICT", str(exc)
        except (ValueError, KeyError, TypeError) as exc:
            state, reason = "REVIEW_REQUIRED", str(exc)
        except Exception as exc:
            state, reason = "TECHNICAL_FAILURE", type(exc).__name__
        return [self.result(event, "MARKET", "PRICE_VOLUME", state, reason, url)] + self.market_extras(event)

    def optional_payload(self, url):
        host = urllib.parse.urlsplit(url).hostname
        if host in self.unavailable_providers:
            raise SourceUnavailable("Provider denied supplemental data earlier in this run")
        try:
            return json.loads(self.body(url))
        except Exception as exc:
            if any(code in str(exc) for code in ("HTTP_401", "HTTP_403", "HTTP_429")):
                self.unavailable_providers.add(host)
            raise

    def market_extras(self, event):
        """Separate dated supplemental observations; never infer float %/borrow."""
        ticker = event["ticker"].upper()
        records = []
        url = "https://api.nasdaq.com/api/quote/" + urllib.parse.quote(ticker) + "/short-interest?assetclass=stocks"
        try:
            data = self.optional_payload(url).get("data") or {}
            if str(data.get("symbol", "")).upper() != ticker:
                raise ValueError("No ticker-matched Nasdaq short-interest response")
            observations = []
            for row in (data.get("shortInterestTable") or {}).get("rows", []):
                settled = datetime.strptime(row["settlementDate"], "%m/%d/%Y").date()
                shares = int(str(row["interest"]).replace(",", ""))
                ratio = float(str(row["daysToCover"]).replace(",", ""))
                if settled <= self.as_of and (self.as_of-settled).days <= 40 and shares >= 0 and math.isfinite(ratio) and ratio >= 0:
                    observations.append((settled, shares, ratio))
            if not observations:
                raise ValueError("No current finite settlement-dated short-interest row")
            settled, shares, ratio = max(observations)
            value = {"settlement_date": settled.isoformat(), "short_shares": shares, "days_to_cover": ratio}
            records.append(self.result(event, "MARKET", "SHORT_INTEREST", "VERIFIED",
                "Nasdaq reported short shares and days to cover; this is not short interest as a percentage of float",
                url, observed=json.dumps(value, sort_keys=True), evidence=json.dumps(value, sort_keys=True), required=False))
        except Exception as exc:
            records.append(self.result(event, "MARKET", "SHORT_INTEREST", "UNAVAILABLE", str(exc), url, required=False))
        url = "https://query1.finance.yahoo.com/v7/finance/options/" + urllib.parse.quote(ticker)
        try:
            result = self.optional_payload(url)["optionChain"]
            if result.get("error") or len(result.get("result") or []) != 1:
                raise ValueError("No unique options chain")
            chain = result["result"][0]
            if chain.get("underlyingSymbol", "").upper() != ticker:
                raise ValueError("Options underlying ticker mismatch")
            expiries = [(abs((datetime.fromtimestamp(t, timezone.utc).date()-self.as_of).days-30), t)
                        for t in chain.get("expirationDates", [])
                        if 21 <= (datetime.fromtimestamp(t, timezone.utc).date()-self.as_of).days <= 45]
            if not expiries:
                raise ValueError("No listed expiration within 21-45 days")
            expiry = min(expiries)[1]
            url += "?date=" + str(expiry)
            chain = self.optional_payload(url)["optionChain"]["result"][0]
            if chain.get("underlyingSymbol", "").upper() != ticker:
                raise ValueError("Dated options underlying mismatch")
            spot = chain.get("quote", {}).get("regularMarketPrice")
            if not numeric(spot) or spot <= 0:
                raise ValueError("No finite underlying quote")
            candidates = []
            for option_set in chain.get("options", []):
                if option_set.get("expirationDate") != expiry:
                    continue
                for contract in option_set.get("calls", []) + option_set.get("puts", []):
                    iv, strike, traded = contract.get("impliedVolatility"), contract.get("strike"), contract.get("lastTradeDate")
                    if not numeric(iv) or not 0 < iv <= 10 or not numeric(strike) or not numeric(traded):
                        continue
                    age = (self.as_of-datetime.fromtimestamp(traded, timezone.utc).date()).days
                    if 0 <= age <= 7 and abs(strike-spot)/spot <= .15:
                        candidates.append((abs(strike-spot), contract))
            if not candidates:
                raise ValueError("No recent near-money option with provider-reported IV")
            contract = min(candidates, key=lambda x:x[0])[1]
            value = {"contract": contract.get("contractSymbol"), "implied_volatility": contract["impliedVolatility"],
                     "expiration": datetime.fromtimestamp(expiry, timezone.utc).date().isoformat(), "strike": contract["strike"]}
            records.append(self.result(event, "MARKET", "OPTIONS_IV", "VERIFIED",
                "Provider IV for a dated near-money option; not an interpolated constant 30-day IV",
                url, observed=json.dumps(value, sort_keys=True), evidence=json.dumps(value, sort_keys=True), required=False))
        except Exception as exc:
            records.append(self.result(event, "MARKET", "OPTIONS_IV", "UNAVAILABLE", str(exc), url, required=False))
        records.append(self.result(event, "MARKET", "BORROW", "UNAVAILABLE",
            "Borrow availability and fees require a broker-specific source; no broker data is configured", required=False))
        return records

    def issuer(self, event):
        event = self.mapped_event(event)
        failures = []
        try:
            for i, url in enumerate(self.issuer_documents(event)):
                if i >= 16:
                    break
                if self.primary(event, url) == "FDA":
                    continue
                try:
                    raw, plain = self.document(url)
                    if not drug_matches(event, plain) or not indication_matches(event, plain) or not company_matches(event, plain):
                        continue
                    if not re.search(r"(?i)\b(?:press release|announced|announces|reported|reports)\b", plain):
                        continue
                    posted = publication_dates(raw, plain)
                    if len(posted) != 1 and self.primary(event, url) == "ISSUER":
                        mapping = self.event_sources(event)
                        if url in mapping.get("urls", []):
                            posted = mapped_issuer_release_dateline(
                                event, plain, mapping.get("primary_release_date", ""))
                    if len(posted) != 1:
                        continue
                    published = next(iter(posted))
                    if published > self.as_of.isoformat():
                        return [self.result(event, "ISSUER", "PRIMARY_RELEASE", "CONFLICT", "Release date is in the future", url, observed=published)]
                    return [self.result(event, "ISSUER", "PRIMARY_RELEASE", "VERIFIED",
                        "Primary company-matched source, drug, indication and explicit publication date checked; release claims are not an FDA decision",
                        url, observed=published, evidence=plain[:900])]
                except (ValueError, KeyError, TypeError):
                    continue
                except Exception as exc:
                    failures.append(str(exc)[:120])
        except (ValueError, KeyError, TypeError):
            pass
        except Exception as exc:
            failures.append(str(exc)[:120])
        return [self.result(event, "ISSUER", "PRIMARY_RELEASE", "TECHNICAL_FAILURE" if failures else "REVIEW_REQUIRED",
            "Primary issuer release not confirmed" + (": " + ", ".join(failures[:3]) if failures else " for this event"))]


def summary(rows):
    counts = Counter(row["verification_status"] for row in rows)
    mandatory = [r for r in rows if r.get("verification_required", "YES") == "YES"]
    incomplete = [r for r in mandatory if r["verification_status"] not in {"VERIFIED", "NOT_APPLICABLE"}]
    return {"findings_due": len(rows), "findings_verified": counts["VERIFIED"],
            "findings_not_applicable": counts["NOT_APPLICABLE"], "findings_unavailable": counts["UNAVAILABLE"],
            "required_findings_due": len(mandatory), "required_findings_unresolved": len(incomplete),
            "optional_findings_unavailable": sum(r["verification_status"] == "UNAVAILABLE" and r.get("verification_required") == "NO" for r in rows),
            "findings_unresolved": counts["REVIEW_REQUIRED"], "findings_conflicted": counts["CONFLICT"],
            "verification_technical_failure_count": counts["TECHNICAL_FAILURE"],
            "verification_status_counts": dict(counts)}


def verify_source(source, data_dir, out, fetch=None, as_of=None, mode="FULL"):
    if mode not in {"FULL", "DELTA"}:
        raise ValueError("Scan mode must be FULL or DELTA")
    events = read_rows(data_dir / "pdufa_candidates.csv")
    companies = read_rows(data_dir / "company_registry.csv")
    if not events or any(not r.get("event_key") or not r.get("ticker") for r in events):
        raise ValueError("Candidate scope is empty or lacks event identities")
    if len({r["event_key"] for r in events}) != len(events):
        raise ValueError("Duplicate candidate event identities")
    if not companies or len({r["ticker"].upper() for r in companies}) != len(companies):
        raise ValueError("Company registry is empty or contains duplicate tickers")
    config_path = Path(__file__).resolve().parents[1] / "config/issuer_sources.json"
    issuer_sources = json.loads(config_path.read_text()) if config_path.exists() else {}
    financing_path = data_dir / "second_financing_status.csv"
    financing_reviews = {r["event_key"]: r for r in read_rows(financing_path)} if financing_path.exists() else {}
    verifier = Verifier(companies, fetch=fetch, as_of=as_of, issuer_sources=issuer_sources)
    results = []
    sec_auto_retries = 0
    sec_auto_recovered = 0
    sec_carried_forward = 0
    sec_financing_live_checked = 0
    fda_carried_forward = 0
    fda_live_checked = 0
    fda_indices_checked = 0
    fda_indices_blocked = 0
    # Persisted source-ledger values can seed DELTA only after a real prior
    # primary-source verification that also stored exact-event and SEC-index
    # fingerprints. Older published rows lack these fields, so they are
    # reverified once instead of being assumed safe.
    prior_fda_rows = (read_rows(data_dir / "pdufa_source_verification.csv")
                      if source == "FDA" and mode == "DELTA" and
                      (data_dir / "pdufa_source_verification.csv").is_file() else [])
    prior_fda = {r["event_key"]: r for r in prior_fda_rows
                 if r.get("category") == "FDA" and r.get("verification_status") == "VERIFIED"}
    fda_issuer_indexes = {}
    fda_company_cik = {r["ticker"].upper(): r.get("cik10", "")
                       for r in companies}
    prior = read_rows(data_dir / "pdufa_source_verification.csv") if source == "SEC" and mode == "DELTA" else []
    prior_registry = {r["event_key"]: r for r in prior if
                      r.get("category") == "SEC" and r.get("claim") == "FILINGS_INVENTORY"
                      and r.get("verification_status") == "VERIFIED"}
    prior_closures = {r["event_key"]: r for r in prior if
                      r.get("category") == "SEC" and r.get("claim") == "FINANCING_CLOSURE"
                      and r.get("verification_status") == "VERIFIED"}
    current_registry = {}
    sec_watch_rows = []
    sec_watch_errors = 0

    def safe_sec_retry(row, recheck):
        nonlocal sec_auto_retries, sec_auto_recovered
        if sec_auto_retries >= SEC_AUTO_RECOVERY_LIMIT or not retryable_sec_failure(row):
            return row
        sec_auto_retries += 1
        # body() intentionally caches *all* outcomes, including failures.
        # Evict ONLY this confirmed transient exception or the retry would
        # immediately replay the cached HTTP_503 instead of a new SEC fetch.
        failed_url = row.get("source_url", "")
        if isinstance(verifier.cache.get(failed_url), Exception):
            verifier.cache.pop(failed_url, None)
        retry_result, attempted = retry_sec_claim(row, recheck)
        if attempted and retry_result["verification_status"] != "TECHNICAL_FAILURE":
            sec_auto_recovered += 1
        return retry_result

    if source == "SEC":
        for company in companies:
            first = verifier.registry(company)
            checked = safe_sec_retry(first, lambda company=company: verifier.registry(company))
            results.append(checked)
            current_registry[company["ticker"].upper()] = checked
            if checked["verification_status"] == "VERIFIED":
                try:
                    from scripts.filings_base_amendments import rows_from_submissions
                    _, _, recent = verifier.submissions({
                        "ticker": company["ticker"],
                        "event_key": "REGISTRY:" + company["ticker"]})
                    sec_watch_rows.extend(rows_from_submissions(
                        ticker=company["ticker"].upper(), cik10=verifier.cik(company),
                        recent=recent, index_sha256=checked["source_sha256"],
                        as_of=verifier.as_of))
                except (ValueError, KeyError, TypeError):
                    sec_watch_errors += 1
    for event in events:
        event = {**event, "_financing_review": financing_reviews.get(event["event_key"], {})}
        if source == "FDA":
            # A stable exact-program fingerprint is necessary: any saved
            # application, outcome, target date, clinical identity or evidence
            # mapping change forces a primary-document review.
            signed_fields = (
                "event_key", "ticker", "company", "drug", "indication", "pdufa_date",
                "decision_date", "outcome", "application_type", "application_number",
                "nda_submission_date", "fda_acceptance_date", "nct_id",
                "phase3_date", "phase3_status", "pdufa_evidence_url",
                "issuer_evidence_url", "trial_evidence_url", "financing_evidence_url",
                "evidence_summary", "regulatory_summary")
            signature = digest(json.dumps(
                {"event": {k: event.get(k, "") for k in signed_fields},
                 "cik": fda_company_cik.get(event["ticker"].upper(), ""),
                 "source_config": verifier.event_sources(event)},
                sort_keys=True, separators=(",", ":")).encode())
            ticker = event["ticker"].upper()
            if ticker not in fda_issuer_indexes:
                index = verifier.registry({"ticker": ticker})
                fda_issuer_indexes[ticker] = (
                    index.get("source_sha256", "") if
                    index.get("verification_status") == "VERIFIED" else "")
                if fda_issuer_indexes[ticker]:
                    fda_indices_checked += 1
                else:
                    fda_indices_blocked += 1
            index_hash = fda_issuer_indexes[ticker]
            old = prior_fda.get(event["event_key"], {})
            resolved = event.get("outcome", "").strip().upper() in {"APPROVED", "CRL"}
            claim = "FDA_DECISION" if resolved else "PDUFA_TARGET"
            expected = event.get("decision_date", "") if resolved else event.get("pdufa_date", "")
            near_catalyst = False
            if not resolved:
                try:
                    target_day = date.fromisoformat(str(expected))
                    near_catalyst = target_day <= verifier.as_of + timedelta(days=45)
                except (TypeError, ValueError):
                    near_catalyst = True
            carry = (
                mode == "DELTA" and not near_catalyst
                and old.get("ticker") == event["ticker"]
                and old.get("claim") == claim
                and old.get("expected") == (
                    event.get("outcome", "").strip().upper() + " " + expected
                    if resolved else expected)
                and old.get("claim_input_sha256") == signature
                and bool(index_hash)
                and old.get("monitor_index_sha256") == index_hash
                and re.fullmatch(r"[a-f0-9]{64}", old.get("source_sha256", "")) is not None
                and old.get("source_url") and verifier.primary(event, old["source_url"])
            )
            if carry:
                retained = dict(old)
                retained["checked_at"] = utcnow()
                retained["reason"] = (
                    "CARRIED_FORWARD: unchanged exact FDA event and SEC issuer-filings "
                    "index; historical primary claim originally reviewed "
                    + str(old.get("checked_at", "unknown"))
                    + ". This is not a fresh FDA action check; Sunday FULL or "
                    "any new filing/amendment reopens the primary document.")
                results.append(retained)
                fda_carried_forward += 1
            else:
                current = verifier.regulatory(event)
                for row in current:
                    # Never cache a REVIEW, CONFLICT or transport failure as
                    # verified; a new exact-event status must be proved anew.
                    if row.get("verification_status") == "VERIFIED":
                        row["claim_input_sha256"] = signature
                        row["monitor_index_sha256"] = index_hash
                results += current
                fda_live_checked += 1
        elif source == "SEC":
            old = prior_closures.get(event["event_key"], {})
            old_index = prior_registry.get("REGISTRY:" + event["ticker"], {})
            new_index = current_registry.get(event["ticker"].upper(), {})
            target_url, target_date = verifier.financing_target(event)
            can_carry = (
                mode == "DELTA"
                and old.get("ticker") == event["ticker"]
                and old.get("source_url") == target_url
                and old.get("expected") == target_date
                and re.fullmatch(r"[a-f0-9]{64}", old.get("source_sha256", "")) is not None
                and new_index.get("verification_status") == "VERIFIED"
                and old_index.get("source_sha256")
                and old_index["source_sha256"] == new_index.get("source_sha256")
            )
            if can_carry:
                # Today's timestamp is the fresh issuer-index comparison, not
                # a claim that the original EDGAR closing body was downloaded.
                carried = dict(old)
                carried["checked_at"] = utcnow()
                carried["reason"] = (
                    "CARRIED_FORWARD: unchanged issuer SEC filings inventory; "
                    "original funded-closing document verified at "
                    + str(old.get("checked_at", "unknown"))
                    + ". New/amended filings or Sunday FULL reopen this claim.")
                results.append(carried)
                sec_carried_forward += 1
            else:
                first = verifier.financing(event)
                results.append(safe_sec_retry(first, lambda event=event: verifier.financing(event)))
                sec_financing_live_checked += 1
        elif source == "FINANCIAL":
            results += verifier.financial(event)
        elif source == "MARKET":
            results += verifier.market(event)
        elif source == "ISSUER":
            results += verifier.issuer(event)
        else:
            raise ValueError("Unsupported verification source")
    # Public/Investor Relations closing leads are retained as provisional.
    # Every SEC run re-opens issuer-matched SEC filings for the dated leads.
    # This secondary ledger NEVER changes the official claim result or entry
    # gate until the normal independent financing-sequence audit passes.
    provisional_recheck = {}
    if source == "SEC":
        targets = data_dir / "finance_ir_sec_recheck_targets.csv"
        if targets.is_file():
            from provisional_financing_sec_recheck import recheck_leads
            try:
                renewed = recheck_leads(
                    verifier, events, targets,
                    out / "finance_ir_sec_recheck.csv"
                )
                provisional_recheck = {
                    "public_ir_recheck_status": "COMPLETE",
                    "public_ir_leads_checked_against_sec": len(renewed),
                    "public_ir_sec_transactions_verified": sum(
                        row["sec_recheck_status"] == "SEC_TRANSACTION_VERIFIED"
                        for row in renewed
                    ),
                    "public_ir_sec_recheck_ledger": "finance_ir_sec_recheck.csv",
                }
            except Exception as exc:
                # The full source audit must not report public-recheck success
                # when even one input fails parsing, writing or validation.
                provisional_recheck = {
                    "public_ir_recheck_status": "FAILED",
                    "public_ir_recheck_error": type(exc).__name__,
                    "public_ir_leads_checked_against_sec": 0,
                    "public_ir_sec_transactions_verified": 0,
                }

    out.mkdir(parents=True, exist_ok=True)
    if source == "SEC":
        from scripts.filings_base_amendments import write_rows as write_sec_watch
        write_sec_watch(out / "sec_filing_watch.csv", sec_watch_rows)
    path = out / (source.lower() + "_verification.csv")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(results)
    totals = summary(results)
    registry_rows = [r for r in results if r["claim"] == "FILINGS_INVENTORY"]
    registry_counts = Counter(r["verification_status"] for r in registry_rows)
    inventory = ({"registry_companies": len(companies), "companies_due": len(companies),
                  "companies_checked": registry_counts["VERIFIED"],
                  "sec_registry_status_counts": dict(registry_counts),
                  "sec_registry_output": path.name} if source == "SEC" else {})
    recovery = ({"sec_auto_retry_attempts": sec_auto_retries,
                 "sec_auto_retry_cleared": sec_auto_recovered,
                 "sec_auto_retry_limit": SEC_AUTO_RECOVERY_LIMIT}
                if source == "SEC" else {})
    return {**totals, **inventory, **recovery, **provisional_recheck, "scan_mode": mode,
            "fda_claims_carried_forward": fda_carried_forward,
            "fda_claims_live_checked": fda_live_checked,
            "fda_issuer_indices_checked": fda_indices_checked,
            "fda_issuer_indices_unavailable": fda_indices_blocked,
            "sec_closures_carried_forward": sec_carried_forward,
            "sec_financing_closures_live_checked": sec_financing_live_checked,
            "sec_filing_watch_rows": len(sec_watch_rows),
            "sec_filing_watch_index_errors": sec_watch_errors,
            "verification_version": VERSION, "verification_run_id": run_identity(),
            "verification_scope_sha256": scope_hash(events, companies),
            "verification_ledger": path.name, "verification_ledger_sha256": digest(path.read_bytes()),
            "verification_events_due": len(events), "verification_events_checked": len({r["event_key"] for r in results if not r["event_key"].startswith("REGISTRY:")}),
            "scope_coverage_verified": bool(results) and totals["required_findings_unresolved"] == 0,
            "verification_issue_examples": [{k: r[k] for k in ("ticker", "category", "claim", "verification_status", "reason")}
                for r in results if r["verification_status"] not in {"VERIFIED", "NOT_APPLICABLE"}] [:12],
            "issuer_press_releases_verified": sum(r["category"] == "ISSUER" and r["verification_status"] == "VERIFIED" for r in results)}

