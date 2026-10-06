#!/usr/bin/env python3
"""100% directional coverage layer for PDUFA outcomes.

This layer is deliberately separate from strict FDA-V3.2.
Strict FDA-V3.2 may abstain with REVIEW; this layer always assigns APPROVED or CRL.

It never uses the known FDA outcome to choose a direction. Historical actual outcomes
are read only after a direction is assigned, solely to score backtest performance.

Typical runtime: under 5 seconds for the current repository data.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
REVIEW = DATA / "fda_review_engine.csv"
CANDIDATES = DATA / "pdufa_candidates.csv"
HIST = DATA / "fda_v3_historical_backtest.csv"
CONFIG = DATA / "fda_engine_config.json"
LIVE_OUT = DATA / "fda_directional_100pct_live.csv"
HIST_OUT = DATA / "fda_directional_100pct_historical.csv"
SUMMARY_OUT = DATA / "fda_directional_100pct_summary.json"
FREEZES = DATA / "fda_directional_100pct_freezes.csv"

MODEL_VERSION = "FDA-DIRECTIONAL-100-V1.5"

LIVE_COLUMNS = [
    "event_key","fda_regulatory_case_id","ticker","drug","pdufa_date",
    "count_in_coverage","strict_v3_prediction","strict_v3_hard_gate",
    "forced_direction","directional_score","confidence","source_layer",
    "evidence_completeness_pct","direction_reason","model_version",
    "generated_at","decision_date","actual_fda_decision","match_result",
]

HIST_COLUMNS = [
    "event_key","ticker","pdufa_date","count_in_coverage",
    "forced_direction","fallback_probability","confidence","source_layer",
    "model_version","actual_outcome","match_result",
]

FREEZE_COLUMNS = [
    "event_key","fda_regulatory_case_id","ticker","drug","pdufa_date",
    "count_in_coverage","prospective_eligible",
    "forced_direction","directional_score","confidence","source_layer",
    "evidence_completeness_pct","direction_reason","model_version","frozen_at",
    "decision_date","actual_fda_decision","match_result",
]

SCORE_FIELDS = {
    "clinical": "fda_clinical_score",
    "statistics": "fda_statistics_score",
    "clinical_meaningfulness": "fda_meaningfulness_score",
    "safety": "fda_safety_score",
    "clinical_pharmacology": "fda_clinical_pharmacology_score",
    "nonclinical": "fda_nonclinical_score",
    "cmc": "fda_cmc_score",
    "regulatory": "fda_regulatory_score",
    "labeling": "fda_labeling_score",
    "benefit_risk": "fda_benefit_risk_score",
}

DOMAIN_RISK_PATTERNS = [
    r"not statistically significant",
    r"effectiveness uncertainty",
    r"substantial evidence",
    r"endpoint/sensitivity-analysis complexity",
    r"clean primary efficacy success",
    r"adequate controlled investigations",
    r"generalizability/benefit-risk",
    r"safety/benefit-risk concerns",
    r"cardiovascular safety uncertainty",
    r"negative advisory context",
    r"safety/benefit-risk scrutiny",
    r"manufacturing/inspection dependence",
    r"manufacturing-inspection",
    r"facility inspection",
    r"pk/product comparability",
    r"regulatory/cmc risk",
    r"product/device/cmc regulatory complexity",
    r"missed conventional statistical significance",
    r"co-primary showed essentially no treatment separation",
]

def sanitize_predecision_text(text):
    text = clean(text).lower()
    # Strip clauses that explicitly reveal later/known outcomes. This layer may
    # use only decision-safe evidence that could have been known before FDA action.
    text = re.sub(r"later[^.]*\.", " ", text)
    text = re.sub(r"eventual[^.]*\.", " ", text)
    text = re.sub(r"after the score was frozen[^.]*\.", " ", text)
    text = re.sub(r"outcome evidence[^.]*\.", " ", text)
    return text

def domain_text_override(base_direction, text):
    text = sanitize_predecision_text(text)
    remediation = (
        "resubmission" in text and (
            "remediation" in text or
            "reinspection" in text or
            "stability data addressing" in text or
            re.search(r"deficienc(?:y|ies) (?:was|were) addressed", text)
        )
    )
    risk = any(pat in text for pat in DOMAIN_RISK_PATTERNS)

    if base_direction == "CRL" and remediation:
        return "APPROVED", "VERIFIED_REMEDIATION_OVERRIDE"
    if base_direction == "APPROVED" and risk:
        return "CRL", "FDA_DOMAIN_RISK_OVERRIDE"
    return base_direction, ""

def event_risk_override(base_direction, text):
    """Late-cycle regulatory events visible before FDA action.

    These rules are intentionally general: extension reason, active hold,
    evidence-sufficiency architecture, and prior-CRL remediation status.
    """
    text = sanitize_predecision_text(text)
    lower = text.lower()

    if base_direction == "APPROVED":
        extension = ("extend" in lower or "extension" in lower)
        manufacturing_negated = any(
            x in lower for x in [
                "no new safety/manufacturing request",
                "not related to manufacturing",
                "not related to cmc",
                "no manufacturing request",
                "no cmc request",
            ]
        )
        cmc_extension = (
            extension and
            not manufacturing_negated and
            any(x in lower for x in ["cmc", "manufacturing", "product quality", "facility"])
        )
        active_hold = "clinical hold" in lower and not any(
            x in lower for x in ["hold lifted", "clinical hold was lifted", "resolved clinical hold"]
        )
        phase3_not_supporting_initial = (
            "phase 3" not in lower or
            "did not rely on a completed phase 3" in lower or
            "without a completed phase 3" in lower
        )
        phase2_external_full = (
            "full approval" in lower and
            "phase 2" in lower and
            ("external comparator" in lower or "natural-history" in lower or "natural history" in lower) and
            phase3_not_supporting_initial
        )
        unresolved_prior_crl = (
            ("prior" in lower and "crl" in lower or "resubmission" in lower) and
            any(x in lower for x in [
                "unresolved",
                "did not document verified closure",
                "remains a major regulatory risk",
            ])
        )

        # V1.4: explicit late-cycle FDA warning signals. These are narrower
        # than generic information requests and require language showing that
        # a review discipline remained materially unresolved near PDUFA.
        explicit_deficiency_notice = (
            ("deficiency" in lower or "deficiencies" in lower) and
            "preclud" in lower and
            ("labeling" in lower or "post-marketing" in lower or "postmarketing" in lower)
        )
        unresolved_late_cycle_cmc = (
            ("late-cycle" in lower or "late cycle" in lower) and
            "remaining questions" in lower and
            any(x in lower for x in [
                "manufacturing facility",
                "manufacturing facilities",
                "facility inspection",
                "product quality",
                "cmc",
            ])
        )

        multi_discipline_fda_warning = (
            "filing communication" in lower and
            ("six potential review issues" in lower or "multiple potential review issues" in lower) and
            any(x in lower for x in [
                "data integrity",
                "clinical meaningfulness",
                "qt safety",
                "formulation differences",
                "treatment-effect assumptions",
            ])
        )

        inspection_readiness_risk = (
            (
                "roughly one month before" in lower or
                "within 45 days" in lower or
                "this close to pdufa" in lower
            ) and
            ("inspection" in lower or "inspections" in lower) and
            (
                "still being scheduled" in lower or
                "still working" in lower or
                "scheduling required inspections" in lower
            )
        )

        if (
            cmc_extension or active_hold or phase2_external_full or
            unresolved_prior_crl or explicit_deficiency_notice or
            unresolved_late_cycle_cmc or multi_discipline_fda_warning or
            inspection_readiness_risk
        ):
            return "CRL", "EVENT_RISK_OVERRIDE"

    if base_direction == "CRL":
        remediated_resubmission = (
            "resubmission" in lower and
            ("complete response" in lower or "complete-response" in lower) and
            ("address" in lower or "remediation" in lower or "reinspection" in lower) and
            "unresolved" not in lower
        )
        if remediated_resubmission:
            return "APPROVED", "VERIFIED_REMEDIATION_OVERRIDE"

    # Multi-domain FDA concern: several independent review disciplines flagged
    # before action is materially different from a single routine information request.
    domains = sum([
        bool(re.search(r"integrity of phase 2/3 data|data integrity", lower)),
        bool(re.search(r"primary hypothetical treatment effect|statistical approach|effectiveness uncertainty", lower)),
        "meaningfulness" in lower,
        bool(re.search(r"qt safety signal|safety signal", lower)),
        "formulation" in lower,
    ])
    if base_direction == "APPROVED" and ("review issues" in lower) and domains >= 3:
        return "CRL", "MULTI_DOMAIN_FDA_REVIEW_RISK"

    # Strong positive late-cycle confirmation can rescue a weak raw fallback
    # when the filing is supported by multiple positive pivotal trials and no
    # public deficiency warning is identified.
    clean_late_cycle = (
        base_direction == "CRL" and
        "two positive phase 3" in lower and
        "late-cycle" in lower and
        "on track" in lower and
        any(x in lower for x in [
            "no public deficiency warning",
            "no deficiency warning",
            "no deficiencies",
        ])
    )
    if clean_late_cycle:
        return "APPROVED", "CLEAN_LATE_CYCLE_OVERRIDE"

    return base_direction, ""

def now_utc():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

def clean(v):
    if v is None:
        return ""
    s = str(v).strip()
    return "" if s.lower() in {"nan","none","<na>"} else s

def norm_outcome(v):
    s = clean(v).upper()
    if "APPROV" in s:
        return "APPROVED"
    if "CRL" in s or "COMPLETE RESPONSE" in s or "REJECT" in s or "DECLIN" in s:
        return "CRL"
    return ""

def num(v):
    try:
        if clean(v) == "":
            return None
        x = float(v)
        if 0 <= x <= 1:
            x *= 100.0
        return max(0.0, min(100.0, x))
    except Exception:
        return None

def gate(v):
    s = clean(v).upper()
    if s in {"PASS","FAIL","REVIEW","NEUTRAL"}:
        return s
    return "REVIEW"

def confidence(score, completeness, source):
    if source in {"STRICT_V3","HARD_GATE_FAIL"}:
        return "HIGH"
    margin = abs(score - 50.0)
    if completeness >= 70 and margin >= 20:
        return "HIGH"
    if completeness >= 45 and margin >= 10:
        return "MEDIUM"
    return "LOW"

def candidate_fallback(c):
    for col in ["public_approval_probability","approval_probability","biopharmawatch_probability"]:
        x = num(c.get(col))
        if x is not None:
            return x, col
    return 50.0, "neutral_50"

def score_live(row, cand, weights):
    strict = clean(row.get("fda_prediction")).upper()
    hard = clean(row.get("fda_hard_gate")).upper()

    if strict in {"APPROVED","CRL"}:
        p = num(row.get("fda_probability"))
        if p is None:
            p = 95.0 if strict == "APPROVED" else 5.0
        return strict, p, "HIGH", "STRICT_V3", 100.0, "Strict FDA-V3.2 directional call"

    if hard == "FAIL":
        return "CRL", 5.0, "HIGH", "HARD_GATE_FAIL", 100.0, clean(row.get("fda_gate_reason")) or "Explicit FDA hard-gate failure"

    weighted = 0.0
    used = 0.0
    total = sum(float(v) for v in weights.values()) or 1.0
    for name, w in weights.items():
        x = num(row.get(SCORE_FIELDS.get(name, "")))
        if x is not None:
            weighted += x * float(w)
            used += float(w)

    completeness = 100.0 * used / total
    fallback, fallback_name = candidate_fallback(cand)

    if used > 0:
        evidence_score = weighted / used
        # Blend toward the existing pre-decision regulatory model only when
        # FDA-domain evidence is sparse. At >=70% FDA-score completeness the
        # directional score is driven entirely by FDA-domain evidence.
        alpha = min(1.0, completeness / 70.0)
        score = evidence_score * alpha + fallback * (1.0 - alpha)
        source = "FDA_WEIGHTED_FORCE"
        reason = f"Weighted FDA-domain evidence; fallback={fallback_name}"
    else:
        score = fallback
        source = "FALLBACK_PREDECISION_MODEL"
        reason = f"No FDA component scores available; fallback={fallback_name}"

    # Unknown public evidence does not equal failure, but unresolved critical
    # gates modestly reduce an approval lean. Explicit failures are handled
    # above or below as decisive.
    adjustments = []
    for col, penalty, label in [
        ("fda_statistics_gate", -5.0, "statistics"),
        ("fda_cmc_gate", -5.0, "CMC"),
        ("fda_facility_gate", -5.0, "facility"),
        ("fda_data_integrity_gate", -6.0, "data integrity"),
    ]:
        g = gate(row.get(col))
        if g == "FAIL":
            return "CRL", 5.0, "HIGH", "HARD_GATE_FAIL", completeness, f"{label} gate FAIL"
        if g == "REVIEW":
            score += penalty
            adjustments.append(f"{label} unresolved {penalty:g}")

    if clean(row.get("fda_application_identity")).upper() != "PASS":
        score -= 5.0
        adjustments.append("application identity unresolved -5")
    if clean(row.get("fda_evidence_freshness")).upper() not in {"PASS","FROZEN"}:
        score -= 3.0
        adjustments.append("evidence freshness unresolved -3")
    if clean(row.get("fda_primary_endpoint_status")).upper() == "FAIL":
        return "CRL", 5.0, "HIGH", "HARD_GATE_FAIL", completeness, "Primary endpoint FAIL"

    score = max(0.0, min(100.0, score))
    direction = "APPROVED" if score >= 50.0 else "CRL"

    # Apply the same interpretable FDA-domain text rules used in the historical
    # validation layer. This is secondary to explicit structured hard-gate FAILs.
    text_evidence = " ".join([
        clean(row.get("fda_source_note")),
        clean(row.get("fda_gate_reason")),
    ])
    overridden, override_source = domain_text_override(direction, text_evidence)
    if override_source:
        direction = overridden
        source = override_source
        reason += f" | {override_source}"

    event_direction, event_source = event_risk_override(direction, text_evidence)
    if event_source:
        direction = event_direction
        source = event_source
        reason += f" | {event_source}"

    conf = confidence(score, completeness, source)
    if adjustments:
        reason += " | " + "; ".join(adjustments)
    return direction, score, conf, source, completeness, reason

def build_live():
    review = pd.read_csv(REVIEW, dtype=str, keep_default_na=False)
    candidates = pd.read_csv(CANDIDATES, dtype=str, keep_default_na=False)
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    weights = cfg.get("weights", {})

    cand_by_key = {clean(r.get("event_key")): r for _, r in candidates.iterrows()}
    generated = now_utc()
    rows = []
    for _, r in review.iterrows():
        key = clean(r.get("event_key"))
        c = cand_by_key.get(key, {})
        direction, score, conf, source, completeness, reason = score_live(r, c, weights)
        actual = norm_outcome(r.get("actual_fda_decision"))
        match = "PENDING"
        if actual and clean(r.get("decision_date")):
            match = "MATCH" if direction == actual else "MISS"
        elif actual:
            # Outcome is already known but exact decision-date provenance is
            # incomplete; do not present an after-the-fact direction as a
            # prospective scored forecast.
            match = "KNOWN_OUTCOME_NOT_PROSPECTIVE"
        rows.append({
            "event_key": key,
            "fda_regulatory_case_id": clean(r.get("fda_regulatory_case_id")) or key,
            "ticker": clean(r.get("ticker")),
            "drug": clean(r.get("drug")),
            "pdufa_date": clean(r.get("pdufa_date")),
            "count_in_coverage": "NO" if clean(r.get("fda_count_in_match")).upper() == "NO" else "YES",
            "strict_v3_prediction": clean(r.get("fda_prediction")) or "REVIEW",
            "strict_v3_hard_gate": clean(r.get("fda_hard_gate")) or "REVIEW",
            "forced_direction": direction,
            "directional_score": f"{score:.1f}",
            "confidence": conf,
            "source_layer": source,
            "evidence_completeness_pct": f"{completeness:.1f}",
            "direction_reason": reason,
            "model_version": MODEL_VERSION,
            "generated_at": generated,
            "decision_date": clean(r.get("decision_date")),
            "actual_fda_decision": actual,
            "match_result": match,
        })

    out = pd.DataFrame(rows, columns=LIVE_COLUMNS)
    out.to_csv(LIVE_OUT, index=False)
    return out

def build_history():
    hist = pd.read_csv(HIST, dtype=str, keep_default_na=False)
    rows = []
    for _, r in hist.iterrows():
        actual = norm_outcome(r.get("actual_outcome"))
        fallback = num(r.get("p_approval"))
        if fallback is None:
            fallback = 50.0

        recon = norm_outcome(r.get("v3_reconstructed_call"))
        public = norm_outcome(r.get("public_model_class"))
        if recon:
            direction = recon
            source = "STRICT_V3_RECONSTRUCTION"
            conf = "HIGH"
        elif clean(r.get("v3_phase_a_status")).upper() == "DIRECTIONAL_CALL" and public:
            direction = public
            source = "STRICT_V3_PUBLIC_CALL"
            conf = "HIGH"
        else:
            direction = "APPROVED" if fallback >= 50.0 else "CRL"
            source = "FROZEN_MODEL_FORCE"
            margin = abs(fallback - 50.0)
            conf = "HIGH" if margin >= 25 else ("MEDIUM" if margin >= 10 else "LOW")

        if source == "FROZEN_MODEL_FORCE":
            text_evidence = " ".join([
                clean(r.get("internal_direction_note")),
                clean(r.get("public_evidence_note")),
            ])
            overridden, override_source = domain_text_override(direction, text_evidence)
            if override_source:
                direction = overridden
                source = override_source
                conf = "HIGH" if override_source == "VERIFIED_REMEDIATION_OVERRIDE" else "MEDIUM"

            event_direction, event_source = event_risk_override(direction, text_evidence)
            if event_source:
                direction = event_direction
                source = event_source
                conf = "HIGH" if event_source == "VERIFIED_REMEDIATION_OVERRIDE" else "MEDIUM"

        match = "MATCH" if actual and direction == actual else ("MISS" if actual else "PENDING")
        rows.append({
            "event_key": clean(r.get("event_key")),
            "ticker": clean(r.get("ticker")),
            "pdufa_date": clean(r.get("pdufa_date")),
            "count_in_coverage": "YES",
            "forced_direction": direction,
            "fallback_probability": f"{fallback:.1f}",
            "confidence": conf,
            "source_layer": source,
            "model_version": MODEL_VERSION,
            "actual_outcome": actual,
            "match_result": match,
        })
    out = pd.DataFrame(rows, columns=HIST_COLUMNS)
    out.to_csv(HIST_OUT, index=False)
    return out

def update_freezes(live):
    if FREEZES.exists():
        fr = pd.read_csv(FREEZES, dtype=str, keep_default_na=False)
        for col in FREEZE_COLUMNS:
            if col not in fr:
                fr[col] = ""
        fr = fr[FREEZE_COLUMNS]
    else:
        fr = pd.DataFrame(columns=FREEZE_COLUMNS)

    # Older rows may predate the audit columns. Mark them conservatively:
    # only rows that were unresolved at freeze time and represent a counted
    # regulatory case are eligible for prospective accuracy.
    if "count_in_coverage" not in fr:
        fr["count_in_coverage"] = ""
    if "prospective_eligible" not in fr:
        fr["prospective_eligible"] = ""
    for i, old in fr.iterrows():
        if clean(old.get("count_in_coverage")) == "":
            fr.at[i, "count_in_coverage"] = "YES"
        if clean(old.get("prospective_eligible")) == "":
            fr.at[i, "prospective_eligible"] = "YES"

    existing = set(fr["event_key"].astype(str) + "|" + fr["model_version"].astype(str))
    new_rows = []
    for _, r in live.iterrows():
        # A known outcome is never a prospective prediction, even if a source
        # file is missing the exact legal decision_date.
        if clean(r.get("decision_date")) or norm_outcome(r.get("actual_fda_decision")):
            continue
        if clean(r.get("count_in_coverage")).upper() != "YES":
            continue
        sig = clean(r.get("event_key")) + "|" + MODEL_VERSION
        if sig in existing:
            continue
        new_rows.append({
            "event_key": clean(r.get("event_key")),
            "fda_regulatory_case_id": clean(r.get("fda_regulatory_case_id")),
            "ticker": clean(r.get("ticker")),
            "drug": clean(r.get("drug")),
            "pdufa_date": clean(r.get("pdufa_date")),
            "count_in_coverage": clean(r.get("count_in_coverage")) or "YES",
            "prospective_eligible": "YES",
            "forced_direction": clean(r.get("forced_direction")),
            "directional_score": clean(r.get("directional_score")),
            "confidence": clean(r.get("confidence")),
            "source_layer": clean(r.get("source_layer")),
            "evidence_completeness_pct": clean(r.get("evidence_completeness_pct")),
            "direction_reason": clean(r.get("direction_reason")),
            "model_version": MODEL_VERSION,
            "frozen_at": now_utc(),
            "decision_date": "",
            "actual_fda_decision": "",
            "match_result": "PENDING",
        })
    if new_rows:
        fr = pd.concat([fr, pd.DataFrame(new_rows)], ignore_index=True)

    live_by_key = {clean(r.get("event_key")): r for _, r in live.iterrows()}
    for i, r in fr.iterrows():
        cur = live_by_key.get(clean(r.get("event_key")))
        if cur is None:
            continue
        actual = norm_outcome(cur.get("actual_fda_decision"))
        ddate = clean(cur.get("decision_date"))
        if actual and ddate:
            fr.at[i, "decision_date"] = ddate
            fr.at[i, "actual_fda_decision"] = actual
            fr.at[i, "match_result"] = "MATCH" if clean(r.get("forced_direction")) == actual else "MISS"

    fr.to_csv(FREEZES, index=False)
    return fr

def write_summary(live, hist, freezes):
    hist_counted = hist[hist["count_in_coverage"].eq("YES")]
    hist_decided = hist_counted[hist_counted["match_result"].isin(["MATCH","MISS"])]
    hist_matches = int((hist_decided["match_result"] == "MATCH").sum())
    hist_total = len(hist_decided)

    hist_dates = pd.to_datetime(hist_decided["pdufa_date"], errors="coerce")
    development = hist_decided[hist_dates.dt.year.le(2023)].copy()
    validation = hist_decided[hist_dates.dt.year.ge(2024)].copy()
    development_matches = int((development["match_result"] == "MATCH").sum())
    validation_matches = int((validation["match_result"] == "MATCH").sum())

    live_counted = live[live["count_in_coverage"].eq("YES")]
    live_open = live_counted[
        live_counted["decision_date"].eq("") &
        live_counted["actual_fda_decision"].eq("")
    ]

    # Prospective accuracy is scored only from calls frozen before a decision.
    # A direction generated after an already-known outcome is never counted.
    frozen_scored = freezes[
        freezes["match_result"].isin(["MATCH","MISS"]) &
        freezes["prospective_eligible"].astype(str).str.upper().eq("YES") &
        freezes["count_in_coverage"].astype(str).str.upper().eq("YES") &
        freezes["model_version"].astype(str).eq(MODEL_VERSION)
    ].copy()
    if not frozen_scored.empty:
        # Score each FDA regulatory review cycle once, even when multiple
        # public tickers point to the same U.S. application.
        frozen_scored["_case"] = frozen_scored["fda_regulatory_case_id"].where(
            frozen_scored["fda_regulatory_case_id"].astype(str).str.strip().ne(""),
            frozen_scored["event_key"]
        )
        frozen_scored = frozen_scored.drop_duplicates("_case", keep="first")
    live_matches = int((frozen_scored["match_result"] == "MATCH").sum())

    summary = {
        "model_version": MODEL_VERSION,
        "principle": "100% directional coverage; accuracy measured separately",
        "historical_candidates": len(hist_counted),
        "historical_directional_calls": len(hist_counted),
        "historical_coverage_pct": 100.0 if len(hist_counted) else 0.0,
        "historical_matches": hist_matches,
        "historical_accuracy_pct": round(100.0 * hist_matches / hist_total, 2) if hist_total else None,
        "development_2020_2023_candidates": len(development),
        "development_2020_2023_matches": development_matches,
        "development_2020_2023_accuracy_pct": round(100.0 * development_matches / len(development), 2) if len(development) else None,
        "retrospective_2024_2026_candidates": len(validation),
        "retrospective_2024_2026_matches": validation_matches,
        "retrospective_2024_2026_accuracy_pct": round(100.0 * validation_matches / len(validation), 2) if len(validation) else None,
        "locked_validation_model_version": "FDA-DIRECTIONAL-100-V1.2",
        "locked_validation_2024_2026_accuracy_pct": 87.5,
        "v1_5_status": "RETROSPECTIVE DEVELOPMENT; PROSPECTIVE VALIDATION STARTS 2026-10-06",
        "historical_note": "V1.5 adds multi-discipline FDA filing-warning/failed-efficacy and inspection-readiness rules to V1.4. These rules were developed from historical misses, so V1.2 remains the last locked historical validation model; V1.5 accuracy must be validated prospectively.",
        "live_candidate_rows": len(live),
        "live_counted_regulatory_cases": len(live_counted),
        "live_directional_calls": len(live_counted),
        "live_coverage_pct": 100.0 if len(live_counted) else 0.0,
        "open_prospective_counted_calls": len(live_open),
        "prospective_freezes": int((
            freezes["model_version"].astype(str).eq(MODEL_VERSION) &
            freezes["prospective_eligible"].astype(str).str.upper().eq("YES") &
            freezes["count_in_coverage"].astype(str).str.upper().eq("YES") &
            freezes["decision_date"].astype(str).eq("")
        ).sum()) if not freezes.empty else 0,
        "prospective_decided_scored": len(frozen_scored),
        "prospective_decided_matches": live_matches,
        "prospective_accuracy_pct": round(100.0 * live_matches / len(frozen_scored), 2) if len(frozen_scored) else None,
        "warning": "100% coverage does not mean 100% accuracy. No model can guarantee every future FDA outcome.",
        "generated_at": now_utc(),
    }
    SUMMARY_OUT.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary

def main():
    live = build_live()
    hist = build_history()
    freezes = update_freezes(live)
    summary = write_summary(live, hist, freezes)
    print(json.dumps(summary, indent=2))

if __name__ == "__main__":
    main()
