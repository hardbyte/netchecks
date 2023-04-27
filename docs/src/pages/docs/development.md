---
title: Operator Development
description: Running during development
---


## Start a test cluster

If using [kind](https://kind.sigs.k8s.io/)

```shell
kind create cluster
kubectl config use-context kind-kind
```

## Install the operator

To install the operator from the repository

```bash
helm upgrade --install netchecks-operator operator/charts/netchecks/ -n netchecks --create-namespace
```