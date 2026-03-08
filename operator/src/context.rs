//! Shared operator context — configuration, Kubernetes client, and observability.

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
            policy_report_max_results: std::env::var("POLICY_REPORT_MAX_RESULTS")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or(1000),
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
    use super::*;

    #[test]
    fn config_defaults_are_reasonable() {
        // Clear relevant env vars for test isolation
        let config = OperatorConfig {
            probe_image_repository: "ghcr.io/hardbyte/netchecks".to_string(),
            probe_image_tag: "main".to_string(),
            probe_image_pull_policy: "IfNotPresent".to_string(),
            policy_report_max_results: 1000,
        };
        assert_eq!(config.probe_image_repository, "ghcr.io/hardbyte/netchecks");
        assert_eq!(config.probe_image_tag, "main");
        assert_eq!(config.probe_image_pull_policy, "IfNotPresent");
        assert_eq!(config.policy_report_max_results, 1000);
    }
}
