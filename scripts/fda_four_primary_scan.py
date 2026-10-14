#!/usr/bin/env python3
"""Live four-event exact-source PDUFA target verification with audited URLs.

This produces a separate candidate-level source-evidence result; it does not
override the canonical nightly source ledgers, probability scores or trade gates.
"""
from __future__ import annotations
import argparse
import json
from datetime import datetime,timezone
from pathlib import Path
from scripts.source_verification import Verifier, read_rows

EVENTS = (
    "ANAB|IMSIDOLIMAB_GPP_20261212",
    "EXEL|ZANZALINTINIB_CRC",
    "HRMY|PITOLISANT_GR_20270401",
    "SVRA|MOLBREEVI_PAP_20261122",
)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--status-file", type=Path, required=True)
    parser.add_argument("--evidence-file", type=Path, required=True)
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    data=root/"data"
    events={r["event_key"]:r for r in read_rows(data/"pdufa_candidates.csv")}
    companies=read_rows(data/"company_registry.csv")
    source_cfg=json.loads((root/"config/issuer_sources.json").read_text())
    v=Verifier(companies,issuer_sources=source_cfg)
    result=[]
    for key in EVENTS:
        e=events.get(key)
        if not e: raise RuntimeError("Exact program missing: "+key)
        checked=v.regulatory(e)
        if len(checked)!=1 or checked[0]["claim"]!="PDUFA_TARGET":
            raise RuntimeError("Unexpected source claim scope: "+key)
        record=checked[0]
        if record["verification_status"]=="VERIFIED" and (
                not record["source_url"] or len(record["source_sha256"])!=64
                or record["observed"]!=e["pdufa_date"]):
            raise RuntimeError("Apparent verification without exact dated source: "+key)
        result.append({field:record[field] for field in (
            "event_key","ticker","category","claim","verification_status","reason",
            "source_url","source_sha256","expected","observed","checked_at","evidence")})
        print(key, record["verification_status"],
              record["source_url"], record["reason"][:140], flush=True)
    confirmed=sum(r["verification_status"]=="VERIFIED" for r in result)
    remaining=len(result)-confirmed
    summary={
       "generated_at_utc":datetime.now(timezone.utc).isoformat(),
       "status":"COMPLETE" if remaining==0 else "PARTIAL",
       "execution_status":"COMPLETE",
       "scope":"Only four previously unresolved FDA target-date events",
       "full_coverage_verified":False,
       "source_observations":4,
       "findings_due":4,
       "findings_verified":confirmed,
       "required_findings_unresolved":remaining,
       "canonical_source_ledger_updated":False,
       "trade_entry_authorized":False,
       "note":"Verifies primary issuer-reported FDA target dates only. Not a signed FDA decision, second financing, probability model or broker authorization.",
       "results":result,
    }
    for target,payload in ((args.evidence_file,summary),(args.status_file,summary)):
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"verified":confirmed,"remaining":remaining},indent=2))
    return 0
if __name__=="__main__":
    raise SystemExit(main())
