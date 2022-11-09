# Cloud Native Network Assertions

## 

kopf

## CRD design

Introduces a `NetworkAssertion` object kind. Providing a cloud native way to dynamically
declare a set of statements about the network (what should work and what shouldn't).

Our custom operator takes these `NetworkAssertion` objects, creates Jobs/Pods to test them and tracks the results. 
Events are created in the k8s api, and exposed via the operator's `/metrics` endpoint?

Example `NetworkAssertion`:

```yaml
apiVersion: kopf.dev/v1
kind: NetworkAssertion
metadata:
  name: deny-cloudflare-dns
  namespace: network-policies
  annotations:
    description: Cluster shouldn't be able to lookup dns on cloudflare.
spec:
  schedule: "@hourly"
  failureActions:
    - slackNotificationConfig
    - SNS topic (TODO)
  rules:
    - name: cloudflare-dns-lookup-must-fail
      type: dns
      server: 1.1.1.1
      host: hardbyte.nz
      validate:
        exitCode: 1
        message: DNS requests to cloudflare's 1.1.1.1 shouldn't succeed.
```

```yaml
apiVersion: hardbyte.nz/v1
kind: NetworkAssertion
metadata:
  name: allow-https-s3-api
spec:
  schedule: "@hourly"
  failureActions:
    - slackNotificationConfig
  rules:
    - name: s3-access-allowed
      type: request
      url: https://s3.ap-southeast-2.amazonaws.com
      method: GET
      validate:
        statusCode: 200
        message: TLS connection to regional S3 should be allowed.
```
