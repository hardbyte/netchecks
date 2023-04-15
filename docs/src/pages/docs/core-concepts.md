---
title: Core Concepts
description: Core concepts for Netchecks
---

## Continuous Assurance

Continuous Assurance is a proactive approach to ensure network policies, connectivity, and security within a Kubernetes cluster are continuously monitored and verified. By leveraging the Netchecks operator and its NetworkAssertions, users can schedule automated network tests at regular intervals. This ongoing validation process helps maintain a high level of network reliability, security, and compliance, providing peace of mind and reducing the risk of unexpected network issues.

## Alerting

Alerting is a crucial aspect of maintaining a reliable and secure Kubernetes environment. With Netchecks and the Kyverno Policy Reporter, you can set up alerting based on the results of your NetworkAssertions and the generated PolicyReports. This enables you to get notified about potential network issues, policy violations, or other anomalies, ensuring timely response and remediation.


## Network Assertions 


Network Assertions are the core building blocks for defining and managing network tests within the Netchecks framework. 

They allow users to create custom rules that specify the expected behavior of various network-related components, such as DNS resolution or HTTP requests. 

Network Assertions are written in YAML format and can be applied like any other Kubernetes resource.

They support various check types and can include custom validation rules using the CEL (Common Expression Language) to tailor the assertion criteria to specific use cases.

### Custom Validation

Netchecks provides built-in default validation for each check type, such as ensuring a DNS response code is NOERROR and contains at least one A record. However, users may need to implement custom validation rules for more specific requirements. Netchecks allows users to write custom validation rules using the CEL (Common Expression Language), offering a flexible and powerful way to extend the default validation logic. Custom validation rules can be added to Network Assertions or used in command-line checks to ensure the network behaves as expected under various conditions.


