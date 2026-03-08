# Changelog

## 0.7.0

### Major Changes

- **Operator rewritten from Python to Rust** — The Kubernetes operator has been completely replaced with a Rust implementation using [kube-rs](https://kube.rs/) 3.0. This brings significantly lower memory usage (~5MB vs ~50MB), faster startup, and compile-time type safety. The operator container now uses a distroless base image (`chainguard/static`).

- **TCP probe type** — New `tcp` probe for testing raw socket connectivity. Available as a CLI command (`netcheck tcp --host <host> --port <port>`) and in NetworkAssertion rules. Useful for verifying non-HTTP services and network policy enforcement.

### Features

- **Status conditions on NetworkAssertion** — The operator now writes reconciliation status back to the NetworkAssertion resource. Visible via `kubectl get nas` (Ready/Reason columns) and `kubectl describe`. Conditions report `Reconciled=True` with probe result summaries, or `Reconciled=False` with error details for invalid specs or API errors.

- **Event-driven CronJob processing** — The controller now watches CronJob changes (`.owns(cronjobs)`), so scheduled assertion results are processed via events rather than polling. The periodic safety-net requeue interval has been relaxed from 60s to 300s.

- **Structured JSON logging** — Operator logs are emitted as structured JSON via the `tracing` crate, with configurable log levels via `RUST_LOG` environment variable.

- **OTLP metrics export** — Optional OpenTelemetry metrics (reconciliation duration, probe duration, assertion counts, PolicyReport updates) exported when `OTEL_EXPORTER_OTLP_ENDPOINT` is set.

- **Health endpoints** — New `/livez` and `/readyz` endpoints (with `/healthz` compatibility) for Kubernetes probes.

### Bug Fixes

- **PolicyReport server-side apply** — Removed invalid `scope.apiGroup` field from PolicyReport data that caused 500 errors with the v1alpha2 CRD schema. Extended fallback to handle both 422 and 500 responses.

- **PolicyReport summary format** — Summary now omits zero-valued counts (e.g. no `fail` key when all probes pass), matching the original operator behavior and integration test expectations.

- **Multi-platform Docker build** — Fixed BuildKit cache mount collisions between amd64 and arm64 builds by using platform-specific cache IDs. Prevents `.cargo-ok: File exists` errors.

### Operator / Helm Chart

- Helm chart version bumped to 0.2.1.
- CRD updated with `subresources: status: {}` to enable the status subresource endpoint.
- New printer columns on `kubectl get networkassertions`: Schedule, Ready, Reason, Status.
- Tighter RBAC — removed Kopf-specific permissions (kopf.dev, apiextensions.k8s.io, admissionregistration.k8s.io).
- Operator configuration via environment variables: `PROBE_IMAGE_REPOSITORY`, `PROBE_IMAGE_TAG`, `PROBE_IMAGE_PULL_POLICY`, `POLICY_REPORT_MAX_RESULTS`.

### Breaking Changes

- **CRD upgrade required** — The NetworkAssertion CRD now includes the status subresource. Existing clusters must re-apply the CRD (`kubectl apply -f crds/networkassertions.yaml`) since Helm does not update CRDs on `helm upgrade`.
- **Operator image changed** — The operator container image is now built from Rust instead of Python. The image name (`ghcr.io/hardbyte/netchecks-operator`) is unchanged.
- **Removed Kopf peering CRDs** — The operator no longer uses `ClusterKopfPeering` or `NamespacedKopfPeering` resources.

### Testing

- 49 unit tests for the Rust operator (CRD deserialization, rule transforms, job/cronjob building, result summarization, status conditions, observability, config loading).
- TCP probe unit tests and integration test manifests.
- CI updated with Rust toolchain job (fmt, clippy, cargo test).

## 0.6.0

Previous release. See [GitHub releases](https://github.com/hardbyte/netchecks/releases) for details.
