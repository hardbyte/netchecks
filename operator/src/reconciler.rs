//! Reconciliation logic for `NetworkAssertion` custom resources.
//!
//! Implements the core reconcile loop: validate spec, create ConfigMap with
//! rules, create Job/CronJob to run the probe, collect results from completed
//! pods, and upsert a PolicyReport.

use std::collections::BTreeMap;
use std::sync::Arc;
use std::time::Duration;

use k8s_openapi::api::batch::v1::{CronJob, CronJobSpec, Job, JobSpec, JobTemplateSpec};
use k8s_openapi::api::core::v1::{
    ConfigMap, ConfigMapVolumeSource, Container, Pod, PodSpec, PodTemplateSpec, SecretVolumeSource,
    Volume, VolumeMount,
};
use k8s_openapi::apimachinery::pkg::apis::meta::v1::ObjectMeta;
use kube::api::{
    Api, DeleteParams, DynamicObject, ListParams, LogParams, Patch, PatchParams, PostParams,
};
use kube::discovery::ApiResource;
use kube::runtime::controller::Action;
use kube::{Client, Resource, ResourceExt};
use tracing::info;

use crate::context::{OperatorConfig, OperatorContext};
use crate::crd::{common_labels, ContextSpec, NetworkAssertion, Rule};

/// Errors that can occur during reconciliation.
#[derive(Debug, thiserror::Error)]
pub enum ReconcileError {
    #[error("invalid spec: {0}")]
    InvalidSpec(String),

