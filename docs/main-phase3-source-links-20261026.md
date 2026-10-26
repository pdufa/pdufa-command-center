# MAIN: source-linked Phase 3 evidence checklist

The 741-row October 26 research checklist now connects each exact NCT/ticker pair
to its ClinicalTrials.gov study/API record, saved issuer CIK and SEC filing index,
and saved Nasdaq market-cap source and check date. Configured issuer homepages
are included where available; websites are not guessed for the remaining issuers.
General FDA CDER and CBER research entry points are explicitly labelled as such.
No trial-specific FDA application, PDUFA date or outcome is established by a link.

The public directory is deterministically generated from the canonical trial CSV,
company registry, saved market-cap file and configured issuer hosts. It records
all four source-file SHA256 hashes. Validation requires exactly 741 distinct NCTs
and 130 company mappings, reconciles exact saved sponsor names, checks CIK/URL
consistency, and refuses incomplete, wrong-issuer or qualification-bearing data.
This is a consistency check on saved inputs, not authentication or independent
reverification of an external source. Market caps and CIK mappings retain their
original snapshot scope and require fresh listing/corporate-action checks.

## Seven checking methods

| Gate | Method and remaining work |
| --- | --- |
| Phase 3 registry identity | Structured recheck of exact NCT, phase, sponsor, status and source date |
| Listed issuer / market cap | Structured recheck of ticker/CIK, current listing, dated quote and corporate actions |
| Drug / formulation / indication | Reconcile registry arms and interventions against exact original program documents |
| Program active | Reconcile dated company program statements, including discontinuations |
| Development rights | Reconcile exact partner/licensee identities and rights documents |
| U.S. FDA / PDUFA | Reconcile original records to exact drug, indication, application and review cycle |
| Mandatory restrictions | Evaluate every existing mandatory rule with its own required evidence |

The display describes checking methods and preserves the separate authenticated
current-registry lookup. This source-link update does not install a bulk
external-source scan. Five independent evidence gates remain unverified per
trial, and the first two gates remain census-only. Qualified Pipeline total and
FDA probabilities stay unknown/unavailable. No membership, FS/FA preset, nightly
scan schedule, trading permission or scientific acceptance state changes.

## Reproduction and validation

From the repository root, run `python3 scripts/build_phase3_census_sources.py --check`.
Run without `--check` only to rebuild the directory from reviewed saved sources.
The frontend tests verify every original mapping and export row, reject forged
qualification and mismatched URLs/identities, and render the source-linked UI.
The existing MAIN evidence-gap CI workflow enforces these checks when inputs,
source contracts, generated pointers or the trial checklist change.

The downloadable checklist has 741 rows and 36 columns, including original source
pointers, source dates, research-only scope and the method for each gate. It is
not a verified Pipeline list or a substitute for the remaining source research.
