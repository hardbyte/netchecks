## Project Overview

Netchecks is a cloud native tool for testing network conditions and asserting that they meet expectations. The repository contains two main components:

1. **Netcheck CLI/Python Library** - Command line tool and Python library for running network checks (DNS, HTTP) with customizable validation rules written in CEL (Common Expression Language)
2. **Netchecks Operator** - Kubernetes Operator that schedules and runs network checks, reporting results as PolicyReport resources

## Architecture

### Netcheck CLI (Python Library)
- **Entry point**: `netcheck/cli.py` - Uses Typer for CLI interface with commands `run`, `http`, `dns`
- **Core logic**: `netcheck/runner.py` - Contains `run_from_config()` for running multiple assertions and `check_individual_assertion()` for individual tests
- **Check implementations**: `netcheck/checks/` - Separate modules for DNS (`dns.py`), HTTP (`http.py`), and internal checks
- **Validation**: `netcheck/validation.py` - CEL expression evaluation using the Rust `common-expression-language` library (via `cel.Context` and `cel.evaluate`). Custom functions: `parse_json`, `parse_yaml`, `b64decode`, `b64encode`
- **Context system**: `netcheck/context.py` - Template replacement using external data from files, inline data, or directories. `LazyFileLoadingDict` is a dict subclass that lazy-loads file contents on access with caching

Test results include `spec` (test configuration), `data` (results), and `status` (pass/fail). Custom validation rules can reference both `data` and `spec` in CEL expressions.

### Netchecks Operator (Kubernetes)
- **Main operator**: `operator/netchecks_operator/main.py` - Kopf-based operator with handlers for NetworkAssertion CRD lifecycle
- **Configuration**: `operator/netchecks_operator/config.py` - Pydantic v2 `BaseSettings` with custom `JsonConfigSettingsSource` that loads config from a JSON file via the `JSON_CONFIG` environment variable. Priority: init > JSON file > env vars > file secrets
- **Flow**:
  1. NetworkAssertion CRD created → operator creates ConfigMap with rules + Job/CronJob with probe pod
  2. Probe pod runs netcheck CLI with mounted config
  3. Operator daemon monitors probe pod completion
  4. Results extracted from pod logs and transformed into PolicyReport CRD
  5. Prometheus metrics updated with test duration and results
- **Helm chart**: `operator/charts/netchecks/` - Includes NetworkAssertion and PolicyReport CRDs

Key transformation: K8s concepts (ConfigMap/Secret contexts) are mapped to CLI format (directory/file/inline contexts) via `transform_context_for_config_file()` at operator/netchecks_operator/main.py:208.

## Development Setup

The project uses **uv** for Python dependency management (not pip or poetry for the CLI).

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

The operator uses **Poetry** for dependency management (separate from CLI).

Install operator dependencies:
```bash
cd operator
poetry install --with dev
```

Run operator unit tests (no cluster required):
```bash
cd operator
poetry run pytest tests/test_config.py -v
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

# Run tests
cd operator
NETCHECKS_IMAGE_TAG=local poetry run pytest -v -x

# Cleanup
kind delete cluster --name netchecks-test
```

Run operator locally (outside cluster):
```bash
cd operator
poetry run kopf run netchecks_operator/main.py --liveness=http://0.0.0.0:8080/healthz
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

Format code with ruff (CLI uses uv, operator uses poetry):
```bash
# CLI
uv run ruff format .

# Operator
cd operator
poetry run ruff format .
```

Lint with ruff:
```bash
# CLI
uv run ruff check .

# Operator
cd operator
poetry run ruff check .
```

## Testing Philosophy

- **Unit tests** in `tests/` test the CLI and library functions
- **Integration tests** in `operator/tests/` deploy NetworkAssertion resources to a real Kubernetes cluster and verify PolicyReport results
- CI runs tests on ubuntu-latest, windows-latest, and macos-latest with Python 3.11 and 3.12

## Key Configuration Files

- `pyproject.toml` - CLI package metadata and dependencies (using uv)
- `operator/pyproject.toml` - Operator package metadata and dependencies (using poetry)
- `operator/charts/netchecks/values.yaml` - Helm chart configuration
- `operator/manifests/deploy.yaml` - Static Kubernetes manifests

## Release Process

1. Update version in `pyproject.toml` (CLI), `operator/pyproject.toml` (operator), and `operator/charts/netchecks/Chart.yaml` (chart `version` + `appVersion`)
2. Push to main branch
3. Create GitHub release with a `v*` tag (e.g. `v0.6.0`)
4. CI automatically:
   - Publishes package to PyPI
   - Builds and pushes Docker images to ghcr.io
   - Runs integration tests with Kind + Cilium
   - Releases helm chart via chart-releaser (creates a `netchecks-*` release)

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
- Operator uses Kopf framework for handling Kubernetes CRD lifecycle events
- Template strings in NetworkAssertion specs use `{{ variable }}` syntax and are replaced via `netcheck/context.py:replace_template()`
- Sensitive fields (headers) are redacted from output unless `--disable-redaction` flag is used
- PolicyReport CRD must be installed before operator (from wg-policy-prototypes)
- Operator metrics exposed on port 9090 (configurable) using OpenTelemetry + Prometheus
