#!/usr/bin/env python3
"""Prepare an actionable, fail-closed SEC/financial research queue.

Uses ONLY the latest published unresolved-source queue, the company registry,
and optional issuer-configured primary-document discovery links. It NEVER
fetches search snippets, rewrites source assertions, certifies a financing,
or changes GEM/PIPELINE trading eligibility. Google search URLs are discovery
shortcuts; any document must be fetched and verified by source_verification.py.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import quote
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen

FIELDS = [
    "priority", "event_key", "ticker", "company", "category", "claim",
    "research_class", "reason", "saved_closing_date",
    "different_mapped_closing_date", "issuer_cik10", "sec_submissions_url",
    "google_sec_company_search", "google_sec_exhibit_search",
    "google_issuer_closing_search", "known_sec_source_urls",
    "official_ir_host", "official_ir_home",
    "official_ir_news_search", "official_ir_sec_filings_search",
    "official_ir_financial_results_search", "investor_relations_review_required",
    "official_ir_live_status", "official_ir_live_links", "official_ir_last_checked_utc",
    "next_evidence_required", "source_claim_verified",
    "second_post_phase3_financing_verified", "trade_entry_authorized",
]
SEC_FORMS = "8-K/8-K-A/10-Q/10-K/6-K/20-F/exhibits"
# Official issuer websites checked against their public Investor Relations pages.
# Research discovery only; not evidence that any financing occurred.
REVIEWED_IR_DOMAINS = {
    "ZLAB": "ir.zailaboratory.com",
    "CORT": "ir.corcept.com",
    "IBRX": "ir.immunitybio.com",
    "ARQT": "investors.arcutis.com",
    "APMD": "ir.apnimed.com",
    "AXSM": "www.axsome.com",
}
DATE_RE = re.compile(r"20\d\d-\d\d-\d\d\Z")


def read_csv(path):
    with Path(path).open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def google(query):
    return "https://www.google.com/search?q=" + quote(query, safe="")


def valid_date(raw):
    if not isinstance(raw, str) or not DATE_RE.fullmatch(raw):
        return ""
    try:
        return date.fromisoformat(raw).isoformat()
    except ValueError:
        return ""


def sec_document_url(url, cik):
    """Allow only SEC archive documents for the exact issuer CIK."""
    from urllib.parse import urlsplit
    p = urlsplit(str(url or ""))
    return bool(
        p.scheme == "https" and p.hostname in {"www.sec.gov", "sec.gov"}
        and not p.query and not p.fragment and cik and cik.isdigit()
        and re.fullmatch(
            r"/Archives/edgar/data/0*(\d+)/\d{18}/[A-Za-z0-9_.-]{1,150}",
            p.path,
        )
        and int(re.fullmatch(
            r"/Archives/edgar/data/0*(\d+)/\d{18}/[A-Za-z0-9_.-]{1,150}",
            p.path,
        ).group(1)) == int(cik)
        and p.path.lower().endswith((".htm", ".html", ".txt"))
    )


class IRLinkCollector(HTMLParser):
    """Bounded links from an official issuer page, never verified claims."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.current = None
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == "a" and self.current is None:
            url = dict(attrs).get("href", "")
            self.current = {"url": url if isinstance(url, str) else "", "parts": []}

    def handle_data(self, data):
        if self.current is not None:
            self.current["parts"].append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.current is not None:
            self.links.append((self.current["url"], " ".join(self.current["parts"])))
            self.current = None


