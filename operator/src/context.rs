//! Shared operator context — configuration, Kubernetes client, and observability.

use k8s_openapi::api::core::v1::ResourceRequirements;

use crate::observability::OperatorObservability;

/// Operator configuration loaded from environment variables.
#[derive(Clone, Debug)]
pub struct OperatorConfig {
    /// Container image repository for the netchecks probe.
    pub probe_image_repository: String,
    /// Container image tag for the netchecks probe.
    pub probe_image_tag: String,
    /// Image pull policy for the probe container.
    pub probe_image_pull_policy: String,
    /// Default resource requests/limits applied to probe containers.
    /// `None` means no resources stanza is set on created Jobs (cluster default).
    pub probe_resources: Option<ResourceRequirements>,
    /// Maximum number of results stored in a PolicyReport.
    pub policy_report_max_results: usize,
}

impl OperatorConfig {
    /// Load configuration from environment variables with sensible defaults.
    pub fn from_env() -> Self {
        Self {
            probe_image_repository: std::env::var("PROBE_IMAGE_REPOSITORY")
                .unwrap_or_else(|_| "ghcr.io/hardbyte/netchecks".to_string()),
            probe_image_tag: std::env::var("PROBE_IMAGE_TAG")
                .unwrap_or_else(|_| "main".to_string()),
            probe_image_pull_policy: std::env::var("PROBE_IMAGE_PULL_POLICY")
                .unwrap_or_else(|_| "IfNotPresent".to_string()),
            probe_resources: parse_probe_resources(),
            policy_report_max_results: std::env::var("POLICY_REPORT_MAX_RESULTS")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or(1000),
        }
    }
}

/// Parse `PROBE_RESOURCES` (JSON-encoded `ResourceRequirements`) from the
/// environment. Empty / unset / `{}` returns `None`; malformed JSON is logged
/// and treated as unset so a typo in Helm values can't crash-loop the operator.
fn parse_probe_resources() -> Option<ResourceRequirements> {
    let raw = std::env::var("PROBE_RESOURCES").ok()?;
    let trimmed = raw.trim();
    if trimmed.is_empty() || trimmed == "{}" {
        return None;
    }
    match serde_json::from_str::<ResourceRequirements>(trimmed) {
        Ok(rr) => Some(rr),
        Err(err) => {
            tracing::warn!(
                error = %err,
                "PROBE_RESOURCES is not valid JSON ResourceRequirements; ignoring"
            );
            None
        }
    }
}

/// Shared state for the operator, passed to every reconciliation.
pub struct OperatorContext {
    /// Kubernetes client for API calls.
    pub kube_client: kube::Client,
    /// Operator configuration.
    pub config: OperatorConfig,
    /// Health and metrics state.
    pub observability: OperatorObservability,
}

impl OperatorContext {
    pub fn new(
        kube_client: kube::Client,
        config: OperatorConfig,
        observability: OperatorObservability,
    ) -> Self {
        Self {
            kube_client,
            config,
            observability,
        }
    }
}

#[cfg(test)]
mod tests {
    use std::sync::Mutex;

    use super::*;

    static ENV_LOCK: Mutex<()> = Mutex::new(());

    #[test]
    fn config_defaults_are_reasonable() {
        let _guard = ENV_LOCK.lock().expect("env lock");
        // Clear relevant env vars for test isolation
        unsafe {
            std::env::remove_var("PROBE_IMAGE_REPOSITORY");
            std::env::remove_var("PROBE_IMAGE_TAG");
            std::env::remove_var("PROBE_IMAGE_PULL_POLICY");
            std::env::remove_var("PROBE_RESOURCES");
            std::env::remove_var("POLICY_REPORT_MAX_RESULTS");
        }
        let config = OperatorConfig::from_env();
        assert_eq!(config.probe_image_repository, "ghcr.io/hardbyte/netchecks");
        assert_eq!(config.probe_image_tag, "main");
        assert_eq!(config.probe_image_pull_policy, "IfNotPresent");
        assert!(config.probe_resources.is_none());
        assert_eq!(config.policy_report_max_results, 1000);
    }

    #[test]
    fn probe_resources_parses_valid_json() {
        let _guard = ENV_LOCK.lock().expect("env lock");
        unsafe {
            std::env::set_var(
                "PROBE_RESOURCES",
                r#"{"requests":{"cpu":"20m","memory":"64Mi"},"limits":{"cpu":"100m","memory":"128Mi"}}"#,
            );
        }
        let config = OperatorConfig::from_env();
        let rr = config.probe_resources.expect("probe_resources set");
        assert_eq!(
            rr.requests
                .as_ref()
                .and_then(|m| m.get("cpu"))
                .map(|q| q.0.as_str()),
            Some("20m")
        );
        assert_eq!(
            rr.limits
                .as_ref()
                .and_then(|m| m.get("memory"))
                .map(|q| q.0.as_str()),
            Some("128Mi")
        );
        unsafe {
            std::env::remove_var("PROBE_RESOURCES");
        }
    }

    #[test]
    fn probe_resources_empty_object_is_none() {
        let _guard = ENV_LOCK.lock().expect("env lock");
        unsafe {
            std::env::set_var("PROBE_RESOURCES", "{}");
        }
        let config = OperatorConfig::from_env();
        assert!(config.probe_resources.is_none());
        unsafe {
            std::env::remove_var("PROBE_RESOURCES");
        }
    }

    #[test]
    fn probe_resources_malformed_is_ignored() {
        let _guard = ENV_LOCK.lock().expect("env lock");
        unsafe {
            std::env::set_var("PROBE_RESOURCES", "not-json");
        }
        let config = OperatorConfig::from_env();
        assert!(config.probe_resources.is_none());
        unsafe {
            std::env::remove_var("PROBE_RESOURCES");
        }
    }

    #[test]
    fn config_from_env_uses_overrides() {
        let _guard = ENV_LOCK.lock().expect("env lock");
        unsafe {
            std::env::set_var("PROBE_IMAGE_REPOSITORY", "custom/repo");
            std::env::set_var("PROBE_IMAGE_TAG", "v1.2.3");
            std::env::set_var("PROBE_IMAGE_PULL_POLICY", "Always");
            std::env::set_var("POLICY_REPORT_MAX_RESULTS", "50");
        }
        let config = OperatorConfig::from_env();
        assert_eq!(config.probe_image_repository, "custom/repo");
        assert_eq!(config.probe_image_tag, "v1.2.3");
        assert_eq!(config.probe_image_pull_policy, "Always");
        assert_eq!(config.policy_report_max_results, 50);
        unsafe {
            std::env::remove_var("PROBE_IMAGE_REPOSITORY");
            std::env::remove_var("PROBE_IMAGE_TAG");
            std::env::remove_var("PROBE_IMAGE_PULL_POLICY");
            std::env::remove_var("POLICY_REPORT_MAX_RESULTS");
        }
    }

    #[test]
    fn config_invalid_max_results_falls_back_to_default() {
        let _guard = ENV_LOCK.lock().expect("env lock");
        unsafe {
            std::env::set_var("POLICY_REPORT_MAX_RESULTS", "not-a-number");
        }
        let config = OperatorConfig::from_env();
        assert_eq!(config.policy_report_max_results, 1000);
        unsafe {
            std::env::remove_var("POLICY_REPORT_MAX_RESULTS");
        }
    }
}
