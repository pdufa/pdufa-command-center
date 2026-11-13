# Phase-first scientific Levels 1–6 — evidence readiness only

This is the **first isolated engineering slice** for #1179. It is **not** a medical assessment, a site release, a verified current FOCUS scan, or an FDA outcome prediction.

## Reused inputs

- Canonical 29 exact-NCT FOCUS snapshot: `new-platform/backend/app/data/focus_snapshot.json`.
- 29-NCT / 23 **provisional** candidate application-cycle crosswalk: `new-platform/backend/app/data/focus_application_snapshot.json`; cycle IDs and indication labels remain *unverified leads*.
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
