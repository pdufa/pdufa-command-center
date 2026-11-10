# Scoped continuous development setup (disabled until owner activation)

This is a coding-agent proposal pipeline, **not** the read-only one-minute Render
heartbeat and not an unrestricted autonomous production deployer.

## Activation required once by the repository owner

1. In the GitHub repository, visit Settings → Secrets and variables → Actions.
   Under **Secrets**, add the repository secret `OPENAI_API_KEY` from an API
   account with billing and usage limits set deliberately. Never paste this key
   into a commit, issue, PR, or chat.
2. Under **Variables**, add `PDUFA_CONTINUOUS_CODEX_ENABLED` = `true`.
   This alone does not provide a key. Without both, no live coding run is
   authorized. Return the variable to `false` to pause new attempts.
3. Ensure Actions policy permits the pinned/open-source Codex action and
   `peter-evans/create-pull-request`, plus workflow `GITHUB_TOKEN` write
   permissions needed to **open draft PRs** (never merge).
4. Inspect the fixed approved queue
   `.github/codex/continuous-development-queue.json`, each checked-in
   prompt, and the exact path allowlist in
   `scripts/check_continuous_codex_patch.py`.

## Operation

- GitHub Actions polls every **15 minutes** on the default branch, when the
  repository variable is enabled. GitHub can delay scheduled jobs; this is not
  a guaranteed continuously executing 24/7 process or a one-second interval.
- The selector picks one approved, source-controlled scope and refuses to
  repeat any task that already has an open/closed/merged PR on its stable head
  branch. Add a new approved scope ID explicitly to continue to the next task.
- The Codex action runs with repository read access and a workspace-write
  sandbox. Only approved file changes are exported as a patch artifact.
- A **separate** job with GitHub write permissions validates and applies
  the scoped patch and opens a **draft PR**. No auto-merges, force pushes
  to main, scientific grades or production deployments.
- If the key, approval variable, repository permissions, source data,
  Codex output or validation is missing, the system fails closed.
- The existing Render minute heartbeat remains read-only; it does not
  execute this agent. GitHub Actions is the source for its own execution runs.
- Set budget/usage limits for any API project before enabling scheduling.
  Token use and GitHub Actions minutes may incur charges.

## Safety and next increments

A draft PR with passing CI still does not authorize independent clinical
adjudication, Phase 3 conclusions, prediction probability, patient safety
claims, trading, or immutable historical FDA outcome edits. Scientific
signoff remains a separate gated process. Expand the approved queue only
by reviewing and recording a narrowly scoped next task.

No personal or provider API credential should ever appear in application logs.
