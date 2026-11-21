"""Link private FDA evidence-search packets to pinned historic PDF-probe records.

Do not export application, document, per-letter, or clinical outcome records.
The public output contains source-count metrics ONLY.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.hop_fda_prior_pdf_lead_join import join_prior_pdf_probes_to_research_packets

SOURCE = Path(__file__).resolve().parents[1] / "app" / "research_sources"


def main() -> int:
    parser = argparse.ArgumentParser(description="Prior FDA PDF bytes source lead join only")
    parser.add_argument("--private-grouped-packets", type=Path, required=True)
    parser.add_argument("--prior-pdf-probes-json", type=Path, required=True)
    parser.add_argument("--prior-pdf-probes-audit-json", type=Path, required=True)
    parser.add_argument("--private-enriched-packets-json", type=Path, required=True)
    parser.add_argument("--public-aggregate-json", type=Path, required=True)
    args = parser.parse_args()

    pdf_index = json.loads((SOURCE / "hop_fda_full_action_pdf_audit_index.json").read_text(encoding="utf-8"))
    group_index = json.loads((SOURCE / "hop_fda_shared_pdf_reconciliation_index.json").read_text(encoding="utf-8"))
    private = json.loads(args.private_grouped_packets.read_text(encoding="utf-8"))
    prior_probes = json.loads(args.prior_pdf_probes_json.read_text(encoding="utf-8"))
    prior_audit = json.loads(args.prior_pdf_probes_audit_json.read_text(encoding="utf-8"))
    enriched, summary = join_prior_pdf_probes_to_research_packets(
        private, prior_probes, prior_audit,
        pinned_pdf_index=pdf_index, pinned_pdf_group_index=group_index,
    )
    # Prevent an operator from accidentally publishing the private source
    # mapping by pointing both outputs at the same file.
    if args.private_enriched_packets_json.resolve() == args.public_aggregate_json.resolve():
        raise ValueError("Private source packets cannot be published as an aggregate")
    args.private_enriched_packets_json.parent.mkdir(parents=True, exist_ok=True)
    args.public_aggregate_json.parent.mkdir(parents=True, exist_ok=True)
    args.private_enriched_packets_json.write_text(
        json.dumps(enriched, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    args.public_aggregate_json.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    # This status confirms ONLY source-reference consistency, not FDA decisions.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
