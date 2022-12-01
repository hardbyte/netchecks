

## Installation

Warning: Don't actually use this yet!

Install the CRDs and operator with:

```shell
kubectl apply -f manifests/crds
kubectl create namespace netcheck
kubectl apply -f manifests/operator -n netcheck
```

Then apply your `NetworkAssertions` as any other resource.



## Development

### Start a test cluster

```shell
kind create cluster
kubectl config use-context kind-kind
```


### Start the operator

```shell
kopf run main.py --verbose
```
