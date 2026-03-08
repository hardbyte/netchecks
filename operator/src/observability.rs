//! Operator health endpoints and optional OTLP metrics export.

use std::net::SocketAddr;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::time::Instant;

use axum::extract::State;
use axum::http::StatusCode;
use axum::response::IntoResponse;
use axum::routing::get;
use axum::{serve, Router};
use opentelemetry::metrics::{Counter, Histogram, Meter, MeterProvider, UpDownCounter};
use opentelemetry::KeyValue;
use opentelemetry_otlp::{MetricExporter, Protocol, WithExportConfig};
use opentelemetry_sdk::metrics::{PeriodicReader, SdkMeterProvider};
use opentelemetry_sdk::Resource;
use tokio::net::TcpListener;

const SERVICE_NAME: &str = "netchecks-operator";

#[derive(Clone)]
pub struct OperatorObservability {
    ready: Arc<AtomicBool>,
    metrics: Option<Arc<Metrics>>,
}

struct Metrics {
    provider: SdkMeterProvider,
    reconcile_total: Counter<u64>,
    reconcile_duration_ms: Histogram<u64>,
    reconcile_inflight: UpDownCounter<i64>,
    assertions_total: Counter<u64>,
    policy_reports_updated: Counter<u64>,
    probe_duration_seconds: Histogram<f64>,
}

pub struct ReconcileGuard {
    metrics: Option<Arc<Metrics>>,
    started_at: Instant,
}

impl OperatorObservability {
    pub fn from_env() -> anyhow::Result<Self> {
        Ok(Self {
            ready: Arc::new(AtomicBool::new(false)),
            metrics: init_metrics_from_env()?,
        })
    }

    pub fn mark_ready(&self) {
        self.ready.store(true, Ordering::Relaxed);
    }

    pub fn mark_not_ready(&self) {
        self.ready.store(false, Ordering::Relaxed);
    }

    pub fn start_reconcile(&self) -> ReconcileGuard {
        if let Some(metrics) = &self.metrics {
            metrics.reconcile_inflight.add(1, &[]);
        }
        ReconcileGuard {
            metrics: self.metrics.clone(),
            started_at: Instant::now(),
        }
    }

    pub fn record_assertion_count(&self, name: &str) {
        if let Some(metrics) = &self.metrics {
            metrics
                .assertions_total
                .add(1, &[KeyValue::new("name", name.to_string())]);
        }
    }

    pub fn record_policy_report_updated(&self) {
        if let Some(metrics) = &self.metrics {
            metrics.policy_reports_updated.add(1, &[]);
        }
    }

    pub fn record_probe_duration(&self, name: &str, probe_type: &str, duration_seconds: f64) {
        if let Some(metrics) = &self.metrics {
            metrics.probe_duration_seconds.record(
                duration_seconds,
                &[
                    KeyValue::new("name", name.to_string()),
                    KeyValue::new("type", probe_type.to_string()),
                ],
            );
        }
    }

    pub fn shutdown(&self) -> anyhow::Result<()> {
        if let Some(metrics) = &self.metrics {
            metrics.provider.shutdown()?;
        }
        Ok(())
    }
}

impl ReconcileGuard {
    pub fn record_result(self, result: &str, reason: &str) {
        if let Some(metrics) = &self.metrics {
            metrics.reconcile_total.add(
                1,
                &[
                    KeyValue::new("result", result.to_string()),
                    KeyValue::new("reason", reason.to_string()),
                ],
            );
            metrics
                .reconcile_duration_ms
                .record(self.started_at.elapsed().as_millis() as u64, &[]);
        }
    }
}

impl Drop for ReconcileGuard {
    fn drop(&mut self) {
        if let Some(metrics) = &self.metrics {
            metrics.reconcile_inflight.add(-1, &[]);
        }
    }
}

