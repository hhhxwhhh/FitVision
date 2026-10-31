#!/usr/bin/env bash
# Commitlint wrapper invoked by pre-commit on the commit-msg stage.
# Runs Conventional Commits validation using the project's commitlint config.
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT/frontend"

exec npx commitlint --edit "$1"
