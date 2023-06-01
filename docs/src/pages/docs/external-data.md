---
title: Injecting External Data
description: Access external data from your Network Assertions
---

Use data from ConfigMaps and Secrets in your Network Assertions. 

When an assertion referencing a ConfigMap or Secret is evaluated, the data is mounted into the
Pod carrying out the assertion at the time the test runs. Should the Secret or ConfigMap be
updated, subsequent probes will pick up the latest data at that point.

This data is made available to the probe in the form of a context.

In order to reference external data in NetworkAssertion rules, a context is required. The context 
data can then be referenced within a CEL template.

```
{{ <context-name>.<key-name> }}
```


## Contexts from ConfigMaps

A [ConfigMap](https://kubernetes.io/docs/concepts/configuration/configmap/) in Kubernetes is commonly used
to store configuration data for applications. Each ConfigMap is namespaced and stores key-value pairs.

Say you have a `ConfigMap` in the target namespace which contains an `API_TOKEN` that you want to use in 
your assertions.

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

Then reference the data in your custom validation patterns, or anywhere in your assertion rules
using the `{{ }}` template syntax.

In this example **somecontext** will load the data from the **some-config-map** ConfigMap and inject
it into a header in the HTTP request:

```yaml
apiVersion: netchecks.io/v1
kind: NetworkAssertion
metadata:
  name: http-with-external-data
  annotations:
    description: Assert probe can access configmap data
spec:
  # Include the full context and headers in the PolicyReport for easier debugging
  disableRedaction: true
  # All rules in the NetworkAssertion share the same context
  context:
    # A unique name for each context object
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

The templated variable `{{ somecontext.API_TOKEN }}` will be substituted with the value 
`some-data-from-a-configmap` before the test is executed.

## Contexts from Secrets

A [Secret](https://kubernetes.io/docs/concepts/configuration/secret/) in Kubernetes is an object 
that contains sensitive data such as passwords, tokens, or other potentially sensitive 
configuration data.

Let's repeat the same example with an `API_TOKEN` this time stored - more appropriately - as a 
secret:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: some-secret
data:
  API_TOKEN: a3E0Z2lodnN6emduMXAwcg==
```

The NetworkAssertion doesn't change much, note the context now refers to a `secret`:

```yaml
apiVersion: netchecks.io/v1
kind: NetworkAssertion
metadata:
  name: http-with-external-secret-data
  annotations:
    description: Assert probe can access secret data
spec:
  context:
    - name: somecontext
      secret:
        name: some-secret
        # [Optionally] Limit which keys from the Secret (or ConfigMap) 
        # get created as files.
        # items:
        #   - key: API_TOKEN
        #     path: API_TOKEN
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


{% callout title="Template Evaluation" %}
The `{{ }}` syntax is used to evaluate CEL templates before the assertion is carried out.

The `validate.pattern` is the exception, always evaluated as a CEL expression after the assertion has run.  
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
    array:
      - "value"
      - "value2"
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
      type: http
      url: https://pie.dev/headers
      headers:
        "X-Netcheck-Header": "{{ parse_yaml(somecontext.yaml_data).toplevel.nestedkey }}"
      expected: pass
      validate:
        message: Http request with header to pie.dev service should reply with header value
        pattern: parse_json(data.body).headers['X-Netcheck-Header'] == "yaml-data"
    - name: yaml-array-parsing-test
      type: http
      url: https://pie.dev/headers
      headers:
        "X-Netcheck-Header": "{{ parse_yaml(somecontext.yaml_data).array[0] }}"
      expected: pass
      validate:
        message: Http request with header to pie.dev service should reply with header value
        pattern: parse_json(data.body).headers['X-Netcheck-Header'] == "value"
```

## Reusable Variables

Data to be used in multiple rules can be declared as an **inline context**, and 
can reference already defined contexts using the `{{ }}` template syntax. 

For example:

```yaml
apiVersion: netchecks.io/v1
kind: NetworkAssertion
metadata:
  name: http-with-inline-data
  annotations:
    description: Assert probe can access configmap data
spec:
  context:
    - name: originalcontext
      inline:
        key: "inline-value"
    - name: derivedcontext
      inline:
        key: "{{ originalcontext.key }}"
  rules:
    - name: pie-dev-headers-and-validation
      type: http
      url: https://pie.dev/headers
      headers:
        "X-Netcheck-Header": "{{ derivedcontext.key }}"
      expected: pass
      validate:
        message: Http request with header to pie.dev service should reply with header value
        pattern: "parse_json(data.body).headers['X-Netcheck-Header'] == derivedcontext.key"
```

## Redaction

By default, contexts are not included in the PolicyReport. This is to because they often include
sensitive information such as passwords or tokens. You can disable this
redaction for debugging purposes by setting `disableRedaction: true` in the `spec` section of the NetworkAssertion.


Note that limiting which keys are projected from the Secret or ConfigMap is also a good way to
limit the amount of sensitive data that is exposed to the Pod carrying out the test.


```yaml
apiVersion: netchecks.io/v1
kind: NetworkAssertion
metadata:
  name: redaction-disabled
spec:
  disableRedaction: true
  context:
    - name: somecontext
      secret:
        name: some-secret
        # [Optionally] Limit which keys from the Secret or ConfigMap 
        # get created as files
        items:
          - key: API_TOKEN
            path: API_TOKEN
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
