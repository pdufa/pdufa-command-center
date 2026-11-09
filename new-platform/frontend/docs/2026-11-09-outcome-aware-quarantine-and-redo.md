# Quarantined outcome-aware historical FDA assessments — November 9, 2026

## User-directed change

Removed these entries and their display components from the active ASSESMENTS page
and assessment-level chart:

- **INO-3107 (INO)**: historical research panel, including its original postdecision CRL-lean call and later outcome-known Level 3-style approval reassessment.
- **Bepirovirsen (GSK/IONS)**: October 26, 2026 target, hindsight Level 3-style approval lean.
- **Joenja (PHAR)**: October 24, 2026 target, hindsight Level 3-style approval lean.
- **SKYRIZI (ABBV)**: October 23, 2026 action, hindsight Level 3-style approval lean.

**Exception explicitly retained:** **AZN / Ultomiris (ravulizumab)**, October 21 FDA accelerated approval, remains visible as the *only historical demonstration* (and must be marked **outcome-aware / not blind**). The original **SMMT / HARMONi prospective pilot** remains visible because its actual FDA outcome was not known when its original directional forecast was recorded.

Prior case JSON and source/dossier files remain in GitHub as historical, read-only archives. This is not data deletion or retroactive revision of frozen predictions. All archived observations and comparisons remain excluded from live accuracy and probability calibration. The FOCUS 29 roster and all retired-system safeguards remain unchanged.

## Redo requirement and current status

The four removed historical cases **cannot be redone as honest blind predictions by the same evaluator**: their FDA outcomes have already been seen in this conversation. Reversing the order in code, erasing the visible prediction or hiding the result afterward cannot restore blindness.

A true independent redo requires all of the following, for each prior case:

1. An independent custodian supplies a frozen, **point-in-time** bundle of regulatory/clinical material dated strictly before the FDA action, with no outcome or hindsight-contaminated passages.
2. An **outcome-unexposed independent evaluator** (human or a separately isolated system without access to historic outcomes) completes phase verification, benefit-risk, FDA legal/pathway risk, clinical and CMC evidence gaps and writes its prediction.
3. The prediction, assessment depth and evidence links are **immutably committed** before the custodian retrieves or discloses the actual FDA result.
4. A separate outcome record is appended and compared; a missed outcome is never overwritten.
5. If the case, evaluator, or evidence bundle leaks the result, the outcome stays **EXCLUDED** from blind accuracy and calibration.

**Current status: NOT REDONE / BLOCKED UNTIL INDEPENDENT UNEXPOSED EVALUATOR IS AVAILABLE.** The quarantine manifest records the cases and the required stages. No new fabricated "blind" forecasts have been placed back into the program. New prospective cases, or independently held-out older cases truly unseen by their evaluator, should be preferred to attempts to unlearn existing FDA outcomes.

Implementation file: `new-platform/frontend/data/historicalOutcomeAwareQuarantine2026.json`.
