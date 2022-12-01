
This example deploys a cilium network policy that intercepts and filters all DNS queries.

Only cluster queries, and github.com subdomains should be allowed.

The NetworkAssertion checks that is the case.


Running the full example locally is something along these lines:

```shell

kind create cluster
kubectl config use-context kind-kind

cilium install --helm-set cni.chainingMode=portmap
cilium hubble enable --ui

# Install the cilium network policy
kubectl apply -f ./dns-netpol.yaml

# Install the network assertion
kubectl apply -f ./dns-assertion.yaml

# Can see what gets blocked using hubble
cilium hubble port-forward&
```


