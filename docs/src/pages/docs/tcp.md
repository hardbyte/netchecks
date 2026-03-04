---
title: TCP NetworkAssertions
description: TCP NetworkAssertions allow you to test raw TCP connectivity from your cluster.
---

This example shows how to write and run a `NetworkAssertion` that checks TCP connectivity
from within a namespace. TCP probes verify that a connection can (or cannot) be established
to a given host and port — the correct primitive for testing connectivity to non-HTTP services
such as databases, caches, and message brokers.

## TCP NetworkAssertion

We create a `NetworkAssertion` to verify that a TCP connection to the Kubernetes API
on port 443 succeeds, and that connections to a non-existent service are blocked:

```yaml
apiVersion: netchecks.io/v1
kind: NetworkAssertion
metadata:
  name: tcp-connectivity
  namespace: default
  annotations:
    description: Assert TCP connectivity to expected services
spec:
  schedule: "*/10 * * * *"
  rules:
    - name: tcp-to-k8s-api
      type: tcp
      host: kubernetes.default.svc
      port: 443
      expected: pass
      validate:
        message: TCP connection to Kubernetes API should succeed.
    - name: tcp-to-blocked-port
      type: tcp
      host: kubernetes.default.svc
      port: 9999
      timeout: 3
      expected: fail
      validate:
        message: TCP connection to non-listening port should fail.
```

### Parameters

| Parameter | Description | Default |
| --- | --- | --- |
| `host` | Hostname or IP address to connect to | (required) |
| `port` | TCP port number | (required) |
| `timeout` | Connection timeout in seconds | `5` |
| `expected` | Whether the check should `pass` or `fail` | `pass` |

## Boundary Protection Example

TCP probes are ideal for verifying network segmentation and boundary protection.
For example, asserting that a web tier cannot directly reach a database:

```yaml
apiVersion: netchecks.io/v1
kind: NetworkAssertion
metadata:
  name: boundary-protection
  namespace: production
  annotations:
    description: Verify network segmentation between tiers
spec:
  schedule: "@hourly"
  rules:
    - name: api-reachable
      type: tcp
      host: api.backend
      port: 8080
      expected: pass
      validate:
        message: Web tier should reach the API tier.
    - name: database-blocked
      type: tcp
      host: postgres.database
      port: 5432
      expected: fail
      validate:
        message: Web tier must not directly access database tier.
```

## Custom Validation Rules

You can write custom CEL validation rules to inspect the probe result data:

```yaml
    - name: tcp-with-custom-rule
      type: tcp
      host: my-service.default.svc
      port: 8080
      validate:
        pattern: "data.connected == true && data.error == null"
        message: TCP connection should succeed with no errors.
```

The `data` object contains:
- `connected` (bool) — whether the TCP connection was established
- `error` (string or null) — error message if the connection failed
- `startTimestamp` — ISO 8601 timestamp when the check began
- `endTimestamp` — ISO 8601 timestamp when the check completed

## Policy Report

After the `NetworkAssertion` has been applied, a `PolicyReport` will be created with the
results. An example `PolicyReport` for a TCP check:

```yaml
apiVersion: wgpolicyk8s.io/v1alpha2
kind: PolicyReport
metadata:
  name: tcp-connectivity
  namespace: default
results:
  - category: tcp
    message: Rule from tcp-to-k8s-api
    policy: tcp-to-k8s-api
    properties:
      data: >-
        {"startTimestamp": "2024-01-15T10:30:00.123456",
        "connected": true, "error": null,
        "endTimestamp": "2024-01-15T10:30:00.234567"}
      spec: >-
        {"type": "tcp", "host": "kubernetes.default.svc",
        "port": 443, "timeout": 5}
    result: pass
    source: netcheck
summary:
  pass: 1
```
