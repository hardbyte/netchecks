//! netchecks-operator — Kubernetes controller for NetworkAssertion CRDs.
//!
//! Watches `NetworkAssertion` custom resources and reconciles them into
//! probe Jobs (or CronJobs), then collects results into PolicyReports.

pub mod context;
pub mod crd;
pub mod observability;
pub mod reconciler;