pub async fn serve_health(
    bind_addr: SocketAddr,
    observability: OperatorObservability,
) -> anyhow::Result<()> {
    let listener = TcpListener::bind(bind_addr).await?;
    let app = Router::new()
        .route("/livez", get(livez))
        .route("/readyz", get(readyz))
        // Legacy endpoint for backward compatibility
        .route("/healthz", get(livez))
        .with_state(observability);

    serve(listener, app).await?;
    Ok(())
}

fn init_metrics_from_env() -> anyhow::Result<Option<Arc<Metrics>>> {
    if !otel_metrics_enabled() {
        return Ok(None);
    }

    let exporter = MetricExporter::builder()
        .with_tonic()
        .with_protocol(Protocol::Grpc)
        .build()?;

    let reader = PeriodicReader::builder(exporter).build();
    let provider = SdkMeterProvider::builder()
        .with_reader(reader)
        .with_resource(
            Resource::builder_empty()
                .with_attributes([
                    KeyValue::new("service.name", SERVICE_NAME),
                    KeyValue::new("service.version", env!("CARGO_PKG_VERSION")),
                ])
                .build(),
        )
        .build();

    let meter = provider.meter(SERVICE_NAME);
    Ok(Some(Arc::new(Metrics::new(provider, meter))))
}

fn otel_metrics_enabled() -> bool {
    let metrics_exporter = std::env::var("OTEL_METRICS_EXPORTER").ok();
    if matches!(metrics_exporter.as_deref(), Some("none")) {
        return false;
    }

    std::env::var_os("OTEL_EXPORTER_OTLP_ENDPOINT").is_some()
        || std::env::var_os("OTEL_EXPORTER_OTLP_METRICS_ENDPOINT").is_some()
}

impl Metrics {
    fn new(provider: SdkMeterProvider, meter: Meter) -> Self {
        Self {
            provider,
            reconcile_total: meter
                .u64_counter("netchecks.reconcile.total")
                .with_description("Total reconciliations by result and reason")
                .build(),
            reconcile_duration_ms: meter
                .u64_histogram("netchecks.reconcile.duration")
                .with_unit("ms")
                .with_description("Reconciliation duration in milliseconds")
                .build(),
            reconcile_inflight: meter
                .i64_up_down_counter("netchecks.reconcile.inflight")
                .with_description("In-flight reconciliations")
                .build(),
            assertions_total: meter
                .u64_counter("netchecks.assertions.total")
                .with_description("Total network assertions processed")
                .build(),
            policy_reports_updated: meter
                .u64_counter("netchecks.policy_reports.updated")
                .with_description("PolicyReport create/update count")
                .build(),
            probe_duration_seconds: meter
                .f64_histogram("netchecks.probe.duration")
                .with_unit("s")
                .with_description("Time spent by netchecks probe running assertions")
                .build(),
        }
    }
}

async fn livez() -> &'static str {
    "ok"
}

async fn readyz(State(observability): State<OperatorObservability>) -> impl IntoResponse {
    if observability.ready.load(Ordering::Relaxed) {
        (StatusCode::OK, "ready")
    } else {
        (StatusCode::SERVICE_UNAVAILABLE, "not ready")
    }
}

#[cfg(test)]
mod tests {
    use std::sync::{Arc, Mutex};

    use axum::extract::State;
    use axum::http::StatusCode;
    use axum::response::IntoResponse;
    use opentelemetry::metrics::MeterProvider;
    use opentelemetry_sdk::metrics::data::{AggregatedMetrics, MetricData, ResourceMetrics};
    use opentelemetry_sdk::metrics::{InMemoryMetricExporter, PeriodicReader, SdkMeterProvider};

    use super::{
        livez, otel_metrics_enabled, readyz, Metrics, OperatorObservability, ReconcileGuard,
        SERVICE_NAME,
    };

    static ENV_LOCK: Mutex<()> = Mutex::new(());

