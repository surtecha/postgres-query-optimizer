#!/bin/sh
# Publish the configured remote, or create a new public repository when none exists.
set -eu
cd "$(dirname "$0")/.."
command -v gh >/dev/null || { echo 'GitHub CLI is required' >&2; exit 1; }
gh auth status
if [ -n "$(scripts/git.sh status --porcelain)" ]; then
  echo 'Commit verified changes before publication' >&2
  exit 1
fi
[ "$(scripts/git.sh branch --show-current)" = main ] || {
  echo 'Publication requires the main branch' >&2
  exit 1
}
if ! scripts/git.sh remote get-url origin >/dev/null 2>&1; then
  account=$(gh api user --jq .login)
  name=postgres-query-optimizer
  if gh repo view "$account/$name" >/dev/null 2>&1; then
    echo 'Repository already exists; configure origin before publication' >&2
    exit 1
  fi
  gh repo create "$account/$name" --public --description 'Controlled PostgreSQL query experiments with deterministic validation and measured acceptance'
  scripts/git.sh remote add origin "https://github.com/$account/$name.git"
fi
scripts/git.sh push --set-upstream origin main
local_sha=$(scripts/git.sh rev-parse HEAD)
remote_sha=$(scripts/git.sh ls-remote origin refs/heads/main | cut -f1)
[ "$local_sha" = "$remote_sha" ] || { echo 'Remote verification failed' >&2; exit 1; }
printf 'Published %s at %s\n' "$(scripts/git.sh remote get-url origin)" "$local_sha"
