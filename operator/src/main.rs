//! netchecks-operator — Kubernetes controller for NetworkAssertion CRDs.
//!
//! Watches `NetworkAssertion` custom resources and reconciles them into
//! probe Jobs (or CronJobs), then collects results into PolicyReports.

use std::sync::Arc;

use futures::StreamExt;
use k8s_openapi::api::batch::v1::{CronJob, Job};
use kube::runtime::{watcher, Controller};
use kube::{Api, Client};
use tracing::info;

use netchecks_operator::context::{OperatorConfig, OperatorContext};
use netchecks_operator::crd::NetworkAssertion;
use netchecks_operator::observability::{serve_health, OperatorObservability};
use netchecks_operator::reconciler::{error_policy, reconcile};

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    // Initialize structured JSON logging.
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| tracing_subscriber::EnvFilter::new("info")),
        )
        .json()
        .with_target(false)
        .init();

    info!(
        version = env!("CARGO_PKG_VERSION"),
        "starting netchecks-operator"
    );

    // Load configuration from environment variables.
    let config = OperatorConfig::from_env();
    info!(
        probe_image = %format!("{}:{}", config.probe_image_repository, config.probe_image_tag),
        policy_report_max_results = config.policy_report_max_results,
        "operator configuration loaded"
    );

    // Build kube client from in-cluster config or KUBECONFIG.
    let client = Client::try_default().await?;

    // Set up observability (health endpoints + optional OTLP metrics).
    let observability = OperatorObservability::from_env()?;
    let http_addr = std::env::var("OPERATOR_HTTP_ADDR")
        .unwrap_or_else(|_| "0.0.0.0:8080".to_string())
        .parse()?;
    let observability_server = observability.clone();
    tokio::spawn(async move {
        if let Err(error) = serve_health(http_addr, observability_server).await {
            tracing::error!(%error, %http_addr, "health server exited");
        }
    });

    // Create the shared operator context.
    let ctx = Arc::new(OperatorContext::new(
        client.clone(),
        config,
        observability.clone(),
    ));

    // Watch all NetworkAssertion resources across all namespaces.
    let network_assertions: Api<NetworkAssertion> = Api::all(client.clone());
    let jobs: Api<Job> = Api::all(client.clone());
    let cronjobs: Api<CronJob> = Api::all(client);

    info!("starting controller");
    observability.mark_ready();

    Controller::new(network_assertions, watcher::Config::default())
        // Re-reconcile when owned Jobs change (e.g. when a probe Job completes).
        .owns(jobs, watcher::Config::default())
        // Re-reconcile when owned CronJobs change (e.g. when a scheduled Job
        // is spawned or completes, the CronJob status is updated).
        .owns(cronjobs, watcher::Config::default())
        .shutdown_on_signal()
        .run(reconcile, error_policy, ctx)
        .for_each(|result| async move {
            match result {
                Ok(action) => {
                    tracing::debug!(?action, "reconcile completed");
                }
                Err(error) => {
                    tracing::error!(%error, "reconcile failed");
                }
            }
        })
        .await;

    observability.mark_not_ready();
    if let Err(error) = observability.shutdown() {
        tracing::warn!(%error, "failed to shut down observability");
    }
    info!("controller shut down");
    Ok(())
}
