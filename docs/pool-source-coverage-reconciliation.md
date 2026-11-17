# Full-POOL raw-source reconciliation

Run this offline after BOTH GitHub Actions source collectors have finished and
their reports have been extracted. This is NOT a scientific review or a
prognostic model. The script does not access the internet or alter any existing
research artifacts, prediction history, ROIs, production services or trial lists.

The manifest utility is scripts/medical/pool_source_coverage_manifest.py.
Supply --registry-dir, --pubmed, and --output. It verifies that source
collectors used the same exact POOL snapshot SHA, that POOL exact-NCT sets
match, and that registry packet contents match saved SHA-256 receipts.

It returns raw packet coverage, successful/failed/unattempted PubMed queries,
unreviewed publication lead counts, and exact-trial gaps. A successful source
capture still is NOT completed clinical source review or FDA prediction.
Missing source records cannot be interpreted as negative efficacy outcomes.

No production merge or deployment authorized.
