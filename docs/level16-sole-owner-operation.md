# Levels 1–6: sole-owner operating direction (2026-11-13)

**Status: owner preference recorded; not a live access-control change or a clinical signoff.**

The owner directs that **one human only** operates/administers the PDUFA
site, performs the owner's clinical research review and controls publication.
Do **not** invite additional site editors, administrators, reviewers,
challengers or other human operators. Do not provision shared human credentials.
The owner is sole decision-maker; automated tools and cloud vendors are
software/service processors, not additional invited human site reviewers.
This preference does not prove that pre-existing provider/team members have
been audited or revoked; audit real access separately before claiming exclusive
access. Providers may still have infrastructure operations access under terms.

## Distinguish two different products

1. **Owner-only phase-first research (the requested default):** One authenticated
   owner may collect publicly accessible original data, generate and inspect all
   32 FOCUS trials' 192 preliminary Levels 1–6 worksheets, review conflicting
   documents, enter their own findings/reasons and decide whether or when to
   publish qualified **owner-authored research**. No external reviewer is needed
   merely to perform research. Owner decisions are **self-review**, and sources
   are **owner-checked** unless independent third-party attestation is actually
   obtained. A prediction estimate, if eventually produced, must be labeled
   as model/owner-estimated, with cutoff, calibration, confidence and limitations.
   Never label it medically independent or 100%-certain.
2. **Existing independent medical adjudication (separate and inactive):** The
   previously proposed five-distinct-person identity/clinical reviewer workflow
   remains unmodified in its existing code and schema. It may **not** be called
   satisfied by one person performing every role or by adding fictional
   aliases. Until a future separate owner decision explicitly requests a genuine
   external verification workflow, this independent certification track is
   **not the operational requirement for owner's own research**. Retain the
   original safeguards for any claims using the term independently adjudicated.

The owner's conversational broad approval expresses intent to proceed with
owner-only, safe software/research preparation. It is **not** evidence of a
particular billing cap, cloud deployment region, paid subscription, legal
source-access authorization, individual account identity, or real protected
infrastructure. Do not mark the independent-review A01–A14 record approved
merely from this preference, do not purchase, and do not deploy to production.

## Implemented non-invasive split

- `infra/level16-staging/sole-owner-intent.json`: strict owner preference,
  single operator slot, MFA requirement, no outside editor/reviewer accounts,
  owner ID and provider still unset, no live-release/billing authority.
- `scripts/medical/level16_sole_owner_work_queue.py`: read-only private
  owner research queue, derived from the existing exact 32-NCT / 192-Level
  immutable-snapshot-consistency research handoff. Every level carries
  source-coverage and phase-applicability status, owner research questions,
  owner-entered-review still pending and zero independent scientific judgments.
  It does **not** grant or accept credentials, fabricate owner-authored notes,
  make a clinical score or alter an application.
- `tests/test_level16_sole_owner_work_queue.py`: assert one human operator,
  no external user accounts, no fabricated signed medical review or FDA
  probabilities, complete NCT/level coverage, no purchased/deployed resources,
  no modification of the existing reviewer workflow. The tests are software
  regression checks, not proof of real account exclusivity.

Run locally, on a reviewed checkout:

```powershell
python scripts/medical/level16_sole_owner_work_queue.py --nct NCT04576949
python scripts/medical/level16_sole_owner_work_queue.py > sole-owner-focus-research-queue.json
python -m unittest discover -s tests -p "test_level16_sole_owner_work_queue.py" -v
```

The initial output has **zero completed owner-written reviews** because no
individual, authenticated owner findings were entered. Research worksheets
already exist and may be used. This is NOT a request to add outside reviewers.

## Real remaining steps for owner-only operation

1. Identify and **verify the actual one owner principal** in GitHub, hosting,
   database and an individual MFA-enabled sign-in path. This requires access
   audit of real accounts, not assumptions. Preserve least-privilege automation
   service identities required to run the software, distinct from humans.
2. Owner confirms exact hosting/database/location and **concrete maximum monthly
   budget**, or explicitly selects a secure local/no-new-cloud-cost option;
   provider pricing and existing subscriptions must be rechecked. Blanket
   approval alone does not specify amounts or authorize purchases.
3. Configure and test login, private ingress/public read-only boundary,
   encryption, backups, recovery, key rotation and secrets without altering
   production or disabling auth. The sole-owner mode still needs real security.
4. Perform actual original-source cross-checking, phase/indication interpretation,
   analytical work and owner decisions for each trial. Unresolved ORCA-2 SAP
   chronology and other missing originals remain real scientific uncertainties.
5. Any publication of predictions needs separate validation, retrospective
   blind-outcome quarantine and appropriately qualified confidence reporting.
   Internal owner research does not require pretend independent certification.
6. An **explicit destination-specific release request** can then be executed
   after a genuine security/deployment preflight. No deployment or merge is
   executed by this document.

This owner-only operating path removes the *five outside reviewers*
requirement from running the owner's own private research, but it does not
magically fill missing evidence, independently prove a paper's correctness or
turn preliminary 192 worksheets into 192 completed clinical adjudications.
