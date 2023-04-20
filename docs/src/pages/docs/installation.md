---
title: Installation
description: Install Netchecks in a Kubernetes Cluster 
---

Netchecks operator is installed via Helm or directly via Kubernetes manifests.

---

## Prerequisites

Netchecks should work on any Kubernetes cluster version `1.21` or later. Helm 3 is recommended for installation, although static manifests are also provided.


## Installation


### Helm

The helm chart is not **yet** available in a public helm repository. To install the operator, 
clone the git repo and run:

```shell
helm upgrade --install netchecks-operator operator/charts/netchecks/ -n netchecks --create-namespace
```


### Static Manifests

Alternatively, install the NetworkAssertion CRDs and the Netchecks operator with:

```shell
kubectl apply -f https://github.com/hardbyte/netchecks/raw/main/operator/manifests/deploy.yaml
```


## Software Supply Chain Integrity

Netchecks docker images are all built by GitHub actions, cryptographically signed using SigStore `cosign` 
and hosted in GHCR.
