# Changelog

## 0.11.0

### Helm Chart

- **CRD installation is configurable** ([#346](https://github.com/hardbyte/netchecks/pull/346), thanks @christianhuth). The CRDs moved from the chart's `crds/` directory (which Helm never templates) into `templates/`, gated by new values:
  - `crds.install` (default `true`; the long-documented `installCRDs` is honored as an alias and finally does something),
  - `crds.keep` (default `true`, annotates the CRDs with `helm.sh/resource-policy: keep` so `helm uninstall` leaves them and their `NetworkAssertion`/`PolicyReport` objects in place, as before),
  - `crds.groups.netchecks` / `crds.groups.wgpolicyk8s` to skip either API group, e.g. when Kyverno, Trivy or Kubescape already own the shared `wgpolicyk8s.io` CRDs.
- **Upgrade note — one-time adoption step.** CRDs installed by chart ≤ 0.3.x carry no Helm ownership metadata, so `helm upgrade` to chart 0.4+ fails with `invalid ownership metadata` until they are adopted once:

  ```bash
  for crd in networkassertions.netchecks.io policyreports.wgpolicyk8s.io clusterpolicyreports.wgpolicyk8s.io; do
    kubectl label crd "$crd" app.kubernetes.io/managed-by=Helm --overwrite
    kubectl annotate crd "$crd" meta.helm.sh/release-name=<release> meta.helm.sh/release-namespace=<namespace> --overwrite
  done
  ```

  Alternatively set `crds.install=false` and manage the CRDs outside the chart. Full details in the [chart README](operator/charts/netchecks/README.md).
- Removed a duplicate `policyreports.wgpolicyk8s.io` definition that was shipped inside `clusterpolicyreports.yaml`.
- Chart version bumped to **0.5.0**, `appVersion` to 0.11.0. Maintainer entry changed to the GitHub username `hardbyte` (required by chart-testing's maintainer validation).

### Operator

- **PolicyReport API version is discovered at runtime** instead of being hardcoded to `wgpolicyk8s.io/v1beta1` ([#347](https://github.com/hardbyte/netchecks/issues/347)). The operator uses `v1beta1` when served and falls back to `v1alpha2`, so it now works when another component's copy of the CRDs (e.g. Kyverno's, which serves only `v1alpha2`) owns the API group. `v1alpha1` is not selected because its result schema differs.
- A missing `wgpolicyk8s.io` API group (or one serving only unsupported versions) is now reported as a `PolicyReportApiUnavailable` status condition on the NetworkAssertion with an actionable message, and logged at startup, instead of an opaque `404 page not found`.
- **kube-rs 3.1 → 4.2, k8s-openapi 0.27 → 0.28**, plus a full `cargo update`.

### CLI

- **Dependency refresh** via `uv lock --upgrade`: `common-expression-language` 0.5.6 → 0.8.0, typer 0.25 → 0.27, psycopg 3.3.5, pydantic 2.13.5, requests 2.34.2. The CEL wrapper now handles cel 0.8's `KeyError`/`TypeError` for missing fields and type mismatches, so rules such as `data['status-code'] == 200` still evaluate to `false` (rather than crashing) when a probe never received a response.

### Static manifests

- `operator/manifests/deploy.yaml` is regenerated from the current chart and, for the first time, actually contains the CRDs — `helm template` never rendered the old `crds/` directory, so `kubectl apply -f .../deploy.yaml` previously installed an operator with no `NetworkAssertion` CRD despite what the docs said.

### Internal / CI

- Fork pull requests can pass CI: image pushes to `ghcr.io` are skipped for forks (and dependabot), which build the images locally and hand them to the integration-test job as artifacts — full test coverage, no registry access for forks.
- Chart linting (`ct lint`) now runs — it had been pointed at a non-existent directory. `ruff` is pinned in the lint workflow to the locked version (0.16.5) so rule additions no longer break CI on unrelated pushes; ruff 0.16 findings across the codebase fixed.
- Integration tests install the chart with `crds.keep=false` and uninstall with `--wait`, so repeated installs into fresh namespaces don't trip over left-over CRD ownership metadata.

## 0.10.0

### CLI

- **PostgreSQL probes** ([732d300](https://github.com/hardbyte/netchecks/commit/732d300)): two new check types, available from the CLI (`netcheck postgres`) and in NetworkAssertion rules.
  - `postgres` runs a single SQL statement and exposes `success`, `row-count`, `columns`, `rows` (and `sqlstate` on error) to CEL validation. Read-only transactions with rollback by default; `params`, `timeout`, `read-only`, `rollback` and `row-limit` are configurable.
  - `postgres-grants` validates *effective* privileges with PostgreSQL's `has_*_privilege` functions (so role membership and `PUBLIC` grants are accounted for). Rules select roles (by name, login flag, membership) and objects (databases, schemas, tables/views/materialized views/foreign tables, sequences, functions) and assert privileges are present (`mode: require`) or absent (`mode: deny`).
- `dsn`, `params`, `password` and `connection` fields are redacted from probe output by default.
- New [PostgreSQL docs](docs/src/pages/docs/postgres.md) including least-privilege guidance for the probe role (why a superuser or `pg_execute_server_program` member must not be used).

### Helm Chart

- Chart version 0.3.1, `appVersion` 0.10.0.

## 0.9.0

### Operator

- **PolicyReports now written as `wgpolicyk8s.io/v1beta1`** — the chart's PolicyReport CRD already has v1beta1 as the storage version; the operator now writes that directly instead of relying on Kubernetes to convert from v1alpha2 on the way to etcd. The v1alpha2 endpoint is still served for backward compatibility.

### Helm Chart

- **Chart version bumped to 0.3.0**, `appVersion` to 0.9.0.
- **`policy-reporter` subchart bumped 2.22.4 → 3.7.4** (major). Users with custom subchart values under `policy-reporter:` should review the upstream changelog. The subchart is opt-in (`policy-reporter.enabled=false` by default) and the keys netchecks itself sets (`enabled`, `ui.enabled`) are unchanged.

### Observability

- **Grafana dashboard** at [`docs/grafana/netchecks-dashboard.json`](docs/grafana/netchecks-dashboard.json) — 11 panels covering reconcile throughput / errors / duration, in-flight reconciliations, assertion processing, PolicyReport upserts, probe duration by type, and stat panel headlines.
- **Grafana unified-alerting rules** at [`docs/grafana/alerts/netchecks-alerts.yaml`](docs/grafana/alerts/netchecks-alerts.yaml) — five rules: operator down, reconcile error rate, reconcile p95, probe p95, no-successful-reconciles.
- **OTel Collector example** at [`operator/examples/observability/`](operator/examples/observability/) — minimal collector + ServiceMonitor wiring for kube-prometheus-stack.

### Documentation

- **Compliance annotations guide** at [`docs/src/pages/docs/compliance-annotations.md`](docs/src/pages/docs/compliance-annotations.md) with three example `NetworkAssertions` (PCI-DSS v4.0 CDE isolation, SOC 2 boundary protection, CIS Kubernetes Benchmark default-deny).

### Internal

- **Rust dependency refresh**: opentelemetry 0.31 → 0.32 across `opentelemetry`, `opentelemetry_sdk`, `opentelemetry-otlp`; kube-rs 3.0 → 3.1 and the rest of the lockfile via `cargo update`.
- **CLI dependency refresh** via `uv lock --upgrade`: pydantic 2.12 → 2.13, typer 0.24 → 0.25, requests 2.32 → 2.34, urllib3 2.6 → 2.7, ruff 0.15.5 → 0.15.12, etc. `rich` constraint relaxed from `<14.0.0` to `<16.0.0`; locked at 15.0.0.
- **CI**: pytest 8 → 9, kind 0.18 → 0.27, kubectl 1.26.3 → 1.32.2, kindest/node v1.32.2, Cilium 1.14.3 → 1.19.3, cilium-cli v0.15.11 → v0.19.2.
- **GitHub Actions**: bumped to Node 24-capable versions ahead of the September 2026 Node 20 deprecation — `actions/checkout` v4→v6, `actions/setup-python` v4→v6, `actions/upload-artifact` v4→v7, `actions/download-artifact` v4→v8, `docker/login-action` v3→v4, `docker/metadata-action` v5→v6, `docker/setup-buildx-action` v3→v4, `docker/setup-qemu-action` v3→v4, `docker/build-push-action` v6→v7, `astral-sh/setup-uv` v2→v7.
- **Dependabot config**: replaced the dead `pip /operator` ecosystem (Python operator gone in v0.7.0) with `cargo /operator`.

### Cilium example

- Rewrote `operator/examples/cilium-tcp-egress-restrictions/tcp-egress-netpol.yaml` to use `toEntities: [kube-apiserver]` instead of `toServices: [kubernetes]`. Cilium 1.17+ changed how `toServices` matching interacts with kube-proxy DNAT — the new rule works on Cilium 1.16+ and is the idiomatic post-1.17 pattern.

## 0.8.0

### Features

- **Default probe resource requests/limits** — The operator now applies a configurable `resources` block to every probe Job it creates. Set `probeConfig.resources` in the Helm chart values and the chart wires it through to the operator via the new `PROBE_RESOURCES` env var. Closes [#147](https://github.com/hardbyte/netchecks/issues/147).

- **Source IP binding for TCP, HTTP, and DNS probes** — All three probe types now accept a `--source-ip` CLI flag (and matching `source-ip` config field for `netcheck run`). The probe binds its outgoing socket to the given local address, which is useful when a host has multiple interfaces and you want to verify a specific egress path. Closes [#70](https://github.com/hardbyte/netchecks/issues/70).

### Operator / Helm Chart

- Helm chart version bumped to 0.2.2.
- New env var `PROBE_RESOURCES` (JSON-encoded `ResourceRequirements`). Empty / unset / malformed values are treated as no resources stanza (cluster default).

### Documentation / Site

- Bumped `next` 14.2.32 → 14.2.35 in the docs site for SNYK-JS-NEXT-14400636 (Next.js high-severity deserialization vuln).

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
