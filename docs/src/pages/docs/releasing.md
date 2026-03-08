---
title: Release
description: How to release a new version of Netchecks
---

## Releasing Netchecks

Netchecks is released via GitHub Actions. To make a release

- Update `version` in `pyproject.toml` (CLI) and `operator/Cargo.toml` (operator). Ensure both versions match.
- Update `version` and `appVersion` in `operator/charts/netchecks/Chart.yaml`. Ensure `appVersion` matches the version in the aforementioned files.
- Make PR against the `main` branch and merge.
- Create a GitHub release with the tag `v<semver>`, where `semver` is the same version as set above.
- Note that a Helm release will automatically be created.

Note that the version needs to follow [semantic versioning](https://semver.org/).
