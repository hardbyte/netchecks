# Grafana Dashboard and Alerts for Netchecks

The netchecks operator emits OTLP metrics (see the operator's `OperatorObservability`). The dashboard and alert rules in this directory consume those metrics via a Prometheus-compatible datasource — i.e. you need an OTel Collector in front of Prometheus (or equivalent) to receive OTLP and re-expose Prometheus format.

A turnkey example of the receiving side lives in [`operator/examples/observability/`](../../operator/examples/observability/): a minimal OTel Collector deployment plus a ServiceMonitor for the kube-prometheus-stack.

## Dashboard

`netchecks-dashboard.json` — Operator-side metrics: reconcile throughput / errors / duration, in-flight reconciliations, assertions processed, PolicyReport upsert rate, probe duration p50/p95/p99 by probe type, and four headline stat panels.

### Import

**Option A — Grafana UI**

1. Open Grafana → Dashboards → Import.
2. Upload `netchecks-dashboard.json`.
3. Select your Prometheus datasource when prompted.

**Option B — Provisioning**

Copy the JSON to `/etc/grafana/provisioning/dashboards/netchecks-dashboard.json`.

**Option C — API**

```bash
curl -X POST "http://admin:admin@localhost:3000/api/dashboards/db" \
  -H "Content-Type: application/json" \
  -d "{\"dashboard\": $(cat netchecks-dashboard.json), \"overwrite\": true}"
```

The dashboard's `$datasource` template variable defaults to "Prometheus" — adjust if your datasource is named differently.

## Alerts

`alerts/netchecks-alerts.yaml` — five Grafana unified-alerting rules, designed to be imported via [`/api/v1/provisioning/alert-rules`](https://grafana.com/docs/grafana/latest/developers/http_api/alerting_provisioning/) or file provisioning under `provisioning/alerting/`.

Before importing, substitute your Prometheus datasource UID:

```bash
sed 's/DS_PROMETHEUS/<your-uid>/g' alerts/netchecks-alerts.yaml > netchecks-alerts.local.yaml
```

| Rule | Severity | Threshold | For |
|---|---|---|---|
| `netchecks_operator_down` | critical | `up{job="netchecks-otel-collector"} < 1` | 5m |
| `netchecks_reconcile_error_rate_high` | warning | `err / total > 0.1` | 10m |
| `netchecks_reconcile_p95_slow` | warning | reconcile p95 > 5000 ms | 15m |
| `netchecks_probe_p95_slow` | warning | probe p95 > 30 s (per type) | 15m |
| `netchecks_no_reconciles` | critical | no successful reconciles in 30m | 5m |

> **Note on `netchecks_no_reconciles`**: this rule uses `increase(...[30m])` which only stabilises once Prometheus has 30 minutes of scrape history. On a fresh install the rule will be in `pending` for ~5 minutes and then briefly fire until enough data has accumulated. Either silence it during install or wait for the first half hour of metrics.

## Metrics reference

| Metric | Type | Labels | Description |
|---|---|---|---|
| `netchecks_reconcile_total` | Counter | `result, reason` | Reconciliations by outcome |
| `netchecks_reconcile_duration_milliseconds` | Histogram (ms) | — | Reconciliation duration |
| `netchecks_reconcile_inflight` | Gauge | — | In-flight reconciliations |
| `netchecks_assertions_total` | Counter | `name` | NetworkAssertions processed (per name) |
| `netchecks_policy_reports_updated_total` | Counter | — | PolicyReport upsert count |
| `netchecks_probe_duration_seconds` | Histogram (s) | `name, type` | Time spent running probe Jobs |

All series also carry the resource attributes `service_name=netchecks-operator` and `service_version=<chart appVersion>`.

After the OTel Collector adds Prometheus-side labels you'll also see `job`, `instance`, `namespace`, `pod`, `service`, `container`, `endpoint`, and `exported_job` — the queries in this directory use `service_name` for filtering so they don't depend on the scrape topology.

## Pipeline

```
┌─────────────┐    OTLP/gRPC     ┌────────────────┐    /metrics    ┌────────────┐
│   netchecks │  ────────────►   │ OTel Collector │  ◄──────────── │ Prometheus │
│   operator  │                  │                │                │            │
└─────────────┘                  └────────────────┘                └────────────┘
                                                                          │
                                                                          ▼
                                                                    ┌──────────┐
                                                                    │  Grafana │
                                                                    └──────────┘
```

For a dev-shaped alternative (single container — Grafana + Prometheus + OTel receiver + Loki + Tempo), use `grafana/otel-lgtm` and point the operator at it via `OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-lgtm:4317`.
