

## Development

### Start a test cluster

```shell
kind create cluster
kubectl config use-context kind-kind
```


### Start the operator

```shell
kind run main.py --verbose
```
