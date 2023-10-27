---
title: Getting started
pageTitle: Netchecks - Verifying your security controls
description: A cloud native tool to dynamically declare a set of statements about the network (what should work and what shouldn't)
---

Learn how to get Netchecks set up in your own Kubernetes cluster. {% .lead %}

---
## Why does this exist?

Like all software, security controls such as firewalls and network policies need validation to ensure they are working as intended. This is often done manually 
as part of a one-off cyber-security review. Best practice is to configure automated checks that notify team members when a security control is not working as expected. 
These can be as simple as a curl command in a cron job that tries to access a service that should be blocked and alerts if it succeeds. With Netchecks, you
declare these checks declaratively and have them run automatically on a schedule, Netchecks will create PolicyReports that can be used for audit purposes, to trigger
actions, alerts and notifications.

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
kubectl wait Deployment -n netchecks -l app.kubernetes.io/instance=netchecks-operator --for condition=Available --timeout=90s
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
Once you have applied the `NetworkAssertion`, Netchecks reacts by creating a `CronJob` in the
same namespace to probe the network according to your schedule. After the first test has run 
Netchecks creates a `PolicyReport` resource with the same name in the same namespace as the `NetworkAssertion`.
The `PolicyReport` contains information about the test run and the results of the test.
{% /callout %}


{% quick-links %}

{% quick-link title="Installation" icon="installation" href="/docs/installation" description="Step-by-step guides to setting up your system and installing the library." /%}

{% quick-link title="Architecture guide" icon="presets" href="/" description="Learn how the internals work and contribute." /%}

{% quick-link title="API reference" icon="theming" href="/" description="Learn to easily customize and modify your app's visual design to fit your brand." /%}

{% quick-link title="Examples" icon="plugins" href="/" description="See how others are using the library in their projects." /%}

{% /quick-links %}
