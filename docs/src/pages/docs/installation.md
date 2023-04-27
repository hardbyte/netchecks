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

The helm chart is available on [Artifact Hub](https://artifacthub.io/packages/helm/netchecks/netchecks/). To install the operator

```shell
helm repo add netchecks https://hardbyte.github.io/netchecks
helm upgrade --install netchecks netchecks/netchecks -n netchecks --create-namespace
```


### Static Manifests

Alternatively, install the NetworkAssertion CRDs and the Netchecks operator with:

```shell
kubectl apply -f https://github.com/hardbyte/netchecks/raw/main/operator/manifests/deploy.yaml
```


## Software Supply Chain Integrity

Netchecks docker images are all built by GitHub actions, cryptographically signed using [SigStore cosign](https://github.com/sigstore/cosign)
and hosted on GitHub Container Registry (GHCR).