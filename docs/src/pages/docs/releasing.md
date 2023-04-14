---
title: Release
description: How to release a new version of Netchecks
---
{% callout type="note" title="Unstable" %}

The method outlined here is subject to change. This document may not reflect the latest state of the project.

{% /callout %}


## Releasing the Netchecks Python Library

Netchecks the Python command line tool is released using GitHub Actions. 
Update version in `pyproject.toml`, create a PR against the `main` branch and after merge, create a release on GitHub. 

GitHub actions will create the release artifacts and upload to Pypi. 

