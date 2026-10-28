"""Research-only offline intake CLI for FDA action-letter PDFs.

Example:
  python -m research.fda_crl_intake_cli --pdf /secure/original.pdf \
    --application NDA218607 --action-date 2025-06-27 \
    --source-url https://download.open.fda.gov/crl/CRL_NDA218607_20250627.pdf \
    --output /secure/metadata.json

No network access, source authentication, predecision promotion, or training.
"""
import argparse
import json
from pathlib import Path

from research.fda_crl_offline_intake import inspect_fda_pdf


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--application", required=True)
    parser.add_argument("--action-date", required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--public-available-on")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output.exists():
        parser.error("output already exists; never overwrite intake audit records")
    if args.output.resolve() == args.pdf.resolve():
        parser.error("output cannot replace original PDF")
    record = inspect_fda_pdf(
        args.pdf, application=args.application, action_date=args.action_date,
        public_available_on=args.public_available_on, source_url=args.source_url)
    # Atomic create: a prior manifest is never silently overwritten.
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(record, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(f"Saved unverified intake metadata: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
