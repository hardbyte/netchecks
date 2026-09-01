//! Shared operator context — configuration, Kubernetes client, and observability.

use k8s_openapi::api::core::v1::ResourceRequirements;
use kube::discovery::ApiResource;
use tokio::sync::OnceCell;

use crate::observability::OperatorObservability;

/// API group of the PolicyReport CRDs the operator writes its results to.
pub const POLICY_REPORT_GROUP: &str = "wgpolicyk8s.io";
/// Kind of the report resource written per NetworkAssertion.
pub const POLICY_REPORT_KIND: &str = "PolicyReport";
/// Versions the operator knows how to write, most preferred first. The report
/// fields netchecks uses (`results`, `summary`, `scope`) are identical across
/// them, so any served version works.
const POLICY_REPORT_VERSION_PREFERENCE: [&str; 3] = ["v1beta1", "v1alpha2", "v1alpha1"];

/// Errors resolving the PolicyReport API on the cluster.
#[derive(Debug, thiserror::Error)]
pub enum DiscoveryError {
    #[error(
        "the {POLICY_REPORT_GROUP} API group is not served by this cluster; install the \
         PolicyReport CRDs or enable `crds.groups.wgpolicyk8s` in the Helm chart"
    )]
    GroupMissing,

    #[error(
        "the {POLICY_REPORT_GROUP} API group is served (versions: {0}) but none of them \
         provides the {POLICY_REPORT_KIND} kind"
    )]
    KindMissing(String),

    #[error("failed to discover the {POLICY_REPORT_GROUP} API group: {0}")]
    Kube(#[from] kube::Error),
}

/// Pick the PolicyReport version to write, given the versions the cluster serves.
///
/// Prefers the operator's known versions in order, then the group's preferred
/// version, then whatever is served first.
pub fn select_policy_report_version<'a>(served: &[&'a str], preferred: &'a str) -> Option<&'a str> {
    POLICY_REPORT_VERSION_PREFERENCE
        .iter()
        .find_map(|wanted| served.iter().find(|v| *v == wanted).copied())
        .or_else(|| served.iter().find(|v| **v == preferred).copied())
        .or_else(|| served.first().copied())
}

/// Resolve the `PolicyReport` API resource from cluster discovery.
///
/// `wgpolicyk8s.io` is a shared API group whose CRDs are distributed by several
/// projects (netchecks, Kyverno, Trivy, Kubescape, ...) that serve different
/// version sets, so the version must not be hardcoded.
pub async fn discover_policy_report_resource(
    client: &kube::Client,
) -> Result<ApiResource, DiscoveryError> {
    let group = match kube::discovery::group(client, POLICY_REPORT_GROUP).await {
        Ok(group) => group,
        Err(kube::Error::Api(err)) if err.code == 404 => return Err(DiscoveryError::GroupMissing),
        Err(err) => return Err(DiscoveryError::Kube(err)),
    };

    let served: Vec<&str> = group.versions().collect();
    let has_kind = |version: &str| {
        group
            .versioned_resources(version)
            .into_iter()
            .find(|(ar, _)| ar.kind == POLICY_REPORT_KIND)
            .map(|(ar, _)| ar)
    };

    // Preferred version first, then any other served version that has the kind.
    select_policy_report_version(&served, group.preferred_version_or_latest())
        .and_then(has_kind)
        .or_else(|| served.iter().find_map(|version| has_kind(version)))
        .ok_or_else(|| DiscoveryError::KindMissing(served.join(", ")))
}

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
    /// PolicyReport API resource, discovered from the cluster on first use.
    policy_report_resource: OnceCell<ApiResource>,
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
            policy_report_resource: OnceCell::new(),
        }
    }

    /// The PolicyReport API resource served by this cluster.
    ///
    /// Discovered once and cached; a failed discovery is not cached so that a
    /// CRD installed after the operator started is picked up on the next call.
    pub async fn policy_report_resource(&self) -> Result<&ApiResource, DiscoveryError> {
        self.policy_report_resource
            .get_or_try_init(|| async {
                let resource = discover_policy_report_resource(&self.kube_client).await?;
                tracing::info!(
                    api_version = %resource.api_version,
                    "resolved PolicyReport API version from cluster discovery"
                );
                Ok(resource)
            })
            .await
    }
}

#[cfg(test)]
mod tests {
    use std::sync::Mutex;

    use super::*;

    static ENV_LOCK: Mutex<()> = Mutex::new(());

    #[test]
    fn policy_report_version_prefers_v1beta1() {
        let served = ["v1alpha1", "v1alpha2", "v1beta1"];
        assert_eq!(
            select_policy_report_version(&served, "v1alpha2"),
            Some("v1beta1")
        );
    }

    #[test]
    fn policy_report_version_falls_back_to_kyverno_v1alpha2() {
        // Kyverno's CRDs serve only v1alpha2.
        assert_eq!(
            select_policy_report_version(&["v1alpha2"], "v1alpha2"),
            Some("v1alpha2")
        );
    }

    #[test]
    fn policy_report_version_uses_group_preference_for_unknown_versions() {
        assert_eq!(
            select_policy_report_version(&["v2", "v1"], "v1"),
            Some("v1")
        );
        assert_eq!(
            select_policy_report_version(&["v2", "v3"], "v9"),
            Some("v2")
        );
        assert_eq!(select_policy_report_version(&[], "v1"), None);
    }

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
