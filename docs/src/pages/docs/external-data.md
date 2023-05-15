---
title: Injecting External Data
description: Access external data from your Network Assertions
---

Netchecks supports referencing external data from your Network Assertions. This allows you to inject 
secrets and other data into your assertions.


## Example loading data from a ConfigMap

Say you have a `ConfigMap` in the target namespace which contains
an `API_TOKEN` that you want to use in your assertions.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: some-config-map
data:
  API_TOKEN: "some-data-from-a-configmap"
```

Create one or more named contexts in your assertion to load the data from the ConfigMap. The name of the 
context can be anything you like except for `data` and `spec` which are already used by Netchecks.

In this example **somecontext** will load the data from the **some-config-map** ConfigMap:

```yaml
apiVersion: netchecks.io/v1
kind: NetworkAssertion
metadata:
  name: http-with-external-data
  annotations:
    description: Assert probe can access configmap data
spec:
  context:
    - name: somecontext
      configMap:
        name: some-config-map
  rules:
    - name: pie-dev-headers-and-validation
      type: http
      url: https://pie.dev/headers
      headers:
        "X-Netcheck-Header": "{{ somecontext.API_TOKEN }}"
      expected: pass
      validate:
        message: Http request with header to pie.dev service should reply with header value
        pattern: "parse_json(data.body).headers['X-Netcheck-Header'] == somecontext.API_TOKEN"
```

Then reference the data in your custom validation patterns, or anywhere in your assertion rules
using the `{{ }}` template syntax.


{% callout title="Template Evaluation" %}
The `{{ }}` syntax is used to evaluate CEL templates before the assertion is carried out.

The `validate.pattern` is the exception, always evaluated as a CEL expression after the assertion has run.  
{% /callout %}
