# Scientific archive: read-only cohort coverage and proposed import plan

**Snapshot audited:** 2026-10-25, connected main PDUFA Neon database
\`pdufa-new-persistent-db\`. Counts below are read-only aggregates of the
user's actual archived \`full_trial_records\` and \`program_identity\` tables.
They are **not** counts from the separate Render scientific PostgreSQL service,
are **not** verified outcome forecasts, and must not be treated as current
GEM JR/GEM/WT membership.

## Source inventory

| Main archive observation | Records |
|---|---:|
| Exact-NCT archived records | 11,598 |
| Exact-NCT program identity rows joined to their archives | 11,598 |
| Program identity rows of any source type | 11,795 |
| Records with posted trial results, according to saved source metadata | 4,916 |
| Records without posted trial results | 6,682 |
| Records where saved p-value status is REPORTED | 2,262 |
| Records where saved p-value status is NOT_REPORTED | 2,654 |
| Records where saved p-value status is NO_POSTED_RESULTS | 6,682 |
| Phase 3 only | 4,316 |
| Phase 2/3 | 291 |
| Phase 4 only | 426 |
| Phase 3/4 combined exact-NCT rows | 5,033 |
| Phase 3/4 with saved posted results | 2,714 |
| Phase 3/4 whose saved p-value status is REPORTED | 1,558 |

**Source identity:** These counts use main Neon only. A separate isolated
scientific Render readback last confirmed 2 stored trials, 2 completed batch
jobs, 4 PDF documents passing **byte** integrity, and **0** independent
scientific source verifications. These are different databases with different
purposes. Never imply that 11,598 records have been migrated into the review
database or completed twenty scientific investigation levels.

Two prior isolated pilot study IDs, \`NCT02142738\` and \`NCT04280705\`,
were **not found** among the 11,598 main archive NCT IDs at audit time.
Do not assume those isolated pilot dossiers represent the main archive.

A field labeled p-value "REPORTED" means only that the source summary
recorded p-value presence. It does not mean p < 0.05, endpoint success,
adequate statistical analysis, a verified result, or FDA approval.
Archived registry SHA256 values are stored-source digests, not proof of
independent clinical/scientific adjudication.

## Controlled list-driven path

1. First obtain currently published **exact permanent Program ID ↔ exact
   TRIAL|NCT identity ↔ list membership** for GEM JR, GEM and WT from
   approved, read-only current workspace/list sources. Do not reconstruct
   list membership from phases, scores, ticker, or market cap.
2. Join those exact NCT identities to main \`full_trial_records\`.
   Missing archived trials remain labeled \`archive_missing\` and must not
   be silently replaced with another company's program or similarly
   spelled drug.
3. Export a bounded UTF-8 inventory in this schema:
   \`nct_id\`, \`cohorts\` (array drawn from WT, GEM, GEM_JR),
   \`phases\` (ClinicalTrials.gov enumeration array),
   \`has_posted_results\` (boolean), \`p_value_status\` (one of
   REPORTED, NOT_REPORTED, NO_POSTED_RESULTS), and the archived
   \`source_sha256\` as 64 hexadecimal characters.
   Never include internal credentials, private SQL URLs, research verdicts
   or financial account data.
4. Run only the offline planner:
   \`\`\`bash
   cd new-platform/backend
   python -m app.scientific_cohort_import_plan \
     --inventory /secure/path/current-exact-program-inventory.json \
     --output /secure/path/proposed-science-batches.json
   \`\`\`
5. Review the immutable input digest, stage memberships and **up to 25 NCT
   IDs per proposed batch**. It orders WT, then GEM, then GEM JR; within each
   stage it puts Phase 3/4 first, then posted results and reported p-value
   presence, with stable NCT ties. This is *data-review priority only*.
6. No batch is authorized to run merely because it is proposed. For each
   import, independently confirm source identity, legal/use permissions,
   operator approval, isolated Render service write gate, storage/headroom,
   spending implications, and a rollback/recovery procedure. The existing
   isolated batch importer remains a separate opt-in operation.
7. A successful archive import **still** leaves each scientific grade
   unassigned until independent protocol, efficacy, safety, statistical,
   regulatory and source-reconciliation evidence is accepted. Preserve
   the separate original GEM JR and GEM FS/FA associations and WT settings.

## Read-only aggregate SQL audit

The exact trial count and phase breakdown can be reproduced without
transferring any clinical record bytes:

\`\`\`sql
SELECT (summary->'phases')::text AS phases,
       COUNT(*) AS records,
       COUNT(*) FILTER (WHERE summary->>'has_results' = 'true') AS posted,
       COUNT(*) FILTER (WHERE summary->>'p_value_status' = 'REPORTED') AS pval_reported
FROM public.full_trial_records
GROUP BY (summary->'phases')::text
ORDER BY records DESC;
\`\`\`

\`\`\`sql
SELECT COUNT(*) AS matched_exact_trials
FROM public.program_identity p
JOIN public.full_trial_records f
  ON p.source_key = ('TRIAL|' || f.nct_id);
\`\`\`

**Do not** cross-connect the production Neon database into the isolated
scientific review service, loosen Render PostgreSQL IP controls, or run
an 11,598-trial import simply to equalize counts. A separate authorized
migration and workload plan is needed before any record transfer.

## Acceptance evidence and current blockers

- Deterministic dry-run planner code:
  \`app/scientific_cohort_import_plan.py\`; no database imports or network calls.
- Guardrail tests:
  \`tests/test_scientific_cohort_import_plan.py\`.
- Required GitHub workflow:
  \`.github/workflows/scientific-integration-checks.yml\`.
- The authenticated preview-to-Render live connection remains unverified
  until the user's PDUFA Vercel team grant permits the protected preview
  to be accessed and the signed-in exact-trial connection check succeeds.
- Verified independent sources/reviewer findings are still absent.
- Production deployment and bulk import require separate user approval.
