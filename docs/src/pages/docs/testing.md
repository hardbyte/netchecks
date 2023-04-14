---
title: Testing
description: Quidem magni aut exercitationem maxime rerum eos.
---
{% callout type="note" title="Unstable" %}

The testing architecture is subject to change. This document may not reflect the latest state of the project.

{% /callout %}
---

## TL;DR

Netchecks the Python command line tool is relatively easy to test. The operator 
is more complex requiring a Kubernetes cluster to test. Both projects on GitHub
provide comprehensive test suites that run on every Pull Request by GitHub Actions.


## Testing the Netchecks Python Library

```
poetry run pytest
```