def live_issuer_ir_research(rows, timeout=5):
    """Visit each official IR homepage once, surfacing actual same-host leads.

    Successful page retrieval does not prove an offering, cash, FDA decision,
    or GEM readiness. A blocked site does not mean the evidence is absent.
    """
    cache = {}
    relevant = re.compile(
        r"(?i)\b(?:investor|press|news|release|filings?|financial|earnings|"
        r"quarterly|offering|financing|placement|clos(?:ed|ing)|report|"
        r"annual|results|cash)\b"
    )
    for row in rows:
        host = row.get("official_ir_host", "")
        row["official_ir_last_checked_utc"] = datetime.now(timezone.utc).isoformat()
        if not host:
            row["official_ir_live_status"] = "OFFICIAL_SITE_NEEDS_DISCOVERY"
            row["official_ir_live_links"] = ""
            continue
        if host not in cache:
            try:
                req = Request(row["official_ir_home"], headers={
                    "User-Agent": "PDUFACommandCenter/1.0 (public issuer research)",
                    "Accept": "text/html",
                })
                with urlopen(req, timeout=timeout) as response:
                    final = response.geturl()
                    site_host = (urlsplit(final).hostname or "").lower()
                    if site_host.removeprefix("www.") != host.removeprefix("www."):
                        raise ValueError("Official IR home redirected to a different domain")
                    if "text/html" not in response.headers.get("Content-Type", ""):
                        raise ValueError("Official IR response was not HTML")
                    body = response.read(650001)
                    if not body or len(body) > 650000:
                        raise ValueError("Official IR response empty or too large")
                collector = IRLinkCollector()
                collector.feed(body.decode("utf-8", errors="replace"))
                leads = []
                for href, title in collector.links:
                    clean = re.sub(r"\s+", " ", title).strip()
                    if not relevant.search(clean) or len(clean) < 5:
                        continue
                    target = urljoin(final, href)
                    parsed = urlsplit(target)
                    # SEC links are primary-record discovery; other third
                    # party links are deliberately not treated as issuer IR.
                    if parsed.scheme != "https" or parsed.username or parsed.password:
                        continue
                    target_host = (parsed.hostname or "").lower()
                    if (target_host.removeprefix("www.") != host.removeprefix("www.")
                            and target_host not in {"www.sec.gov", "sec.gov"}):
                        continue
                    item = clean[:70] + " (" + target[:220] + ")"
                    if item not in leads:
                        leads.append(item)
                    if len(leads) >= 8:
                        break
                cache[host] = (
                    "FETCHED_DISCOVERY_ONLY" if leads else "FETCHED_NO_MATCHING_LINKS",
                    " | ".join(leads),
                )
            except Exception as exc:
                cache[host] = ("RETRIEVAL_BLOCKED_OR_UNAVAILABLE", type(exc).__name__[:55])
        row["official_ir_live_status"], row["official_ir_live_links"] = cache[host]
    return rows


