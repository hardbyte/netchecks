---
title: Compliance annotations
description: Annotate NetworkAssertions with compliance framework control IDs for audit-ready reporting.
---

# Compliance Annotations

Netchecks supports compliance annotations on `NetworkAssertion` resources. These annotations map
your active network tests to specific compliance framework controls, enabling automated generation
of audit-ready compliance reports via [netchecks-compliance](/docs/compliance-reporting).

## Supported Annotations

| Annotation | Description | Example |
|---|---|---|
| `netchecks.io/controls` | Comma-separated list of compliance control IDs | `"pci-dss-v4/1.3.2, soc2/CC6.6"` |
| `netchecks.io/description` | Human-readable description of what this assertion verifies | `"Verify CDE egress is restricted"` |
| `netchecks.io/severity` | Risk severity: `critical`, `high`, `medium`, `low` | `"critical"` |

## Supported Frameworks

| Framework | Control IDs | License |
|---|---|---|
| CIS Kubernetes Benchmark | `cis-k8s/5.3.1`, `cis-k8s/5.3.2` | Free |
| PCI-DSS v4.0 | `pci-dss-v4/1.2.1`, `pci-dss-v4/1.3.2`, `pci-dss-v4/11.3.4`, `pci-dss-v4/11.3.4.1` | Pro |
| SOC 2 Type II | `soc2/CC6.6`, `soc2/CC6.7`, `soc2/CC7.1` | Pro |

## Example

```yaml
apiVersion: netchecks.io/v1
kind: NetworkAssertion
metadata:
  name: cde-isolation-egress
  namespace: payments
  annotations:
    netchecks.io/controls: "pci-dss-v4/1.3.2, pci-dss-v4/11.3.4"
    netchecks.io/description: >
      Verify CDE namespace cannot reach external networks except
      whitelisted payment processor endpoints.
    netchecks.io/severity: critical
spec:
  schedule: "*/30 * * * *"
  rules:
    - name: block-egress-to-internet
      type: http
      url: https://example.com
      expected: fail
      validate:
        message: CDE pods must not reach arbitrary external hosts
    - name: allow-payment-processor
      type: http
      url: https://api.stripe.com/v1/health
      expected: pass
      validate:
        message: CDE pods must be able to reach payment processor
```

## How It Works

1. **Annotate** your `NetworkAssertion` resources with `netchecks.io/controls` to map tests to
   compliance framework controls.
2. The netchecks operator runs the tests as usual, producing `PolicyReport` resources.
3. The **netchecks-compliance** tool reads both the `NetworkAssertion` annotations and `PolicyReport`
   results, then maps them to framework controls.
4. A compliance report is generated in PDF, HTML, or JSON format showing per-control pass/fail
   status backed by active test evidence.

## Control Mapping Logic

- A control is **PASS** if all associated NetworkAssertion test results pass.
- A control is **FAIL** if any associated test result fails.
- A control is **NOT_ASSESSED** if no NetworkAssertions are mapped to it.

Multiple NetworkAssertions can map to the same control — all results are aggregated.

## Generating Reports

Install the [netchecks-compliance](/docs/compliance-reporting) CLI:

```bash
pip install netchecks-compliance
```

Generate a report:

```bash
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
```
