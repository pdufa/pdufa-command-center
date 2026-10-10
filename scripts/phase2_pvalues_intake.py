"""Collect published Phase 2 primary-endpoint p-values for linked Phase 3 candidates.

This is an EVIDENCE ledger, not an automatic Phase 3-success score.
No Phase 3 results are consumed. Each source has a registry publication date.
"""
import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
FIELDS = ["phase2_nct_id", "phase3_nct_id", "ticker", "program_key",
          "result_first_posted", "primary_endpoint", "p_value", "p_value_modifier",
          "statistical_method", "effect_parameter", "effect_value", "ci_lower",
          "ci_upper", "source_url", "checked_at", "evidence_status"]


def read(path):
    if not Path(path).exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def linked_trials(rows):
    links = {}
    for r in rows:
        if r.get("phases", "").upper() != "PHASE3":
            continue
        phase3 = r.get("nct_id", "")
        if not re.fullmatch(r"NCT\\d{8}", phase3):
            continue
        for phase2 in set(re.findall(r"NCT\\d{8}", r.get("phase2_nct_ids", ""))):
            if phase2 != phase3:
                links.setdefault(phase2, set()).add(
                    (phase3, r.get("ticker", ""), r.get("program_key", "")))
    return links


def fetch(nct):
    req = Request("https://clinicaltrials.gov/api/v2/studies/" + nct,
                  headers={"User-Agent": "PDUFA-Research/1.0", "Accept": "application/json"})
    with urlopen(req, timeout=35) as resp:
        return json.load(resp)


def evidence_from_study(nct, study, checked_at):
    protocol = study.get("protocolSection") or {}
    status = protocol.get("statusModule") or {}
    phase = (protocol.get("designModule") or {}).get("phases") or []
    posted = (status.get("resultsFirstPostDateStruct") or {}).get("date", "")
    if "PHASE2" not in phase or not re.fullmatch(r"\\d{4}-\\d{2}-\\d{2}", posted):
        return []
    measures = ((study.get("resultsSection") or {}).get("outcomeMeasuresModule") or {}).get("outcomeMeasures") or []
    rows = []
    for measure in measures:
        if str(measure.get("type", "")).upper() != "PRIMARY":
            continue
        for item in measure.get("analyses") or []:
            value = str(item.get("pValue") or "").strip()
            if not value:
                continue
            rows.append({
                "result_first_posted": posted,
                "primary_endpoint": str(measure.get("title") or ""),
                "p_value": value,
                "p_value_modifier": str(item.get("pValueModifier") or ""),
                "statistical_method": str(item.get("statisticalMethod") or ""),
                "effect_parameter": str(item.get("paramType") or ""),
                "effect_value": str(item.get("paramValue") or ""),
                "ci_lower": str(item.get("ciLowerLimit") or ""),
                "ci_upper": str(item.get("ciUpperLimit") or ""),
                "source_url": "https://clinicaltrials.gov/study/" + nct,
                "checked_at": checked_at,
                "evidence_status": "PHASE2_PRIMARY_P_RECORDED_NOT_ADJUDICATED",
            })
    return rows


def collect(data_dir=DATA, fetcher=fetch):
    data_dir = Path(data_dir)
    links = linked_trials(read(data_dir / "phase_pipeline.csv"))
    saved = read(data_dir / "phase2_primary_pvalues.csv")
    # Retain older records if the registry API fails.
    by_nct = {}
    for r in saved:
        by_nct.setdefault(r.get("phase2_nct_id", ""), []).append(r)
    now = datetime.now(timezone.utc).isoformat()
    errors = {}
    for nct, assignments in sorted(links.items()):
        try:
            study = fetcher(nct)
            rows = evidence_from_study(nct, study, now)
            # Updated links may differ even if p-values did not change.
            by_nct[nct] = [
                {"phase2_nct_id": nct, "phase3_nct_id": phase3,
                 "ticker": ticker, "program_key": program, **evidence}
                for phase3, ticker, program in sorted(assignments)
                for evidence in rows
            ]
        except Exception as exc:
            errors[nct] = str(exc)[:200]
    flat = [r for key in sorted(by_nct) for r in by_nct[key]]
    data_dir.mkdir(parents=True, exist_ok=True)
    with (data_dir / "phase2_primary_pvalues.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(flat)
    unique_p2 = {r["phase2_nct_id"] for r in flat if r.get("p_value", "").strip()}
    p3_linked = {r["phase3_nct_id"] for r in flat if r.get("p_value", "").strip()}
    state = {
        "checked_at": now, "linked_phase2_trials": len(links),
        "phase2_trials_with_recorded_primary_p": len(unique_p2),
        "linked_phase3_trials_with_phase2_p": len(p3_linked),
        "primary_p_analysis_rows": len(flat),
        "api_errors": len(errors), "errors": errors,
        "status": "COMPLETE" if not errors else "PARTIAL",
        "note": "Published Phase 2 primary-endpoint p-values, not trial success. "
                "An original publication date before the target Phase 3 readout is required.",
    }
    (data_dir / "phase2_pvalues_status.json").write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in state.items() if k != "errors"}, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(collect(Path(sys.argv[1]) if len(sys.argv) > 1 else DATA))
