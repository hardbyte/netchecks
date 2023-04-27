---
title: Release
description: How to release a new version of Netchecks
---

## Releasing Netchecks

Netchecks is released via GitHub Actions. To make a release

1. Update `version` in both `pyproject.toml` and `operator/pyproject.toml`. Ensure both versions match
2. Update `version` in `operator/charts/netchecks/Chart.yaml`
3. Update `appVersion` in `operator/charts/netchecks/Chart.yaml`. Ensure this matches the `version` in the aforementioned `pyproject.toml` files
3. Make PR against the `main` branch and merge
4. Create a and push a tag `v<semver>`, where `semver` is the same version as set in the `pyproject.toml` files
5. Create a release on GitHub. Note that a Helm release will automatically be created on git tag pushes

Note that the version needs to follow [semantic versioning](https://semver.org/).
