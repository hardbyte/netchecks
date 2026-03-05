---
title: Compliance Reporting
description: Generate audit-ready compliance reports from netchecks test results.
---

# Compliance Reporting

**netchecks-compliance** is a paid add-on that takes netchecks `PolicyReport` results and produces
compliance reports mapped to specific framework controls. The output is evidence an auditor can
directly reference in a SOC 2 Type 2 report or PCI-DSS ROC.

## The Problem

Organizations running Kubernetes need to prove their network security controls actually work — not
just that policies exist. Every KSPM tool checks whether `NetworkPolicy` objects exist and are
correctly configured. None of them verify that traffic is actually blocked in practice.

Netchecks fills the testing gap — it actively sends traffic and validates results. **netchecks-compliance**
bridges those test results to auditor-ready compliance evidence.

## Supported Frameworks

| Framework | Key Controls | Tier |
|---|---|---|
| **CIS Kubernetes Benchmark** | 5.3.1, 5.3.2 | Community (Free) |
| **PCI-DSS v4.0** | 1.2.1, 1.3.2, 11.3.4, 11.3.4.1 | Pro |
| **SOC 2 Type II** | CC6.6, CC6.7, CC7.1 | Pro |

## Output Formats

| Format | Use Case |
|---|---|
| **PDF** | Hand to auditor. Print-ready. Primary deliverable. |
| **HTML** | Self-contained single-file. View in browser. Share internally. |
| **JSON** | GRC platform integration (Vanta, Drata, Secureframe). |

## How It Works

1. **Annotate** your `NetworkAssertion` resources with [compliance annotations](/docs/compliance-annotations)
   to map tests to compliance framework controls.
2. The netchecks operator runs the tests as usual, producing `PolicyReport` resources.
3. **netchecks-compliance** reads both the `NetworkAssertion` annotations and `PolicyReport` results,
   maps them to framework controls, and generates a compliance report.

Reports include:
- **Executive summary** — overall compliance posture (X/Y controls passing), critical findings
- **Per-control detail** — control ID, description, status (PASS/FAIL/NOT_ASSESSED), evidence count,
  last tested timestamp, mapped NetworkAssertions, finding details
- **Attestation footer** — tool version, SHA-256 integrity hash, automation statement

## Example Report

![CIS Kubernetes Benchmark Compliance Report](/images/compliance/cis-report-example.png)

## Quick Start

```bash
pip install netchecks-compliance

# Free CIS report (no license required)
netchecks-compliance report \
  --framework cis-k8s \
  --format pdf \
  --output cis-report.pdf

# PCI-DSS report (requires Pro license)
netchecks-compliance report \
  --framework pci-dss-v4 \
  --namespace payments \
  --format pdf \
  --output pci-report.pdf \
  --license license.jwt \
  --organization "Acme Corp" \
  --environment "Production"

# List available frameworks and controls
netchecks-compliance frameworks
```

## Pricing

| Tier | What's Included |
|---|---|
| **Community (Free)** | CIS Kubernetes Benchmark reports. PDF + HTML + JSON output. CLI generation. |
| **Pro ($99/month or $999/year)** | All frameworks. PDF + HTML + JSON. Up to 5 clusters. |
| **Enterprise (custom)** | Unlimited clusters. Custom frameworks. OSCAL output. |

Contact [brian@hardbyte.nz](mailto:brian@hardbyte.nz) for Enterprise licenses.

## Next Steps

- [Compliance Annotations](/docs/compliance-annotations) — how to annotate your NetworkAssertions
- [Example manifests](https://github.com/hardbyte/netchecks/tree/main/operator/examples/compliance) — PCI-DSS, SOC 2, and CIS example NetworkAssertions
- [Architecture Guide](/docs/architecture-guide) — how netchecks works end-to-end
