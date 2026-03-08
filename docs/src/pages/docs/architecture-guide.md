---
title: Architecture guide
description: Netchecks architecture overview.
---

Netchecks runs in Kubernetes as an [operator](https://kubernetes.io/docs/concepts/extend-kubernetes/operator/). The 
operator is implemented in Python using the [kopf](https://kopf.readthedocs.io/en/stable) framework.

The netchecks operator:
- Listens for `NetworkAssertion` resources across the kubernetes cluster and creates `CronJobs` (or `Jobs`) for each of them.
- Probe pods are created by the `CronJob` and run the tests that make up a particular network assertion. External data may be mounted into the Pod for use by the probe.
- Listens for _probe_ Pods created by the NetworkAssertion's CronJob and parses assertion results from the Pod logs.
- Creates and updates `PolicyReport` resources for each NetworkAssertion in response to the assertion results.

Each probe pod uses the `netchecks` docker image to run the tests that make up a particular network assertion.


{% architecture-diagram /%}

---

The `netchecks` image is based on the [python:3.12-slim-bookworm](https://hub.docker.com/_/python) image.

[Kyverno's PolicyReporter](https://kyverno.github.io/policy-reporter/) is optionally installed alongside Netchecks to
provide a convenient way to expose metrics, view the results, and generate notifications.

## Compliance Reporting

For organizations that need to map active network test results to compliance framework controls,
the [netchecks-compliance](/docs/compliance-reporting) add-on reads
`PolicyReport` results and `NetworkAssertion` annotations to generate audit-ready compliance
reports (PDF/HTML/JSON) for frameworks including PCI-DSS v4.0, SOC 2, and CIS Kubernetes Benchmark.

See the [compliance annotations](/docs/compliance-annotations) documentation for details on
annotating your NetworkAssertions with control IDs.
