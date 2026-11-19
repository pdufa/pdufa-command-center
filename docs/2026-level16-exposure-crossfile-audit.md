# 2026 Level 1–6 blind coverage: cross-file exposure consistency audit

**Audit date:** 2026-11-19. **Scope:** Current development branch files `data/backtest/2026-clinical-evidence-backlog.csv` and `data/backtest/2026-level01-06-blind-assessment-coverage.csv`. This is a **structural data consistency audit**, not independent FDA source verification or a scientific prediction.

## Result

- **89** distinct candidate rows in the clinical evidence backlog.
- **534** level rows in the coverage tracker (89 candidates × six levels).
- **Zero exposure-flag mismatches** between the two files, checked by event ID and level after the TIMING-025 and TIMING-037 corrections.
- **10 candidates** in the backlog have OBSERVED or POTENTIAL outcome exposure; all six levels for each have the same exposure classification as the backlog.
- The other 79 candidates have `NOT_DOCUMENTED` exposure, **which is not the same as an independently verified non-exposure attestation**.
- This audit does not assert that all 89 events are correctly identified or that the proposed full-year 196-event denominator is validated.

## Flagged candidates

| Exposure | Candidate IDs | Count |
|---|---|---:|
| OBSERVED | PDUFA26-TIMING-002, -004, -006, -021, -025 | 5 |
| POTENTIAL | PDUFA26-TIMING-005, -009, -010, -011, -037 | 5 |

**Required controls:** Do not issue, lock or score a *blind* directional prediction for any flagged candidate until a demonstrably outcome-unexposed independent reviewer completes the frozen pre-cutoff assessment. For `NOT_DOCUMENTED` candidates, collect an affirmative independent reviewer non-exposure attestation before locking.

## Verification method

Parsed the event ID and exposure status from each of the 89 backlog records; parsed event ID, level and exposure status from each of the 534 tracker records; compared each level's exposure flag to its corresponding backlog flag. **No mismatches found.**

**Accuracy status:** No directional blind predictions or scores established by this audit. No production changes.
