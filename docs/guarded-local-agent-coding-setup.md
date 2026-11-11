# Guarded Windows local AI coding workflow — installation plan

Status: PREPARATION ONLY. This document does not enable code execution, autonomous commits, GitHub PR creation, or deployments.

## Approved scope
- Local Windows scheduled agent may generate code on a disposable worktree or sandbox branch.
- Run project-specific lint, type checks, and tests with timeouts and bounded resources.
- After passing checks, push to a dedicated agent/* branch and open a **draft** pull request.
- Never push to main, merge PRs, enable auto-merge, deploy, modify production configuration, or run generated code outside an isolated sandbox.
- No credentials or proprietary data in public issue #1096, PR descriptions, or logs.

## Required installation gates
1. Inspect the installed Windows task and local agent script; confirm the actual source and installed revision.
2. Verify sandbox containment, command allowlist, file/path restrictions, network and secret isolation. Generated code must not execute on the host without sandbox enforcement.
3. Set up least-privilege GitHub credentials scoped to repository contents and pull requests, stored securely on Windows. Never paste tokens into chat or public GitHub.
4. Add an agent execution path that uses a disposable checkout and isolated tests; protect against untrusted issue instructions and prompt injection.
5. Add a bounded queue, retries, per-run timeouts, concurrency lock, duplicate-PR detection, and clear failure reports.
6. Require test success and diff review before any agent branch is pushed. PRs must be draft, with provenance and test results.
7. Verify repository branch protections and required reviews on main; repository-level auto-merge is currently disabled.
8. Run one end-to-end dry run, then one harmless test task. Verify a draft PR appears without merge or deployment.
9. Only after passing these checks, enable the 4-hour schedule for coding mode. Preserve a kill switch and rollback.

## Current known status
- Existing Windows scheduled task: PDUFA-Local-AI-Proposals, every four hours (reported by user).
- Public status issue #1096: PASS for read-only proposals and sandbox-only Python code drafts at 2026-11-11 10:00 UTC.
- Existing agent explicitly does not execute generated code or change production.
- This PR is a reviewable checklist, **not proof of installation**.

## Acceptance criteria
- One isolated task produces a draft PR and test evidence.
- No commit to main, merge, deployment, or production modification.
- Repeated task does not create duplicate PRs.
- Failed tests block publication.
- Disabling the scheduled task stops subsequent coding runs.
