# Controlled coding-agent dry run

Publishing is disabled pending independent review. No execution flag enables publishing.
The dry-run CLI rejects root, state, contract, status and recovery overrides. It first
runs the unchanged retirement guard against the source checkout, then creates a new
repository and separate state directory beneath a fresh system temporary directory.
It retains the directory (printed as `artifacts`) for inspection. It never commits
generated files, sets a GitHub remote, pushes, or creates a PR. The fixture baseline
commit is local only. No production worker or scientific state is involved.

The fixture asks the actual local Ollama model to implement `has_gap`, validates the
returned file map, and runs immutable baseline tests with the existing offline,
read-only, credential-free Docker sandbox. No image or model is downloaded by the
runner. Use an independently reviewed, already cached Python image with a repository
digest. The following PowerShell command resolves that digest from a local image:

```powershell
$image = docker image inspect python:3.13-slim --format '{{index .RepoDigests 0}}'
if ($LASTEXITCODE -ne 0 -or $image -notmatch '@sha256:[a-f0-9]{64}$') { throw 'Reviewed cached image digest required' }
& C:\Users\asiri\AppData\Local\Python\pythoncore-3.13-64\python.exe -B scripts/pdufa_coding_agent.py --dry-run --image $image --model qwen2.5-coder:1.5b
```

Substitute the tag of your reviewed cached image if different. Successful state is
`dry_run_passed`, `published: false`, `scientifically_accepted: false`. A failed run
is never automatically replayed. Create `STOP` in the printed artifacts directory's
`state` subdirectory to stop work; process polling checks it, and Ollama requests
check it on return (HTTP timeout 180 seconds). Docker cleanup still runs after STOP.
Retained artifacts can be inspected without enabling remote recovery.

Local validation reported on 2026-11-13: coding-agent unit tests, including
the empty-response regression, passed. The historical retirement audit passed.
The isolated Docker/Ollama dry run completed with dry_run_passed and publishing
disabled. GitHub CI and independent code review are still required.
Unattended operation, automatic merging, deployment, and scientific approvals
remain disabled.
