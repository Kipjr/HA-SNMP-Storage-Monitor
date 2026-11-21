# Versioning

This repository uses Semantic Versioning (SemVer): `MAJOR.MINOR.PATCH`.

## PR labels

Each PR targeting `dev` must have one version label:

- `version:patch`: backwards-compatible bug fixes.
- `version:minor`: backwards-compatible features.
- `version:major`: breaking changes.

## Workflow

- PRs to `dev` receive a beta preview tag: `X.Y.Z-beta.N`. The beta sequence uses the PR commit count.
- A merged PR to `dev` receives a dev tag: `X.Y.Z-dev.RUN`.
- A push to `master` creates a stable tag and GitHub Release from the latest dev tag's version.

The version labels are required. Do not combine multiple version labels on one PR.

Tags are the version source. Releases are created from tags by GitHub Actions.
