---
title: Testing
description: Netchecks testing on GitHub Actions and locally.
---

Both the Netchecks command line tool and Kubernetes operator have comprehensive test suites that run on GitHub Actions after every commit. The GitHub Actions workflows for testing can be found [here](https://github.com/hardbyte/netchecks/tree/main/.github/workflows).

---

## Testing the Netchecks Python Library

Unit tests for the Python probe:

```bash
uv run pytest
```

## Testing the Rust Operator

Build and run clippy checks:

```bash
cd operator
cargo build --workspace
cargo clippy --all-targets --all-features -- -D warnings
```

## Integration Tests with Kind

The integration tests run the operator in a real Kubernetes cluster using [Kind](https://kind.sigs.k8s.io/). They are written in Python/pytest and use kubectl subprocess calls to interact with the cluster.

### Setup

```bash
kind create cluster --name netchecks-test
docker build -t ghcr.io/hardbyte/netchecks:local .
docker build -t ghcr.io/hardbyte/netchecks-operator:local operator/
kind load docker-image ghcr.io/hardbyte/netchecks:local --name netchecks-test
kind load docker-image ghcr.io/hardbyte/netchecks-operator:local --name netchecks-test
helm dependency build operator/charts/netchecks
```

### Running integration tests

```bash
cd operator
NETCHECKS_IMAGE_TAG=local pytest -v -x
```

### Cleanup

```bash
kind delete cluster --name netchecks-test
```

{% callout title="Cilium tests" %}
Some integration tests require Cilium CNI. These tests are automatically skipped when Cilium is not installed on the cluster.
{% /callout %}
