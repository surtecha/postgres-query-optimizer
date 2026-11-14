#!/bin/sh
# Alternate Git storage supports hosts that prohibit writes to a .git directory.
set -eu
cd "$(dirname "$0")/.."
if [ -d .git ]; then exec git "$@"; fi
exec env GIT_DIR="$PWD/.git-store" GIT_WORK_TREE="$PWD" git "$@"
