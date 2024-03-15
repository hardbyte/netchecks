---
title: Validating K8s Data
description: Validate external data from your Network Assertions
---

Netchecks can validate data stored in a ConfigMaps or Secret using the check type `internal`.
If you have some other service storing results in a ConfigMap, you can use Netchecks to validate that 
the data is as expected using [custom validation rules](custom-validation-rules).

This may be useful for checking that a particular key exists in a ConfigMap or Secret, or that the data
is valid JSON, Base64 encoded, truthy etc. 

## Example ConfigMaps Validation


Say you have a `ConfigMap` in the target namespace which contains a `foo` key that you want to assert
has the value `bar`.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: some-config-map
data:
  foo: "bar"
```

Create a Network Assertion with a `context` to load the data from the ConfigMap and validate it.

```yaml
apiVersion: netchecks.io/v1
kind: NetworkAssertion
metadata:
  name: validate-some-configmap
  annotations:
    description: Assert that some configmap contains expected data
spec:
  schedule: "*/15 * * * *"  
  context:
    - name: somecontext
      configMap:
        name: some-config-map
  rules:
    - name: validate-bar
      type: internal
      expected: pass
      validate:
        message: Expected foo to be bar
        pattern: "somecontext.foo == 'bar'"
```

{% callout title="Not familiar with ConfigMaps?" type="beginner" %}
A [ConfigMap](https://kubernetes.io/docs/concepts/configuration/configmap/) in Kubernetes is commonly used
to store configuration data for applications. Each ConfigMap is namespaced and stores key-value pairs.
{% /callout %}


## Handling JSON and YAML data

Often a config map contains JSON or YAML data. The `parse_json` and `parse_yaml` functions 
can be used to extract data from these formats.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: a-config-map
data:
  yaml_data: |
    toplevel:
      nestedkey: "yaml-data"
```

```yaml
apiVersion: netchecks.io/v1
kind: NetworkAssertion
metadata:
  name: example-with-yaml-format
spec:
  context:
    - name: somecontext
      configMap:
        name: a-config-map
  rules:
    - name: yaml-parsing-test
      type: internal
      validate:
        message: Inner yaml value
        pattern: parse_yaml(somecontext.yaml_data).toplevel.nestedkey == "yaml-data"
```

## See also

- [Custom Validation Rules](custom-validation-rules)
- [External Data](external-data)
