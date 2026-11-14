# ORCA-2 owner research delivery — cutoff 2026-11-14 UTC

The owner explicitly selected the newer owner-only workflow. External reviewers, source attestors, challengers and A01–A14 are not assessment prerequisites. No owner acceptance, independent certification, deployment or FDA probability was invented.

The remote branch advanced from the initially supplied baseline `8ff3ea3c` to `20df1db2` during this session. Its updated owner-only policy and existing ORCA-2 publication/chronology modules were inspected and preserved. Earlier local work proposing the obsolete multi-person gates was set aside outside Git; it was not committed or pushed. This delivery composes the current policy and existing checks rather than replacing them. No Levels 7–20 runtime, worker, schedule, membership or production configuration was changed by this delivery.

Completed:

- New source-linked owner dossier with six separate levels, 11 retained original source receipts, chronological observations, supporting reasons, clinical/statistical questions, contradictions, limitations and exact missing evidence.
- Original primary report HTML retrieved and checked for the ORCA-2 identity. The previous collection distinction is explicit: its primary full-text XML request had failed while the collected full text was a COPD post-hoc article. Previous snapshots remain unchanged.
- SAP PDF completion certificate inspected: it reports signing completion on 2022-03-29, distinct from the 2022-03-25 cover date. No signer names, certificate IDs or private contacts are reproduced in the new packet. This is an embedded document claim, not independent authentication or an owner signoff.
- SAP introduction references protocol v3.0 (2020-09-10), while the collected protocol is v4.0 (2021-03-08). Actual database lock, first unblinding, effective approval and earlier standalone SAP versions remain unresolved. Primary completion (2021-12-23) alone proves no post-hoc planning.
- Contemporaneous sponsor disclosures for DSMC follow-up (2021-11-22), last visit (2022-01-04), pre-readout expectation (2022-03-10) and public topline results (2022-04-27) retained. These do not establish actual unblinding dates. Sponsor archive redirects/branding remain an owner source-identity question; frozen ACHV relationships were not changed.
- Original FDA E9 and 2017 draft/2022 final multiple-endpoint guidance retained as context only, not trial-specific FDA endorsement. The 2022 final guidance cannot establish what was prespecified before the trial.
- Journal supplement requests returned HTML download/challenge pages, historical registry JSON returned HTTP403 and the candidate earlier SAP URL returned HTTP404. None was promoted into an original clinical PDF or proof that earlier documents do not exist. An unrelated financing-page redirect was explicitly excluded.
- Existing numerical publication checks reused. Additional questions cover the paper's Hochberg/FDR citation mismatch, SAP familywise-error/secondary-alpha rules, missing data, ITT versus exposed safety denominators, serious events versus attributed relatedness and endpoint durability.
- Offline owner preview accepts the optional dossier and preserves all 32 trials/192 worksheet sets. No external verification gate is added. Account security and deployment permission remain separate.
- Documentary queue for the remaining 31 trials: ORCA-3 NCT05206370, SynAIRgy NCT05813275, GRACE NCT03697109, IMPALA-2 NCT04544293 and ORIGIN NCT04716231 are the next five under explicit documentary tiers/NCT tie-break. Primary-report full texts, amendment/analysis histories and clinical questions are listed per record. This is not an efficacy or FDA-approval ranking. All three unmapped exceptions remain visible.

Readiness for each level: code implemented and tested; core originals collected; owner review can proceed with limitations. Every level is OWNER_NOT_REVIEWED. Evidence completeness remains unresolved, especially Level5 chronology and version history. Independent authenticated-source and adjudicated-assessment counts remain zero as factual historical labels, not owner-assessment gates. FDA probabilities remain null.

Operational access audit: existing Next.js authentication is a password/HMAC cookie, with no individual subject or demonstrated MFA; its root page is a client-side gate and proxy.ts does not enforce global authentication. A private dossier route needs explicit server protection. The owner-only intent still has null owner issuer/principal and no live-release authorization. Real owner login/MFA, chosen private destination, persistence/access/backup acceptance and a specific release are the remaining operational actions. No outside clinician, attestor or adjudicator is required.

Local validation: 280 unit/interface tests plus 42 existing disposable PostgreSQL/integration/recovery tests passed (322 distinct applicable tests, including 28 new owner-dossier tests). The retirement audit passes with zero active dependencies. Current-head Windows/Linux/PostgreSQL and broader repository CI are inspected and linked in PR #1181; local success is not substituted for CI evidence.

Reproduce the read-only preview outside Git:

```bash
python scripts/medical/level16_offline_research_preview.py --output /tmp/orca2-owner-preview-new.html --owner-dossier reports/scientific-levels1-6/orca2-owner-research-dossier-20261114-v1.json
```

A new output path is required. This does not start a server or enable access. Originals and the generated local preview remain outside Git.

Next action: the owner can inspect the six-level dossier and record evidence questions/limitations now. For live access, identify the real owner account/provider and private destination; implement and test that destination's server-side owner access/MFA, versioned persistence and rollback before separately authorized release. The concise operational handoff is `docs/level16-owner-live-access-handoff.md`; retired A01–A14 do not apply.
