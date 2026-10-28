# Frozen census source lineage

PR #498 already corrected the market-cap drift at commit `b80577c449b4ba123b64cee9bac24d520b2e2194`. Its existing `data/phase_pipeline_market_caps_census_2026-10-26.csv` is retained byte-for-byte. The historical census cutoff and all 741 trial / 130 company records remain unchanged.

The remaining three inputs (trial inventory, company registry and configured issuer sources) now also have frozen copies under `data/snapshots/phase3-census-2026-10-26/`. `provenance.json` identifies their original repository paths, exact source commit, Git blob identifiers, HTTPS source locators and SHA-256 digests. These are versioned repository snapshots, not new external observations or independent FDA evidence. The builder and frontend parser pin all four input hashes. Altered bytes, missing snapshots and forged lineage are rejected; no current-source fallback occurs.

`python scripts/build_phase3_census_sources.py --check` reproduces the historical public manifest from these inputs. Newer live market-cap, registry, trial or issuer files cannot change this dated directory. Refreshing a historical inventory requires a separately reviewed version with its own cutoff; this change does not rewrite observation timestamps or relax chronology validation.

Regression tests replay live-input drift in a temporary directory, reject changed or missing frozen bytes, and preserve the research-only scope. Original live scanner inputs and schedules are untouched. SHA-256 and Git lineage establish byte identity, not clinical validity, FDA qualification or prediction accuracy.
