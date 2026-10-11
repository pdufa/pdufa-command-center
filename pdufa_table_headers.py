"""Shared help headers for PDUFA tables; source field names never change."""
import re

import pandas as pd
from pandas.io.formats.style import Styler
import streamlit as st


HELP_ICON = "?\u20dd"
FIELD_HELP = {
    "ticker": "Stock-market ticker identifying the company. Trial and FDA evidence must still match the exact drug and event.",
    "company": "Company associated with this trial or FDA application.",
    "drug": "Drug, biologic or program associated with this exact record.",
    "indication": "Disease, condition or proposed use studied for this drug.",
    "nct id": "Unique ClinicalTrials.gov trial identifier. Separate trials for one company must not share results automatically.",
    "nct": "Unique ClinicalTrials.gov trial identifier.",
    "score /100": "Displayed research score out of 100, using the model named in Score type. Higher scores appear first by default. Blank means not scored; this is not a calibrated FDA approval probability.",
    "score type": "Identifies the clinical, evidence or research-priority model behind Score /100. Scores from different models are not interchangeable.",
    "pdufa date": "Saved FDA target decision date for this exact application. Check the adjacent source and verification status.",
    "pdufa target": "Saved FDA target decision date for this exact application. A reported target must be verified against its source.",
    "days to pdufa": "Calendar days from today to the displayed PDUFA date. Negative means past due; blank means no usable date. Equal scores sort by this value highest first.",
    "days left": "Calendar days from today to the PDUFA target date. Negative means the date has passed; blank means no usable date.",
    "date classification": "Countdown band for the displayed PDUFA date: 90+, 90–61, 60–31, 30–14, 13–1, decision day, or past/recheck.",
    "dates": "PDUFA countdown category assigned to this program. NO PDUFA YET means there is no linked target date.",
    "stage": "Saved stage for the exact clinical program or regulatory application; a trial phase alone does not confirm a successful readout.",
    "current stage": "Latest reconciled clinical or regulatory stage of this program, rather than a historical milestone.",
    "pipeline stage": "Clinical or regulatory stage from the linked pipeline record.",
    "trial phase": "Development phase recorded for the exact trial; this is not proof that results are positive or publicly released.",
    "registered phase": "Development phase recorded in the trial registry.",
    "trial status": "Registry recruitment or study status. Completion alone does not confirm a corporate topline readout.",
    "f": "Separate financing cycle: F START = started, F RUN = running, F CLOSED = source-supported closure, F UNKNOWN = not verified. This is not the trade lifecycle.",
    "primary p": "Reported p-value for a primary trial endpoint. Read with the exact trial, endpoint, effect size and statistical plan; it is not FDA approval probability.",
    "cash runway (months)": "Source-reported or reviewed estimate of months of cash coverage. Check Cash Runway As Of; blank means unavailable.",
    "cash runway as of": "Date associated with the cash-runway estimate, which may differ from the current date.",
    "market cap": "Saved company market capitalization, rather than a live quote.",
    "count": "Number of matching source records in this category under the current filters; not a count of patients.",
    "watchlist": "Whether this ticker is included in your session watchlist.",
    "add to analysis": "Check to add this ticker to Analysis; uncheck to remove it.",
    "add to invest": "Check to add this ticker to Invest; this does not place an order.",
    "planned exit (-7 days)": "Research exit cutoff seven calendar days before the applicable PDUFA date. It is not an executed sale.",
    "entry qualification": "Result of the saved post-readout clinical, financing and regulatory research gates; not an automatic trade instruction.",
    "source": "Link to the source supporting this saved record. Review the source and the date before relying on the field.",
    "results posted": "Whether results are recorded as posted in the registry. Registry posting and issuer topline announcements are separate events.",
}



