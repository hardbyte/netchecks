# Cloud Native Network Assertions

## 

kopf could be used.
https://kopf.readthedocs.io/en/stable/

## CRD design

Introduces a `NetworkAssertion` object kind. Providing a cloud native way to dynamically
declare a set of statements about the network (what should work and what shouldn't).

The netcheck operator watches for `NetworkAssertion` objects, creates CronJobs/Jobs to carry out the tests. CronJobs for 
periodically scheduled tests (the default), and Jobs for one off assertions.

Ultimately the operator makes the results available as `PolicyReport` instances. Each Pod would be ["owned"](https://kubernetes.io/docs/concepts/overview/working-with-objects/owners-dependents/) by the
`NetworkAssertion` - so if the NetworkAssertion is deleted the test gets cleaned up by the Kubernetes garbage collector 
thanks to a declared ownership model.

Design decision - how should the result data get from the Job's Pod? Would be ideal to be stateless.
Kyverno manages to stay stateless with something like a `ReportChangeRequest`, which their operator
integrates into the appropriate `PolicyReport` then deletes the change request CRD.

Options:
- Could be a netcheck api/service. So each test pod would be responsible for posting own results (e.g., to `netcheck.kube-system.svc.cluster.local`)
- By setting a long `Job` TTL (or using a Finalizer), the operator could monitor progress. grab the Pod stdout, or attach to the pods and copy result files, then delete the Job. See https://kopf.readthedocs.io/en/stable/daemons/#spawning
- I don't think having each test pod talk to the k8s api e.g. adding annotations, creating or modify CRDs is a good idea? Is it?


Events are created in the k8s api, and exposed via the operator's `/metrics` endpoint?

Example `NetworkAssertion`:

```yaml
apiVersion: kopf.dev/v1
kind: NetworkAssertion
metadata:
  name: deny-cloudflare-dns
  namespace: default
  annotations:
    description: Cluster shouldn't be able to lookup dns on cloudflare in default namespace.
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

A corresponding `PolicyReport` might look like:


```yaml
apiVersion: policy.kubernetes.io/v1alpha1
kind: PolicyReport
metadata:
  name: policyreport-cloudflare-default
  namespace: default
  ownerReferences:
  - apiVersion: v1
    blockOwnerDeletion: true
    controller: true
    kind: Namespace
    name: default
    uid: 76d4081d-c86f-4e8f-a5ec-d9b1516bff06
results:
- message: Validation rule 'cloudflare-dns-lookup-must-fail' succeeded.
  policy: cloudflare-dns-lookup
  resources:
  - apiVersion: v1
    kind: Pod
    name: netcheck-cloudflare
    namespace: default
    uid: b0a4e899-6b12-4c47-8343-422f6aad4f56
  rule: cloudflare-dns-lookup-must-fail
  scored: true
  status: Pass
  data:
    {
      "type": "dns",
      "nameserver": "1.1.1.1",
      "host": "hardbyte.nz",
      "timeout": 10,
      "result": {
        "A": [
          "209.58.165.79"
        ]
      }
    }


```

### Another example

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
