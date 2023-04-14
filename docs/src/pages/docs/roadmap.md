---
title: Roadmap
description: Where is netchecks heading?
---



{% callout type="note" title="Unstable" %}

The project roadmap is still being defined. The following is a list of features that are likely to be considered for implementation in the near future.

{% /callout %}

## Open Source

- Document the custom validation rules for probes (e.g. check that the response body contains a specific string)
- Support for configuring probes using secrets (e.g. injecting API keys into http requests)
- NetworkAssertion CRD validation and documentation.
- Tracing support for better debugging.
- Plugin architecture for supporting custom test types.
- Full CI integration test suite across managed Kubernetes providers.
- The option to run certain probes on matching Nodes via DaemonSets instead of CronJobs.
- PolicyReporter plugin to better expose NetworkAssertion results.
- Example of alert manager integration
- Grafana dashboard

## Enterprise

- Exporting reports
- externally executed probes from hosted service. Run tests from the internet (can I access some internal service, locked down S3 bucket etc). UI for creating and managing tests.
- Curated network assertions for standard enterprise policies.
- Integration with enterprise security tools (e.g. Splunk, Sumo Logic, etc)
- Is this S3 bucket accessible with this role?
- Run on demand - after a change/release?
- License available on AWS Marketplace and/or Github Marketplace
- Hardened distro for enterprise.
- Long term support/Service level agreements.
- commercial plugin ecosystem could also be explored.
- Operator dashboard

## Longer term

- Using netchecks outside k8s - e.g. to test “Container as a service” and “Function as a service” systems.
- Netchecks on the edge - e.g. to test IoT devices.
- Netchecks on end user devices - e.g. to test mobile apps.
