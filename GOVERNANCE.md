# Governance

FitVision is a community-driven open-source project. This document describes how
the project is maintained and how decisions are made.

## Roles

- **Maintainers** — review and merge pull requests, triage issues, and own releases.
  The current maintainer is listed in [CODEOWNERS](.github/CODEOWNERS).
- **Contributors** — anyone who opens issues, improves docs, reports bugs, or sends
  pull requests. All contributions are welcome.

## How decisions are made

- Most changes happen through pull requests. A maintainer reviews and merges once the
  CI passes and the change is scoped to a single concern.
- Larger design decisions are discussed in issues or
  [GitHub Discussions](https://github.com/hhhxwhhh/FitVision/discussions) before code
  is written. When in doubt, open an issue first.
- Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/)
  and are validated by `commitlint`.

## Releases

- Releases are tagged as `vX.Y.Z` following [Semantic Versioning](https://semver.org/).
- Pushing a tag triggers the release workflow, which builds the frontend and publishes
  a GitHub Release with automatically generated notes (see `CHANGELOG.md`).

## Code of conduct

- All participation is governed by the [Code of Conduct](CODE_OF_CONDUCT.md). Be
  respectful, assume good intent, and help keep the community welcoming.

## Becoming a maintainer

- Consistent, high-quality contributions and a track record of helping others are the
  main path to becoming a maintainer. Reach out in Discussions if you are interested.
