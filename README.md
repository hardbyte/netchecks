

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
