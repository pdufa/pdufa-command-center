# MAIN Revision 41 — pinned 29/23 FOCUS original source-access metadata and PREDICTIONS evidence overlay

**Date:** November 9, 2026. **Owners:** GitHub issues #979, #980 and Stage 4 draft #965. **Source run:** [R40 public-source recovery #42654460905](https://github.com/pdufa/pdufa-command-center/actions/runs/42654460905), exact commit 30ba3db611d2adfe4f694c715fd714267643edfb.

## What was actually collected

R40 independently retrieved metadata/response fingerprints for all **29 canonical exact-NCT ClinicalTrials.gov v2 records** and **23/23 provisional FDA application groups** through 21 successfully fetched distinct public-source URLs among 22 attempted. One original issuer-hosted Achieve 10-Q returned HTTP 301 / denied redirect; an official SEC archived equivalent was retrieved (bytes 2,759,323, SHA-256 b0ea5daad7ab6d7682e53348c2158d7e16939ad8c2776a51c2921d25abec3cc2). Sarepta's large Form 10-Q was hashed by bounded streaming; no issuer source bodies were copied to the repo.

The official exact-NCT registry response JSON has an identifiable results section for **12/29 trials**, and lacks such a section for **17/29 trials**. This is not a pass/fail for efficacy, a negative finding or a universal measure of Phase 3 publication. A company or peer-reviewed journal may already publish outcomes not deposited in ClinicalTrials.gov. Of the 29 registry phase entries, 28 are PHASE3 and one (NCT04871282) lists PHASE2 and PHASE3. API identity matching and response digest are not an independently verified final clinical phase signoff.

Source receipt:
- Full original source-access receipt digest: **0601058cd65f62380c3f3242b408f95ca13408f21d2845e589e9e4f5faf7d32c**, captured 2026-11-09 16:24:54 UTC.
- [GitHub Actions artifact 13691348436](https://github.com/pdufa/pdufa-command-center/actions/runs/42654460905/artifacts/13691348436), ZIP SHA-256 **5a13370a47d864c7a5a900a9d9d9b773d98fb792e091215c06b0190808b536b4**, expires February 7, 2027 UTC. This source metadata archive is **not permanent backup**.
- The new pinned \`focus-r40-public-source-audit.json\` preserves the 29 exact NCT IDs, 12 observed registry-results-section identifiers, the 23 exact provisional application IDs, Achieve SEC alternative, run/archive provenance, count totals and SHA-256 of the full receipt. It contains metadata only, not copyrighted copies or clinically signed source documents.

## UI and read-only machine interface

\`focus-r40-source-readiness.ts\` fails closed if the record/version/hash/29+23 membership/research-only status changes. It overlays **source-access metadata** on the existing Version 39 qualitative clinical research panel:
- Summary: 29/29 trial records, 23/23 application groups with public-source access, 12/29 current registry results sections, 21/22 distinct source URLs fetched.
- Per exact NCT: registry results section present vs absent in the *current* record, with no negative efficacy inference.
- Per provisional application: canonical public source retrieved or official SEC fallback; first-publication evidence, clinical conclusions and regulator cycle remain independently unverified.
- Distinct JSON metadata endpoint \`/api/predictions/focus-source-readiness\` supports source-audit exports without modifying the original version 39 assessment feed \`/api/predictions/focus-preliminary\`.

The source metadata, scientific findings, independent grade and official forecast remain distinct. **All future FDA approval/CRL and review-delay predictions still ABSTAIN; authorized new independent clinical signoffs 0; calibrated probabilities and historical valid FDA backtests unavailable.** Source-fetch success is not clinical source-authentication or regulatory approval verification.

## Continuation

First reconstruct documented pivotal endpoint quantities and original safety/reporting definitions from each accessible source where lawful, including alternative peer-reviewed primary Phase 3 papers, trial protocols/SAP, sponsor SEC disclosures and FDA primary application/CMC information. Record exact original-first-publication clocks and independent reviewer quality signoffs before changing scientific grades. Keep separate original-application historical cohort construction (#980), without importing the selected 412 research leads as validated prediction cases. Freeze the previous qualitative Rev39 leans without silently revising their audit history.

No production deployment, reviewer-score writes, Vercel routing aliases or security-role changes are authorized by this research metadata overlay.