def triage(queue, companies, config):
    registry = {r["ticker"].upper(): r for r in companies if r.get("ticker")}
    if len(registry) != len([r for r in companies if r.get("ticker")]):
        raise ValueError("Duplicate company ticker in registry")
    identities = set()
    result = []
    for item in queue:
        key = (item.get("event_key"), item.get("category"), item.get("claim"))
        if key in identities or not all(key):
            raise ValueError("Duplicate or incomplete unresolved source claim")
        identities.add(key)
        if item.get("verification_required") != "YES":
            raise ValueError("Research queue includes nonmandatory finding")
        if item.get("verification_status") in {"VERIFIED", "NOT_APPLICABLE"}:
            raise ValueError("Resolved claim cannot be requeued as missing")
        category = item["category"]
        if category not in {"SEC", "FINANCIAL"}:
            continue
        ticker = item.get("ticker", "").upper()
        event_key = item["event_key"]
        # Company SEC filings-inventory checks have exact REGISTRY:TICKER IDs,
        # not program-event TICKER|PROGRAM IDs. Keep both identity rules strict.
        registry_inventory = (category == "SEC" and
                              item["claim"] == "FILINGS_INVENTORY" and
                              event_key.startswith("REGISTRY:"))
        prefix = (event_key[len("REGISTRY:"):] if registry_inventory
                  else event_key.split("|", 1)[0] if "|" in event_key else "")
        if not ticker or prefix.upper() != ticker:
            raise ValueError("Claim event/ticker mismatch")
        company = registry.get(ticker, {})
        cik = company.get("cik10", "")
        cik = cik.zfill(10) if cik.isdigit() and int(cik) else ""
        name = company.get("company", ticker)
        src = (config.get(ticker, {}).get("events", {})
               .get(item["event_key"], {}))
        mapped = src.get("individual_financing_close")
        if not isinstance(mapped, dict):
            mapped = {}
        date_saved = valid_date(str(item.get("expected") or "").strip())
        date_mapped = valid_date(mapped.get("date", ""))
        # The mapped deal can differ from the prior ledger's deal. Never let
        # a newly found close silently replace an old recorded transaction.
        date_different = date_mapped if date_mapped and date_mapped != date_saved else ""
        if registry_inventory:
            research_class = "SEC_ISSUER_CIK_TICKER_IDENTITY_RECONCILIATION"
            priority = "1"
            next_evidence = (
                "Independently reconcile this company's current ticker and "
                "CIK against SEC company submissions and dated corporate actions. "
                "Do not mark the inventory VERIFIED or infer any financing close "
                "until the mismatch is resolved."
            )
        elif category == "FINANCIAL":
            research_class = "CASH_AND_RUNWAY_PRIMARY_RECONCILIATION"
            priority = "2"
            next_evidence = (
                "Read same-issuer SEC companyfacts or 6-K/20-F cash balance "
                "AND dated operating cash-flow period; validate currency, units, "
                "burn window and runway independently."
            )
        elif date_saved and date_different:
            research_class = "DIFFERENT_TRANSACTION_DATE_REVIEW"
            priority = "1"
            next_evidence = (
                "Verify stored date/deal against its own SEC closing clause; "
                "separately inspect mapped newer deal. DO NOT overwrite an "
                "older transaction or count two financings without a Phase 3 chronology."
            )
        elif date_saved:
            research_class = "DATED_CLOSING_NEEDS_SEC_CLAUSE"
            priority = "1"
            next_evidence = (
                "Find same-issuer 8-K/10-Q/10-K/6-K/20-F or exhibit that "
                "explicitly confirms this exact closing date, transaction "
                "and funded proceeds. An expected close is insufficient."
            )
        else:
            research_class = "TRANSACTION_NOT_IDENTIFIED"
            priority = "3"
            next_evidence = (
                "Identify a real dated financing transaction first using "
                "SEC filings and issuer closing releases. No closing claim "
                "exists to verify; do not treat missing evidence as a failed fetch."
            )
        documents = []
        links = list(src.get("financing_research_documents", []))
        if mapped.get("sec_url"):
            links.append(mapped["sec_url"])
        if item.get("source_url"):
            links.append(item["source_url"])
        if isinstance(src.get("financing_urls"), list):
            links += src["financing_urls"]
        for url in links:
            if sec_document_url(url, cik) and url not in documents:
                documents.append(url)
        # Search queries only, not evidence. Restrict Google discovery by
        # exact SEC issuer archive path and issuer identity.
        sec_path = "site:sec.gov/Archives/edgar/data/" + str(int(cik)) + "/" if cik else "site:sec.gov"
        terms = f'"{name}" "offering" ("closed" OR "completed")'
        if date_saved:
            terms += f' "{date_saved[:4]}"'
        exhibit_terms = f'"{name}" ("EX-99" OR "10-Q" OR "8-K") "net proceeds"'
        issuer_hosts = config.get(ticker, {}).get("hosts") or []
        issuer_query = (
            "site:" + issuer_hosts[0] + ' "' + name +
            '" ("closing" OR "completed") "offering"'
            if issuer_hosts and isinstance(issuer_hosts[0], str)
            else f'"{name}" investor relations closing public offering'
        )
        # Mandatory company-first escalation for every difficult claim.
        # These are DISCOVERY ROUTES on configured official hosts only.
        # Neither an IR home page nor a search result proves a closing.
        official_hosts = config.get(ticker, {}).get("hosts") or ([REVIEWED_IR_DOMAINS[ticker]] if ticker in REVIEWED_IR_DOMAINS else [])
        ir_host = next((
            host.lower() for host in official_hosts
            if isinstance(host, str) and re.fullmatch(
                r"[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+", host
            )
        ), "")
        ir_home = "https://" + ir_host + "/" if ir_host else ""
        def ir_lookup(topic):
            return google(f'site:{ir_host} "{name}" {topic}') if ir_host else google(
                f'"{name}" investor relations {topic}'
            )
        result.append({
            "official_ir_host": ir_host,
            "official_ir_home": ir_home,
            "official_ir_news_search": ir_lookup(
                '"closed" OR "completed" "offering" OR "financing"'),
            "official_ir_sec_filings_search": ir_lookup(
                '"SEC filings" OR "Form 8-K" OR "Form 6-K"'),
            "official_ir_financial_results_search": ir_lookup(
                '"financial results" "cash" "operating activities"'),
            "investor_relations_review_required": "YES",
            "priority": priority, "event_key": item["event_key"],
            "ticker": ticker, "company": name,
            "category": category, "claim": item["claim"],
            "research_class": research_class,
            "reason": item.get("reason", ""),
            "saved_closing_date": date_saved,
            "different_mapped_closing_date": date_different,
            "issuer_cik10": cik,
            "sec_submissions_url": (
                f"https://data.sec.gov/submissions/CIK{cik}.json" if cik else ""),
            "google_sec_company_search": google(sec_path + " " + terms),
            "google_sec_exhibit_search": google(sec_path + " " + exhibit_terms),
            "google_issuer_closing_search": google(issuer_query),
            "known_sec_source_urls": " | ".join(documents),
            "next_evidence_required": next_evidence,
            "source_claim_verified": "NO",
            "second_post_phase3_financing_verified": "NO",
            "trade_entry_authorized": "NO",
        })
    return sorted(result, key=lambda row: (row["priority"], row["ticker"], row["event_key"]))


