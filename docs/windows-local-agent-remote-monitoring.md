# Windows local AI coding agent — installation plan

Status: **starter readiness tooling only; agent not installed or running**.

## Goal
Run a free Ollama coding model on the owner's Windows PC; review work on iPhone using GitHub, and eventually display read-only status in the PDUFA website. Preserve AGENTS.md policies, historical provenance, and all production data.

## First run
1. Install Git for Windows, Python 3, GitHub CLI, and Ollama from their official websites.
2. Clone `https://github.com/pdufa/pdufa-command-center.git` to the Windows PC.
3. From PowerShell in the repository run `powershell -ExecutionPolicy Bypass -File scripts/windows_agent_diagnostics.ps1`.
4. Choose a model based on actual RAM, VRAM and free storage. Do not assume a 14B/32B model will fit.
5. Use GitHub CLI `gh auth login` interactively on the PC, granting only the permissions needed. Never paste tokens into ChatGPT or commit them.
6. Do not enable unattended changes until the local sandbox and integration tests pass.

## Proposed guarded worker
- Runs on a dedicated local non-admin Windows account in a disposable working copy.
- Reads one bounded development task and AGENTS.md.
- Calls the local Ollama API at `127.0.0.1:11434` only.
- Permits edits to tests/docs and explicitly approved non-production scripts only.
- Executes mandatory retirement and regression checks; rejects failed patches.
- Creates a GitHub branch and a pull request, never pushes to main, merges, deploys, trades, or changes production predictions.
- Enforces time and disk limits, a stop switch, and bounded retries.
- Publishes a redacted run summary through GitHub; avoid uploading private research or secrets.

## iPhone monitoring
- GitHub mobile app: Actions logs, pull requests, checks, and review status.
- PDUFA website: a read-only development monitor **still requires a separate backend/frontend implementation**; do not publish local IP addresses, machine credentials, prompts, or source files.
- Never expose Ollama port 11434 directly to the internet. Remote desktop, if desired, should use authenticated private-network access.

## Costs and limitations
Ollama local inference has no per-token API charges, but PC electricity and hardware have costs. A sleeping/offline PC cannot run jobs. GitHub-hosted usage has quotas. No guarantee of uninterrupted autonomous development or correct patches.
