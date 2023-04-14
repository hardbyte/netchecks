---
title: Installation
description: Quidem magni aut exercitationem maxime rerum eos.
---

Quasi sapiente voluptates aut minima non doloribus similique quisquam. In quo expedita ipsum nostrum corrupti incidunt. Et aut eligendi ea perferendis.

---

## Prerequisites

Netchecks should work on any Kubernetes cluster version 1.21 or later. Helm 3 is recommended for installation, although static manifests are also provided.


## Installation

The PolicyReport CRD is required to be installed before the operator. The CRD can be installed by running:

```shell 
kubectl apply -f https://github.com/kubernetes-sigs/wg-policy-prototypes/raw/master/policy-report/crd/v1alpha2/wgpolicyk8s.io_policyreports.yaml
```


### Helm

The helm chart is not **yet** available in a public helm repository. To install the operator, 
clone the git repo and run:

```shell
helm upgrade --install netchecks-operator  charts/netchecks/ -n netchecks --create-namespace
```


### Static Manifests

Alternatively, install the NetworkAssertion CRDs and the Netchecks operator with:

```shell
kubectl apply -f https://github.com/netchecks/operator/raw/main/manifests/deploy.yaml
```


## Docker Image Verification

Netchecks docker images are all built by GitHub actions, cryptographically signed and hosted in GHCR.

To manually verify the signatures, install [cosign](https://docs.sigstore.dev/cosign/installation/), then run:

```shell
$ COSIGN_EXPERIMENTAL=1 cosign verify \
    --certificate-github-workflow-repository netchecks/operator \
    --certificate-oidc-issuer https://token.actions.githubusercontent.com \
    ghcr.io/netchecks/operator:main | jq
```

{% callout type="note" title="Keyless Signing" %}

`COSIGN_EXPERIMENTAL=1` is used to allow verification of images signed in KEYLESS mode. To learn more about keyless signing, please refer to [Keyless Signatures](https://github.com/sigstore/cosign/blob/main/KEYLESS.md#keyless-signatures) in the `cosign` documentation.

{% /callout %}


To verify that an image was created for a specific release add the following to the cosign command:

```
--certificate-github-workflow-ref refs/tags/[RELEASE TAG] \
ghcr.io/hardbyte/netcheck-operator:[VERSION] | jq
```