def run(root, csv_output, json_output, live_ir=False):
    data = root / "data"
    report = json.loads((data / "pdufa_source_report.json").read_text())
    if not str(report.get("latest_run_id", "")).isdigit():
        raise ValueError("No canonical source audit run identity")
    queue = read_csv(data / "pdufa_source_review_queue.csv")
    if len(queue) != report.get("required_findings_unresolved"):
        raise ValueError("Canonical issue queue/count mismatch; stop")
    cfg = json.loads((root / "config" / "issuer_sources.json").read_text())
    rows = triage(queue, read_csv(data / "company_registry.csv"), cfg)
    if live_ir:
        rows = live_issuer_ir_research(rows)
    expected_scoped = sum(r.get("category") in {"SEC", "FINANCIAL"} for r in queue)
    if len(rows) != expected_scoped or not rows:
        raise ValueError("Research coverage differs from canonical SEC/financial queue")
    csv_output.parent.mkdir(parents=True, exist_ok=True)
    with csv_output.open("w", encoding="utf-8", newline="") as stream:
        w = csv.DictWriter(stream, FIELDS)
        w.writeheader()
        w.writerows(rows)
    info = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_run_id": str(report["latest_run_id"]),
        "research_only": True,
        "findings_scoped": len(rows),
        "by_class": dict(Counter(r["research_class"] for r in rows)),
        "by_category": dict(Counter(r["category"] for r in rows)),
        "rows_with_primary_sec_links": sum(bool(r["known_sec_source_urls"]) for r in rows),
        "issuer_ir_escalations_required": len(rows),
        "official_ir_hosts_configured": sum(bool(r["official_ir_host"]) for r in rows),
        "official_ir_hosts_missing": sum(not bool(r["official_ir_host"]) for r in rows),
        "official_ir_live_checked": sum(bool(r.get("official_ir_live_status", "")) for r in rows),
        "official_ir_live_fetched": sum(r.get("official_ir_live_status", "").startswith("FETCHED") for r in rows),
        "official_ir_live_blocked": sum(r.get("official_ir_live_status", "") == "RETRIEVAL_BLOCKED_OR_UNAVAILABLE" for r in rows),
        "canonical_source_ledger_modified": False,
        "source_claims_verified": 0,
        "second_post_phase3_financings_verified": 0,
        "trade_entries_authorized": 0,
        "csv_path": str(csv_output),
        "note": "Mandatory company Investor Relations first, then claim-specific SEC/FDA/clinical proof. IR and search links are discovery leads, NEVER proof of financing or runway.",
    }
    json_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(json.dumps(info, indent=2, sort_keys=True) + "\n")
    return info


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=Path("."))
    ap.add_argument("--live-ir", action="store_true", help="Visit each official investor site to collect research links, never verify claims")
    ap.add_argument("--output-csv", type=Path, default=Path("reports/sec_financing_gap_triage.csv"))
    ap.add_argument("--output-json", type=Path, default=Path("reports/sec_financing_gap_triage.json"))
    args = ap.parse_args()
    print(json.dumps(run(args.root, args.output_csv, args.output_json, live_ir=args.live_ir), indent=2))


if __name__ == "__main__":
    main()
