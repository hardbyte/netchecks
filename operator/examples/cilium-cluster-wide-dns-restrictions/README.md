
This example deploys a cilium network policy that intercepts and filters all DNS queries in the default namespace.
Any DNS queries are allowed to be made via `kube-dns` in the `kube-system` namespace.

A further `CiliumNetworkPolicy` applied to the `kube-system` namespace restricts the external lookups that `kube-dns`
can carry out.


Apply the network policies:
```
kubectl apply -n default -f examples/cilium-cluster-wide-dns-restrictions/default-dns-netpol.yaml
kubectl apply -n kube-system -f examples/cilium-cluster-wide-dns-restrictions/kube-dns-netpol.yaml
```

Apply the network assertions:

```
kubectl apply -n default -f examples/cilium-cluster-wide-dns-restrictions/cluster-dns-should-work.yaml
kubectl apply -n default -f examples/cilium-cluster-wide-dns-restrictions/dns-res-restrictions-assertion.yaml
```