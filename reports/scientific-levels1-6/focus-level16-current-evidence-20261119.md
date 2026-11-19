# FOCUS current-source scientific checks, November 19, 2026

The November 18 FOCUS snapshot and retained evidence artifact contain the same 32 exact NCT IDs and 192 preliminary worksheets. All 32 current ClinicalTrials.gov records were retrieved on November 19. Each intake checked NCT identity, the reported edition date, and the filtered receipt digest. Two registry edition dates differ from the retained artifact. No trial phase or overall status changed. Existing preliminary contradiction leads remain attached to the corresponding levels for adjudication.

| Level | Executed out of 32 | Current-source findings | Accepted evidence dispositions |
| --- | ---: | --- | ---: |
| L01 | 32 | Exact-trial intake only | — |
| L02 | 32 | 32 partial design reviews | 96 / 160 |
| L03 | 32 | 13 partial results reviews and 19 awaiting evidence review | 15 / 160 |
| L04 | 32 | 13 partial safety reviews and 19 awaiting evidence review | 38 / 160 |
| L05 | 32 | 32 partial indication reviews | 32 / 160 |
| L06 | 32 | 32 await exact application-cycle and regulatory review. Three have cited sponsor filing leads. | 0 / 160 |

All 192 contracts executed. Zero scientific assessment packages or owner reviews are complete. Every FDA direction is ABSTAIN. Registry observations and the two dated ORCA publications and the dated LUCIDITY sponsor release add substantive observations and limited quantitative findings. The criterion dispositions remain inconclusive where conduct, estimands, follow-up, target populations, or regulatory evidence require further review. No validated scores, calibrated confidence, regulatory outcomes, or historical backtest files entered this run. Application leads remain provisional.

The [CSV](focus-level16-current-evidence-20261119.csv) supplies one row per trial and level for FOCUS and ASSESSMENTS review. Join by exact NCT and level and keep the assessment SHA-256 and contract state. The [JSON](focus-level16-current-evidence-20261119.json) carries the corresponding per-trial versions, timestamps, citations, accepted evidence and outstanding criteria. These exports retain owner review as `OWNER_NOT_REVIEWED` and are separate from saved runtime records and historical outcomes.

The [normalized registry receipts](focus-level16-registry-receipts-20261119.json.gz) include the current-source document projections and their original response and filtered document hashes. Full original registry response bytes were not retained beside the normalized snapshots. The offline replay checks every normalized document digest and the exact roster before running the installed contracts.

```sh
python scripts/medical/review_focus_level16.py \
  --receipts reports/scientific-levels1-6/focus-level16-registry-receipts-20261119.json.gz \
  --output /tmp/focus-level16-replay
```

The command uses the repository's backend dependencies. It refuses to replace a different existing output under the same version date.