    #[error("kubernetes API error: {0}")]
    Kube(#[from] kube::Error),

    #[error("JSON error: {0}")]
    Json(#[from] serde_json::Error),

    #[error("failed to parse probe results: {0}")]
    ResultParse(String),

    #[error("missing namespace on NetworkAssertion")]
    MissingNamespace,
}

/// Main reconcile entry point, called by the kube-rs controller.
pub async fn reconcile(
    resource: Arc<NetworkAssertion>,
    ctx: Arc<OperatorContext>,
) -> Result<Action, ReconcileError> {
    let name = resource.name_any();
    let namespace = resource
        .namespace()
        .ok_or(ReconcileError::MissingNamespace)?;

    let guard = ctx.observability.start_reconcile();
    ctx.observability.record_assertion_count(&name);
    info!(name, namespace, "reconciling NetworkAssertion");

    // Validate
    if resource.spec.rules.is_empty() {
        guard.record_result("error", "InvalidSpec");
        return Err(ReconcileError::InvalidSpec(
            "rules must not be empty".into(),
        ));
    }

    // Step 1: Ensure ConfigMap with probe rules config
    ensure_config_map(&ctx.kube_client, &resource, &namespace).await?;

    // Step 2: Ensure Job or CronJob
    if let Some(schedule) = &resource.spec.schedule {
        ensure_cron_job(
            &ctx.kube_client,
            &resource,
            &namespace,
            schedule,
            &ctx.config,
        )
        .await?;
    } else {
        ensure_job(&ctx.kube_client, &resource, &namespace, &ctx.config).await?;
        // Clean up any stale CronJob left from a previous scheduled config
        delete_stale_cronjob(&ctx.kube_client, &name, &namespace).await?;
    }

    // Step 3: Process completed probe pods
    let processed = process_completed_jobs(
        &ctx.kube_client,
        &resource,
        &namespace,
        &ctx.config,
        &ctx.observability,
    )
    .await?;

    guard.record_result("success", "Reconciled");

    // Determine requeue interval
    if resource.spec.schedule.is_some() {
        // Scheduled assertion — requeue to pick up new CronJob results
        Ok(Action::requeue(Duration::from_secs(60)))
    } else if processed {
        // One-time job completed and results processed — slow requeue
        Ok(Action::requeue(Duration::from_secs(3600)))
    } else {
        // One-time job still running — requeue to check again
        // (also triggered earlier via owns() on Job changes)
        Ok(Action::requeue(Duration::from_secs(60)))
    }
}

/// Error policy: determines requeue delay after reconciliation failure.
pub fn error_policy(
    _resource: Arc<NetworkAssertion>,
    error: &ReconcileError,
    _ctx: Arc<OperatorContext>,
) -> Action {
    tracing::error!(%error, "reconciliation failed");
    match error {
        ReconcileError::InvalidSpec(_) => Action::requeue(Duration::from_secs(300)),
        ReconcileError::ResultParse(_) => Action::requeue(Duration::from_secs(60)),
        _ => Action::requeue(Duration::from_secs(30)),
    }
}

// ---------------------------------------------------------------------------
// ConfigMap
// ---------------------------------------------------------------------------

/// Create or update the ConfigMap containing the netchecks CLI config.
async fn ensure_config_map(
    client: &Client,
    na: &NetworkAssertion,
    namespace: &str,
) -> Result<(), ReconcileError> {
    let name = na.name_any();
    let cm_api: Api<ConfigMap> = Api::namespaced(client.clone(), namespace);

    let cli_config = build_cli_config(&na.spec.rules, &na.spec.context);
    let config_json = serde_json::to_string(&cli_config)?;

    let labels = common_labels(&name);
    let owner_ref = na
        .controller_owner_ref(&())
        .ok_or_else(|| ReconcileError::InvalidSpec("cannot create owner reference".into()))?;

    let config_map = ConfigMap {
        metadata: ObjectMeta {
            name: Some(name.clone()),
            namespace: Some(namespace.to_string()),
            labels: Some(labels),
            owner_references: Some(vec![owner_ref]),
            ..Default::default()
        },
        data: Some(BTreeMap::from([("config.json".to_string(), config_json)])),
        ..Default::default()
    };

    cm_api
        .patch(
            &name,
            &PatchParams::apply("netchecks-operator").force(),
            &Patch::Apply(config_map),
        )
        .await?;

    tracing::debug!(name, namespace, "ensured ConfigMap");
    Ok(())
}

/// Build the netchecks CLI config JSON from rules and context definitions.
fn build_cli_config(rules: &[Rule], contexts: &[ContextSpec]) -> serde_json::Value {
    let cli_contexts: Vec<serde_json::Value> =
        contexts.iter().map(transform_context_for_config).collect();

    let assertions: Vec<serde_json::Value> = rules
        .iter()
        .map(|rule| {
            serde_json::json!({
                "name": rule.name,
                "rules": [transform_rule_for_config(rule)],
            })
        })
        .collect();

    serde_json::json!({
        "contexts": cli_contexts,
        "assertions": assertions,
    })
}

/// Transform a Rule for the netchecks CLI config format.
///
/// Moves `validate.pattern` to a top-level `validation` key if present.
fn transform_rule_for_config(rule: &Rule) -> serde_json::Value {
    let mut value = serde_json::to_value(rule).expect("Rule serialization should not fail");

    if let Some(validate) = value.get("validate") {
        if let Some(pattern) = validate.get("pattern").cloned() {
            value
                .as_object_mut()
                .unwrap()
                .get_mut("validate")
                .unwrap()
                .as_object_mut()
                .unwrap()
                .remove("pattern");
            value
                .as_object_mut()
                .unwrap()
                .insert("validation".to_string(), pattern);
        }
    }

    value
}

/// Transform a ContextSpec for the netchecks CLI config format.
fn transform_context_for_config(context: &ContextSpec) -> serde_json::Value {
    let mut result = serde_json::json!({"name": context.name});

    if context.config_map.is_some() || context.secret.is_some() {
        result["type"] = serde_json::json!("directory");
        result["path"] = serde_json::json!(format!("/mnt/{}", context.name));
    } else if let Some(inline) = &context.inline {
        result["type"] = serde_json::json!("inline");
        result["data"] = inline.clone();
    }

    result
}

// ---------------------------------------------------------------------------
// Job / CronJob
// ---------------------------------------------------------------------------

/// Ensure a one-time Job exists for this assertion.
///
/// If the spec generation changed, the old Job is deleted and a new one created.
async fn ensure_job(
    client: &Client,
    na: &NetworkAssertion,
    namespace: &str,
    config: &OperatorConfig,
) -> Result<(), ReconcileError> {
    let name = na.name_any();
    let generation = na.metadata.generation.unwrap_or(0).to_string();
    let jobs_api: Api<Job> = Api::namespaced(client.clone(), namespace);

    match jobs_api.get(&name).await {
        Ok(existing) => {
            let existing_gen = existing
                .metadata
                .annotations
                .as_ref()
                .and_then(|a| a.get("netchecks.io/spec-generation"))
                .cloned()
                .unwrap_or_default();

            if existing_gen == generation {
                tracing::debug!(name, namespace, "Job already current");
                return Ok(());
            }

            // Spec changed, delete old job
            tracing::info!(name, namespace, "spec changed, recreating Job");
            let _ = jobs_api.delete(&name, &DeleteParams::default()).await;
        }
        Err(kube::Error::Api(err)) if err.code == 404 => {
            // No job exists, will create
        }
        Err(err) => return Err(err.into()),
    }

    let job = build_job(na, config)?;
    jobs_api.create(&PostParams::default(), &job).await?;

    tracing::info!(name, namespace, "created Job");
    Ok(())
}

/// Ensure a CronJob exists for this scheduled assertion.
async fn ensure_cron_job(
    client: &Client,
    na: &NetworkAssertion,
    namespace: &str,
    schedule: &str,
    config: &OperatorConfig,
) -> Result<(), ReconcileError> {
    let name = na.name_any();
    let cronjobs_api: Api<CronJob> = Api::namespaced(client.clone(), namespace);

    let cron_job = build_cron_job(na, config, schedule)?;

    cronjobs_api
        .patch(
            &name,
            &PatchParams::apply("netchecks-operator").force(),
            &Patch::Apply(cron_job),
        )
        .await?;

    tracing::info!(name, namespace, schedule, "ensured CronJob");
    Ok(())
}

/// Delete any stale CronJob left when a scheduled assertion becomes one-shot.
async fn delete_stale_cronjob(
    client: &Client,
    name: &str,
    namespace: &str,
) -> Result<(), ReconcileError> {
    let cronjobs_api: Api<CronJob> = Api::namespaced(client.clone(), namespace);

    match cronjobs_api.get(name).await {
        Ok(_) => {
            tracing::info!(name, namespace, "deleting stale CronJob (schedule removed)");
            cronjobs_api.delete(name, &DeleteParams::default()).await?;
        }
        Err(kube::Error::Api(err)) if err.code == 404 => {
            // No stale CronJob — nothing to do
        }
        Err(err) => return Err(err.into()),
    }

    Ok(())
}

/// Build a one-time Job for a NetworkAssertion.
fn build_job(na: &NetworkAssertion, config: &OperatorConfig) -> Result<Job, ReconcileError> {
    let name = na.name_any();
    let labels = common_labels(&name);

    let generation = na.metadata.generation.unwrap_or(0).to_string();
    let mut annotations = BTreeMap::new();
    annotations.insert("netchecks.io/spec-generation".to_string(), generation);

    let owner_ref = na
        .controller_owner_ref(&())
        .ok_or_else(|| ReconcileError::InvalidSpec("cannot create owner reference".into()))?;

    Ok(Job {
        metadata: ObjectMeta {
            name: Some(name),
            namespace: na.namespace(),
            labels: Some(labels),
            annotations: Some(annotations),
            owner_references: Some(vec![owner_ref]),
            ..Default::default()
        },
        spec: Some(build_job_spec(na, config)),
        ..Default::default()
    })
}

/// Build a CronJob for a scheduled NetworkAssertion.
fn build_cron_job(
    na: &NetworkAssertion,
    config: &OperatorConfig,
    schedule: &str,
) -> Result<CronJob, ReconcileError> {
    let name = na.name_any();
    let labels = common_labels(&name);

    let owner_ref = na
        .controller_owner_ref(&())
        .ok_or_else(|| ReconcileError::InvalidSpec("cannot create owner reference".into()))?;

    Ok(CronJob {
        metadata: ObjectMeta {
            name: Some(name),
            namespace: na.namespace(),
            labels: Some(labels),
            owner_references: Some(vec![owner_ref]),
            ..Default::default()
        },
        spec: Some(CronJobSpec {
            schedule: schedule.to_string(),
            job_template: JobTemplateSpec {
                metadata: None,
                spec: Some(build_job_spec(na, config)),
            },
            ..Default::default()
        }),
        ..Default::default()
    })
}

/// Build the JobSpec (shared between Job and CronJob).
fn build_job_spec(na: &NetworkAssertion, config: &OperatorConfig) -> JobSpec {
    let name = na.name_any();
    let mut probe_labels = common_labels(&name);
    probe_labels.insert(
        "app.kubernetes.io/component".to_string(),
        "probe".to_string(),
    );

    // Build volumes and volume mounts
    let mut volumes = vec![Volume {
        name: "netcheck-rules".to_string(),
        config_map: Some(ConfigMapVolumeSource {
            name: name.clone(),
            ..Default::default()
        }),
        ..Default::default()
    }];
    let mut volume_mounts = vec![VolumeMount {
        name: "netcheck-rules".to_string(),
        mount_path: "/netcheck".to_string(),
        ..Default::default()
    }];

    // Add volumes for each context data source
    for ctx in &na.spec.context {
        if let Some(cm_ref) = &ctx.config_map {
            let cm_name = cm_ref
                .get("name")
                .and_then(|v| v.as_str())
                .unwrap_or(&ctx.name);
            let mut cm_source = ConfigMapVolumeSource {
                name: cm_name.to_string(),
                ..Default::default()
            };
            // Preserve optional ConfigMap volume fields (items, optional, defaultMode)
            if let Some(optional) = cm_ref.get("optional").and_then(|v| v.as_bool()) {
                cm_source.optional = Some(optional);
            }
            if let Some(default_mode) = cm_ref.get("defaultMode").and_then(|v| v.as_i64()) {
                cm_source.default_mode = Some(default_mode as i32);
            }
            if let Some(items) = cm_ref.get("items") {
                if let Ok(key_to_paths) = serde_json::from_value(items.clone()) {
                    cm_source.items = Some(key_to_paths);
                }
            }
            volumes.push(Volume {
                name: ctx.name.clone(),
                config_map: Some(cm_source),
                ..Default::default()
            });
            volume_mounts.push(VolumeMount {
                name: ctx.name.clone(),
                mount_path: format!("/mnt/{}", ctx.name),
                ..Default::default()
            });
        } else if let Some(secret_ref) = &ctx.secret {
            let secret_name = secret_ref
                .get("name")
                .and_then(|v| v.as_str())
                .unwrap_or(&ctx.name);
            let mut secret_source = SecretVolumeSource {
                secret_name: Some(secret_name.to_string()),
                ..Default::default()
            };
            // Preserve optional Secret volume fields (items, optional, defaultMode)
            if let Some(optional) = secret_ref.get("optional").and_then(|v| v.as_bool()) {
                secret_source.optional = Some(optional);
            }
            if let Some(default_mode) = secret_ref.get("defaultMode").and_then(|v| v.as_i64()) {
                secret_source.default_mode = Some(default_mode as i32);
            }
            if let Some(items) = secret_ref.get("items") {
                if let Ok(key_to_paths) = serde_json::from_value(items.clone()) {
                    secret_source.items = Some(key_to_paths);
                }
            }
            volumes.push(Volume {
                name: ctx.name.clone(),
                secret: Some(secret_source),
                ..Default::default()
            });
            volume_mounts.push(VolumeMount {
                name: ctx.name.clone(),
                mount_path: format!("/mnt/{}", ctx.name),
                ..Default::default()
            });
        }
        // Inline contexts don't need volumes — they're in the ConfigMap config
    }

    // Build probe command
    let mut command = vec![
        "netcheck".to_string(),
        "run".to_string(),
        "--config".to_string(),
        "/netcheck/config.json".to_string(),
    ];
    if na.spec.disable_redaction {
        command.push("--disable-redaction".to_string());
    }

    let container = Container {
        name: "netcheck".to_string(),
        image: Some(format!(
            "{}:{}",
            config.probe_image_repository, config.probe_image_tag
        )),
        image_pull_policy: Some(config.probe_image_pull_policy.clone()),
        command: Some(command),
        volume_mounts: Some(volume_mounts),
        ..Default::default()
    };

    let mut pod_template = PodTemplateSpec {
        metadata: Some(ObjectMeta {
            labels: Some(probe_labels),
            ..Default::default()
        }),
        spec: Some(PodSpec {
            restart_policy: Some("Never".to_string()),
            containers: vec![container],
            volumes: Some(volumes),
            ..Default::default()
        }),
    };

    // Apply template overrides from the NetworkAssertion spec
    if let Some(overrides) = &na.spec.template {
        apply_template_overrides(&mut pod_template, overrides);
    }

    JobSpec {
        template: pod_template,
        backoff_limit: Some(4),
        ..Default::default()
    }
}

/// Apply user-provided template overrides to the pod template.
///
/// Supports overriding metadata labels/annotations and spec fields
/// like serviceAccountName.
fn apply_template_overrides(pod_template: &mut PodTemplateSpec, overrides: &serde_json::Value) {
    if let Some(meta_overrides) = overrides.get("metadata") {
        let metadata = pod_template
            .metadata
            .get_or_insert_with(ObjectMeta::default);

        if let Some(extra_labels) = meta_overrides.get("labels").and_then(|v| v.as_object()) {
            let labels = metadata.labels.get_or_insert_with(BTreeMap::new);
            for (key, val) in extra_labels {
                if let Some(string_val) = val.as_str() {
                    labels.insert(key.clone(), string_val.to_string());
                }
            }
        }

        if let Some(extra_annotations) = meta_overrides
            .get("annotations")
            .and_then(|v| v.as_object())
        {
            let annotations = metadata.annotations.get_or_insert_with(BTreeMap::new);
            for (key, val) in extra_annotations {
                if let Some(string_val) = val.as_str() {
                    annotations.insert(key.clone(), string_val.to_string());
                }
            }
        }
    }

    if let Some(spec_overrides) = overrides.get("spec") {
        if let Some(pod_spec) = &mut pod_template.spec {
            if let Some(sa_name) = spec_overrides
                .get("serviceAccountName")
                .and_then(|v| v.as_str())
            {
                pod_spec.service_account_name = Some(sa_name.to_string());
            }

            if let Some(node_selector) = spec_overrides
                .get("nodeSelector")
                .and_then(|v| v.as_object())
            {
                let mut selector = BTreeMap::new();
                for (key, val) in node_selector {
                    if let Some(string_val) = val.as_str() {
                        selector.insert(key.clone(), string_val.to_string());
                    }
                }
                pod_spec.node_selector = Some(selector);
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Result processing
// ---------------------------------------------------------------------------

/// Check for completed probe pods and process their results into a PolicyReport.
///
/// Returns `true` if results were successfully processed.
async fn process_completed_jobs(
    client: &Client,
    na: &NetworkAssertion,
    namespace: &str,
    config: &OperatorConfig,
    observability: &crate::observability::OperatorObservability,
) -> Result<bool, ReconcileError> {
    let name = na.name_any();
    let pods_api: Api<Pod> = Api::namespaced(client.clone(), namespace);

    let label_selector = format!(
        "app.kubernetes.io/name=netchecks,app.kubernetes.io/component=probe,app.kubernetes.io/instance={}",
        name
    );

    let pods = pods_api
        .list(&ListParams::default().labels(&label_selector))
        .await?;

    // Find the most recently completed pod (by creation timestamp)
    let completed_pod = pods
        .items
        .iter()
        .filter(|p| p.status.as_ref().and_then(|s| s.phase.as_deref()) == Some("Succeeded"))
        .max_by_key(|p| p.metadata.creation_timestamp.clone());

    let Some(pod) = completed_pod else {
        // Check for failed pods
        let has_failed = pods
            .items
            .iter()
            .any(|p| p.status.as_ref().and_then(|s| s.phase.as_deref()) == Some("Failed"));
        if has_failed {
            tracing::warn!(name, namespace, "probe pod(s) failed");
        }
        return Ok(false);
    };

    let pod_name = pod.name_any();
    tracing::info!(name, namespace, pod = %pod_name, "processing completed probe pod");

    let log = pods_api.logs(&pod_name, &LogParams::default()).await?;

    if log.starts_with("unable to retrieve container logs") {
        tracing::warn!(pod = %pod_name, "unable to retrieve container logs");
        return Ok(false);
    }

    let probe_results: serde_json::Value = serde_json::from_str(&log).map_err(|err| {
        ReconcileError::ResultParse(format!("failed to parse probe output as JSON: {err}"))
    })?;

    upsert_policy_report(client, &probe_results, na, namespace, config).await?;

    // Record probe duration metrics
    record_probe_metrics(&probe_results, &name, observability);

    observability.record_policy_report_updated();
    Ok(true)
}

/// Record probe timing metrics from the results.
fn record_probe_metrics(
    probe_results: &serde_json::Value,
    assertion_name: &str,
    observability: &crate::observability::OperatorObservability,
) {
    if let Some(assertions) = probe_results.get("assertions").and_then(|a| a.as_array()) {
        for assertion in assertions {
            if let Some(results) = assertion.get("results").and_then(|r| r.as_array()) {
                for result in results {
                    let probe_type = result
                        .get("spec")
                        .and_then(|s| s.get("type"))
                        .and_then(|t| t.as_str())
                        .unwrap_or("unknown");

                    let start = result
                        .get("data")
                        .and_then(|d| d.get("startTimestamp"))
                        .and_then(|t| t.as_str())
                        .and_then(|s| chrono::DateTime::parse_from_rfc3339(s).ok());
                    let end = result
                        .get("data")
                        .and_then(|d| d.get("endTimestamp"))
                        .and_then(|t| t.as_str())
                        .and_then(|s| chrono::DateTime::parse_from_rfc3339(s).ok());

                    if let (Some(start), Some(end)) = (start, end) {
                        let duration = (end - start).num_milliseconds() as f64 / 1000.0;
                        observability.record_probe_duration(assertion_name, probe_type, duration);
                    }
                }
            }
        }
    }
}

// ---------------------------------------------------------------------------
// PolicyReport
// ---------------------------------------------------------------------------

/// Create or update a PolicyReport from probe results.
async fn upsert_policy_report(
    client: &Client,
    probe_results: &serde_json::Value,
    na: &NetworkAssertion,
    namespace: &str,
    config: &OperatorConfig,
) -> Result<(), ReconcileError> {
    let assertion_name = na.name_any();

    let owner_ref = na
        .controller_owner_ref(&())
        .ok_or_else(|| ReconcileError::InvalidSpec("cannot create owner reference".into()))?;

    let mut report_results = convert_results_for_policy_report(probe_results);
    let report_summary = summarize_results(probe_results);

    // Truncate results if necessary
    if report_results.len() > config.policy_report_max_results {
        let start = report_results.len() - config.policy_report_max_results;
        report_results = report_results.split_off(start);
    }

    let mut labels = common_labels(&assertion_name);
    labels.insert(
        "policy.kubernetes.io/engine".to_string(),
        "netcheck".to_string(),
    );

    let annotations = BTreeMap::from([
        ("category".to_string(), "Network".to_string()),
        ("created-by".to_string(), "netcheck".to_string()),
        (
            "netcheck-operator-version".to_string(),
            env!("CARGO_PKG_VERSION").to_string(),
        ),
    ]);

    let gvk = kube::api::GroupVersionKind::gvk("wgpolicyk8s.io", "v1alpha2", "PolicyReport");
    let api_resource = ApiResource::from_gvk(&gvk);
    let api: Api<DynamicObject> = Api::namespaced_with(client.clone(), namespace, &api_resource);

    let report_data = serde_json::json!({
        "results": report_results,
        "summary": report_summary,
    });

    let mut obj = DynamicObject::new(&assertion_name, &api_resource);
    obj.metadata = ObjectMeta {
        name: Some(assertion_name.clone()),
        namespace: Some(namespace.to_string()),
        labels: Some(labels),
        annotations: Some(annotations),
        owner_references: Some(vec![owner_ref]),
        ..Default::default()
    };
    obj.data = report_data;

    // Try server-side apply first; fall back to create-or-replace
    match api
        .patch(
            &assertion_name,
            &PatchParams::apply("netchecks-operator").force(),
            &Patch::Apply(&obj),
        )
        .await
    {
        Ok(_) => {
            tracing::info!(assertion = %assertion_name, "upserted PolicyReport");
        }
        Err(kube::Error::Api(err)) if err.code == 422 || err.code == 500 => {
            // Server-side apply may fail with 422 (field conflicts) or 500
            // (schema validation on CRDs like PolicyReport). Fall back to
            // get-then-create-or-replace.
            tracing::warn!(
                assertion = %assertion_name,
                code = err.code,
                "server-side apply failed, falling back to create/replace"
            );
            match api.get(&assertion_name).await {
                Ok(existing) => {
                    obj.metadata.resource_version = existing.metadata.resource_version.clone();
                    api.replace(&assertion_name, &PostParams::default(), &obj)
                        .await?;
                }
                Err(kube::Error::Api(err)) if err.code == 404 => {
                    api.create(&PostParams::default(), &obj).await?;
                }
                Err(err) => return Err(err.into()),
            }
        }
        Err(err) => return Err(err.into()),
    }

    Ok(())
}

/// Summarize probe results into pass/fail/warn/error/skip counts.
fn summarize_results(probe_results: &serde_json::Value) -> serde_json::Value {
    let mut pass: i64 = 0;
    let mut fail: i64 = 0;
    let mut warn: i64 = 0;
    let mut error: i64 = 0;
    let mut skip: i64 = 0;

    if let Some(assertions) = probe_results.get("assertions").and_then(|a| a.as_array()) {
        for assertion in assertions {
            if let Some(results) = assertion.get("results").and_then(|r| r.as_array()) {
                for result in results {
                    match result
                        .get("status")
                        .and_then(|s| s.as_str())
                        .unwrap_or("skip")
                    {
                        "pass" => pass += 1,
                        "fail" => fail += 1,
                        "warn" => warn += 1,
                        "error" => error += 1,
                        _ => skip += 1,
                    }
                }
            }
        }
    }

    // Only include non-zero counts (matches PolicyReport convention and
    // existing integration test expectations).
    let mut summary = serde_json::Map::new();
    if pass > 0 {
        summary.insert("pass".to_string(), serde_json::json!(pass));
    }
    if fail > 0 {
        summary.insert("fail".to_string(), serde_json::json!(fail));
    }
    if warn > 0 {
        summary.insert("warn".to_string(), serde_json::json!(warn));
    }
    if error > 0 {
        summary.insert("error".to_string(), serde_json::json!(error));
    }
    if skip > 0 {
        summary.insert("skip".to_string(), serde_json::json!(skip));
    }
    serde_json::Value::Object(summary)
}

/// Convert probe results to PolicyReport result entries.
fn convert_results_for_policy_report(probe_results: &serde_json::Value) -> Vec<serde_json::Value> {
    let mut results = Vec::new();

    let Some(assertions) = probe_results.get("assertions").and_then(|a| a.as_array()) else {
        return results;
    };

    for assertion in assertions {
        let assertion_name = assertion
            .get("name")
            .and_then(|n| n.as_str())
            .unwrap_or("unknown");

        let Some(test_results) = assertion.get("results").and_then(|r| r.as_array()) else {
            continue;
        };

        for (i, test_result) in test_results.iter().enumerate() {
            let rule_name = test_result
                .get("name")
                .and_then(|n| n.as_str())
                .map(|s| s.to_string())
                .unwrap_or_else(|| format!("{assertion_name}-rule-{}", i + 1));

            let category = test_result
                .get("spec")
                .and_then(|s| s.get("type"))
                .and_then(|t| t.as_str())
                .unwrap_or("unknown");

            let status = test_result
                .get("status")
                .and_then(|s| s.as_str())
                .unwrap_or("skip");

            let message = test_result
                .get("message")
                .and_then(|m| m.as_str())
                .map(|s| s.to_string())
                .unwrap_or_else(|| format!("Rule from {assertion_name}"));

            let timestamp = test_result
                .get("data")
                .and_then(|d| d.get("endTimestamp"))
                .and_then(|t| t.as_str())
                .map(convert_iso_timestamp);

            let properties = serde_json::json!({
                "spec": test_result.get("spec").map(|v| v.to_string()).unwrap_or_default(),
                "data": test_result.get("data").map(|v| v.to_string()).unwrap_or_default(),
            });

            let mut result = serde_json::json!({
                "source": "netchecks",
                "policy": assertion_name,
                "rule": rule_name,
                "category": category,
                "result": status,
                "message": message,
                "properties": properties,
            });

            if let Some(ts) = timestamp {
                result
                    .as_object_mut()
                    .unwrap()
                    .insert("timestamp".to_string(), ts);
            }

            results.push(result);
        }
    }

    results
}

/// Convert an ISO 8601 timestamp string to Kubernetes meta/v1.Timestamp format.
fn convert_iso_timestamp(iso: &str) -> serde_json::Value {
    if let Ok(dt) = chrono::DateTime::parse_from_rfc3339(iso) {
        serde_json::json!({
            "nanos": 0,
            "seconds": dt.timestamp(),
        })
    } else if let Ok(dt) = chrono::NaiveDateTime::parse_from_str(iso, "%Y-%m-%dT%H:%M:%S%.f") {
        serde_json::json!({
            "nanos": 0,
            "seconds": dt.and_utc().timestamp(),
        })
    } else {
        serde_json::json!({
            "nanos": 0,
            "seconds": 0,
        })
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use crate::crd::NetworkAssertionSpec;

    /// Create a test NetworkAssertion with realistic metadata (including UID).
    fn test_network_assertion(name: &str, rules: Vec<Rule>) -> NetworkAssertion {
        NetworkAssertion {
            metadata: ObjectMeta {
                name: Some(name.to_string()),
                namespace: Some("default".to_string()),
                uid: Some("test-uid-12345".to_string()),
                generation: Some(1),
                ..Default::default()
            },
            spec: NetworkAssertionSpec {
                rules,
                schedule: None,
                context: vec![],
                template: None,
                disable_redaction: false,
            },
            status: None,
        }
    }

    fn test_config() -> OperatorConfig {
        OperatorConfig {
            probe_image_repository: "ghcr.io/hardbyte/netchecks".to_string(),
            probe_image_tag: "test".to_string(),
            probe_image_pull_policy: "IfNotPresent".to_string(),
            policy_report_max_results: 100,
        }
    }

    fn simple_http_rule() -> Rule {
        Rule {
            name: "http-check".to_string(),
            fields: BTreeMap::from([
                ("type".to_string(), serde_json::json!("http")),
                ("url".to_string(), serde_json::json!("https://example.com")),
                ("expected".to_string(), serde_json::json!("pass")),
            ]),
        }
    }

    #[test]
    fn build_job_creates_valid_job_with_owner_ref() {
        let na = test_network_assertion("my-job", vec![simple_http_rule()]);
        let config = test_config();
        let job = build_job(&na, &config).expect("should build job");

        assert_eq!(job.metadata.name.as_deref(), Some("my-job"));
        assert_eq!(job.metadata.namespace.as_deref(), Some("default"));

        let owner_refs = job.metadata.owner_references.as_ref().unwrap();
        assert_eq!(owner_refs.len(), 1);
        assert_eq!(owner_refs[0].name, "my-job");

        let annotations = job.metadata.annotations.as_ref().unwrap();
        assert_eq!(annotations["netchecks.io/spec-generation"], "1");
    }

    #[test]
    fn build_cron_job_creates_valid_cronjob() {
        let na = test_network_assertion("scheduled", vec![simple_http_rule()]);
        let config = test_config();
        let cron = build_cron_job(&na, &config, "*/5 * * * *").expect("should build cronjob");

        assert_eq!(cron.metadata.name.as_deref(), Some("scheduled"));
        let spec = cron.spec.as_ref().unwrap();
        assert_eq!(spec.schedule, "*/5 * * * *");
        assert!(spec.job_template.spec.is_some());
    }

    #[test]
    fn build_job_spec_mounts_config_volume() {
        let na = test_network_assertion("test", vec![simple_http_rule()]);
        let config = test_config();
        let job_spec = build_job_spec(&na, &config);

        let volumes = job_spec
            .template
            .spec
            .as_ref()
            .unwrap()
            .volumes
            .as_ref()
            .unwrap();
        assert!(volumes.iter().any(|v| v.name == "netcheck-rules"));

        let container = &job_spec.template.spec.as_ref().unwrap().containers[0];
        assert_eq!(container.name, "netcheck");
        assert_eq!(
            container.image.as_deref(),
            Some("ghcr.io/hardbyte/netchecks:test")
        );

        let mounts = container.volume_mounts.as_ref().unwrap();
        assert!(mounts
            .iter()
            .any(|m| m.name == "netcheck-rules" && m.mount_path == "/netcheck"));
    }

    #[test]
    fn build_job_spec_with_context_volumes() {
        let mut na = test_network_assertion("ctx-test", vec![simple_http_rule()]);
        na.spec.context = vec![
            ContextSpec {
                name: "my-cm".to_string(),
                config_map: Some(serde_json::json!({"name": "source-cm", "optional": true})),
                secret: None,
                inline: None,
            },
            ContextSpec {
                name: "my-secret".to_string(),
                config_map: None,
                secret: Some(serde_json::json!({"name": "source-secret"})),
                inline: None,
            },
            ContextSpec {
                name: "my-inline".to_string(),
                config_map: None,
                secret: None,
                inline: Some(serde_json::json!({"key": "val"})),
            },
        ];
        let config = test_config();
        let job_spec = build_job_spec(&na, &config);

        let volumes = job_spec
            .template
            .spec
            .as_ref()
            .unwrap()
            .volumes
            .as_ref()
            .unwrap();
        // netcheck-rules + my-cm + my-secret = 3 (inline doesn't get a volume)
        assert_eq!(volumes.len(), 3);
        assert!(volumes.iter().any(|v| v.name == "my-cm"));
        assert!(volumes.iter().any(|v| v.name == "my-secret"));

        // Check optional flag was preserved on ConfigMap volume
        let cm_vol = volumes.iter().find(|v| v.name == "my-cm").unwrap();
        assert_eq!(cm_vol.config_map.as_ref().unwrap().optional, Some(true));

        let mounts = job_spec.template.spec.as_ref().unwrap().containers[0]
            .volume_mounts
            .as_ref()
            .unwrap();
        assert!(mounts.iter().any(|m| m.mount_path == "/mnt/my-cm"));
        assert!(mounts.iter().any(|m| m.mount_path == "/mnt/my-secret"));
    }

    #[test]
    fn build_job_spec_disable_redaction_flag() {
        let mut na = test_network_assertion("redact-test", vec![simple_http_rule()]);
        na.spec.disable_redaction = true;
        let config = test_config();
        let job_spec = build_job_spec(&na, &config);

        let command = job_spec.template.spec.as_ref().unwrap().containers[0]
            .command
            .as_ref()
            .unwrap();
        assert!(command.contains(&"--disable-redaction".to_string()));
    }

    #[test]
    fn template_overrides_node_selector() {
        let mut template = PodTemplateSpec {
            metadata: None,
            spec: Some(PodSpec {
                containers: vec![],
                ..Default::default()
            }),
        };

        let overrides = serde_json::json!({
            "spec": {
                "nodeSelector": {"disktype": "ssd", "region": "us-east"}
            }
        });

        apply_template_overrides(&mut template, &overrides);
        let node_selector = template
            .spec
            .as_ref()
            .unwrap()
            .node_selector
            .as_ref()
            .unwrap();
        assert_eq!(node_selector["disktype"], "ssd");
        assert_eq!(node_selector["region"], "us-east");
    }

    #[test]
    fn summarize_results_empty_assertions() {
        let probe_results = serde_json::json!({"assertions": []});
        let summary = summarize_results(&probe_results);
        assert!(summary.as_object().unwrap().is_empty());
    }

    #[test]
    fn summarize_results_missing_assertions_key() {
        let probe_results = serde_json::json!({});
        let summary = summarize_results(&probe_results);
        assert!(summary.as_object().unwrap().is_empty());
    }

    #[test]
    fn convert_results_multiple_assertions() {
        let probe_results = serde_json::json!({
            "assertions": [
                {"name": "a1", "results": [{"status": "pass", "spec": {"type": "http"}, "data": {}}]},
                {"name": "a2", "results": [
                    {"status": "fail", "spec": {"type": "dns"}, "data": {}},
                    {"status": "pass", "spec": {"type": "dns"}, "data": {}}
                ]}
            ]
        });
        let results = convert_results_for_policy_report(&probe_results);
        assert_eq!(results.len(), 3);
        assert_eq!(results[0]["policy"], "a1");
        assert_eq!(results[1]["policy"], "a2");
        assert_eq!(results[2]["policy"], "a2");
    }

    #[test]
    fn transform_rule_preserves_fields() {
        let rule = Rule {
            name: "test".to_string(),
            fields: BTreeMap::from([
                ("type".to_string(), serde_json::json!("http")),
                ("url".to_string(), serde_json::json!("https://example.com")),
                ("expected".to_string(), serde_json::json!("pass")),
            ]),
        };

        let transformed = transform_rule_for_config(&rule);
        assert_eq!(transformed["name"], "test");
        assert_eq!(transformed["type"], "http");
        assert_eq!(transformed["url"], "https://example.com");
    }

    #[test]
    fn transform_rule_moves_validate_pattern_to_validation() {
        let rule = Rule {
            name: "test".to_string(),
            fields: BTreeMap::from([
                ("type".to_string(), serde_json::json!("http")),
                (
                    "validate".to_string(),
                    serde_json::json!({
                        "message": "Should work",
                        "pattern": {"status": "pass"}
                    }),
                ),
            ]),
        };

        let transformed = transform_rule_for_config(&rule);
        assert_eq!(transformed["validation"]["status"], "pass");
        assert!(transformed["validate"]
            .as_object()
            .unwrap()
            .get("pattern")
            .is_none());
        assert_eq!(transformed["validate"]["message"], "Should work");
    }

    #[test]
    fn transform_context_configmap() {
        let ctx = ContextSpec {
            name: "my-config".to_string(),
            config_map: Some(serde_json::json!({"name": "cm-name"})),
            secret: None,
            inline: None,
        };

        let transformed = transform_context_for_config(&ctx);
        assert_eq!(transformed["name"], "my-config");
        assert_eq!(transformed["type"], "directory");
        assert_eq!(transformed["path"], "/mnt/my-config");
    }

    #[test]
    fn transform_context_secret() {
        let ctx = ContextSpec {
            name: "my-secret".to_string(),
            config_map: None,
            secret: Some(serde_json::json!({"name": "secret-name"})),
            inline: None,
        };

        let transformed = transform_context_for_config(&ctx);
        assert_eq!(transformed["type"], "directory");
        assert_eq!(transformed["path"], "/mnt/my-secret");
    }

    #[test]
    fn transform_context_inline() {
        let ctx = ContextSpec {
            name: "inline-data".to_string(),
            config_map: None,
            secret: None,
            inline: Some(serde_json::json!({"key": "value"})),
        };

        let transformed = transform_context_for_config(&ctx);
        assert_eq!(transformed["type"], "inline");
        assert_eq!(transformed["data"]["key"], "value");
    }

    #[test]
    fn build_cli_config_structure() {
        let rules = vec![Rule {
            name: "test-rule".to_string(),
            fields: BTreeMap::from([
                ("type".to_string(), serde_json::json!("http")),
                ("url".to_string(), serde_json::json!("https://example.com")),
            ]),
        }];
        let contexts = vec![ContextSpec {
            name: "ctx".to_string(),
            config_map: Some(serde_json::json!({"name": "cm"})),
            secret: None,
            inline: None,
        }];

        let config = build_cli_config(&rules, &contexts);
        assert!(config.get("assertions").is_some());
        assert!(config.get("contexts").is_some());
        assert_eq!(config["assertions"].as_array().unwrap().len(), 1);
        assert_eq!(config["contexts"].as_array().unwrap().len(), 1);
    }

    #[test]
    fn summarize_results_counts_correctly() {
        let probe_results = serde_json::json!({
            "assertions": [
                {
                    "name": "test",
                    "results": [
                        {"status": "pass"},
                        {"status": "pass"},
                        {"status": "fail"},
                        {"status": "warn"},
                    ]
                }
            ]
        });

        let summary = summarize_results(&probe_results);
        assert_eq!(summary["pass"], 2);
        assert_eq!(summary["fail"], 1);
        assert_eq!(summary["warn"], 1);
        assert!(summary.get("error").is_none());
        assert!(summary.get("skip").is_none());
    }

    #[test]
    fn summarize_results_unknown_status_counted_as_skip() {
        let probe_results = serde_json::json!({
            "assertions": [{"name": "t", "results": [{"status": "unknown"}]}]
        });
        let summary = summarize_results(&probe_results);
        assert_eq!(summary["skip"], 1);
    }

    #[test]
    fn summarize_results_missing_status_counted_as_skip() {
        let probe_results = serde_json::json!({
            "assertions": [{"name": "t", "results": [{}]}]
        });
        let summary = summarize_results(&probe_results);
        assert_eq!(summary["skip"], 1);
    }

    #[test]
    fn convert_results_creates_policy_report_entries() {
        let probe_results = serde_json::json!({
            "assertions": [
                {
                    "name": "http-test",
                    "results": [
                        {
                            "name": "rule-1",
                            "status": "pass",
                            "message": "HTTP check passed",
                            "spec": {"type": "http", "url": "https://example.com"},
                            "data": {
                                "startTimestamp": "2024-01-01T00:00:00+00:00",
                                "endTimestamp": "2024-01-01T00:00:01+00:00"
                            }
                        }
                    ]
                }
            ]
        });

        let results = convert_results_for_policy_report(&probe_results);
        assert_eq!(results.len(), 1);
        assert_eq!(results[0]["source"], "netchecks");
        assert_eq!(results[0]["policy"], "http-test");
        assert_eq!(results[0]["rule"], "rule-1");
        assert_eq!(results[0]["category"], "http");
        assert_eq!(results[0]["result"], "pass");
        assert!(results[0]["timestamp"].is_object());
    }

    #[test]
    fn convert_results_generates_rule_name_when_missing() {
        let probe_results = serde_json::json!({
            "assertions": [
                {"name": "test", "results": [{"status": "pass", "spec": {"type": "http"}, "data": {}}]}
            ]
        });

        let results = convert_results_for_policy_report(&probe_results);
        assert_eq!(results[0]["rule"], "test-rule-1");
    }

    #[test]
    fn convert_iso_timestamp_rfc3339() {
        let ts = convert_iso_timestamp("2024-01-01T00:00:00+00:00");
        assert_eq!(ts["seconds"], 1704067200);
        assert_eq!(ts["nanos"], 0);
    }

    #[test]
    fn convert_iso_timestamp_naive() {
        let ts = convert_iso_timestamp("2024-01-01T00:00:00.000");
        assert_eq!(ts["nanos"], 0);
        // Exact seconds depend on UTC interpretation
        assert!(ts["seconds"].as_i64().unwrap() > 0);
    }

    #[test]
    fn convert_iso_timestamp_invalid_returns_zero() {
        let ts = convert_iso_timestamp("not-a-timestamp");
        assert_eq!(ts["seconds"], 0);
    }

    #[test]
    fn template_overrides_merge_labels() {
        let mut template = PodTemplateSpec {
            metadata: Some(ObjectMeta {
                labels: Some(BTreeMap::from([(
                    "existing".to_string(),
                    "label".to_string(),
                )])),
                ..Default::default()
            }),
            spec: Some(PodSpec {
                containers: vec![],
                ..Default::default()
            }),
        };

        let overrides = serde_json::json!({
            "metadata": {
                "labels": {"new-label": "value"},
                "annotations": {"my": "annotation"}
            }
        });

        apply_template_overrides(&mut template, &overrides);

        let labels = template.metadata.as_ref().unwrap().labels.as_ref().unwrap();
        assert_eq!(labels["existing"], "label");
        assert_eq!(labels["new-label"], "value");

        let annotations = template
            .metadata
            .as_ref()
            .unwrap()
            .annotations
            .as_ref()
            .unwrap();
        assert_eq!(annotations["my"], "annotation");
    }

    #[test]
    fn template_overrides_service_account() {
        let mut template = PodTemplateSpec {
            metadata: None,
            spec: Some(PodSpec {
                containers: vec![],
                ..Default::default()
            }),
        };

        let overrides = serde_json::json!({
            "spec": {"serviceAccountName": "my-sa"}
        });

        apply_template_overrides(&mut template, &overrides);
        assert_eq!(
            template.spec.as_ref().unwrap().service_account_name,
            Some("my-sa".to_string())
        );
    }
}
