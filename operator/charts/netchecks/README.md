# Netchecks

Proactively verifies whether your security controls are working as intended with a policy as code approach, making no assumptions about how your security controls are implemented. Learn more at [netchecks.io](https://netchecks.io).

Netchecks is written and maintained by Brian Thorne [@hardbyte](https://github.com/hardbyte).


## Documentation

The full documentation can be found at [docs.netchecks.io](https://docs.netchecks.io/) and the [GitHub repository](https://github.com/hardbyte/netchecks/tree/main/operator).

## Prerequisites

* Kubernetes 1.21+


## Installing the Chart

Full installation instructions can be found in the [documentation installation page](https://docs.netchecks.io/docs/installation).
G
To install the chart

```bash
helm repo add netchecks https://hardbyte.github.io/netchecks
helm upgrade --install netchecks netchecks/netchecks -n netchecks --create-namespace

```

## Source Code

<https://github.com/hardbyte/netchecks>