# Reproducible, unsigned FOCUS Levels 1–6 research handoff

This engineering step prepares a portable, **read-only research metadata
handoff** for subsequent authorized independent source and clinical review.
It does not create an authenticated clinical source or an authorized review
event. It does not score trials, forecast FDA action, change FOCUS membership,
activate staging, or merge/deploy code.

## What is bound to the handoff

`scripts/medical/level16_research_handoff_bundle.py` recomputes the 32-trial
review handoff from the exact committed research metadata snapshots:

| Snapshot | Use |
| --- | --- |
| `reports/scientific-levels1-6/scientific-coverage-20261114.json` | Unreviewed phase-appropriate source coverage |
| `new-platform/frontend/data/p3PostDataActive.json` | Frozen exact 32-NCT FOCUS roster, despite legacy path name |
| `new-platform/backend/app/data/focus_application_snapshot.json` | 29 provisional NCT mappings, 23 provisional candidate cycles, 3 unresolved NCTs |
| `reports/scientific-levels1-6/orca2-statistical-chronology-20261114.json` | ORCA-2 original-public-source statistical chronology and unresolved lock/unblinding facts |
| `reports/scientific-levels1-6/orca2-publication-outcomes-20261114.json` | Reported JAMA ORCA-2 primary/secondary efficacy, serious adverse events and clinical limitations—unreviewed |
| `reports/scientific-levels1-6/orca3-publication-outcomes-20261114.json` | Distinct ORCA-3 Phase 3 paper efficacy/safety, publication CI discrepancies and source limitations—unreviewed |
| `reports/scientific-levels1-6/maple-hcm-source-review-20261114.json` | MAPLE-HCM original NEJM abstract/secondary ACC trial summary, continuous pVO2 efficacy, distinct active comparator and safety—unreviewed |


The script reuses the existing strict phase-first handoff and ORCA-2
timeline validators. It computes a SHA-256 over each raw input snapshot and
a separate SHA-256 over the canonical serialized 32-trial, 192-level
research-only output. It will refuse altered NCT rosters, missing source
snapshots, contradictory current-source identities, invalid ORCA-2 timeline
conclusions, or any final-science/FDA prediction promotion in those inputs.

**Critical:** This proves only local source-metadata and output-byte
consistency. It does NOT independently verify original clinical PDFs,
ClinicalTrials.gov authenticity, the identity of a medical reviewer, or
whether evidence was appropriate at its publication date. There is no
cryptographic signature or timestamp authority; malicious replacement of
both a bundle and its source checkout is not prevented. Preserve and
authenticate original clinical document bytes using the separate approved
source-verification workflow before any scientific certification.

## Produce a research-only bundle

On a reviewed checkout of draft PR #1181:

```powershell
python scripts/medical/level16_research_handoff_bundle.py > focus-level16-unsigned-review-bundle.json
```

On the *same* exact source snapshot checkout, verify a received local copy:

```powershell
python scripts/medical/level16_research_handoff_bundle.py --verify focus-level16-unsigned-review-bundle.json
```

Expected successful verification status is
`LOCAL_RESEARCH_SNAPSHOT_AND_PACKET_BYTES_MATCH_ONLY`, with zero
authenticated sources, zero adjudicated levels and no FDA prediction.
If source metadata changes, the exact source content must be captured as
a **new version**, not silently substituted into an older review.

Generate the original human-readable review questions if desired:

```powershell
python scripts/medical/level16_review_handoff.py --nct NCT04576949 --format markdown
```

Do not upload clinical study reports containing confidential material,
protected patient information, private reviewer notes, credentials or
identity-proofing documents to GitHub.

## Validation

```powershell
python -m unittest discover -s tests -p "test_level16_research_handoff_bundle.py" -v
python -m unittest discover -s tests -p "test_level16_review_handoff.py" -v
python scripts/audit_raas_retirement.py --check
```

The tests cover deterministic replay of 32-trial research metadata,
all 192 unreviewed Levels 1–6, exact raw-byte changes even with JSON
semantics unchanged, tampered packet contents, forged digests, altered
NCT identity, false scientific review/FDA probabilities, malformed
approval metadata, missing snapshots and symlinked files.
No live authentication provider, source attestation, staging resource,
append-only reviewer event or independent clinical assessment is used.

## Remaining actual dependencies

A01–A14 owner choices, approved isolated staging and real individual
identity-proofed reviewers are still outstanding. Original sources,
protocol/SAP versions, amendments, trial phase and statistical chronology
must be verified independently. ORCA-2 remains a first **research** handoff
candidate only; exact database-lock/unblinding timing and signed final SAP
versions remain unresolved. Zero trials have independently adjudicated
Levels 1–6 in the current static research packet.

Do not claim this engineering test replaces qualified clinical/statistical
review or that a review-packet hash creates an FDA outcome prediction.
