# Netchecks observability examples

Manifests for getting netchecks operator metrics into Prometheus and Grafana.

| File | Purpose |
|---|---|
| `otel-collector.yaml` | Minimal OpenTelemetry Collector deployment + Service in an `observability` namespace. Receives OTLP from the operator on port 4317/4318 and re-publishes the metrics in Prometheus format on `:8889/metrics`. |
| `servicemonitor.yaml` | `monitoring.coreos.com/v1` ServiceMonitor that points Prometheus (kube-prometheus-stack) at the collector's Prometheus port. Adjust the `release: kube-prometheus-stack` selector label to match your Prometheus Operator's `serviceMonitorSelector`. |

## Wiring it up

```bash
# 1. Install the receiving side
kubectl apply -f operator/examples/observability/otel-collector.yaml
kubectl apply -f operator/examples/observability/servicemonitor.yaml   # requires Prometheus Operator CRDs

# 2. Point the netchecks operator at the collector
helm upgrade netchecks operator/charts/netchecks -n netchecks \
  --set operator.env[0].name=OTEL_EXPORTER_OTLP_ENDPOINT \
  --set operator.env[0].value=http://netchecks-otel-collector.observability:4317 \
  --set operator.env[1].name=OTEL_EXPORTER_OTLP_PROTOCOL \
  --set operator.env[1].value=grpc \
  --set operator.env[2].name=OTEL_SERVICE_NAME \
  --set operator.env[2].value=netchecks-operator
```

> The `operator.env` extension is a placeholder — the netchecks chart doesn't yet expose an `operator.env` values key. For now, add the env vars with `kubectl set env deploy/netchecks ...` after install. If you want this baked into the chart, see [issue tracker](https://github.com/hardbyte/netchecks/issues).

Then import the Grafana dashboard and alert rules from [`docs/grafana/`](../../../docs/grafana/).

## What's emitted

See the operator-side metric catalog in [`docs/grafana/README.md`](../../../docs/grafana/README.md#metrics-reference).

## Dev-shaped alternative

For local development the [`grafana/otel-lgtm`](https://github.com/grafana/docker-otel-lgtm) all-in-one container (Grafana + Prometheus + OTel receiver + Loki + Tempo) is much simpler than running kube-prometheus-stack. Run it as a sidecar Deployment in kind, point the operator at `:4317` on its Service, and load the dashboard JSON via Grafana's UI.
