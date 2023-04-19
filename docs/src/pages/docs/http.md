---
title: HTTP NetworkAssertions
description: HTTP NetworkAssertions allow you to test HTTP requests from your cluster.
---


This example shows how to write and run a `NetworkAssertion` that checks HTTP requests are
working within a namespace. This example should work on any Kubernetes cluster with Netchecks
installed.


## HTTP NetworkAssertion

We create a `NetworkAssertion` to verify that the kubernetes API is available and
responds to a GET request `https://kubernetes/version`. The `NetworkAssertion` has a 
custom label `optional-label: applied-to-test-pod` that will be applied to the test pod, 
and a `schedule` to run the test every 10 minutes. `verify-tls-cert` is set to `false`
to disable TLS certificate verification because most Kubernetes clusters use self-signed
certificates internally.


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
  schedule: "*/10 * * * *"
  rules:
    - name: kubernetes-version
      type: http
      url: https://kubernetes/version
      verify-tls-cert: false
      expected: pass
      validate:
        message: Http request to Kubernetes API should succeed.
```

## Policy Report

After the `NetworkAssertion` has been applied, a `CronJob` will be created in the `defalt` namespace to run the test every 10 minutes. The `CronJob` will create a `Pod` that runs the test and then a `PolicyReport` resource with the same name as the `NetworkAssertion` will be created in the same namespace. An example `PolicyReport` created by Netchecks is shown below:

```yaml
apiVersion: wgpolicyk8s.io/v1alpha2
kind: PolicyReport
metadata:
  annotations:
    category: Network
    created-by: netcheck
    netcheck-operator-version: 0.1.0
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