LEGACY_FIELD_HELP = {
    "ticker": "Public-company ticker. Click the ticker to open the event detail page.",
    "pdufa date": "FDA target action date for this application/review cycle.",
    "decision date": "Actual FDA decision/action posting date. Once populated from a verified FDA decision, the PDUFA matter is closed/decided.",
    "pdufa": "FDA target action date for this application/review cycle.",
    "suggestion %": "ChatGPT/model pre-decision probability of FDA approval for this event.",
    "suggestion": "Suggestion in words from SUGGESTION %: PASS at 50% or higher; CRL below 50%.",
    "fda model %": "FDA-only regulatory approval probability. Trading variables are excluded.",
    "fda call": "FDA-only directional call: APPROVED, CRL, or REVIEW.",
    "fda gate": "FDA-like hard-gate status: PASS, FAIL, or REVIEW/unknown.",
    "fda decision": "Final FDA outcome when resolved. Future or unresolved events show PENDING.",
    "match %": "Historical direction match: 100% when the model direction matched the final FDA outcome, 0% when it missed; blank before a final outcome.",
    "p%": "All-sources model probability of FDA approval for this event.",
    "p": "Reported pivotal/Phase 3 p-value evidence saved for the event.",
    "f": "Model-predicted FDA direction: APPROVED, CRL, or REVIEW.",
    "c": "Combined display of the approval probability and model FDA direction.",
    "probability of approval % — public": "Approval probability using public-source evidence only.",
    "probability of approval % — all sources": "Approval probability using all permitted saved evidence sources.",
    "public p%": "Approval probability using public-source evidence only.",
    "i direction": "Internal-evidence direction call.",
    "p direction": "Public-evidence direction call.",
    "all-source direction": "Direction call using all permitted evidence sources.",
    "direction / fda match": "Predicted FDA direction before decision; after decision, shows whether the direction matched the FDA result.",
    "company": "Issuer/company associated with the PDUFA event.",
    "drug": "Drug, biologic, or product under FDA review.",
    "indication": "Disease/condition or use being reviewed by FDA.",
    "days left": "Calendar days from today to the PDUFA target date.",
    "market cap": "Saved market capitalization for the company/event.",
    "historical market cap": "Historical market capitalization used for this validation event.",
    "market cap bucket": "Market-cap range assigned to this event.",
    "cap bucket": "Market-cap range assigned to this event.",
    "trade score": "Saved trading-setup score; separate from FDA approval probability.",
    "outcome": "Current/final FDA outcome when known.",
    "actual fda outcome": "Final FDA decision used to score the historical prediction.",
    "model prediction": "Frozen model direction predicted before the FDA decision.",
    "correct / wrong": "Whether Model Prediction matches Actual FDA Outcome.",
    "time": "Current PDUFA timing/window status.",
    "signal": "Saved trading/setup signal.",
    "confidence": "Saved model confidence label.",
    "application": "FDA application type when known.",
    "n": "NDA/sNDA indicator. A check means the exact application is verified as an NDA-family filing.",
    "b": "BLA/sBLA indicator. A check means the exact application is verified as a BLA-family filing.",
    "announced": "Second post-Phase-3 financing has been verified as announced.",
    "running": "Second post-Phase-3 financing has been verified as in progress.",
    "closed": "Second post-Phase-3 financing has been verified as closed.",
    "financing": "Saved financing status for the company/event.",
    "phase": "Current trading/PDUFA workflow phase.",
    "short %": "Saved short interest as a percentage of float.",
    "iv (30d)": "Saved 30-day implied-volatility measure.",
    "record source": "Whether this row comes from the live saved feed or historical model set.",
    "v2 status": "Prediction Engine V2 validation/gating status.",
    "audit status": "Historical audit status for this event.",
    "failure reason": "Reason an audited row failed, was blocked, or required repair.",
    "canonical pdufa": "Verified canonical PDUFA date used after audit/reconciliation.",
    "audit action": "Audit repair or disposition applied to the row.",
    "needs rescore": "Whether the event still requires a decision-safe model rescore.",
    "count in adjusted accuracy": "Whether this row is eligible for the adjusted historical accuracy calculation.",
    "audit source": "Source used to verify the historical audit result.",
    "validation period": "Validation cohort/period assigned to the event.",
    "validation role": "Whether the row is tuning, retrospective, holdout, or other validation role.",
    "v2 call": "Prospective V2 direction call after the V2 evidence gates.",
    "v2 confidence": "Confidence assigned to the V2 call.",
    "v2 gate reason": "Reason the V2 gate allowed, blocked, or abstained on the call.",
    "pdufa verification": "Status of the saved evidence confirming the exact PDUFA event/date.",
    "phase 3": "Status of the pivotal/Phase 3 evidence for this event.",
    "eligibility": "Whether the event passes the saved monitoring eligibility rules.",
    "conflict": "Saved evidence-conflict flag for the event."
}
for _field, _help in LEGACY_FIELD_HELP.items():
    FIELD_HELP.setdefault(_field, _help)

