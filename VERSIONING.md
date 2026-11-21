# Versioning

This repository uses Semantic Versioning (SemVer): `MAJOR.MINOR.PATCH`.

## PR labels

Each PR targeting `dev` must have exactly one version label:

- `version:patch`: backwards-compatible bug fixes.
- `version:minor`: backwards-compatible features.
- `version:major`: breaking changes.

## Workflow

- PRs to `dev` receive a beta tag: `X.Y.Z-beta.N`. N is the PR commit count.
- A merged PR to `dev` receives a dev tag: `X.Y.Z-dev.RUN`.
- A push to `master` creates a stable tag and GitHub Release using the version from the latest dev tag.

Tags are the version source. Releases are created by GitHub Actions.
