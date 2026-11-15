#!/usr/bin/env bash
# Inspect whether the assessment branch can merge current origin/main.
# Never commits, pushes, resets, or changes the operator's working tree.
set -euo pipefail
repo="${1:-.}"
cd "$repo"
if [[ -n "$(git status --porcelain)" ]]; then
  echo "ABORT: working tree is not clean; no merge attempted." >&2
  exit 2
fi
branch="$(git branch --show-current)"
if [[ -z "$branch" || "$branch" == "main" ]]; then
  echo "ABORT: diagnostic must run on a named non-production integration branch; found '$branch'." >&2
  exit 2
fi
git fetch --no-tags origin main
temp="$(mktemp -d)"
cleanup() {
  git -C "$temp" merge --abort >/dev/null 2>&1 || true
  git worktree remove --force "$temp" >/dev/null 2>&1 || true
}
trap cleanup EXIT
git worktree add --detach "$temp" HEAD >/dev/null
set +e
git -C "$temp" -c user.name='PDUFA diagnostic' -c user.email='diagnostic@localhost' merge --no-commit --no-ff origin/main >"$temp/merge-diagnostic.log" 2>&1
status=$?
set -e
if [[ "$status" -eq 0 ]]; then
  echo "CLEAN_MERGE: origin/main can merge into this branch (no commit created)."
else
  echo "CONFLICTS: files requiring manual resolution:"
  git -C "$temp" diff --name-only --diff-filter=U
  echo "Merge diagnostic:"
  cat "$temp/merge-diagnostic.log"
fi
exit "$status"
