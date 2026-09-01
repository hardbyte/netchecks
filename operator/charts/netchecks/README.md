# Netchecks

Proactively verifies whether your security controls are working as intended with a policy as code approach, making no assumptions about how your security controls are implemented. Learn more at [netchecks.io](https://netchecks.io).

Netchecks is written and maintained by Brian Thorne [@hardbyte](https://github.com/hardbyte).


## Documentation

The full documentation can be found at [netchecks.io](https://netchecks.io/) and the [GitHub repository](https://github.com/hardbyte/netchecks/tree/main/operator).

## Prerequisites

* Kubernetes 1.21+


## Installing the Chart

Full installation instructions can be found in the [documentation installation page](https://netchecks.io/docs/installation).

To install the chart

```bash
helm repo add netchecks https://hardbyte.github.io/netchecks
helm upgrade --install netchecks netchecks/netchecks -n netchecks --create-namespace

```

## Custom Resource Definitions

The chart installs two sets of CRDs:

| Values key | API group | Contents |
| --- | --- | --- |
| `crds.groups.netchecks` | `netchecks.io` | `NetworkAssertion` |
| `crds.groups.wgpolicyk8s` | `wgpolicyk8s.io` | `PolicyReport`, `ClusterPolicyReport` |

`wgpolicyk8s.io` is a shared, vendor-neutral API group. Other components install the same
CRDs — Kyverno, the Trivy PolicyReport adapters, Kubescape — so if one of those already
owns them in your cluster, you may want to turn them off here:

```yaml
crds:
  groups:
    wgpolicyk8s: false
```

The operator discovers the PolicyReport API version the cluster serves when it starts
(preferring `v1beta1`, then `v1alpha2`, then `v1alpha1`), so it works with any of the
commonly distributed copies of these CRDs — including Kyverno's, which serves only
`v1alpha2`. If no `wgpolicyk8s.io` API group is served at all, the operator logs a warning at
startup and NetworkAssertions report a `PolicyReportApiUnavailable` status condition until the
CRDs are installed.

To see which versions are served: `kubectl get crd policyreports.wgpolicyk8s.io -o jsonpath='{.spec.versions[*].name}'`.

`crds.install: false` disables all of them, in which case the CRDs must be present before
the operator is installed.

By default the CRDs are annotated with `helm.sh/resource-policy: keep`, so `helm uninstall`
leaves them — and any `NetworkAssertion` and `PolicyReport` resources — in place. Set
`crds.keep: false` to have Helm remove them with the release.

### Upgrading from chart versions before 0.4.0

Earlier versions shipped these CRDs in the chart's `crds/` directory, where Helm installs
them but does not track them as part of the release. They are now regular templates, so
Helm needs to adopt the existing objects once. Without this, `helm upgrade` fails with
`invalid ownership metadata`:

```bash
for crd in networkassertions.netchecks.io policyreports.wgpolicyk8s.io clusterpolicyreports.wgpolicyk8s.io; do
  kubectl label crd "$crd" app.kubernetes.io/managed-by=Helm --overwrite
  kubectl annotate crd "$crd" \
    meta.helm.sh/release-name=<release> \
    meta.helm.sh/release-namespace=<namespace> --overwrite
done
```

Alternatively, set `crds.install: false` to leave the existing CRDs untouched and manage
them outside of the chart.

## Source Code

<https://github.com/hardbyte/netchecks>