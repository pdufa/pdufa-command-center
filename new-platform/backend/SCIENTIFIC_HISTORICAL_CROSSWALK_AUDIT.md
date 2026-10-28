# Historical GEM and GEM JR trial-reference audit

**Read-only audit date:** October 25, 2026  
**Historical membership snapshot:** `snapshot/gem_stage_membership.json`, October 16, 2026  
**Main archive checked:** connected Neon `public.full_trial_records`  
**Scientific Render import executed:** **No**

## Observed coverage

| Observation | Count |
|---|---:|
| Historical GEM program entries | 5 |
| Historical GEM JR program entries | 14 |
| Historical entries total | 19 |
| Entries with exactly one NCT hint | 16 |
| Entries with multiple NCT hints | 1 |
| Entries without an NCT hint | 2 |
| Distinct hinted NCT identifiers (including multi-NCT split) | 17 |
| Distinct identifiers present in main Neon archive | 17 |
| Entries with direct `TRIAL|NCT########` source keys | 3 |
| Application-level entries with NCT candidate hints | 14 |
| Independently approved application ↔ NCT crosswalks | 0 |
| Independently verified scientific claims or FDA outcome grades | 0 |

### Why the 17 distinct references matter

The application-level entry `APPLICATION|IONS|BEPIROVIRSEN_CHB_20261026`
contains **two** references:

- `NCT05630807`
- `NCT05630820`

Both references were observed in the main Neon `full_trial_records` archive.
They must **not** be collapsed into one trial, scored as a single study, or
treated as independently verified regulatory evidence. The remaining 15
unique identifiers were also observed in the archive during the read-only
October 25 query. Presence in the archive is not confirmation that the
program-to-study association is clinically or regulatorily correct.

Two older GEM JR entries (`CYTK / MYQORZO` and `SMMT / IVONESCIMAB`)
have **no valid NCT hint** in this historical snapshot. Do not assign a
study based on drug or ticker similarity.

`IRD` and `VTRS` historical application entries both cite
`NCT06542497`. This is a source-level reuse, not proof that each
company's regulatory application is identical or that either outcome is
resolved. Human regulatory crosswalk review is needed.

## Release and source-truth boundaries

1. The saved October 16 membership is **nine days old** as of this audit.
   Its labels `ACTIVE`, `GEM` and `GEM_JR` are **historical**, not current
   membership proof.
2. The current published GEM JR/GEM lists and actual saved WT permanent
   Program IDs must be separately loaded using the authenticated read-only
   scientific coverage endpoint (`/api/scientific-cohort/coverage`).
3. Application-level `nct_id` strings in the old snapshot are only
   candidate review references. Of the historical entries, only three
   originate from direct `TRIAL|NCT########` source keys, which certify
   *identity syntax only*.
4. All 17 referenced registry trials being archived in main Neon
   **does not** mean they are present in isolated Render scientific
   PostgreSQL, have accepted efficacy/safety citations, have completed
   20-level investigations, or qualify for regulatory-outcome prediction.
5. No GEM JR/GEM FS/FA preset or WT membership is changed by this audit.
   No archive imports, approval scores, trading orders, scans, or
   new Render services were initiated.

## Implemented code and regression checks

- `app/scientific_historical_crosswalk.py` analyzes the historic snapshot
  with a separately supplied list of exact archived NCT identifiers.
- `tests/test_scientific_historical_crosswalk.py` validates the
  19-entry, 17-NCT historical fixture; preserves multi-study references,
  quarantines unverified application-to-study associations, flags missing
  archives, rejects contradictory direct trial keys and future snapshot
  dates, and confirms zero imports/scores/preset changes.
- `.github/workflows/scientific-integration-checks.yml` requires the
  audit tests as part of the isolated integration validation suite.

### Read-only Neon reproduction

To independently confirm archive availability for proposed NCTs, use
a parameterized read-only query against main Neon:

```sql
SELECT nct_id, summary->>'has_results' AS results_posted,
       summary->>'p_value_status' AS p_value_presence,
       (summary->'phases')::text AS phases
FROM public.full_trial_records
WHERE nct_id = ANY($1::text[])
ORDER BY nct_id;
```

Populate `$1` only with exact NCT strings validated by the Python
historical-crosswalk tool. Missing archive rows must remain missing;
never fetch arbitrary regulatory files or initiate an import to make
these counts match. A source label `p_value_status=REPORTED` means
p-value *presence only*, not significance, trial success, or FDA approval.

**Decision:** Candidate research queue available for controlled human source
review. **Not approved for automatic crosswalk, bulk import, independent
scientific grading, or production release.**
