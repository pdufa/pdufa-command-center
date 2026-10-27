# PDUFA master directive development report — October 27, 2026 Pacific

Repository: `pdufa/pdufa-command-center`. Branch:
`feature/decision-workstream-20261026`. Existing draft PR: #498.

## Preserved starting work

The environment was running and connected. The clean local checkpoint
`77846c77` was behind the PR. Fast-forwarded to `8a0f1184`, preserving all **49**
intervening commits, including the governing directive, original historical
parallel specification, FDA source registry, taxonomy/staging scripts, and exact
trial-source identity guards. Both `dd4f9f65` and `e5800a07` exist and are ancestors.
All 12 PR-triggered workflows reported success on `8a0f1184` before development.

Read `docs/MASTER_PDUFA_PASS_FAIL_DIRECTIVE.md`, the comparison specification,
source registry, existing HOP imports/comparators, chronology/calibration gates,
and scientific dossier/manifest/dashboard contracts. Existing functionality was
extended; no historical corpus or prediction model was recreated.

## Implemented and verified engineering

| Commit | Correction and resulting behavior |
| --- | --- |
| `e59f3a2a` | Bounded original-PDF intake: explicit new development archives only, exact original manifest and content-addressed bytes, proxy/TLS downloads or secure offline hash receipt, no overwrite/symlink/traversal/ZIP extraction. Receipt integrity never grants source truth or model eligibility. |
| `43defa46` | Versioned HOP JSON intake shares CSV validation. Predecision features and later outcome-document availability have separate dates. Ambiguous old arrays are rejected with migration instructions; canonical application/cycle identity is retained and imported cases remain quarantined. |
| `a58f3f4c` | Historical matching returns explicitly unverified candidates rather than invented verified matches. Enforce exact application/submission/cycle identity and chronology, exclude the target application, deduplicate trial rows, and quarantine conflicting cycle claims. Similarity remains unscored. |
| `c74939ae` | FDA action staging no longer turns any nonempty URL into a verified PASS/FAIL training label. Require exact identity and distinct source/action/retrieval dates; separate candidate counts from verified counts. Record actual ZEVASKYN source observations with unknown fields preserved. |
| `cf93ffc3` | SCIENCE requires qualitative approval direction with rationale plus source-bound supporting/opposing challenge arguments for research readiness. Strict manifest transport and dashboard support these records. Explicit prediction output remains INSUFFICIENT EVIDENCE even for complete synthetic research fixtures. |
| `6b109651` | Same-cycle rescissions/corrections withhold dependent candidates pending prior-action adjudication. Different cycles remain separate and later revisions cannot rewrite earlier cutoffs. Each document's receipt timestamp follows its actual acquisition and hashing, separate from intake start. |

Source URLs, matching identifiers, hashes and declared reviewers are consistency
inputs, not independent scientific/source validation. Dossiers keep 20 levels,
40 assessments and eight layers. Record completeness, qualitative inference,
model probability and confidence remain distinct. Missing directions/challenges
block readiness; declarations cannot authenticate reviewer independence.

## Actual source evidence and historical counts

Reopened the FDA April 16, 2024 CRL and April 28, 2025 approval for prademagene
zamikeracel / ZEVASKYN. Read the FDA regulatory action summary, which explicitly
documents the original September 25, 2023 receipt, October 28, 2024 resubmission,
and April 29, 2025 action due date. It adds FDA support for the resubmission
previously supported by a sponsor SEC statement. See
`research/fda/zevaskyn-source-reconciliation-20261027.md` for exact URLs and PDF
page locators.

| Measurement for this selected application intake | Count/status |
| --- | --- |
| Official source PDF text observations | 3 documents |
| Source action headings observed | 1 approval; 1 complete response |
| Applications selected | 1; deliberately selected, not a cohort denominator |
| Independently verified eligible PASS cycles | **0** |
| Independently verified eligible FAIL cycles | **0** |
| Model-eligible records | **0** |
| Original PDF bytes acquired by the CLI | **0** |
| Independent predictive accuracy/calibration/discrimination | **Unavailable** |

The connected research tool could read those exact FDA PDFs. Direct cloud
acquisition failed with `Tunnel connection failed: 403 Forbidden`; the enforced
network policy excludes FDA hosts. No archive was created. Three observations
are structured transcriptions, not retained original PDFs. No original-PDF hash,
source publication date, official cycle ordinal, independent review, complete
denominator or predecision scientific feature set is invented.

The two JSONL observations intentionally retain null review-cycle/publication
fields. Running the corrected audit excludes both with
`missing_exact_application_submission_cycle` and
`unknown_or_invalid_source_chronology`. The committed staging audit reports zero
verified/model-eligible records. A CRL and subsequent approval are separate action
observations; this does not independently certify their complete cycle histories.

## Verification

Baseline at the preserved upstream head: **2,212 passed, 1 skipped; 557 subtests**.
Intermediate complete runs passed after integration and action-revision repairs.