    fn test_observability() -> (
        OperatorObservability,
        SdkMeterProvider,
        InMemoryMetricExporter,
    ) {
        let exporter = InMemoryMetricExporter::default();
        let provider = SdkMeterProvider::builder()
            .with_reader(PeriodicReader::builder(exporter.clone()).build())
            .build();
        let meter = provider.meter(SERVICE_NAME);
        let observability = OperatorObservability {
            ready: Arc::new(std::sync::atomic::AtomicBool::new(false)),
            metrics: Some(Arc::new(Metrics::new(provider.clone(), meter))),
        };

        (observability, provider, exporter)
    }

    fn metric_exists(metrics: &[ResourceMetrics], name: &str) -> bool {
        metrics.iter().any(|resource_metrics| {
            resource_metrics
                .scope_metrics()
                .flat_map(|scope_metrics| scope_metrics.metrics())
                .any(|metric| metric.name() == name)
        })
    }

    fn u64_sum_value(metrics: &[ResourceMetrics], name: &str) -> Option<u64> {
        metrics
            .iter()
            .flat_map(|resource_metrics| resource_metrics.scope_metrics())
            .flat_map(|scope_metrics| scope_metrics.metrics())
            .find(|metric| metric.name() == name)
            .and_then(|metric| match metric.data() {
                AggregatedMetrics::U64(MetricData::Sum(sum)) => sum
                    .data_points()
                    .next()
                    .map(|data_point| data_point.value()),
                _ => None,
            })
    }

    #[test]
    fn otel_metrics_stay_disabled_without_endpoint() {
        let _guard = ENV_LOCK.lock().expect("env lock should not be poisoned");
        unsafe {
            std::env::remove_var("OTEL_EXPORTER_OTLP_ENDPOINT");
            std::env::remove_var("OTEL_EXPORTER_OTLP_METRICS_ENDPOINT");
            std::env::remove_var("OTEL_METRICS_EXPORTER");
        }
        assert!(!otel_metrics_enabled());
    }

    #[test]
    fn otel_metrics_enable_with_explicit_endpoint() {
        let _guard = ENV_LOCK.lock().expect("env lock should not be poisoned");
        unsafe {
            std::env::set_var("OTEL_EXPORTER_OTLP_ENDPOINT", "http://collector:4317");
            std::env::remove_var("OTEL_EXPORTER_OTLP_METRICS_ENDPOINT");
            std::env::remove_var("OTEL_METRICS_EXPORTER");
        }
        assert!(otel_metrics_enabled());
        unsafe {
            std::env::remove_var("OTEL_EXPORTER_OTLP_ENDPOINT");
        }
    }

    #[tokio::test]
    async fn health_endpoints_reflect_readiness() {
        let (observability, _provider, _exporter) = test_observability();

        assert_eq!(livez().await, "ok");

        let not_ready = readyz(State(observability.clone())).await.into_response();
        assert_eq!(not_ready.status(), StatusCode::SERVICE_UNAVAILABLE);

        observability.mark_ready();
        let ready = readyz(State(observability)).await.into_response();
        assert_eq!(ready.status(), StatusCode::OK);
    }

    #[test]
    fn metrics_are_recorded_and_flushed() {
        let (observability, provider, exporter) = test_observability();

        let guard: ReconcileGuard = observability.start_reconcile();
        observability.record_assertion_count("test-assertion");
        observability.record_policy_report_updated();
        observability.record_probe_duration("test", "http", 1.5);
        guard.record_result("success", "Reconciled");

        provider.force_flush().expect("flush should succeed");

        let metrics = exporter
            .get_finished_metrics()
            .expect("metrics should be exported");

        assert!(metric_exists(&metrics, "netchecks.reconcile.total"));
        assert!(metric_exists(&metrics, "netchecks.reconcile.duration"));
        assert_eq!(
            u64_sum_value(&metrics, "netchecks.assertions.total"),
            Some(1)
        );
        assert_eq!(
            u64_sum_value(&metrics, "netchecks.policy_reports.updated"),
            Some(1)
        );
    }
}