def _name(column):
    return re.sub(r"[_\s]+", " ", str(column).strip()).casefold()


def column_help(column):
    name = _name(column)
    if name in FIELD_HELP:
        return FIELD_HELP[name]
    label = str(column).replace("_", " ").strip()
    if " · " in label:
        source, field = label.split(" · ", 1)
        return f"{source} source field. {column_help(field)}"
    points = re.search(r"/(\d+)$", name)
    if points:
        maximum = int(points.group(1))
        if maximum == 100:
            return f"{label}: research score out of 100 under its named model. Blank means not scored; this is not an FDA approval probability."
        return f"{label}: component of the named research rubric, worth up to {maximum} points. Blank means the component is unavailable, not a zero."
    if "p value" in name or "primary p" in name:
        return "Reported statistical p-value or its exact-trial evidence. Read with the endpoint and study design; rounded 0.0000 need not mean an exact zero."
    if "rank" in name:
        return f"{label}: position in its research-review worklist. Lower ranks indicate earlier review under that rubric, not FDA approval probability."
    if any(term in name for term in ("source", "url", "link")):
        return f"{label}: saved source reference or exact-record evidence link. A link alone is not independent verification."
    if any(term in name for term in ("checked", "as of", "updated", "cutoff")):
        return f"{label}: saved observation, update or validity timestamp. Check it to determine whether this field is current."
    if "runway" in name:
        return f"{label}: source-supported cash-coverage estimate or its verification status. Blank means unavailable."
    if any(term in name for term in ("missing", "gap", "next action", "next step")):
        return f"{label}: unresolved evidence or the research follow-up needed for this exact record."
    if "date" in name or "completion" in name or "readout" in name:
        return f"{label}: saved milestone date or readout evidence for this exact program. Check the source; scheduled, registry and publicly announced dates can differ."
    if "financ" in name or "offering" in name or "dilution" in name:
        return f"{label}: saved financing or dilution evidence for the exact company/event. Verify announcement, progress and actual closure separately."
    if "status" in name or "gate" in name or "qualification" in name:
        return f"{label}: saved research or verification status for this record. REVIEW or missing data does not confirm a pass."
    return f"{label}: source-supplied field for this company, trial or FDA event. Read with its source and as-of date; blank means unavailable."


def header_config(data, config=None):
    """Decorate visible labels and supply tooltips without changing column keys."""
    frame = data.data if isinstance(data, Styler) else data
    if not hasattr(frame, "columns"):
        frame = pd.DataFrame(frame)
    result = dict(config or {})
    for column in frame.columns:
        original = result.get(column)
        if column in result and original is None:
            continue  # Deliberately hidden editor/source field.
        entry = dict(original) if isinstance(original, dict) else {"label": original}
        label = str(entry.get("label") or column)
        label = label.replace(HELP_ICON, "").replace("ⓘ", "").strip()
        entry["label"] = f"{HELP_ICON} {label}"
        help_text = entry.get("help")
        if (not help_text or help_text == str(column) or
                str(help_text).startswith(("Watchlist event field:", "Analysis event field:"))):
            entry["help"] = column_help(column)
        result[column] = entry
    return result


def pdufa_dataframe(data, **kwargs):
    kwargs["column_config"] = header_config(data, kwargs.get("column_config"))
    return st.dataframe(data, **kwargs)


def pdufa_editor(data, **kwargs):
    kwargs["column_config"] = header_config(data, kwargs.get("column_config"))
    return st.data_editor(data, **kwargs)