| Final check | Result |
| --- | --- |
| Complete default pytest at final implementation | **2,452 passed, 1 skipped; 557 subtests passed** |
| FDA taxonomy/audit/matching/document-intake regressions | **216 passed** |
| HOP JSON/comparator/staging/CSV subset | **71 passed** |
| Frontend `npm test` | **93 files passed; 0 failures** |
| TypeScript, no incremental cache | Passed |
| Next.js local build | Passed; no deployment |
| Frozen census rebuild | Passed; 741 exact trials / 130 company mappings |
| Read-only schedule audit | METADATA_DRIFT; runtime CONSISTENT; warning exit 2 |
| Whitespace/source checks | Passed |

The existing opt-in smoke skip is unchanged; dependency/Pandas deprecations are
unchanged. An initial SCIENCE panel run exposed two strict-transport schema
failures; the manifest validator was updated and the full frontend rerun passed.
Synthetic PDF bytes, dossiers and forecast fixtures test software behavior only.
They are not historical FDA records or independently validated prediction results.

Execution logs are ignored development artifacts under
`work/master-directive-20261027/`, including `final-head-pytest.log`,
`science-direction-frontend-final.log`, `final-typecheck.log`, `build.log`,
`schedule-audit.json` and `document-download.log`. Inspect Actions for the actual
pushed PR head; earlier CI results do not certify a later commit.

## Installation, scientific readiness and predictive performance

| Workstream | Verified installation behavior | Scientific/performance gap |
| --- | --- | --- |
| Historical FDA | Source registry, retained-byte intake, exact-cycle staging, corrections/CRL-to-approval separation, explicit audit counts | Original bytes, independent source/cycle/indication/publication adjudication and complete approval/nonapproval denominator |
| SCIENCE | Exact-trial dossier transport, qualitative directions, challenge argument sources/chronology, 20/40/8 inventory gates | Real independently reviewed protocols/SAP/endpoints/populations/efficacy/safety/regulatory/CMC evidence |
| OUTCOME | Existing leakage/holdout/calibration safeguards retained; new staging cannot self-certify labels | Original frozen predecision forecasts, blinded feature snapshots, independent temporal/forward evaluation against baselines |
| MAIN | Existing issuer/market/financing/restriction associations retained; scientific challenge evidence visible | Independently audited point-in-time issuer/financial/market/risk inputs and validated predictions |
| DECISION/dashboard | Explicit INSUFFICIENT EVIDENCE abstention, null approval/nonapproval probability and confidence, research readiness separate | Reliable model predictions remain unavailable for every stage |
| SCAN | Census reproducibility and existing clock audited without dispatch/write | No new live scan refresh, model version activation or trading integration |

No global installation percentage or ETA is inferred. Evidence and independently
validated performance remain incomplete. The existing dated platform acceptance
baseline is not changed by passing software tests. All research/model/trading
boundaries remain in place; GEM JR, GEM, WT and separate FS/FA associations are
preserved.

## Access observations and next priorities

The shell has no configured `DATABASE_URL`; tests use their isolated development
fixtures. No production database was connected, migrated or modified. Vercel's
connected tool identified `pdufa-new-dashboard` read-only. Render service listing
requires a confirmed workspace and none was selected; no service changes were
attempted. These observations do not certify production service health.

1. Enable supported direct FDA access, starting with `download.open.fda.gov` and
   `www.fda.gov` for the committed manifest; historical bulk reconciliation also
   needs `api.fda.gov`, `accessdata.fda.gov` and `www.accessdata.fda.gov`. Use the
   cloud environment network-configuration workflow, or reviewed offline exports.
   Do not bypass the proxy or reinterpret a policy denial as missing FDA evidence.
2. Retain original documents, independently adjudicate application/submission/
   cycle/indication/action/publication identity, and define the historical target
   population and coverage gaps. Keep corrected/rescinded/nonbinary events explicit.
3. Recover original predecision scientific disclosures and genuine frozen
   forecasts/plans. Obtain distinct independent supporting/opposing review. A
   retrospective FDA review is a label/context source, not a predecision feature.
4. Connect the resulting adjudicated corpus to the existing comparison and
   reviewed-manifest workflow. The reviewed evidence directory remains opt-in and
   unconfigured; no default or synthetic product evidence was installed.
5. Fit and evaluate only after data gates pass: blinded temporal application
   partitions, baseline comparison, calibration, discrimination, uncertainty,
   abstention coverage and independent forward evidence. No model was trained or
   called validated in this session.
6. Complete dated MAIN evidence and common stage integration with real reviewed
   inputs. Preserve all membership, ranking, restriction and FS/FA rules.

Push only the named development branch and update PR #498. No merge into main,
production deployment, live scan schedule/configuration change, real/paper trading
activation, order placement, new paid service or security weakening is authorized
or performed by this development work.
