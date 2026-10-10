#!/usr/bin/env python3
"""Collect original, prospectively observed Phase 2 primary p-value analyses.

Never treat these as Phase 3 results or as a success probability. Only exact
Phase 2 NCT links from currently eligible Phase 3 pre-readout programs are read.
Individual result p-values may have been published later than results-first-posted:
first_verified_at_utc is the defensible date of initial observation.
"""
import argparse
import csv
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from zoneinfo import ZoneInfo

import pandas as pd
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pre_readout_score import candidate_queue

FIELDS = [
    "observation_id", "nct_id", "ticker", "primary_endpoint",
    "comparison", "p_value", "p_value_modifier", "statistical_method",
    "results_first_posted", "observed_at_utc", "source_url",
    "protocol_last_update",
]

def load_csv(path):
    if not Path(path).exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str, keep_default_na=False)

def fetch_study(nct):
    url = "https://clinicaltrials.gov/api/v2/studies/" + nct
    for attempt in range(4):
        try:
            with urlopen(Request(url, headers={
                "User-Agent": "PDUFA-Phase2-P-Evidence/1.0",
                "Accept": "application/json",
            }), timeout=35) as reply:
                return json.load(reply)
        except HTTPError as exc:
            if exc.code in (400, 401, 403, 404) or attempt == 3:
                raise
            header = exc.headers.get("Retry-After") if exc.headers else None
            delay = int(header) if header and header.isdigit() else 2 ** (attempt + 1)
            time.sleep(min(60, max(2, delay)))
        except (URLError, TimeoutError, OSError):
            if attempt == 3:
                raise
            time.sleep(2 ** (attempt + 1))

def extract(study, expected_nct, ticker, observed_at):
    p = study.get("protocolSection") or {}
    nct = (p.get("identificationModule") or {}).get("nctId") or ""
    if nct != expected_nct:
        raise ValueError("Registry study ID mismatch")
    phases = (p.get("designModule") or {}).get("phases") or []
    if "PHASE2" not in phases:
        return [], "NOT_PHASE2"
    status = p.get("statusModule") or {}
    posted = (status.get("resultsFirstPostDateStruct") or {}).get("date") or ""
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", posted):
        return [], "NO_REGISTRY_RESULTS_DATE"
    if posted > observed_at[:10]:
        return [], "FUTURE_RESULTS_DATE"
    measures = ((study.get("resultsSection") or {}).get("outcomeMeasuresModule") or {}).get("outcomeMeasures") or []
    rows = []
    for m in measures:
        if m.get("type") != "PRIMARY":
            continue
        title = str(m.get("title") or "").strip()
        for analysis in m.get("analyses") or []:
            val = str(analysis.get("pValue") or "").strip()
            if not val or not title:
                continue
            info = {
                "nct_id": nct, "ticker": ticker, "primary_endpoint": title,
                "comparison": " | ".join(str(x) for x in analysis.get("groupIds") or []),
                "p_value": val, "p_value_modifier": str(analysis.get("pValueModifier") or "="),
                "statistical_method": str(analysis.get("statisticalMethod") or ""),
                "results_first_posted": posted, "observed_at_utc": observed_at,
                "source_url": "https://clinicaltrials.gov/study/" + nct,
                "protocol_last_update": str((status.get("lastUpdatePostDateStruct") or {}).get("date") or ""),
            }
            # Stable observation ID deduplicates unchanged result values;
            # when an endpoint/result changes, retain a new first-seen record.
            identity = "|".join(str(info[x]) for x in
                ("nct_id", "ticker", "primary_endpoint", "comparison",
                 "p_value", "p_value_modifier", "statistical_method"))
            info["observation_id"] = sha256(identity.encode()).hexdigest()[:24]
            rows.append(info)
    return rows, "PRIMARY_P_FOUND" if rows else "PRIMARY_P_NOT_REPORTED"

def linked_phase2_ids(data_dir, today):
    pipeline = load_csv(data_dir / "phase_pipeline.csv")
    announcements = load_csv(data_dir / "phase3_announcements.csv")
    caps = load_csv(data_dir / "phase_pipeline_market_caps.csv")
    protocols = load_csv(data_dir / "pre_readout_protocols.csv")
    selected = candidate_queue(
        pipeline, announcements, caps, today,
        protocols=protocols, require_protocol=True,
    )
    result = {}
    for _, trial in selected.iterrows():
        for nct in re.findall(r"NCT\d{8}", str(trial.get("Phase 2 NCT Links", "")).upper()):
            ticker = str(trial.get("Ticker", "")).strip().upper()
            if nct in result and result[nct] != ticker:
                # Ambiguous ownership/identity: do not attach p values.
                result.pop(nct, None)
                continue
            result[nct] = ticker
    return result, len(selected)

def run(root, limit):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    today = datetime.now(ZoneInfo("America/Los_Angeles")).date()
    ids, n_candidates = linked_phase2_ids(root, today)
    output = root / "phase2_primary_p_evidence.csv"
    past = load_csv(output)
    existing = {r["observation_id"]: r for r in past.to_dict("records")
                if r.get("observation_id", "")} if not past.empty else {}
    # Keep first-seen p observations. Do not retroactively make them
    # available earlier than the actual collection.
    already = {r["nct_id"] for r in existing.values()}
    due = [nct for nct in sorted(ids) if nct not in already][:max(1, limit)]
    states = {}
    errors = {}
    for nct in due:
        try:
            observed = datetime.now(timezone.utc).isoformat()
            rows, state = extract(fetch_study(nct), nct, ids[nct], observed)
            states[nct] = state
            for row in rows:
                existing.setdefault(row["observation_id"], row)
        except (HTTPError, URLError, OSError, TimeoutError, ValueError) as exc:
            errors[nct] = f"{type(exc).__name__}: {str(exc)[:130]}"
        time.sleep(0.15)
    # Preserve all prior observations, including those no longer in the
    # current active candidate list, for immutable evidence history.
    with output.with_suffix(".tmp").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(sorted(existing.values(), key=lambda x:(x["nct_id"],x["observed_at_utc"])))
    output.with_suffix(".tmp").replace(output)
    state = {
        "as_of":datetime.now(timezone.utc).isoformat(),
        "eligible_phase3_trials":n_candidates,
        "linked_unique_phase2_nct":len(ids),
        "phase2_nct_queried_this_run":len(due),
        "primary_p_observations_stored":len(existing),
        "primary_p_linked_nct":len(set(r["nct_id"] for r in existing.values()) & set(ids)),
        "unattempted_linked_nct":max(len(ids)-len(already)-len(due),0),
        "no_primary_p_this_run":sum(v!="PRIMARY_P_FOUND" for v in states.values()),
        "errors":errors,
        "status":"COMPLETE" if not errors and len(ids)<=len(already)+len(due) else "PARTIAL",
        "limitations":"Only registry PRIMARY analyses for exact Phase 2 NCT links; p-value does not establish efficacy, trial success or calibrated Phase 3 PoS. First known date is actual collector observation, not results-first-posted. No issuer-level full-text Phase 2 results.",
    }
    (root/"phase2_p_intake_status.json").write_text(json.dumps(state,indent=2)+"\n")
    print(json.dumps({k:v for k,v in state.items() if k!="errors"},indent=2))
    return 0 if not errors else 1

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir",type=Path,default=ROOT/"data")
    parser.add_argument("--limit",type=int,default=150)
    args=parser.parse_args()
    raise SystemExit(run(args.data_dir,args.limit))
