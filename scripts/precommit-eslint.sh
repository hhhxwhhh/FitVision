#!/usr/bin/env bash
# ESLint wrapper invoked by pre-commit for staged frontend files.
# Strips the "frontend/" prefix and runs ESLint from the frontend directory so it
# resolves the project's flat config and node_modules.
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT/frontend"

files=()
for f in "$@"; do
  files+=("${f#frontend/}")
done

exec npx eslint --fix "${files[@]}"
