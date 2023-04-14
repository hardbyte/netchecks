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

### Installation

Install the `NetworkAssertion` and `PolicyReport` CRDs and the `Netchecks` operator with:

```shell
kubectl apply -f https://github.com/kubernetes-sigs/wg-policy-prototypes/raw/master/policy-report/crd/v1alpha2/wgpolicyk8s.io_policyreports.yaml
kubectl create namespace netchecks
kubectl apply -f https://github.com/netchecks/operator/raw/main/manifests/deploy.yaml
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

---

## Example

Assume we have a Kubernetes cluster using Cilium as a CNI plugin. We can use Netchecks to verify that the network policies are being enforced.

### DNS Policy

Cilium allows you to restrict DNS access to specific domains. For example, the following 
CiliumNetworkPolicy only allows access to the Kubernetes API, and github.com, denying all
other DNS requests:


```yaml
apiVersion: "cilium.io/v2"
kind: CiliumNetworkPolicy
metadata:
  name: intercept-dns
spec:
  endpointSelector: {}
  egress:
  - toEndpoints:
    - matchLabels:
        "k8s:io.kubernetes.pod.namespace": kube-system
        "k8s:k8s-app": kube-dns
    toPorts:
      - ports:
          - port: "53"
            protocol: ANY
        rules:
          dns:
            # https://docs.cilium.io/en/v1.12/policy/language/#dns-based
            - matchPattern: "*.github.com"
            - matchName: "github.com"
            - matchPattern: "*.svc.cluster.local"
            - matchPattern: "*.*.svc.cluster.local"
            - matchPattern: "*.*.*.svc.cluster.local"
            - matchPattern: "*.*.*.*.svc.cluster.local"
            - matchPattern: "*.cluster.local"
            - matchPattern: "*.*.cluster.local"
            - matchPattern: "*.*.*.cluster.local"
            - matchPattern: "*.*.*.*.cluster.local"
            - matchPattern: "*.*.*.*.*.cluster.local"
            - matchPattern: "*.*.*.*.*.*.cluster.local"
            - matchPattern: "*.*.*.*.*.*.*.cluster.local"
            - matchPattern: "*.*.localdomain"
            - matchPattern: "*.*.*.localdomain"
            - matchPattern: "*.*.*.*.localdomain"
            - matchPattern: "*.*.*.*.*.localdomain"
```

### Network Assertions

We can create a `NetworkAssertion` to verify every 10 minutes that the DNS restrictions
are working as expected:

```yaml
apiVersion: netchecks.io/v1
kind: NetworkAssertion
metadata:
  name: dns-restrictions-should-work
  namespace: default
  annotations:
    description: Check cluster dns restrictions are working
spec:
  schedule: "*/10 * * * *"
  rules:
    - name: external-dns-lookup-should-fail
      type: dns
      server: 1.1.1.1
      host: hardbyte.nz
      expected: fail
      validate:
        message: DNS requests using an external DNS provider such as cloudflare should fail.
    - name: external-dns-host-lookup-should-fail
      type: dns
      host: hardbyte.nz
      expected: fail
      validate:
        message: DNS requests to a non-approved host should fail.
    - name: approved-dns-host-lookup-should-work
      type: dns
      host: github.com
      expected: pass
      validate:
        message: DNS requests to an approved host.
    - name: approved-dns-host-subdomain-lookup-should-work
      type: dns
      host: status.github.com
      expected: pass
      validate:
        message: DNS requests for a subdomain of an approved host.
    - name: internal-k8s-service-dns-lookup-should-work
      type: dns
      host: kubernetes
      expected: pass
      validate:
        message: DNS lookup of the kubernetes service should work.
    - name: k8s-svc-dns-lookup-should-work
      type: dns
      host: kubernetes.default
      expected: pass
      validate:
        message: DNS lookup of the kubernetes service with namespace should work.
    - name: k8s-svc-dns-lookup-should-work
      type: dns
      host: kubernetes.default.svc
      expected: pass
      validate:
        message: DNS lookup of the kubernetes service should work.
    - name: k8s-svc-with-cluster-domain-lookup-should-work
      type: dns
      host: kubernetes.default.svc.cluster.local
      expected: pass
      validate:
        message: DNS lookup of the kubernetes service should work.

```

Optionally you may want to verify that DNS that is expected to work continues to work too:

```yaml
apiVersion: netchecks.io/v1
kind: NetworkAssertion
metadata:
  name: cluster-dns-should-work
  namespace: default
  annotations:
    description: Check cluster dns behaviour
spec:
  # Every 20 minutes
  schedule: "*/20 * * * *"
  rules:
    - name: external-dns-host-lookup-should-work
      type: dns
      host: github.com
      expected: pass
      validate:
        message: DNS lookup of an external host using default nameserver.
    - name: approved-dns-host-subdomain-lookup-should-work
      type: dns
      host: status.github.com
      expected: pass
      validate:
        message: DNS requests for a subdomain of an external host.
    - name: internal-k8s-service-dns-lookup-should-work
      type: dns
      host: kubernetes
      expected: pass
      validate:
        message: DNS lookup of the kubernetes service should work.
    - name: k8s-svc-dns-lookup-should-work
      type: dns
      host: kubernetes.default.svc
      expected: pass
      validate:
        message: DNS lookup of the kubernetes service should work.
    - name: k8s-svc-with-cluster-domain-lookup-should-work
      type: dns
      host: kubernetes.default.svc.cluster.local
      expected: pass
      validate:
        message: DNS lookup of the fqdn kubernetes service should work.
    - name: missing-svc-dns-lookup-should-fail
      type: dns
      host: unlikely-a-real-service.default.svc.cluster.local
      expected: fail
      validate:
        message: DNS lookup of the missing service should fail.
```


## Next Steps

### Policy Reporter Integration

#### UI
#### Alerts
#### Reports
#### Metrics

