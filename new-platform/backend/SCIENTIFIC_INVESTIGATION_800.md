# Scientific investigation: 800-point planned review matrix

**Status:** isolated review-branch implementation, NOT production and NOT
scientifically adjudicated. This is a deterministic list of work to perform,
not a clinical result.

The requested scientific architecture is eight subject layers with five
assessments per layer (40 unique assessments), independently reviewed at
20 methodological depths. That creates **40 × 20 = 800 pending tasks per
exact-NCT trial**, with two independent reviewer roles to be assigned.

The 20 methodological depths begin with Document Reading and end with
Red-Team Adjudication. They are **not** the same as the pre-existing
20-stage ClinicalTrials.gov registry-source coverage panel, which reports
document/field presence only. Nor are they the pre-existing eight-depth
320-task worksheet. This new matrix is separately versioned so that the
existing offline A/B worksheets and release safety assertions remain valid.

## Module and integrity contract

`app.scientific_investigation_800.build_investigation_800("NCT02142738")`
returns an unscored dictionary with the exact `TRIAL|NCT...` identity, 20
methods, 40 assessments and 800 stable task IDs. Every task begins
`pending_independent_review`, with both reviewers unassigned and no
scientific score. The plan cannot assert list membership or infer NCT IDs
from ticker, molecule, indication, company, application or PDUFA event.

Both independent scientific/clinical adjudication and dated primary
evidence are prerequisites for a task to be completed by a future,
separately authorized reviewer subsystem. Plan-generation does not
authenticate reviewers, load scientific source bytes, fetch a registry,
submit findings, modify PostgreSQL, compute readiness or reluctance grades,
fit an FDA success model or write data to GEM JR / GEM / WT. All grades,
conclusions and approval probabilities emitted by this plan are `null`.

## Validation and subsequent integration

The isolated regression test verifies exact 800-task uniqueness and
40-by-20 coverage; no fake completion or scores; strict exact NCT IDs;
and backward compatibility with the existing 320-task handoff contract.
Run from `new-platform/backend`:

```sh
python -m unittest discover -s tests -p 'test_scientific_investigation_800.py' -v
```

After code review, a future explicit integration step can attach this
new planned-task contract to a **read-only** exact-NCT scientific endpoint
and separate reviewer A/B worksheet exports. Do not silently replace the
existing 320-task API or exports. Later readiness/reluctance calculations
must remain distinct from any eventual calibrated FDA outcome prediction.

Before a production release: validate original source content and hashes;
validate reviewer identities and qualifications, sign independent paired
judgments and resolve disputes; verify cohort membership; run the full
scientific/WT FS-FA parity suite; and receive explicit release approval.
No import, scan, trading, production deploy, charge, or new service is
authorized by this isolated work.
