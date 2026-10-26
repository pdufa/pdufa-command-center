#!/usr/bin/env python3
"""Build a conservative 741-record *research* overlay for issuer rights claims.

Three issuer disclosure cases across four programs are source pointers, not
independent contract/legal determinations. No individual trial, drug, company or
ticker may be silently promoted to PDUFA eligibility. The registry census is
the immutable denominator and unknown remains an explicit state.
"""
import csv
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
CENSUS = ROOT / "data/phase3_all_years_300m_10b_trials.csv"
ISSUERS = ROOT / "new-platform/frontend/public/phase3-census-sources-2026-10-26.json"
ABVX_CASE = ROOT / "data/research_abvx_obefazimod_rights_2026-10-26.json"
OTHER_CASES = ROOT / "data/research_issuer_rights_claims_achv_mirm_2026-10-26.json"

def load_originals():
    with CENSUS.open(newline="", encoding="utf-8-sig") as handle:
        trials = list(csv.DictReader(handle))
    research = json.loads(ISSUERS.read_text(encoding="utf-8"))
    if (len(trials) != 741 or len({t["nct_id"] for t in trials}) != 741
            or len({t["ticker"] for t in trials}) != 130
            or research.get("scope") != "RESEARCH_POINTERS_ONLY"
            or research.get("trialCount") != 741 or research.get("companyCount") != 130):
        raise ValueError("Original 741/130 research census identity mismatch")
    by_ticker = {x["ticker"]: x for x in research["companies"]}
    if len(by_ticker) != 130:
        raise ValueError("Issuer CIK pointers not unique")
    for t in trials:
        issuer = by_ticker[t["ticker"]]
        if t["nct_id"] not in issuer["nctIds"] or t["company"] not in issuer["leadSponsorNames"]:
            raise ValueError("Trial no longer linked to exact original issuer research pointer")
    return trials, by_ticker


def collect_cases():
    """Normalize existing ABVX dossier alongside new ACHV and MIRM dossiers."""
    abvx = json.loads(ABVX_CASE.read_text(encoding="utf-8"))
    if (abvx.get("scope") != "PRIMARY_ISSUER_DISCLOSURE_RESEARCH_CASE_NOT_LEGAL_ADJUDICATION"
        or abvx.get("issuer", {}).get("ticker") != "ABVX"):
        raise ValueError("ABVX baseline evidence source not recognized")
    findings = abvx["evidenceFindings"]
    if (findings.get("rights_contract_terms_independently_validated") is not False
        or findings.get("current_unencumbered_legal_rights_independently_verified") is not False
        or findings.get("qualified_pipeline") is not None
        or findings.get("official_pdufa_target_date_confirmed") is not False):
        raise ValueError("ABVX legal or FDA status was silently promoted")
    old_program = {
        "issuerTicker": "ABVX", "issuerCik": abvx["issuer"]["cik"],
        "asset": abvx["program"]["drug"],
        "rightsClaimType": "ISSUER_SELF_REPORTED_WORLDWIDE_RIGHTS",
        "rightsClaimSummary": "ABVX filing states worldwide obefazimod rights; independent contract terms, territory restrictions and subsequent transfers not adjudicated.",
        "rightsIndependentlyAdjudicated": False,
        "contractScopeIndependentlyVerified": False,
        "risks": ["CURRENT_CONTRACT_RIGHTS_NOT_INDEPENDENTLY_ADJUDICATED"],
        "sourceDocuments": [
            {"type": x["sourceType"], "url": x["url"], "assertion": x["details"]}
            for x in abvx["primarySources"]
        ],
        "trialLinks": [
            {"nctId": nct, "study": "ABTECT",
             "indication": abvx["program"]["indication"],
             "trialSourceUrl": "https://clinicaltrials.gov/study/" + nct,
             "regulatoryContext": "OBEFAZIMOD_UC_NDA_PLANNED_NOT_ACCEPTED_CONFIRMED",
             "historicalIssuerReportedPdufaDate": None,
             "currentPdufaTargetVerified": None}
            for nct in abvx["program"]["trialNctIds"]
        ],
    }
    newer = json.loads(OTHER_CASES.read_text(encoding="utf-8"))
    if (newer.get("scope") != "ISSUER_PRIMARY_DISCLOSURE_PROGRAM_TO_TRIAL_RIGHTS_CLAIMS_ONLY"
        or newer.get("schemaVersion") != 1 or len(newer.get("programs", [])) != 3):
        raise ValueError("ACHV/MIRM primary issuer disclosure source missing")
    return [old_program] + newer["programs"]


