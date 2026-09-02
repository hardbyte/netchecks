## Project Overview

Netchecks is a cloud native tool for testing network conditions and asserting that they meet expectations. The repository contains two main components:

1. **Netcheck CLI/Python Library** - Command line tool and Python library for running network checks (DNS, HTTP) with customizable validation rules written in CEL (Common Expression Language)
2. **Netchecks Operator** - Kubernetes Operator (Rust, using kube-rs) that schedules and runs network checks, reporting results as PolicyReport resources

## Architecture

### Netcheck CLI (Python Library)
- **Entry point**: `netcheck/cli.py` - Uses Typer for CLI interface with commands `run`, `http`, `dns`
- **Core logic**: `netcheck/runner.py` - Contains `run_from_config()` for running multiple assertions and `check_individual_assertion()` for individual tests
- **Check implementations**: `netcheck/checks/` - Separate modules for DNS (`dns.py`), HTTP (`http.py`), and internal checks
- **Validation**: `netcheck/validation.py` - CEL expression evaluation using the Rust `common-expression-language` library (via `cel.Context` and `cel.evaluate`). Custom functions: `parse_json`, `parse_yaml`, `b64decode`, `b64encode`
- **Context system**: `netcheck/context.py` - Template replacement using external data from files, inline data, or directories. `LazyFileLoadingDict` is a dict subclass that lazy-loads file contents on access with caching

Test results include `spec` (test configuration), `data` (results), and `status` (pass/fail). Custom validation rules can reference both `data` and `spec` in CEL expressions.

### Netchecks Operator (Rust / kube-rs)
- **Entry point**: `operator/src/main.rs` - Tokio-based async main with Controller setup
- **CRD types**: `operator/src/crd.rs` - NetworkAssertion CRD definition using kube-rs `CustomResource` derive
- **Reconciler**: `operator/src/reconciler.rs` - Core reconciliation logic: ConfigMap creation, Job/CronJob management, PolicyReport updates
- **Configuration**: `operator/src/context.rs` - `OperatorConfig` loaded from env vars (PROBE_IMAGE_REPOSITORY, PROBE_IMAGE_TAG, etc.)
- **Observability**: `operator/src/observability.rs` - Health endpoints (/livez, /readyz) and optional OTLP metrics
- **Flow**:
  1. NetworkAssertion CRD created → operator creates ConfigMap with rules + Job/CronJob with probe pod
  2. Probe pod runs netcheck CLI with mounted config
  3. Controller re-reconciles when owned Jobs complete (via `Controller.owns(jobs)`)
  4. Results extracted from pod logs and transformed into PolicyReport CRD
  5. Optional OTLP metrics export for reconciliation and probe durations
- **Helm chart**: `operator/charts/netchecks/` - Includes NetworkAssertion and PolicyReport CRDs

Key transformation: K8s concepts (ConfigMap/Secret contexts) are mapped to CLI format (directory/file/inline contexts) via `transform_context_for_config()` in `operator/src/reconciler.rs`.

## Development Setup

The project uses **uv** for Python dependency management (CLI) and **cargo** for Rust (operator).

### CLI/Library Development

Install dependencies:
```bash
uv sync
```

Run tests with coverage:
```bash
uv run pytest tests --cov netcheck --cov-report=lcov --cov-report=term
```

Run a single test:
```bash
uv run pytest tests/test_cli.py::test_name -v
```

Run the CLI locally:
```bash
uv run netcheck dns --host github.com -v
uv run netcheck http --url https://github.com/status -v
uv run netcheck run --config example-config.json -v
```

### Operator Development

The operator is written in Rust using kube-rs.

Build the operator:
```bash
cd operator
cargo build
```

Run unit tests:
```bash
cd operator
cargo test
```

Format and lint (required before committing):
```bash
cd operator
cargo fmt --all
cargo clippy --all-targets --all-features -- -D warnings
```

Integration tests require:
- Kind cluster (Cilium CNI optional — Cilium-specific tests are skipped without it)
- PolicyReport CRD installed (via helm chart dependency)
- Netcheck operator and probe images loaded into cluster

