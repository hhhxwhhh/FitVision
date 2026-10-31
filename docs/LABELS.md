# Issue & PR Labels

Labels help triage and discoverability. Most area labels are applied automatically
by the [Labeler](.github/workflows/labeler.yml) workflow based on changed files; the
rest are applied manually by maintainers.

## Area (auto-applied)

| Label | Applied when |
| --- | --- |
| `frontend` | Changes under `frontend/` |
| `backend` | Changes under `backend/` |
| `documentation` | Changes under `docs/` or any `*.md` |
| `ci` | Changes under `.github/`, `Makefile`, or `docker-compose.yml` |
| `dependencies` | Changes to `package-lock.json` or `requirements*.txt` |

## Type

| Label | Meaning |
| --- | --- |
| `bug` | Something is broken |
| `enhancement` | New feature or improvement |
| `documentation` | Docs only |
| `good first issue` | Friendly for new contributors |
| `help wanted` | Maintainers are looking for help |

## Lifecycle

| Label | Meaning |
| --- | --- |
| `stale` | No activity for 60 days (see [Stale](.github/workflows/stale.yml)) |
| `pinned` | Kept open regardless of staleness |
| `security` | Security-related; handled per [SECURITY.md](SECURITY.md) |
| `wontfix` | Decided not to proceed |
| `duplicate` | Already covered by another issue/PR |
