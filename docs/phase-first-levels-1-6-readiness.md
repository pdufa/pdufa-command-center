# Phase-first scientific Levels 1–6 — evidence readiness only

This is the **first isolated engineering slice** for #1179. It is **not** a medical assessment, a site release, a verified current FOCUS scan, or an FDA outcome prediction.

## Reused inputs

- Current 32 exact-NCT FOCUS roster (as of 2026-11-13): `new-platform/frontend/data/p3PostDataActive.json`. This legacy filename remains an internal source artifact, not an active P3 workspace.
- Existing application crosswalk: `new-platform/backend/app/data/focus_application_snapshot.json`, with 29/32 FOCUS NCTs mapped to 23 **provisional** cycle IDs. Three newly added exact NCTs are explicitly **NOT_MAPPED_APPLICATION_CYCLE**, never silently excluded or assigned guessed FDA applications. The unreviewed cycle IDs and indication labels remain leads only.
- The existing `scripts/medical/level4_registry_extraction.py` source checkpoint, now with an additional read-only `studyOverallStatus` field for future captures.
- Existing 20-level names: `new-platform/frontend/data/deepMedicalTwentyLevelExpansion.json`; only Levels 1–6 are read.

No legacy score model is imported. This does not touch POOL/FOCUS membership, FDA outcomes, assessment history, production or the separate automatic coder.

## Run offline, against an existing checkpoint

```powershell
python scripts/medical/phase_first_levels_1_6.py --checkpoint path/to/level4-checkpoint.json > levels1-6-readiness.json
```

The process performs **no network calls**, database writes or predictions, and only emits JSON to standard output. Its report is provenance-gated: an exact-NCT/source-location mismatch, invalid SHA-256 metadata, duplicate FOCUS trial or mismatched candidate application identity stops processing. A SHA-256 string is a source-receipt attribute, **not** proof the underlying source was independently reviewed.

Each exact-NCT trial returns six separate Level readiness records:

| Level | Original scientific objective | This first slice |
| --- | --- | --- |
| 1 | Source identity and provenance | Registry-source capture/identity check; independent provenance review still required |
| 2 | Registry and phase verification | Captured phase and trial status are explicitly *unreviewed*; absent status unresolved |
| 3 | Clinical results evidence | Phase 1/2 does not automatically require future pivotal readout; registered endpoints are not results |
| 4 | Trial design and protocol investigation | Captured design attributes are not scientific judgments; single-arm/open-label applicability must be reviewed |
| 5 | Statistical analysis and multiplicity | Original SAP/multiplicity evidence is required for potential pivotal Phase 3; future pivotal SAP not imposed on earlier phases |
| 6 | Endpoint clinical relevance | Indication leads and registered outcomes need independent specialty/contextual review |

All scores, probabilities, FDA outcome/timing judgments and scientific conclusions remain **null**. Every level is **NOT_ADJUDICATED**. Real phase-specific assessment code, original-document review, independent scientific signoff, validated assessment outputs, FOCUS UI integration and runtime verification remain future engineering/review tasks.

For a Phase 4 or `NA` registry category the pivotal requirements remain subject to applicability/manual review; Phase 4 is never automatically treated as an upcoming FDA approval trial.

## Tests and acceptance boundaries

```powershell
python -m unittest discover -s tests -p "test_phase_first_levels_1_6.py" -v
python -m unittest discover -s tests -p "test_level4_registry_extraction.py" -v
python scripts/audit_raas_retirement.py --check
```

The isolated workflow `.github/workflows/phase-first-levels1-6-tests.yml` runs these on Windows and Ubuntu. This test receipt verifies **software structure**, never actual clinical validity.

**Next slice:** independently verified trial phase/status and indication provenance; source-specific clinical evidence requests and phase-specific reviewer workflow; staging integration after acceptance. Preserve distinct approvals, CRLs, extensions and abstentions and ensure postdecision historical outcomes are not laundered as predictions.


## Second engineering slice — source-submission review queue and offline preview

A separate fail-closed source intake is implemented in
`scripts/medical/level16_source_submissions.py`. It accepts bounded
source metadata for **Levels 1–6** only and attaches each lead to its exact
NCT and (optionally) its *provisional* application-cycle ID.

A submission contains `submissionId`, `nct`, `level`, `sourceKind`,
`sourceUrl`, `sourceDate`, `accessedDate`, `documentSha256`,
`locator`, `claim`, `role` (SUPPORTS/CHALLENGES/CONTEXT), and
`submittedBy`; `candidateApplicationCycleId` is optional. The enclosing
object requires `schemaVersion: 1`, `kind:
FOCUS_LEVELS_1_6_SOURCE_SUBMISSIONS`, `cutoffDate`, and `records`.

**Crucial trust boundary:** a submitted SHA-256 string or source URL is
**unverified metadata**, not proof that the underlying document bytes have
been accessed or authenticated. Likewise, a string in `submittedBy` is
not an independently authenticated reviewer signature. Caller-supplied
verification, reviewer approval, score or FDA prediction fields are rejected.
Every accepted source lead is marked
`SUBMITTED_SOURCE_NOT_INDEPENDENTLY_AUTHENTICATED` and every level remains
`NOT_ADJUDICATED`. Even a registry source lead must match the checkpoint's
exact NCT, URL, SHA-256 and captured field locator. No self-attestation can
promote an item into independent scientific review.

### No-source example

Create a local `source-submissions.json` file containing this example.
It is a valid **empty queue**, not actual verified evidence:

```json
{
  "schemaVersion": 1,
  "kind": "FOCUS_LEVELS_1_6_SOURCE_SUBMISSIONS",
  "cutoffDate": "2026-11-13",
  "records": []
}
```

### Read-only workflow

```powershell
python scripts/medical/phase_first_levels_1_6.py --checkpoint path/to/level4-checkpoint.json --source-submissions source-submissions.json > levels1-6-readiness.json

python scripts/medical/render_level16_focus_preview.py --report levels1-6-readiness.json --output levels1-6-preview.html
```

The output HTML is **offline-only**, not a deployed route. It displays a
32-NCT (or exact current FOCUS roster count), six-level, expandable review queue and strongly labels all evidence
as unauthenticated and all assessments as unreviewed. All free-text and
source links are escaped/validated. It does not connect to the live FOCUS
site or modify databases, records, memberships, scoring or predictions.

### Tests

```powershell
python -m unittest discover -s tests -p "test_phase_first_levels_1_6.py" -v
python -m unittest discover -s tests -p "test_render_level16_focus_preview.py" -v
python -m unittest discover -s tests -p "test_level4_registry_extraction.py" -v
python scripts/audit_raas_retirement.py --check
```

Windows and Ubuntu CI run the checks with byte-preserving checkout and
UTF-8 decoding so the historical-record hash audit is not invalidated by
Windows line-ending conversion. Do not weaken that audit.

### Still required before functional assessments

- Provenance authentication against actual permitted original source bytes;
  reproducible hashes, publication/access dates and phase-first identity
  verification;
- A separate *authenticated* reviewer workflow with demonstrably independent
  source and clinical reviews, amendment tracking and contradictory evidence;
- Trial/indication-specific clinical analyses and methods for Levels 1–6;
  independent specialist challenge, and FDA application-cycle adjudication;
- Approved frontend integration on an actual protected FOCUS page, runtime
  smoke testing and explicit release approval before deployment;
- Historical point-in-time blind validation before quantitative probability
  forecasts. These submissions and this preview cannot be used to assert
  clinical accuracy, reviewer completion or approval probability.
