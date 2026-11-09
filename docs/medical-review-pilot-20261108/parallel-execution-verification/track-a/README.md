# Actual Track A execution verification

The [development workflow run 42678294690](https://github.com/pdufa/pdufa-command-center/actions/runs/42678294690), job129365556705, completed successfully at commit `f42605f7228960386e7fce207327c7a996391cb7`. Its actual job interval was November9,2026,18:54:52–18:55:22UTC. The parent report must compare this interval with TrackB before claiming simultaneous execution.

The [machine verification receipt](./verification-receipt.json) was independently reproduced from both original downloaded ZIPs. Their byte digests match GitHub's artifact metadata. The raw-artifact provenance and full checkpoint reconstruction passed against the canonical29-NCT/23-application crosswalk. Recorded23 application research cases comprise22ABSTAIN and one previously observed/nonforecast case. There are0 qualified new scientific predictions,0 independently graded methods and no measured accuracy/calibration.

Actual source coverage:29 registry records,12NCTs with current posted primary tables,12NCTs with SAP attachment metadata, and required independent evidence gaps in all29. Of24unique application-source URLs,23 yielded captured bytes and one original ACHV investor URL returnedHTTP301; an alternate SEC source remains available. All23groups have at least one retrieved public source. These retrieval facts do not establish original as-published timing, FDA cycle identity, or independently adjudicated clinical evidence.

Both additional original FDA responses are actual PDFs (PDF magic, byte counts and SHA-256 checked): the Capricor staff briefing is **pre-amendment, not a final FDA action**; the aficamten letter is **prior obstructive-HCM approval, not the current trial's review-cycle decision**. Exact public URLs and hashes are retained in the receipt.

The separate [history artifact](https://github.com/pdufa/pdufa-command-center/actions/runs/42678294690/artifacts/13701591373) contains one valid hash-linked snapshot with23initial review gates,0clinical writes and prediction release disabled. This initial run skipped restore because no earlier history artifact existed; it does not independently prove a later live restore. The [source artifact](https://github.com/pdufa/pdufa-command-center/actions/runs/42678294690/artifacts/13702050485) includes the matching history. Both have90-day retention and expire February7,2027,18:54:49UTC; indefinite archival was not established.

Reproduce without any network request or source extraction:

```sh
python docs/medical-review-pilot-20261108/parallel-execution-verification/track-a/verify_artifacts.py --sources /path/to/track-a-sources.zip --history /path/to/track-a-history.zip
```

No original source bodies, credentials, signed download URLs, clinical grades or production changes are stored in this verification directory.

## Independently verified live restore

The second [manual run42679838862](https://github.com/pdufa/pdufa-command-center/actions/runs/42679838862) also succeeded, job129371094058,19:04:40–19:05:05UTC at the same code commit. The actual restore step passed and found the prior history. Its [history artifact13702370831](https://github.com/pdufa/pdufa-command-center/actions/runs/42679838862/artifacts/13702370831) matched GitHub's ZIP digest. The [restart receipt](./restart-verification-receipt.json) verifies every first-event field was preserved, the new event points to the exact prior head, and the two-event chain validates.

Nineteen application records require source-version review; four have unchanged source fingerprints. These are raw source-response byte changes, which can include webpage metadata changes. They are **not19 new clinical findings, adjudicated material changes, scientific grades, or predictions**. Every materiality flag remains false, no authorized grade/prediction was modified, and all22future outcome cases remainABSTAIN. The original observed-only case remains separate.

This second verification independently downloaded the history ZIP. The workflow's raw-source verification step passed, but this verification did not independently download the second raw-source ZIP. The first run's complete source-byte audit and both history-artifact byte audits remain separate evidence.
