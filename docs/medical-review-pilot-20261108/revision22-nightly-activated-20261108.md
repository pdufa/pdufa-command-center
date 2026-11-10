# MAIN Revision 22 — isolated nightly public-source monitoring activated

**Pilot:** ACACIA-HCM / NCT06081894. **Date:** November 8, 2026 (Pacific).
**Medical installation:** PR #965 remains DRAFT, separate from the small main-branch workflow installation.

## Controlled activation on GitHub's default branch

The user authorized continuing installation of the previously staged, public-only evidence monitor. On the default branch `main`, exact atomic commit [9c3eb5e](https://github.com/pdufa/pdufa-command-center/commit/9c3eb5ebf86789e39c2c68ba9ab833a32821adc1) added **exactly three files**:

- `scripts/medical/acacia_nightly_evidence_monitor.py`
- `tests/test_acacia_nightly_evidence_monitor.py`
- `.github/workflows/main-acacia-public-evidence-nightly.yml`

The active workflow declares an **8:17 PM America/Los_Angeles** nightly schedule with automatic DST handling. It runs only on the repository's current default branch, `main`, and only reads two fixed HTTPS public source APIs. It uses minimal GitHub token read permissions, archives a provenance receipt with 90-day retention, and has no backend deployment, clinical-write credentials, reviewer signoff, production DB or app changes. **No part of PR #965 was merged**; the source of this narrow standalone monitor was copied without importing the unfinished medical application.

## Verified first default-branch execution

[GitHub Actions main-branch run #42550358445](https://github.com/pdufa/pdufa-command-center/actions/runs/42550358445) completed **SUCCESS** after the scoped release, event=`push`, exact head SHA `9c3eb5ebf86789e39c2c68ba9ab833a32821adc1`.

- **11/11 monitor safety tests passed.**
- `REGISTRY=MATCH`, `NEJM_PIVOTAL_INDEX=MATCH`.
- `newResearchCandidates=[]`, `sourceChangesSincePrevious=[]`, `historyStatus=NONE_PROVIDED` (first *main-branch* baseline; earlier draft-only archives are separate).
- Dated research documentary checklist state remained 5.1=3/5, 4.2=3/5, 5.3=2/5; zero scientific reviewer grades, no FDA probability.
- Saved artifact `acacia-public-evidence-checkpoint-42550358445-1`, artifact ID `13644509982`, created November 8 Pacific / November 9 UTC, 90-day retention.
- Public source checkpoint SHA-256 `daa95c1c35225abd541be9a8e716f2aae904675c047432d74b3beb191610a17d`.

### Important remaining acceptance distinction

**GitHub nightly schedule is now installed/configured on the default branch.** But the first actual **event=`schedule`** execution has not yet been observed. The successful event=`push` run confirms workflow execution, public identity check, GitHub token scope and artifact upload—not GitHub's future clock delivery. GitHub schedules may occasionally run late or be skipped during platform congestion. Check the workflow history after 8:17 PM Pacific and inspect a run with event=`schedule` before describing the timed cycle as empirically verified.

## Updated PREDICTIONS preview

The pilot source-monitor panel now links archived research evidence receipts and states **“Nightly schedule: CONFIGURED ON MAIN”**, with an explicit caveat that the first timed schedule run remains pending. The separate on-screen 15-minute live-source refresh remains functional and unchanged.

This activation does not create independent clinical method grades (still **0/800**), phase signoff (still **0/29**), FDA forecast (still **ABSTAIN**) or calibrated prediction accuracy (**NOT CALIBRATED**). Full SAP retrieval, independent safety reconciliation and separate reviewer authorization remain the actual scientific completion gates. The isolated Render medical backend remains unchanged and its manual deployment policy is preserved.
