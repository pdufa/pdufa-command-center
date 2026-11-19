# Blind Level 1 worker — deployment and isolation requirements

The runner is `scripts/run_2026_l1_isolated_blind_worker.py`. The validator is `scripts/validate_2026_l1_blind100_packets.py`.

**Current status: runner source installed in development branch; NOT deployed or running. 0 blind predictions.** No independent model executable has been provisioned. No pre-cutoff evidence packets have been verified.

## Required isolation (outside the contaminated repository)

1. Create a new access-controlled runtime/VM or clean repository. Deny access to the original PDUFA repository, decision database, FDA outcome feeds, historical outcome files, chat history, GitHub credentials and general internet. This is an infrastructure permission boundary, not a prompt instruction.
2. Copy ONLY the runner, validator and separately curated `manifest.csv` and `evidence/<case_id>.json` files into the runtime. Never clone the outcome-bearing repository inside it. The source branch used to author the runner is **not** itself blind.
3. Supply a separate local predictor executable that reads one JSON evidence packet from stdin and emits JSON with exactly `case_id,prediction,confidence,rationale`. It must use only the packet and its trained knowledge; an unverified model may still have learned historical decisions. Audit the predictor's training cutoff and tools.
4. Before executing, verify every case's FDA application identity, original PDUFA goal and pre-cutoff sources. The validator rejects all 100 currently unverified candidates. For 179, a separate expanded validated manifest and validator would be required.
5. Run `python scripts/run_2026_l1_isolated_blind_worker.py --input /isolated/inputs --predictor /isolated/predictor --locks /isolated/locks` in the restricted environment. Keep output locks inaccessible to outcome custodian until the prediction batch finishes. Back up locks immutably with trusted timestamps.
6. Independent custodian verifies runtime access logs and evidence chronology before unmasking outcomes. Only then calculate blind accuracy; report abstentions and coverage.

**Security limitations:** The Python runner is not a sandbox; setting subprocess environment variables does not restrict filesystem, network or inherited process privileges. The operator must enforce OS/container/network and repository access controls. The validator detects certain textual leaks but cannot prove that sources or predictor weights are free from outcome contamination. Do not call a result 100% blind without independent verification.

**No deployment, external worker invocation, prediction, merge, or scoring has occurred.**