def build():
    trials, issuers = load_originals()
    claims = {}
    programs = collect_cases()
    ticker_claims = set()
    for p in programs:
        ticker, cik, asset = p["issuerTicker"], p["issuerCik"], p["asset"]
        if (ticker not in issuers or issuers[ticker]["cik"] != cik
                or not isinstance(asset, str) or not asset
                or (ticker, asset.casefold()) in ticker_claims):
            raise ValueError("Issuer asset CIK or duplicate program mismatch")
        ticker_claims.add((ticker, asset.casefold()))
        if p.get("rightsIndependentlyAdjudicated") is not False:
            raise ValueError("Issuer disclosures cannot independently adjudicate rights")
        if p.get("contractScopeIndependentlyVerified") is not False:
            raise ValueError("Contract scope must remain unverified")
        sources = p["sourceDocuments"]
        if (len(sources) < 2
                or not any(s["type"].startswith(("ISSUER_SEC_", "SEC_FORM_")) for s in sources)
                or not all(s["url"].startswith("https://") and s.get("assertion") for s in sources)):
            raise ValueError("Issuer primary filing sources insufficient")
        for link in p["trialLinks"]:
            nct = link["nctId"]
            if nct in claims:
                raise ValueError("Duplicate NCT across evidence programs")
            if (not re.fullmatch(r"NCT\d{8}", nct)
                    or nct not in issuers[ticker]["nctIds"]
                    or link["trialSourceUrl"] != "https://clinicaltrials.gov/study/" + nct
                    or not link.get("indication") or not link.get("study")
                    or link.get("currentPdufaTargetVerified") is not None):
                raise ValueError("NCT/asset/indication or PDUFA evidence check failed")
            claims[nct] = {
                "issuer_claim_documented": True, "ticker": ticker,
                "asset": asset, "study": link["study"],
                "indication": link["indication"],
                "rights_claim_type": p["rightsClaimType"],
                "issuer_primary_disclosure_url": sources[0]["url"],
                "primary_sources": sources,
                "trial_registry_url": link["trialSourceUrl"],
                "material_rights_or_regulatory_risks": p["risks"],
                "trial_regulatory_context": link["regulatoryContext"],
                "historical_issuer_reported_pdufa_target": link["historicalIssuerReportedPdufaDate"],
            }
    rows = []
    for t in sorted(trials, key=lambda x: x["nct_id"]):
        linked = claims.get(t["nct_id"])
        entry = {
            "nct_id": t["nct_id"], "ticker": t["ticker"],
            "registry_lead_sponsor": t["company"], "registry_url": t["source_url"],
            "research_claim_status": ("ISSUER_DISCLOSED_ASSET_RIGHTS_CLAIM_LINKED"
                                      if linked else "NO_TRIAL_SPECIFIC_RIGHTS_CLAIM_REVIEWED"),
            "source_document_links_cataloged": linked["primary_sources"] if linked else [],
            "linked_asset": linked["asset"] if linked else None,
            "linked_indication": linked["indication"] if linked else None,
            "rights_claim_type": linked["rights_claim_type"] if linked else None,
            "material_risk_flags": linked["material_rights_or_regulatory_risks"] if linked else [],
            "regulatory_context": linked["trial_regulatory_context"] if linked else None,
            "historical_issuer_reported_pdufa_target": (
                linked["historical_issuer_reported_pdufa_target"] if linked else None),
            "independently_verified_current_legal_rights": False,
            "independent_fda_pdufa_target_verified": False,
            "current_pdufa_target_date": None,
            "qualified_pipeline": None,
        }
        rows.append(entry)
    linked_n = sum(x["research_claim_status"] == "ISSUER_DISCLOSED_ASSET_RIGHTS_CLAIM_LINKED" for x in rows)
    return {
        "schema_version": 1, "scope": "HISTORICAL_PHASE3_PRIMARY_ISSUER_DISCLOSURE_RESEARCH_OVERLAY_ONLY",
        "evidence_as_of": "2026-10-26",
        "original_census_sha256": hashlib.sha256(CENSUS.read_bytes()).hexdigest(),
        "denominator_trials": 741, "denominator_issuers": 130,
        "issuer_rights_claim_evidence_linked_trials": linked_n,
        "claim_evidence_missing_or_unreviewed_trials": 741 - linked_n,
        "issuers_with_rights_claim_dossiers": len({p["issuerTicker"] for p in programs}),
        "asset_program_dossiers": len(programs),
        "independently_adjudicated_current_legal_rights_count": 0,
        "independently_verified_current_fda_pdufa_count": 0,
        "qualified_pipeline_count": None,
        "limitations": "These are primary issuer-disclosed rights CLAIMS linked to original registry NCTs, not independent legal adjudication or evidence of unencumbered global rights. Some have material disputes/territorial restrictions. An historical issuer-reported PDUFA target may have already passed; it is not a current pending FDA action. Unreviewed means unknown, not negative. Existing drug approval for a different indication is not a new-label approval.",
        "trials": rows,
    }


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: build_phase3_issuer_rights_claim_overlay.py <report.json>")
    result = build()
    out = Path(sys.argv[1])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("Historical trials with issuer rights-claim evidence linked:", result["issuer_rights_claim_evidence_linked_trials"], "/741")
    print("Historical trials not yet rights-claim reviewed:", result["claim_evidence_missing_or_unreviewed_trials"], "/741")
    print("Issuers with source-linked disclosures:", result["issuers_with_rights_claim_dossiers"], "/130")
    print("Drug development programs supported by issuer disclosures:", result["asset_program_dossiers"], "/4 researched")
    print("Independently adjudicated legal rights: 0/741; independently verified current FDA/PDUFA targets: 0/741")
    print("Qualified Pipeline: UNKNOWN, never inferred from rights claims.")
