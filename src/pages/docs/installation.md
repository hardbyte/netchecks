---
title: Installation
description: Quidem magni aut exercitationem maxime rerum eos.
---

Quasi sapiente voluptates aut minima non doloribus similique quisquam. In quo expedita ipsum nostrum corrupti incidunt. Et aut eligendi ea perferendis.

---

## Docker Image Verification

### Prerequisites

You will need to install [cosign](https://docs.sigstore.dev/cosign/installation/).

Verify Signed Container Images
```
$ COSIGN_EXPERIMENTAL=1 cosign verify --certificate-github-workflow-repository netchecks/operator --certificate-oidc-issuer https://token.actions.githubusercontent.com ghcr.io/netchecks/operator:main | jq
```

### Note

`COSIGN_EXPERIMENTAL=1` is used to allow verification of images signed in KEYLESS mode. To learn more about keyless signing, please refer to [Keyless Signatures](https://github.com/sigstore/cosign/blob/main/KEYLESS.md#keyless-signatures).

To verify that an image was created for a specific release add the following to the cosign command:

--certificate-github-workflow-ref refs/tags/[RELEASE TAG] ghcr.io/hardbyte/netcheck-operator:[VERSION] | jq
