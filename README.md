
## Installation


Install the NetworkAssertion and PolicyReport CRDs and the netchecks operator with:

```shell
kubectl apply -f https://github.com/netchecks/operator/raw/main/manifests/crds/networkassertion-crd.yaml
kubectl apply -f https://github.com/kubernetes-sigs/wg-policy-prototypes/raw/master/policy-report/crd/v1alpha2/wgpolicyk8s.io_policyreports.yaml
kubectl create namespace netchecks
kubectl apply -f manifests/operator -n netchecks
```

Then apply your `NetworkAssertions` as any other resource.

For example:

```yaml
apiVersion: hardbyte.nz/v1
kind: NetworkAssertion
metadata:
  name: http-k8s-api-should-work
  namespace: default
  annotations:
    description: Assert pod can connect to k8s API
spec:
  template:
    metadata:
      labels:
        optional-label: applied-to-test-pod
  schedule: "@hourly"
  rules:
    - name: kubernetes-version
      type: http
      url: https://kubernetes/version
      verify-tls-cert: false
      expected: pass
      validate:
        message: Http request to Kubernetes API should succeed.
```

## Image Verification

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

## Development

### Start a test cluster

```shell
kind create cluster
kubectl config use-context kind-kind
```


### Start the operator

```shell
kopf run main.py --verbose
```

### Install the CRDs

Our Netcheck CRDs:

```shell
kubectl apply -f manifests/crds
```

The PolicyReport CRD:

```shell
kubectl create -f https://github.com/kubernetes-sigs/wg-policy-prototypes/raw/master/policy-report/crd/v1alpha2/wgpolicyk8s.io_policyreports.yaml
```

### Create a NetworkAssertion

```shell
kubectl apply -f examples/default-k8s/http.yaml
```