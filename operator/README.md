The **Netchecks Operator** provides a cloud native way to dynamically declare a set of statements about 
the network (what should work and what shouldn't).


## High Level Diagram

![High Level Diagram](doc/High-Level-Diagram.png)

## Example



```yaml
apiVersion: netchecks.io/v1
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

`PolicyReport` resources will be created in the same namespace as the `NetworkAssertion`, e.g:

```yaml
apiVersion: wgpolicyk8s.io/v1alpha2
kind: PolicyReport
metadata:
  annotations:
    category: Network
    created-by: netcheck
    netcheck-operator-version: 0.1.0
  creationTimestamp: '2023-01-08T04:14:07Z'
  generation: 2
  labels:
    app.kubernetes.io/component: probe
    app.kubernetes.io/instance: http-should-work
    app.kubernetes.io/name: netcheck
    job-name: http-should-work-manual-w7e1x
    optional-label: applied-to-test-pod
    policy.kubernetes.io/engine: netcheck
  name: http-should-work
  namespace: default
results:
  - category: http
    message: Rule from kubernetes-version
    policy: kubernetes-version
    properties:
      data: >-
        {"startTimestamp": "2023-01-08T04:20:52.433681", "status-code": 200,
        "endTimestamp": "2023-01-08T04:20:52.441192"}
      spec: >-
        {"type": "http", "shouldFail": false, "timeout": null,
        "verify-tls-cert": false, "method": "get", "url":
        "https://kubernetes/version"}
    result: pass
    rule: kubernetes-version-rule-1
    source: netcheck
    timestamp:
      nanos: 0
      seconds: 1673151652
summary:
  pass: 1
```


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

Alternatively, install the NetworkAssertion and PolicyReport CRDs and the Netchecks operator with:

```shell
kubectl apply -f https://github.com/netchecks/operator/raw/main/manifests/deploy.yaml
```

Then apply your `NetworkAssertions` as any other resource.

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

--certificate-github-workflow-ref refs/tags/[RELEASE TAG] ghcr.io/netchecks/operator:[VERSION] | jq

## Development


### Generate the static manifests (manually)

```shell
./create-static-manifests.sh
```

### Start a test cluster

```shell
kind create cluster
kubectl config use-context kind-kind
```


### Start the operator outside of Kubernetes

```shell
kopf run main.py --liveness=http://0.0.0.0:8080/healthz
```

### Create a NetworkAssertion

```shell
kubectl apply -f examples/default-k8s/http.yaml
```
