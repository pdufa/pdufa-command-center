# Revision 36: original ACACIA-HCM registry history

This packet preserves original ClinicalTrials.gov responses for NCT06081894, protocol CY 6033, obtained November 9, 2026. It appends evidence to Revision 35; its HTTP 403 receipts and previous research/assessment histories are retained.

A standard Chromium browser navigated the official public history pages. Their own original-record requests returned HTTP 200. No login, custom user agent, access challenge handling, or access restriction bypass was used. The public government records were obtained from their original source; no third-party dataset or incompatible dataset license was introduced. The public page screenshots and visible text are supporting captures; the exact JSON bytes, not an HTML shell, establish original version contents.

| UI version / API index | Submitted | Publicly posted | Primary / secondary endpoints | Enrollment |
| --- | --- | --- | --- | --- |
| 26 / 25 | 2025-01-11 | 2025-01-14 | 1 / 5 | 420 ESTIMATED |
| 27 / 26 | 2025-05-15 | 2025-05-20 | 2 / 5 | 500 ESTIMATED |
| 29 / 28 | 2026-01-29 | 2026-02-02 | 2 / 5 | 500 ESTIMATED |
| 30 / 29 | 2026-08-03 | 2026-08-05 | 2 / 5 | 500 ESTIMATED |

Version 26 lists KCCQ-CSS change from baseline to week 36 as the primary endpoint. Version 27 additionally lists change in pVO2 over the same interval. Versions 29 and 30 retain those two primary definitions; secondary descriptions change, including the LAVI baseline atrial fibrillation/flutter restriction. Exact endpoint text, secondary definitions and study-design fields are retained in each original response and [validated_comparison.json](./validated_comparison.json).

The original registry change is now documentary evidence. It is not a finding about whether the change preceded data lock/unblinding, a protocol/SAP compliance judgment, an independently adjudicated clinical test, or a clinical grade. The final dated locked SAP and amendment/lock chronology remain required. Public availability uses the posting date, not the earlier submission date. Estimated registry enrollment does not resolve the 516 versus 517 randomized/treated population discrepancy.

[public_browser_receipt.json](./public_browser_receipt.json) records exact source/page URLs, UTC retrieval times, lengths and SHA-256 hashes. The history index was captured during the initial successful public-page probe. The subsequent four-version run encountered an intermittent index 403 but successfully obtained all four original versions. The exact second-run receipt is retained as [public_browser_attempt_2_receipt.json](./public_browser_attempt_2_receipt.json); the composed manifest identifies that composition explicitly. The initial index retrieval time is its local file capture-completion time, not an inferred server publication date. The failed index request is preserved and was not recast as successful.

Reproduce the offline validation from the repository root:

```sh
python scripts/medical/acacia_ctg_historical_versions.py --public-browser-capture docs/medical-review-pilot-20261108/revision36-original-history
python -m unittest discover -s tests -p test_acacia_ctg_historical_versions.py -v
```

Validation binds all four payload version IDs, exact NCT, expected submission dates, the independent official history index, response byte lengths and SHA-256 hashes. It retains complete endpoint wording and rejects malformed/truncated or mismatched originals. The existing GitHub workflow now replays these preserved captures offline; its success proves reproducibility, not a fresh source retrieval. The browser adapter is an optional, bounded single-trial collection tool for authorized public navigation, separate from offline verification.

These findings enrich existing handoffs **4.2:L1, 4.4:L1 and 8.2:L1**. Coverage remains **18 mapped source leads, 782 positions not source mapped, 0/800 official method grades, 0 independent completed assessments and 0 qualified phase signoffs**. Every earlier provisional research score remains separate. APPROVAL, CRL and REVIEW_DELAY remain **ABSTAIN**; certainty **NOT_VALIDATED** and accuracy **NOT_CALIBRATED**.
