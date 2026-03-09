---
title: Operator Development
description: Setting up a development environment for the Netchecks operator.
---

The Netchecks operator is written in Rust using [kube-rs](https://kube.rs/). The probe CLI is written in Python.

---

## Prerequisites

- [Rust](https://rustup.rs/) (latest stable)
- [Docker](https://docs.docker.com/get-docker/)
- [kind](https://kind.sigs.k8s.io/) for local Kubernetes clusters
- [kubectl](https://kubernetes.io/docs/tasks/tools/)
- [Helm](https://helm.sh/docs/intro/install/)
- [uv](https://docs.astral.sh/uv/) for Python dependency management

## Start a test cluster

```shell
kind create cluster --name netchecks-test
```

## Build the Docker images

Build both the probe and operator images locally:

```shell
docker build -t ghcr.io/hardbyte/netchecks:local .
docker build -t ghcr.io/hardbyte/netchecks-operator:local operator/
```

Load them into Kind:

```shell
kind load docker-image ghcr.io/hardbyte/netchecks:local --name netchecks-test
kind load docker-image ghcr.io/hardbyte/netchecks-operator:local --name netchecks-test
```

## Install the operator via Helm

```shell
helm dependency build operator/charts/netchecks
helm upgrade --install netchecks-operator operator/charts/netchecks/ \
  -n netchecks --create-namespace \
  --set operator.image.tag=local \
  --set netchecks.image.tag=local
```

## Building the Rust operator

```shell
cd operator
cargo build --workspace
cargo fmt --all
cargo clippy --all-targets --all-features -- -D warnings
```

## Running the Python probe tests

```shell
uv run pytest
```

## Cleanup

```shell
kind delete cluster --name netchecks-test
```
