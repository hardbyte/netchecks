---
title: Architecture guide
description: Quidem magni aut exercitationem maxime rerum eos.
---

Netchecks runs in Kubernetes as an [operator](https://kubernetes.io/docs/concepts/extend-kubernetes/operator/). The 
operator is implemented in Python using the [kopf](https://kopf.readthedocs.io/en/stable) framework.

The netchecks operator:
- listens for `NetworkAssertion` resources across the kubernetes cluster and creates `CronJobs` for each of them.
- listens for _probe_ Pods created by the NetworkAssertion's CronJob and parses assertion results from the Pod logs. 
- creates and updates PolicyReport resources for each NetworkAssertion in response to the assertion results.

Each probe pod uses the `netcheck` docker image to run the tests that make up a particular network assertion.
The `netcheck` image is based on the [python:3.11](https://hub.docker.com/_/python) image.

[Kyverno's PolicyReporter](https://kyverno.github.io/policy-reporter/) is optionally installed alongside Netchecks to
provide a convenient way to expose metrics, view the results, and generate notifications.

![](/images/architecture/Netcheck-High-Level-Lifecycle.png)

---
