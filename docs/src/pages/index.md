---
title: Getting started
pageTitle: Netchecks - Verifying your security controls
description: A cloud native tool to dynamically declare a set of statements about the network (what should work and what shouldn't)
---

Learn how to get Netchecks set up in your own Kubernetes cluster. {% .lead %}

{% quick-links %}

{% quick-link title="Installation" icon="installation" href="/docs/installation" description="Step-by-step guides to setting up your system and installing the library." /%}

{% quick-link title="Architecture guide" icon="presets" href="/" description="Learn how the internals work and contribute." /%}

{% quick-link title="API reference" icon="theming" href="/" description="Learn to easily customize and modify your app's visual design to fit your brand." /%}

{% quick-link title="Examples" icon="plugins" href="/" description="See how others are using the library in their projects." /%}

{% /quick-links %}


---
## Quick start

The Netchecks operator is a Kubernetes operator that helps users verify network policies and connectivity within their clusters. By creating NetworkAssertions, users can automate and schedule network tests, making it easier to ensure the network is operating as expected.


### Prerequisites

Before installing the Netchecks operator, ensure you have the following:

- A Kubernetes cluster up and running
- Kubectl installed and configured to communicate with your cluster

### Installation

Install the `Netchecks` operator with:

```shell
kubectl create namespace netchecks
kubectl apply -f https://github.com/hardbyte/netchecks/raw/main/operator/manifests/deploy.yaml
```

Wait until the netchecks namespace is running a Deployment with a ready Pod:

```shell
kubectl wait Deployment -n netchecks -l app=netcheck-operator --for condition=Available --timeout=90s
```

### Basic Usage

Create and apply your `NetworkAssertions` as any other Kubernetes resource.

For example a `NetworkAssertion` with a single rule that checks HTTP requests to the Kubernetes API should succeed:

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


{% callout title="What happens next?" %}
Once you have applied the `NetworkAssertion`, netchecks reacts by creating a `CronJob` in the
same namespace to schedule the test. After the first test has run Netchecks creates a `PolicyReport` resource with the same name in the same namespace as the `NetworkAssertion`.
{% /callout %}


