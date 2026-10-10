"""Auditable *input availability* for Phase 3 trials before the results release.

No Phase 3 result p-values, outcomes, future market action, or eventual FDA
decisions are used. Coverage is NOT design strength or probability of success.
Current ClinicalTrials.gov protocol versions cannot be used for past cutoffs
unless their actual retrieval timestamp preceded that cutoff.
"""
from datetime import date
import re
import pandas as pd

INPUTS = (
    ("Identity & registry source", "identity"),
    ("Primary endpoint and time frame", "endpoint"),
    ("Allocation recorded", "allocation"),
    ("Masking recorded", "masking"),
    ("Comparator recorded", "comparator"),
    ("Sample size documented", "enrollment"),
    ("Linked Phase 2 trial ID", "phase2_id"),
    ("Verified Phase 2 efficacy source", "phase2_efficacy"),
    ("Verified Phase 2 safety source", "safety"),
    ("Phase 3 design / power dossier", "phase3_design"),
    ("Documented FDA alignment", "fda_alignment"),
    ("Issuer's unreleased topline checked", "issuer_check"),
)
CHECK_KEYS = [label for label, _ in INPUTS]


def clean(v):
    text = "" if v is None else str(v).strip()
    # ClinicalTrials.gov's literal NONE is a meaningful masking value
    # (open-label), not a missing-data sentinel.
    return "" if text.lower() in {"nan", "nat", "<na>"} or text == "None" else text


def day(v):
    try:
        return date.fromisoformat(clean(v)[:10])
    except (ValueError, TypeError):
        return None


def http(v):
    return clean(v).startswith(("https://", "http://"))


def in_time(row, cutoff, *, fields):
    return all(day(row.get(f)) is not None and day(row.get(f)) <= cutoff for f in fields)


def manually_documented(e, name, max_pts, cutoff):
    if not isinstance(e, dict):
        return False
    try:
        points = float(clean(e.get(f"{name}_points")))
    except (ValueError, TypeError):
        return False
    return (0 <= points <= max_pts and http(e.get(f"{name}_source"))
            and in_time(e, cutoff, fields=(f"{name}_source_date",)))


def audit_inputs(candidates, protocols=None, evidence=None, *, as_of):
    """Return (per-trial coverage dataframe, per-input available counts).

    Each NCT is joined EXACTLY; cross-ticker or cross-drug manual evidence is
    not accepted. A blank manual evidence CSV is ordinary and leaves clinical
    inputs missing, rather than counting as negative evidence.
    """
    cutoff = day(as_of)
    if cutoff is None:
        raise ValueError("A valid as-of date is mandatory")
    if candidates is None or candidates.empty:
        return pd.DataFrame(columns=["NCT ID", "Input Coverage %", "Available Inputs",
                                     "Missing Inputs", "Issuer Check", *CHECK_KEYS]), {x: 0 for x in CHECK_KEYS}
    def records(df, field):
        if df is None or df.empty or field not in df:
            return {}
        return {clean(r.get(field)):r.to_dict() for _,r in df.iterrows() if clean(r.get(field))}
    p=records(protocols, "nct_id")
    manual=records(evidence, "nct_id")
    out=[]
    for _,c in candidates.iterrows():
        nct=clean(c.get("NCT ID"))
        ticker=clean(c.get("Ticker")).upper()
        drug=clean(c.get("Drug"))
        e=manual.get(nct, {})
        if e and (
            clean(e.get("ticker")).upper()!=ticker or
            clean(e.get("drug"))!=drug or
            clean(e.get("indication"))!=clean(c.get("Indication")) or
            day(e.get("assessment_cutoff_date"))!=cutoff
        ):
            e={}
        protocol=p.get(nct,{})
        if not (
            protocol and in_time(protocol,cutoff,fields=("checked_at","source_updated"))
            and clean(protocol.get("source_url"))==f"https://clinicaltrials.gov/study/{nct}"
        ):
            protocol={}
        checks={
            "identity":(clean(c.get("Program Identity")).upper()=="VERIFIED"
                        and http(c.get("Source")) and bool(re.fullmatch(r"NCT\d{8}",nct))),
            "endpoint":bool(clean(protocol.get("primary_endpoint")) and clean(protocol.get("primary_timeframe"))),
            "allocation":bool(clean(protocol.get("allocation"))),
            "masking":bool(clean(protocol.get("masking"))),
            "comparator":bool(clean(protocol.get("comparator"))),
            "enrollment":bool(re.fullmatch(r"\d+",clean(protocol.get("enrollment")))
                              and int(clean(protocol.get("enrollment")))>0),
            "phase2_id":bool(re.search(r"NCT\d{8}",clean(c.get("Phase 2 NCT Links")))),
            "phase2_efficacy":manually_documented(e,"phase2_efficacy",25,cutoff),
            "safety":manually_documented(e,"safety",15,cutoff),
            "phase3_design":manually_documented(e,"phase3_design",30,cutoff),
            "fda_alignment":manually_documented(e,"regulatory_alignment",15,cutoff),
            "issuer_check":(
                clean(e.get("issuer_readout_status")).upper()=="VERIFIED_UNRELEASED"
                and http(e.get("issuer_readout_source"))
                and in_time(e,cutoff,fields=("issuer_readout_checked_at",))
                and (day(e.get("actual_topline_release_date")) is None or
                     day(e.get("actual_topline_release_date"))>cutoff)
            ),
        }
        available=[label for label,k in INPUTS if checks[k]]
        missing=[label for label,k in INPUTS if not checks[k]]
        out.append({
            "NCT ID":nct, "Input Coverage %":round(len(available)/len(INPUTS)*100,1),
            "Available Inputs":len(available),
            "Missing Inputs":"; ".join(missing),
            "Issuer Check":"CHECKED — ANALYST DOCUMENTED" if checks["issuer_check"] else "NOT VERIFIED",
            **{label:("DOCUMENTED" if checks[key] else "MISSING / UNVERIFIED")
               for label,key in INPUTS},
        })
    detail=pd.DataFrame(out)
    coverage={label:int(detail[label].eq("DOCUMENTED").sum()) for label in CHECK_KEYS}
    return detail, coverage
