# MAIN Revision 66 — Exact original trial phase-first registry source census

**November 9, 2026 PST.** Existing draft development branch `feature/medical-stage4-verified-method-matrix-20261108`, [PR #965](https://github.com/pdufa/pdufa-command-center/pull/965). No production merge, reviewer signoff, trial science grade, FDA probability or historical outcomes accessed.

## Verified installation and actual research

- [Original R66 phase-first acceptance workflow #42720903307](https://github.com/pdufa/pdufa-command-center/actions/runs/42720903307) **SUCCESS**, on code commit `b4593dd9a483d2557c83a75231afc86bcfc014f4`.
- All **15 source and tamper tests passed**. The dedicated workflow restored the immutable R53 original dated ClinicalTrials.gov API JSON bodies for all **29 FOCUS exact NCTs**, original R46 source receipt `7e1681399ed242d0080d8517bbe62cfb931e88e1340295fdf9839affbc0d3f92`, and independent original R65 unsigned reviewer queue `1238d5a0ed120cd47d05dec12486e59e2bf8dbd6e7b73b989372955db622127a`.
- **[Research artifact #13720041195](https://github.com/pdufa/pdufa-command-center/actions/runs/42720903307/artifacts/13720041195)** (retained through **2027-02-07**), files `FOCUS_29_ORIGINAL_REGISTRY_PHASE_EVIDENCE_R66.json` and human-readable `FOCUS_29_ORIGINAL_REGISTRY_PHASE_EVIDENCE_R66.md`. The source research is read-only/write-once and not integrated into the live assessment page yet.
- Each original NCT record is required to match independent R46 and R65 registry response SHA-256 hashes, byte counts, exact application-cycle identity, and absent human phase reviewer attestation. Modified original response, invented application membership, fake qualified clinical grade, or simulated FDA decision fails closed.
- Each of the 29 trial source records includes its **source-reported phases, recruiting/status designation, status-verification month, last public update date, reported design allocation, masking, study population/enrollment, conditions, interventions, primary and total completion dates**, exact registry source URI, research exceptions and zero qualified phase-adjudication events.

## What the archived original ClinicalTrials.gov records say

| Original registry-reported scope | Unique trials |
| --- | ---: |
| Phase 3 only | **28** |
| Combined Phase 2/3 | **1** |
| Completed | **19** |
| Active, not recruiting | **8** |
| Recruiting | **2** |
| Randomized allocation | **28** |
| Allocation N/A | **1** |

Special scientific review flags:
- `NCT04871282`: Combined Phase 2/3 label in this *original registry version*; this is not evidence of phase-inappropriate data collection.
- `NCT06331299`: Registry design allocation `NA`; phase/study design must be independently assessed, and no unsupported randomized comparison should be inferred.
- `NCT02500381`: One original source trial under two distinct provisional Sarepta application-cycle groups. It is one unique NCT, not two independent trials.
- `NCT05126758`: Current original registry Phase 3 / active-not-recruiting, with absent posted results in the separate R60 source audit; the absence is **not** inferred to mean trial failure.

These are the *recorded phase/status in the retained public registry copies*, not independently verified clinical phase, the original pre-unblinding SAP, treatment efficacy, FDA submission status, or regulator acceptance. Historical and new source changes must be separately reconciled rather than silently replacing dated original receipts.

## Files installed

- `new-platform/backend/scripts/build_focus_source_phase_census_r66.py`
- `new-platform/backend/tests/test_focus_source_phase_census_r66.py`
- `.github/workflows/main-r66-source-phase-first-census.yml`

## Scientific and release limitations

- **29/29** dated original registry Phase 3-including entries retrieved and source-checked, but **0 qualified independent trial-phase reviewer decisions**.
- **0** scientific method grades or signed efficacy/safety assessments, **0/23 independently validated future FDA application forecasts**, historical accuracy **not measured**, numerical approval/CRL/delay **ABSTAIN**.
- These registry categories do not prove FDA authorization or application submission; study `COMPLETED` does not establish that the trial met prespecified outcomes.
- No clinical reviewer/production write, no model training, no historical Track B access and no modification of FOCUS/POOL records.

## Next

1. Add a fail-closed, exact-R66-archive-linked **read-only phase-first source** strip to each selected FOCUS assessment page, including dated registry status, original design/recruiting flags, and independent reviewer signoff still **PENDING**. The current R66 data are in a GitHub Actions artifact, not the active frontend snapshot.
2. Independently verify original pre-unblinding Phase 3 and statistical plan chronology, complete human efficacy/safety review, and separate FDA application-cycle source/reviewer signoffs.
3. Preserve source version dates and proof of disagreement, and conduct genuine prospective/out-of-time FDA validation separately from historical Track B before publishing any probability, certainty or measured prediction accuracy.

R66 research evidence engineering is complete; Stage 4 source-gathering/qualified adjudication remains unfinished; production unchanged.
