---
title: Custom Validation Rules
description: Writing custom validation rules.
---

Netchecks has built in default validation for each check type. For example, the `dns` check will pass if:
- the DNS response code is `NOERROR`, 
- there is at least one `A` record, and
- the resolver responds in under 10 seconds.

But you may want to instead define your own conditions for success. This is possible by
providing a `validate.pattern` in the rule configuration.

## Common Expression Language (CEL)

The validation pattern is defined using the _Common Expression Language_ (CEL) a simple expression language built on top of protocol buffer types by Google.

In Netchecks, the CEL expression is evaluated with the `data` returned by the check and `spec` objects in scope.

In addition to the [built-in functions](https://github.com/google/cel-spec/blob/master/doc/langdef.md#list-of-standard-definitions) 
(`endsWith`, `contains`, `timestamp` etc), Netchecks also provides the following:

- parse_json
- b64decode
- b64encode


## Examples

### HTTP Status and Body Validation

The following example checks that the GitHub status page returns a 200 or 201 status code and includes
the text "GitHub lives!" in the response body:

```yaml
apiVersion: netchecks.io/v1
kind: NetworkAssertion
metadata:
  name: github-should-live
  annotations:
    description: Check that GitHub reports itself as alive.
spec:
  rules:
    - name: github-status-should-work
      type: http
      url: https://github.com/status
      validate:
        message: Http request to github status API should succeed.
        pattern: "data.body.contains('GitHub lives!') && data['status-code'] in [200, 201]"
```

{% callout title="Identifiers" %}
Keys that are not valid identifiers in CEL (e.g. `status-code`) can be accessed with the `[]` operator.
{% /callout %}

### DNS Validation

DNS checks can also be validated with custom rules. The following example asserts that `A` record 
for `github.com` contains a particular IP address:

```yaml
apiVersion: netchecks.io/v1
kind: NetworkAssertion
metadata:
  name: dns-returns-specific-ip
spec:
    - name: github-expected-ip
      type: dns
      server: 1.1.1.1
      host: github.com
      expected: pass
      validate:
        message: DNS requests to cloudflare's 1.1.1.1 should contain a specific IP address for github.com
        pattern: "data['A'].contains('20.248.137.48')"
```

## Writing Custom Rules

The easiest way to see the `data` and `spec` that can be used in a custom validation rule is by looking
at the `properties` of a PolicyReport's `results`:

```yaml
results:
  - category: http
    message: Rule from kubernetes-version
    policy: kubernetes-version
    properties:
      data: >-
        {"startTimestamp": "2023-01-08T04:20:52.433681", "status-code": 200,
        "endTimestamp": "2023-01-08T04:20:52.441192"}
      spec: >-
        {"type": "http", "shouldFail": false, "timeout": null,
        "verify-tls-cert": false, "method": "get", "url":
        "https://kubernetes/version"} 
```

Note you can also get these with kubectl:

```shell
kubectl get policyreport/<network-assertion> -o jsonpath='{.results}'
```

## Data Available for Validation

### HTTP

The following keys are available in the `data` object for HTTP checks:
- `status-code` - the HTTP status code
- `body` - the HTTP response body
- `headers` - the HTTP response headers

### DNS 

- `response` - the raw DNS response
- `response-code` - the DNS response code e.g. `NOERROR`, `TIMEOUT`, `NXDOMAIN`, `DNSERROR`
- `A` - the `A` records returned by the DNS query
- `canonical_name` - the canonical name returned by the DNS query
- `expiration` - the expiration time of the DNS record


### Common

- `startTimestamp`
- `endTimestamp` 


{% callout title="Exceptions" type="warning" %}
If an exception occurs during the check, the `exception` and `exception-type` keys get set in the
data. 
{% /callout %}


## Links

- [Introduction to CEL](https://github.com/google/cel-spec/blob/master/doc/intro.md)
- [CEL Specification](https://github.com/google/cel-spec/blob/master/doc/langdef.md)