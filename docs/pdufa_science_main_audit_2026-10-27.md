# SCIENCE and MAIN completion audit — 2026-10-27 (targeted)

This is a **limited repository inspection**, not a complete operational acceptance test. Use alongside `docs/pdufa_completion_evidence_audit_2026-10-27.md`.

## Inspected
- `README.md` identifies `new-platform/frontend` (Next.js/Vercel) as the active dashboard, `new-platform/backend` (Render) as backend, and GitHub Actions scanners as separate operational components. Streamlit is described as retired. This is architectural documentation, not live deployment proof.
- `new-platform/frontend/app/page.tsx` contains a client-side dashboard entrypoint, stage selection, and screening preference UI. This demonstrates implementation presence but does not establish the specific M1 acceptance requirements (verified historical parallels, evidence/readiness/abstention displays, mobile/desktop tests against real cases).
- `docs/MASTER_PDUFA_PASS_FAIL_DIRECTIVE.md` records the 20-depth-level SCIENCE and automatic historical parallels requirements. It is a **governing plan**, not evidence of deployed scientific scoring.
- `scripts/historical_parallel_matching.py` implements conservative historical-parallel candidate retrieval; it explicitly does not promote candidates to verified comparisons or FDA probabilities.
- GitHub Actions tests on commit `f0bb33d` passed 13/13, including research tests; latest review queue test workflow passed on commit `b04b0cf`. Passing CI does not verify production scanner operation, deployment receipts, or independent scientific outcomes.

## Acceptance decision
| Criterion | Points earned in this targeted audit | Maximum | Finding |
| --- | ---: | ---: | --- |
| S1 | 0 | 8 | Design directive found; reviewed complete scientific schema and traceable 40-assessment evidence not established |
| S2 | 0 | 7 | Representative audited dossiers and trial-to-application lineage not inspected |
| S3 | 0 | 8 | Candidate retrieval code present; verified dated source snapshots and independent review absent from evidence inspected |
| S4 | 0 | 7 | Reproducible scored cases, uncertainty calibration and disagreement analysis not inspected |
| S5 | 0 | 5 | No signed independent scientific reproducibility audit inspected |
| M1 | 0 | 5 | Frontend exists; required integrated real-case acceptance not verified |
| M2 | 0 | 5 | Scanner CI exists; unattended operational run/alert/recovery acceptance not verified |
| M3 | 0 | 5 | Architecture described; deployment/security/rollback acceptance not verified |
| M4 | 0 | 5 | No signed end-to-end user acceptance inspected |

**Interpretation:** Zero additional **verified acceptance points** in this limited audit; **not** evidence that SCIENCE and MAIN have zero implementation or zero real-world progress. No partial-credit rubric exists yet, so full criterion credit requires all specified evidence.

## Running total and next evidence
- Previously confirmed O1: **5/5**.
- Newly verified criterion completions in this audit: **0**.
- **Verified lower bound: 5/100**, not an estimate of overall completion.
- To assign more points, inspect: scientific assessment schemas and sample dossiers; frontend feature-level tests; unattended scan execution receipts and alert logs; deployed environment validation; independent reviewer signoff.

No production deployment, DB/network changes, GEM JR/GEM FS/FA reassignment, or trading activation.
