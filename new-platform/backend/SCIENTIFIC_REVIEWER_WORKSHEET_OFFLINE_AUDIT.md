# Offline A/B scientific reviewer worksheet audit — isolated research only

This diagnostic compares the **three CSV files for one exact NCT** downloaded from the isolated trial's Scientific Assessment panel:

1. The unchanged `Download 320-task review matrix (CSV)` inventory.
2. The independently editable `Download reviewer A worksheet (CSV)` handoff.
3. The independently editable `Download reviewer B worksheet (CSV)` handoff.

Reviewers may fill their own **names (unverified)**, primary document locator, claimed SHA-256, public document date, cited section/table, notes and `reviewer_decision` (`supports`, `contradicts`, `uncertain` or `not_assessable`). The worksheet's locked source columns, `qualification_verification=NOT_VERIFIED` and `submission_status=NOT_SUBMITTED` must **not** be changed. Filled names or signatures do not establish independently verified identities, genuine source content or signed adjudications.

To run **offline** from `new-platform/backend` (no network or service credentials):

```sh
python -m app.scientific_reviewer_handoff_audit \
  --nct-id NCT02142738 \
  --inventory /path/to/NCT02142738_scientific_320_depth_review.csv \
  --reviewer-a /path/to/NCT02142738_scientific_reviewer_A_320_tasks.csv \
  --reviewer-b /path/to/NCT02142738_scientific_reviewer_B_320_tasks.csv
```

The diagnostic emits only aggregate counts and exact task keys for **candidate** disagreement, not reviewers' names or document contents. It rejects malformed, wrong-trial, duplicated, incomplete, mutated or falsely completed review records. It flags missing reviewer notes/provenance and A/B disagreements. It **does not** fetch or verify URLs, compare cited hash claims against actual source bytes, authenticate qualifications, validate typed signatures, perform clinical reconciliation or write to a database.

The script **always exits nonzero** by design: exit 1 for malformed/unsafe inputs and exit 2 for a structurally valid but scientifically unauthenticated worksheet audit. Do not wire its candidate counts to the platform's evidence admission, FDA probability, rankings or trading signals. The result always states `promotionAllowed=false`, `tasksIndependentlyAdjudicated=0`, `scientificScore=null` and `fdaApprovalProbability=null`.

For independent science completion, acquire original dated source bytes and independently verify source hashes, authenticate qualified individual reviewers, record independent signed judgments and reconcile conflicts under approved controls. Keep the production scientific rollout PR **DRAFT** until separate scientific and release authorization.
