# Guarded Windows local AI coding workflow — continuous mode installation plan

Status: PREPARATION ONLY. Continuous coding is **not yet installed or enabled**. No autonomous commits, PRs, merges, or deployments are authorized by this document alone.

## Approved architecture
- Ollama coding model on Windows, using a **single isolated worker** and a persistent, bounded approved-task queue.
- On successful completion, immediately dequeue the next eligible task. No fixed four-hour delay between tasks.
- When the queue is empty, idle with a low-frequency check and backoff rather than spinning or inventing work.
- Each task: isolated checkout -> generate patch -> review allowed paths and diff -> isolated tests -> push agent/* branch -> open **draft** PR.
- GitHub is the review and test record; main and production remain protected.
- Never automatically merge, enable auto-merge, deploy, or directly edit main.

## Required gates before activation
1. Inspect actual Windows task, installed script, Ollama model and hardware limits.
2. Verify sandbox containment, network/secret isolation, command allowlist and safe execution limits.
3. Provision least-privilege GitHub credential securely on Windows; never post secrets in issues or logs.
4. Implement a persistent queue of explicitly approved tasks, bounded retries, timeouts, resource limits, a concurrency lock, deduplication and crash recovery.
5. Run tests in a disposable isolated environment; failed tests block branch publication.
6. Create draft PRs only, with provenance and test evidence; no production merge/deployment permission.
7. Verify main branch protection and required review settings independently.
8. Perform one dry run and one harmless end-to-end task, proving draft PR creation without merges or deployments.
9. After acceptance tests pass, replace the four-hour proposal schedule with the supervised continuous worker, avoiding overlapping agents. Include stop/disable control, failure backoff and resource monitoring.

## Known status
- User-reported Windows Task Scheduler task: PDUFA-Local-AI-Proposals, scheduled every four hours.
- GitHub issue #1096 reported PASS for read-only proposals and sandbox-only drafts at 2026-11-11 10:00 UTC.
- Existing agent does **not** execute AI-generated code or modify the repository.
- This PR documents the requested change; no Windows installation can be inferred from it.

## Acceptance
- At least two queued approved tasks process sequentially without waiting four hours.
- Successful isolated task creates a draft PR; failed task does not publish code.
- Duplicate work is skipped, idle queue does not consume sustained CPU, and stop switch prevents further tasks.
- No automatic merges or deployments.
