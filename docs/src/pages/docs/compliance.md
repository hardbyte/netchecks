---
title: Compliance Reporting
description: Automated compliance evidence for regulated Kubernetes environments.
---

Netchecks **Compliance Pro** provides automated compliance reporting for regulated Kubernetes environments. Generate evidence for auditors that your network security controls are continuously tested and working.

---

## Supported Frameworks

### CIS Kubernetes Benchmark

Automatically verify network-related CIS controls:

- Network policy enforcement between namespaces
- API server access restrictions
- DNS policy compliance
- Egress filtering validation

### PCI-DSS v4

Generate evidence for PCI-DSS v4 network segmentation requirements:

- Cardholder data environment isolation testing
- Firewall and network policy validation
- Periodic automated verification of segmentation controls

### SOC 2

Continuous monitoring evidence for SOC 2 Type II:

- Network security monitoring assertions
- Change detection for network policies
- Automated evidence collection for audit periods

---

## How It Works

Compliance Pro builds on the open source Netchecks operator. You define NetworkAssertions that map to compliance controls, and Netchecks continuously runs them on a schedule. Results are stored as PolicyReports and can be exported as compliance evidence.

```yaml
apiVersion: netchecks.io/v1
kind: NetworkAssertion
metadata:
  name: pci-cde-isolation
  namespace: cardholder-data
  labels:
    compliance/framework: pci-dss-v4
    compliance/control: "1.3.1"
  annotations:
    description: Verify CDE namespace cannot reach public internet
spec:
  schedule: "*/15 * * * *"
  rules:
    - name: no-egress-to-internet
      type: http
      url: https://example.com
      expected: fail
      validate:
        message: CDE should not have internet egress
```

---

## Getting Started with Compliance Pro

Compliance Pro includes exportable reports, framework-specific assertion templates, and priority support.

[Get Compliance Pro](https://buy.stripe.com/cN25or9rA8Ur6xa4gi) to start generating automated compliance evidence for your Kubernetes clusters.

For questions, [contact us](https://calendly.com/brian-thorne-netchecks/30min) to discuss your compliance requirements.
