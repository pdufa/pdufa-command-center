# Historical FDA comparison engine — research installation

This increment preserves PR #522 on `research/fda-decision-label-gate-20261028`.
It implements research software, not a validated FDA prediction model. Every
projection remains **NOT_READY / ABSTAIN** with unavailable probabilities.

## Recovered baseline

The interrupted checkout was at `04b49ec9`. Before editing, the branch was
fetched and fast-forwarded through these GitHub commits:

| Commit | Preserved implementation |
| --- | --- |
| `331c9568` | Eight-definition evidence-slot registry with 650 proposed slots |
| `8a34d406` | Registry missingness and verification safety tests |
| `d853599a` | Point-in-time historical label provenance gate |
| `34fe1d06` | FDA label and leakage regressions |

All 11 GitHub Actions workflows succeeded at `34fe1d06`, including evidence
safety run #45 and FDA label gate run #305. Local baseline verification passed
133 security tests and 388 historical research tests; one external RFC3161
fixture test was skipped. A skipped fixture does not establish independent
timestamp verification. Existing uncommitted catalog, registry and comparison
drafts were retained and completed rather than replaced.

`dd576e40` additionally fixes malformed label inputs and nonboolean independent
verification flags while preserving the four commits' research-only contracts.

## Implemented interfaces

- `research.historical_decision_registry`: deterministic import, strict schema,
  scoped validation, source-bound predecision views and FDA label-gate receipts.
- `research.scientific_historical_comparison`: ten comparison criteria across
  15 descriptive fields, known-evidence denominators, selection explanations,
  relevance limitations and explicit exclusions.
- `research.scientific_field_catalog`: versioned draft definitions and mappings
  for the eight domains, all 40 original assessments and 50 investigation tasks.
- `research.scientific_evidence_registry`: dated source reports, conflicting
  evidence, completeness and source quality tracked separately. It withholds
  excluded finding values and cannot accept self-certified verification.
- `research.scientific_comparison_service`: server integration functions joining
  the evidence and comparator projections after authorization of every scope.
  It also examines the real six-case registry and reports why those records
  cannot yet enter the comparison engine. It never substitutes guessed review
  cycles or outcome-derived features for missing inputs.

The comparison criteria are indication, therapeutic class, mechanism, endpoints,
efficacy, safety, trial design/statistics, regulatory pathway, manufacturing and
prior FDA decisions. Case-insensitive text/list agreement is descriptive. Its
matched/comparable fraction and coverage have explicit denominators; neither is
an approval probability, clinical equivalence assessment, effect-size distance,
validated similarity score or automated clinical relevance ranking.

Historical actions require the preserved label gate's document identity, SHA-256
and aware decision/publication timestamps. A passed metadata gate permits research
review only: it does not authenticate the supplied document bytes. Actions and
publication must precede the current comparison cutoff; features must precede
their own historical action. UTC boundaries, missing publication clocks, source
roles, conflicting findings and unknown evidence remain explicit. Duplicate
application/cycle aliases are rejected. A first formal extension or CRL cannot be
replaced by a later approval. Missed targets, withdrawal, unresolved review and
refusal to file cannot silently become CRL or EXTENSION.

`program_id` is an access scope; `program_family` identifies related drug
programs. The server service uses the existing `ResearchPrincipal` authorization
contract before any projection and passes only its immutable program grants to
the pure comparator. The pure functions do not authenticate users. No HTTP route
is mounted and no production authentication is changed.

## Actual historical evidence

The importer reuses **six existing curated cases**, preserving **26 source
observations**: NVAX, UNCY, TNXP, BCRX, CORT and VNDA. It also retains three TNXP
trial metadata leads from the existing RELIEF/RALLY/RESILIENT dossier. Their
public availability remains unverified, so they are excluded as prediction
features. No new FDA source document was retrieved or independently verified
by this engineering increment.

The curated action dates remain distinct from legacy goal dates: NVAX May 16,
2025 versus April 1; UNCY June 27 versus June 28; BCRX December 11 versus
December 12. TNXP August 15, CORT December 30 and VNDA December 30 retain their
existing action claims. These are attributed research records, not newly
authenticated decision labels. CORT still has a later corrected CRL, and UNCY's
original first page needs review. Original document bytes/publication clocks,
exact cycle adjudication and independent evidence review remain missing.

