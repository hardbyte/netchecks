---
title: Architecture guide
description: Netchecks architecture overview.
---

Netchecks runs in Kubernetes as an [operator](https://kubernetes.io/docs/concepts/extend-kubernetes/operator/). Since v0.7.0, the operator is implemented in Rust using [kube-rs](https://kube.rs/) 3.0. It runs as a minimal distroless container based on [chainguard/static](https://images.chainguard.dev/directory/image/static/overview).

The netchecks operator:
- Watches for `NetworkAssertion` resources across the cluster and reconciles `CronJobs` (or `Jobs`) for each of them. CronJobs are tracked via `.owns(cronjobs)` so changes are automatically detected.
- Probe pods are created by the `CronJob` and run the tests that make up a particular network assertion. External data may be mounted into the Pod for use by the probe.
- Parses assertion results from completed probe Pod logs.
- Creates and updates `PolicyReport` resources for each NetworkAssertion in response to the assertion results.
- Writes status conditions back to `NetworkAssertion` resources to reflect reconciliation state.
- Exposes health endpoints (`/livez`, `/readyz`) for liveness and readiness probes.
- Uses structured JSON logging via the `tracing` crate, with optional OTLP metrics export.

Each probe pod uses the `netchecks` docker image to run the tests that make up a particular network assertion.


{% architecture-diagram /%}

---

The `netchecks` probe image is based on the [python:3.12-slim-bookworm](https://hub.docker.com/_/python) image.

[Kyverno's PolicyReporter](https://kyverno.github.io/policy-reporter/) is optionally installed alongside Netchecks to
provide a convenient way to expose metrics, view the results, and generate notifications.
