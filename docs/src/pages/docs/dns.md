---
title: DNS NetworkAssertions
description: Writing and running DNS NetworkAssertions
---

This example shows how to write and run a `NetworkAssertion` that checks DNS requests are
being appropriately restricted by a `CiliumNetworkPolicy`.


## DNS Policy

Many firewalls, proxies and network appliances can be used to restrict DNS requests. In this example we
will use Cilium's DNS proxy to restrict DNS requests to specific domains. To follow along you will need a
Kubernetes cluster using Cilium as a CNI plugin.

Cilium allows you to restrict DNS access to specific domains. For example, the following 
CiliumNetworkPolicy only allows access to the Kubernetes API and github.com, denying all
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

### Network Assertion

Next create a `NetworkAssertion` to verify that the DNS restrictions
are working every 10 minutes as expected:

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
    description: Check cluster dns behavior
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
