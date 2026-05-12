# Netchecks alert rules

`netchecks-alerts.yaml` ships five Grafana unified-alerting rules tuned for steady-state operator health. They follow the same shape as the awa alerts: a single Prometheus query (refId A), an explicit `reduce` step (refId B), then a threshold expression (refId C) — required so Grafana doesn't reject multi-series queries with "frame cannot uniquely be identified by its labels".

| Rule | Severity | What it watches | Threshold | For |
|---|---|---|---|---|
| `netchecks_operator_down` | critical | `up{job="netchecks-otel-collector"}` | `< 1` | 5m |
| `netchecks_reconcile_error_rate_high` | warning | Non-success / total reconcile ratio | `> 0.10` | 10m |
| `netchecks_reconcile_p95_slow` | warning | p95 reconcile duration | `> 5000 ms` | 15m |
| `netchecks_probe_p95_slow` | warning | p95 probe duration per `type` | `> 30 s` | 15m |
| `netchecks_no_reconciles` | critical | `increase(success[30m]) < 1` | n/a | 5m |

## Import

The file is in Grafana provisioning v1 format. Replace `DS_PROMETHEUS` with the UID of your Prometheus datasource and copy into `/etc/grafana/provisioning/alerting/`, or POST each rule body to `/api/v1/provisioning/alert-rules` with the `X-Disable-Provenance: true` header.

```bash
sed 's/DS_PROMETHEUS/<your-uid>/g' netchecks-alerts.yaml > /etc/grafana/provisioning/alerting/netchecks.yaml
```

## Tuning notes

- **`netchecks_operator_down`** assumes the ServiceMonitor labels its scrape job `netchecks-otel-collector`. If you renamed the Service, update the `up{job=...}` matcher.
- **`netchecks_no_reconciles`** uses `increase(...[30m])`. Prometheus's `increase` extrapolates over the window — on fresh installs with less than 30m of scrape history it conservatively returns 0, so the rule will go `pending` for 5 minutes then briefly fire until enough scrapes have accumulated. Silence during install, or extend `for: 5m` to `for: 35m`.
- Severity labels (`critical` / `warning`) are conventions only — Grafana's contact-point routing is what actually decides who gets paged.

## Triggering each rule locally

A rough script for verifying the rules end-to-end on a kind cluster:

```bash
# 1. Force "operator down" — scale to zero
kubectl scale deploy/netchecks -n netchecks --replicas=0     # wait 6m, rule fires
kubectl scale deploy/netchecks -n netchecks --replicas=1     # rule clears

# 2. Force "probe p95 slow" — point at a non-routable host
kubectl apply -f - <<EOF
apiVersion: netchecks.io/v1
kind: NetworkAssertion
metadata: { name: stuck, namespace: default }
spec:
  rules:
    - name: stuck
      type: tcp
      host: 10.255.255.1   # unreachable
      port: 443
      timeout: 60
      expected: pass
EOF
# wait ~20m of probe runs at 60s each, rule fires
```
