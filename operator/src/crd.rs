//! NetworkAssertion custom resource definition and helper types.

use std::collections::BTreeMap;

use kube::CustomResource;
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

/// Spec for a NetworkAssertion custom resource.
#[derive(CustomResource, Debug, Clone, Serialize, Deserialize, JsonSchema)]
#[kube(
    group = "netchecks.io",
    version = "v1",
    kind = "NetworkAssertion",
    namespaced,
    status = "NetworkAssertionStatus",
    shortname = "nas",
    printcolumn = r#"{"name": "Schedule", "type": "string", "jsonPath": ".spec.schedule"}"#,
    printcolumn = r#"{"name": "Ready", "type": "string", "jsonPath": ".status.conditions[?(@.type==\"Reconciled\")].status"}"#,
    printcolumn = r#"{"name": "Reason", "type": "string", "jsonPath": ".status.conditions[?(@.type==\"Reconciled\")].reason"}"#,
    printcolumn = r#"{"name": "Status", "type": "string", "jsonPath": ".status.conditions[?(@.type==\"Reconciled\")].message", "priority": 1}"#
)]
pub struct NetworkAssertionSpec {
    /// Network assertion rules to evaluate.
    pub rules: Vec<Rule>,

    /// Optional cron schedule. If set, a CronJob is created; otherwise a one-time Job.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub schedule: Option<String>,

    /// Context data sources (ConfigMaps, Secrets, or inline data).
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub context: Vec<ContextSpec>,

    /// Optional pod template overrides for the probe job.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub template: Option<serde_json::Value>,

    /// Disable output redaction in probe results.
    #[serde(default, rename = "disableRedaction")]
    pub disable_redaction: bool,
}

/// A network assertion rule (http, dns, or tcp check).
///
/// The `name` field is required. All other rule fields (type, url, host, port,
/// headers, expected, validate, etc.) are captured in `fields` via serde flatten.
#[derive(Debug, Clone, Serialize, Deserialize, JsonSchema)]
pub struct Rule {
    /// Name of this rule.
    pub name: String,

    /// All other rule fields (type, url, host, port, verify-tls, expected, validate, etc.).
    #[serde(flatten)]
    pub fields: BTreeMap<String, serde_json::Value>,
}

/// Context data source specification.
#[derive(Debug, Clone, Serialize, Deserialize, JsonSchema)]
pub struct ContextSpec {
    /// Name for this context, used as the volume mount name.
    pub name: String,

    /// Reference to a ConfigMap.
    #[serde(default, rename = "configMap", skip_serializing_if = "Option::is_none")]
    pub config_map: Option<serde_json::Value>,

    /// Reference to a Secret.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub secret: Option<serde_json::Value>,

    /// Inline data.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub inline: Option<serde_json::Value>,
}

/// Status of a NetworkAssertion — updated by the operator on each reconciliation.
///
/// Conditions follow the standard Kubernetes convention:
/// - `Reconciled=True`  — operator successfully reconciled; results may be available
/// - `Reconciled=False` — reconciliation failed (see reason/message)
/// - `Reconciled=Unknown` — probe running, waiting for results
#[derive(Debug, Clone, Serialize, Deserialize, JsonSchema, Default)]
pub struct NetworkAssertionStatus {
    /// Generation that was last successfully reconciled.
    #[serde(
        default,
        skip_serializing_if = "Option::is_none",
        rename = "observedGeneration"
    )]
    pub observed_generation: Option<i64>,

    /// Name of the Job or CronJob managing this assertion.
    #[serde(default, skip_serializing_if = "Option::is_none", rename = "jobName")]
    pub job_name: Option<String>,

    /// Standard Kubernetes-style conditions.
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub conditions: Vec<StatusCondition>,

    /// Summary of the latest probe results (pass/fail/warn/error/skip counts).
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub summary: Option<serde_json::Value>,
}

/// A Kubernetes-style status condition.
#[derive(Debug, Clone, Serialize, Deserialize, JsonSchema, PartialEq)]
pub struct StatusCondition {
    /// Condition type, e.g. "Reconciled".
    #[serde(rename = "type")]
    pub condition_type: String,

    /// "True", "False", or "Unknown".
    pub status: String,

    /// Machine-readable reason (PascalCase).
    pub reason: String,

    /// Human-readable description.
    pub message: String,

    /// RFC 3339 timestamp of the last status transition.
    #[serde(rename = "lastTransitionTime")]
    pub last_transition_time: String,
}