Run integration tests locally with kind:
```bash
# Create cluster and build images
kind create cluster --name netchecks-test
docker build -t ghcr.io/hardbyte/netchecks:local .
docker build -t ghcr.io/hardbyte/netchecks-operator:local operator/
kind load docker-image ghcr.io/hardbyte/netchecks:local --name netchecks-test
kind load docker-image ghcr.io/hardbyte/netchecks-operator:local --name netchecks-test
helm dependency build operator/charts/netchecks

# Run tests (integration tests are Python/pytest using kubectl subprocess calls)
cd operator
NETCHECKS_IMAGE_TAG=local pytest -v -x
# Cleanup
kind delete cluster --name netchecks-test
```

### Docker Build

Build probe image:
```bash
docker build -t ghcr.io/hardbyte/netchecks:main .
```

Build operator image:
```bash
docker build -t ghcr.io/hardbyte/netchecks-operator:main operator/
```

### Code Quality

Format and lint CLI code (Python):
```bash
uv run ruff format .
uv run ruff check .
```

Format and lint operator code (Rust):
```bash
cd operator
cargo fmt --all
cargo clippy --all-targets --all-features -- -D warnings
```

## Testing Philosophy

- **Unit tests** in `tests/` test the CLI and library functions (Python)
- **Unit tests** in `operator/src/` test the operator logic (Rust, inline `#[cfg(test)]` modules)
- **Integration tests** in `operator/tests/` deploy NetworkAssertion resources to a real Kubernetes cluster and verify PolicyReport results (Python/pytest using kubectl)
- CI runs CLI tests on ubuntu-latest, windows-latest, and macos-latest with Python 3.11 and 3.12

## Key Configuration Files

- `pyproject.toml` - CLI package metadata and dependencies (using uv)
- `operator/Cargo.toml` - Operator package metadata and dependencies (Rust)
- `operator/charts/netchecks/values.yaml` - Helm chart configuration
- `operator/manifests/deploy.yaml` - Static Kubernetes manifests

## Release Process

Modeled on `hardbyte/awa`: the tag is the trigger, and publication is gated on the tag
matching every version manifest and on CI having passed on that exact commit.

1. Open a release PR that bumps the version everywhere it lives, in lockstep:
   `pyproject.toml` (+ `uv lock`), `operator/Cargo.toml` (+ `Cargo.lock`), and
   `operator/charts/netchecks/Chart.yaml` (`appVersion`, plus the chart `version`
   and its `artifacthub.io/changes`). Regenerate `operator/manifests/deploy.yaml`
   (`operator/create-static-manifests.sh`) and move the `## [Unreleased]` entries in
   `CHANGELOG.md` under a new `## X.Y.Z` heading. `scripts/check_versions.py` must
   pass; `ct lint` requires the chart version bump.
2. Merge it and wait for the push-triggered CI run on `main` to go green — the release
   workflow refuses to publish a commit without one.
3. Tag that exact commit `vX.Y.Z` — either `git tag vX.Y.Z && git push origin vX.Y.Z`,
   or create a GitHub release (draft is fine) for that tag and publish it; publishing
   creates the tag.
4. `.github/workflows/release.yaml` then runs: version check → exact-SHA CI check →
   multi-arch probe and operator images pushed to ghcr.io with `X.Y.Z`, `X.Y` and
   `latest` tags, keyless-signed with cosign and with build provenance attested →
   `netcheck` published to PyPI → Helm chart released via chart-releaser
   (`netchecks-<chart version>`) → GitHub release created from the `CHANGELOG.md`
   section (if none exists yet) with the sdist/wheel attached, then published.

## CEL Validation Examples

Default DNS validation rule:
```cel
data['response-code'] == 'NOERROR' &&
size(data['A']) >= 1 &&
(timestamp(data['endTimestamp']) - timestamp(data['startTimestamp']) < duration('10s'))
```

Default HTTP validation rule:
```cel
data['status-code'] in [200, 201]
```

Custom validation with JSON parsing:
```cel
parse_json(data.body).headers['X-Header'] == 'expected-value'
```

## Important Notes

- CEL evaluation uses the Rust `common-expression-language` library (PyPI: `common-expression-language`), not the Python `celpy` library
- Operator uses kube-rs Controller framework with `Controller.owns(jobs)` for Job lifecycle tracking
- Template strings in NetworkAssertion specs use `{{ variable }}` syntax and are replaced via `netcheck/context.py:replace_template()`
- Sensitive fields (headers) are redacted from output unless `--disable-redaction` flag is used
- PolicyReport CRD must be installed before operator (from wg-policy-prototypes)
- Operator metrics optionally exported via OTLP when `OTEL_EXPORTER_OTLP_ENDPOINT` is set
