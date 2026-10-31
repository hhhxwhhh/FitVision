#!/usr/bin/env bash
# Prettier wrapper invoked by pre-commit for staged frontend files.
# pre-commit passes repository-relative paths (e.g. frontend/src/App.vue); we
# strip the "frontend/" prefix and run Prettier from the frontend directory so it
# picks up the project's .prettierrc.json and node_modules.
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT/frontend"

files=()
for f in "$@"; do
  files+=("${f#frontend/}")
done

exec npx prettier --write "${files[@]}"