/// Standard labels applied to all resources created by the operator.
pub fn common_labels(instance_name: &str) -> BTreeMap<String, String> {
    BTreeMap::from([
        (
            "app.kubernetes.io/name".to_string(),
            "netchecks".to_string(),
        ),
        (
            "app.kubernetes.io/version".to_string(),
            env!("CARGO_PKG_VERSION").to_string(),
        ),
        (
            "app.kubernetes.io/instance".to_string(),
            instance_name.to_string(),
        ),
    ])
}

/// Label selector string for resources belonging to a given assertion.
pub fn label_selector(instance_name: &str) -> String {
    format!(
        "app.kubernetes.io/name=netchecks,app.kubernetes.io/instance={}",
        instance_name
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn deserialize_http_rule() {
        let json = serde_json::json!({
            "name": "test-http",
            "type": "http",
            "url": "https://example.com",
            "verify-tls": false,
            "expected": "pass",
            "validate": {
                "message": "Should succeed"
            }
        });
        let rule: Rule = serde_json::from_value(json).unwrap();
        assert_eq!(rule.name, "test-http");
        assert_eq!(rule.fields.get("type").unwrap(), "http");
        assert_eq!(rule.fields.get("url").unwrap(), "https://example.com");
    }

    #[test]
    fn deserialize_dns_rule() {
        let json = serde_json::json!({
            "name": "dns-check",
            "type": "dns",
            "server": "1.1.1.1",
            "host": "github.com",
            "expected": "pass"
        });
        let rule: Rule = serde_json::from_value(json).unwrap();
        assert_eq!(rule.name, "dns-check");
        assert_eq!(rule.fields.get("type").unwrap(), "dns");
        assert_eq!(rule.fields.get("server").unwrap(), "1.1.1.1");
    }

    #[test]
    fn deserialize_tcp_rule() {
        let json = serde_json::json!({
            "name": "tcp-check",
            "type": "tcp",
            "host": "kubernetes.default.svc",
            "port": 443,
            "expected": "pass"
        });
        let rule: Rule = serde_json::from_value(json).unwrap();
        assert_eq!(rule.name, "tcp-check");
        assert_eq!(rule.fields.get("port").unwrap(), 443);
    }

    #[test]
    fn deserialize_full_spec() {
        let json = serde_json::json!({
            "rules": [
                {"name": "r1", "type": "http", "url": "https://example.com"}
            ],
            "schedule": "@hourly",
            "context": [
                {"name": "ctx1", "configMap": {"name": "my-config"}}
            ]
        });
        let spec: NetworkAssertionSpec = serde_json::from_value(json).unwrap();
        assert_eq!(spec.rules.len(), 1);
        assert_eq!(spec.schedule.as_deref(), Some("@hourly"));
        assert_eq!(spec.context.len(), 1);
        assert!(!spec.disable_redaction);
    }

    #[test]
    fn deserialize_spec_with_inline_context() {
        let json = serde_json::json!({
            "rules": [{"name": "r1", "type": "http", "url": "https://example.com"}],
            "context": [
                {"name": "inline-data", "inline": {"key": "value", "other": "data"}}
            ]
        });
        let spec: NetworkAssertionSpec = serde_json::from_value(json).unwrap();
        assert_eq!(spec.context[0].name, "inline-data");
        assert!(spec.context[0].inline.is_some());
        assert!(spec.context[0].config_map.is_none());
    }

    #[test]
    fn deserialize_spec_with_secret_context() {
        let json = serde_json::json!({
            "rules": [{"name": "r1"}],
            "context": [
                {"name": "secret-data", "secret": {"name": "my-secret"}}
            ]
        });
        let spec: NetworkAssertionSpec = serde_json::from_value(json).unwrap();
        assert!(spec.context[0].secret.is_some());
    }

    #[test]
    fn deserialize_spec_with_disable_redaction() {
        let json = serde_json::json!({
            "rules": [{"name": "r1"}],
            "disableRedaction": true
        });
        let spec: NetworkAssertionSpec = serde_json::from_value(json).unwrap();
        assert!(spec.disable_redaction);
    }

    #[test]
    fn common_labels_include_required_fields() {
        let labels = common_labels("my-assertion");
        assert_eq!(labels["app.kubernetes.io/name"], "netchecks");
        assert_eq!(labels["app.kubernetes.io/instance"], "my-assertion");
        assert!(labels.contains_key("app.kubernetes.io/version"));
    }

    #[test]
    fn rule_roundtrip_preserves_all_fields() {
        let json = serde_json::json!({
            "name": "test",
            "type": "http",
            "url": "https://example.com",
            "verify-tls-cert": false,
            "headers": {"Authorization": "Bearer token"},
            "expected": "pass",
            "validate": {"message": "Should work"}
        });
        let rule: Rule = serde_json::from_value(json.clone()).unwrap();
        let roundtripped = serde_json::to_value(&rule).unwrap();
        assert_eq!(json, roundtripped);
    }
}
