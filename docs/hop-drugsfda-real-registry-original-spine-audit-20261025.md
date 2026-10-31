# Reproduced real FDA approved-registry original submission inventory (Oct 25, 2026)

**Status:** research-only, official source extraction previously collected,
registry *coverage* checked from its GitHub artifact, **no original FDA
decision independently adjudicated**.

## Source bytes actually inspected

The existing GitHub Actions source collection run
[40224730350](https://github.com/pdufa/pdufa-command-center/actions/runs/40224730350)
produced [artifact 12611090768](https://github.com/pdufa/pdufa-command-center/actions/runs/40224730350/artifacts/12611090768)
named `hop-drugsfda-approved-registry-quarantined`. Its downloaded ZIP
contained `drugsfda_approved_registry_audit.json` and
`drugsfda_approved_registry_quarantined.json`.

The archived quarantined JSON (approximately 72.5 MB uncompressed) was
inspected **in this research operation**. The ZIP's SHA-256 is
`58f9197c4d040fbf21f2bbf4edf223318b46c4df354a2a1efc95a844cad502c0`;
the JSON payload SHA-256 is
`adb24d7921d56bc3824b57e785164a32287efc69a9d3fe9b940da97f6c65f5b2`.
The artifact reports its original FDA export archive SHA as
`d218e3d6ced00a6d117612529faa1eafa223ee65668a69f8139b5cd35054b3de`,
which **was not rehashed from the original FDA ZIP in this operation**.

Source export date is October 23, 2026, retrieved October 25, 2026.
The reproducibility snapshot is
`new-platform/backend/app/research_sources/hop_drugsfda_original_submissions_artifact_index.json`.
The original, full JSON remains an artifact and is **not committed into git**.

## Actual observed results

| Units / reported attribute | Source-backed observation |
|---|---:|
| Approved-centric Drugs@FDA application records | 29,416 |
| NDA application records | 5,908 |
| BLA application records | 485 |
| ANDA application records (excluded from original NDA/BLA study) | 23,023 |
| All published registry submission-history entries | 188,890 |
| NDA original-submission entries (`ORIG`) | 5,529 |
| BLA original-submission entries (`ORIG`) | 503 |
| **All NDA/BLA original-submission entries** | **6,032** |
| **Unique NDA/BLA applications with an original submission entry** | **5,972** |
| Applications showing more than one original submission entry | 58 |
| Raw `AP` statuses attached to original entries | 5,904 |
| Raw `TA` statuses attached to original entries | 127 |
| Missing original-submission status | 1 |
| Independently adjudicated unique application review cycles | **0** |
| Verified complete NDA/BLA approval/nonapproval denominator | **No** |
| Model-eligible historical outcomes | **0** |

Counts are from the **approved-product-centric registry**, not a
representative sample of distinct review-cycle decisions. An FDA application
may have multiple original submissions; a submission number is not necessarily
an FDA review cycle; `AP` or `TA` is only the source's raw status metadata.
A raw `TA` is not a scientific probability, a clinical trial outcome, or a
validated negative decision. There are also source records not captured by
this approval-centric extract, including never-approved applications.

## Reproduce locally from original saved artifact

Obtain the saved official GitHub Actions artifact ZIP through permitted
repository access and run:

```bash
PYTHONPATH=new-platform/backend python \
  new-platform/backend/scripts/audit_hop_drugsfda_saved_registry_artifact.py \
  /path/to/hop-drugsfda-approved-registry-quarantined.zip \
  --as-of 2026-10-25 \
  --expected-payload-sha256 adb24d7921d56bc3824b57e785164a32287efc69a9d3fe9b940da97f6c65f5b2 \
  --output-json /path/to/private/original_ndabla_source_audit.json
```

The reader validates archived member names, the source JSON fingerprint,
application identity, internal source-document hashes and source index
ordering, duplicate original-submission identifiers, data-quality gaps
and all mandatory scientific quarantine flags. It counts genuine source
metadata without translating raw codes into FDA decisions or filling
unknown review cycles. An output from a different source collection needs
its own separately recorded artifact fingerprint and source validation.

**The CLI deliberately exits nonzero even for correctly parsed data:** valid
registry source history is not proof that the complete population of original
NDA/BLA FDA review-cycle decisions has been reconstructed. No live scanner,
database, GEM JR/GEM FS/FA presets, scientific trial rating or predictive
probability is changed by this operation.

Next steps require independently obtaining omitted never-approved NDA/BLA
applications, establishing a precise original submission/decision-cycle
study protocol, reconciling original FDA letters and action dates, and
independent predecision data and time-forward validation.

### Preserved historical identifier exceptions

Two source application records are printed as `NDA21939` and `NDA19019`
rather than six-digit identifiers. Neither has an original-submission entry
in this artifact. Both remain included in the 29,416 application-reference
count, with a `NONSTANDARD_APPLICATION_NUMBER_LENGTH` warning. They are
**not** padded, removed, mapped to other applications, or converted into
review-cycle outcome labels. One additional original submission has a
missing raw status code. Independent official identity and action-date
resolution is still necessary.