Company names and 17 structured scientific comparison fields remain null where
the source assets do not contain reviewed structured findings. Missing fields
are not negative clinical or manufacturing findings. Source narratives and
references are retained for investigation; narrative presence never completes
an assessment. Local manifest checksums identify imported repository artifacts,
not original FDA bytes or independent timestamp anchors.

**Independently verified decision cycles: 0. Independently backtested forecasts:
0. Validated predictive accuracy, Brier score, calibration and discrimination:
unavailable.** The unchanged legacy history still has 146 records. Its retrospective
outcomes and post-action archive locks do not become prospective forecasts.

## Scientific catalog status

The original eight field definitions and their base properties remain unchanged
in the original catalog. A separate draft catalog adds specific scientific
definitions with rationale, conditional applicability, source requirements,
canonical assessment mappings, criteria and uncertainty handling:

| Domain | Draft definitions |
| --- | ---: |
| Biological rationale | 70 |
| Mechanism of action | 70 |
| Clinical trial design and execution | 110 |
| Efficacy and statistical evidence | 110 |
| Safety and tolerability | 100 |
| Chemistry, manufacturing and controls | 80 |
| Regulatory history and FDA precedent | 60 |
| Independent validation and prediction uncertainty | 50 |
| Total | 650 |

These are 650 structurally checked draft definitions, including the preserved
eight, with **zero independently scientifically validated definitions**. They
contain no clinical values. Their organization is a proposed crosswalk; original
canonical layers, S01–S40 IDs and FS/FA associations are not renamed. All 50
investigation task contracts have inputs, criteria, sources, uncertainty and
readiness conditions. Zero task levels or canonical assessments are independently
completed by defining that architecture.

The evidence registry deliberately cannot remove conditional fields from the
denominator through client-supplied applicability claims. Independent applicability
adjudication is still needed. Completeness counts describe available source
reports across defined slots, not clinical quality or probability of approval.
Computed observation hashes and reference histories are derived diagnostics,
not persisted append-only audit events or source authentication.

## Reproduce verification

```sh
python -m research.historical_decision_registry
python -m research.scientific_field_catalog
python research/prediction_v1_1_catalog_validator.py
python -m unittest discover -s tests -p 'test_prediction_v1_1_*.py' -v
python -m pytest -q tests/test_scientific_*.py tests/test_historical_decision_registry.py
```

The new `Scientific historical comparison safety` workflow runs the original
security gates and the new regression suites. Tests use clearly identified
synthetic documents to verify software behavior; those fixtures are never
counted as scientific evidence or validated predictions.

Local verification of this increment:

| Check | Result |
| --- | --- |
| Combined security, FDA history, scientific architecture and TNXP regressions | 739 passed; 298 subtests passed; 1 external timestamp fixture skipped |
| Existing backend preservation suite | 1,001 passed |
| Existing GEM source-ledger structure validator | Passed; saved evidence only, not live verification |
| Draft scientific catalog | 650 distinct definitions, 40 original assessment IDs, 50 task contracts; zero independently validated |

The combined suite reports a Starlette/httpx deprecation warning and an existing
unregistered integration-mark warning. The backend reports six existing warnings.
There are no failed tests in these completed local runs. Final GitHub Actions
status is reported against the pushed commit rather than inferred from local
results.

## Integration limits and next milestone

The code is ready for review and isolated server integration testing. It is not
production-mounted or scientifically validated. Evidence completeness, source
quality, scientific readiness, prediction confidence, calibration, independent
validation and abstention remain separate fields. Full projections can support
expandable dashboard details; this increment adds no dashboard route or live
database writes.

Next: retain and independently review original action bytes and public timestamps;
adjudicate exact cycles and the 650 draft definitions; extract source-bound
predecision findings into comparable structured values; prespecify endpoint and
indication harmonization; then freeze a chronological holdout protocol and test
reproducible baselines. Independent validation and calibration must precede
probabilities. The unresolved RESILIENT exclusion authority and actual-provider
authentication acceptance remain separate blockers.

Production authentication, data, scanners, schedules, list memberships, original
GEM JR/GEM FS/FA associations, spreadsheet writes and trading are unchanged.
Nothing is merged or deployed by this milestone.
