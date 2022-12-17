# Cloud Native Network Assertions

Introduces a `NetworkAssertion` object kind. Providing a cloud native way to dynamically
declare a set of statements about the network (what should work and what shouldn't).

## Purpose

A tool to periodically validate that your cloud networking controls are working. Doesn't make
any assumptions about how your security controls are implemented. Netcheck tests current conditions
by verifying connections that should work do, and verifying that connection that shouldn't work 
don't!

## Example use-cases

### Kubernetes Access

- Verify that a Pod can connect to the K8s API
- Verify that a Pod can connect via HTTP to a service in the same namespace
- Verify that a Pod can connect via HTTP to a service in a different namespace

Verifying that cluster internal restrictions are working. E.g., if `NetworkPolicies` have been configured to block access between namespaces:

- Verify that a Pod cannot connect via HTTP to a service in a different namespace
- Verify that a Pod with the correct labels/annotations/service account can connect via HTTP to a service in a different namespace


### DNS Verification

- Verify that DNS lookups of local cluster services is allowed
- Verify that DNS lookups of external websites is allowed using the default nameserver

### Verifying DNS Restrictions

- Assert that external nameservers are blocked
- Assert that approved hosts are allowed to be queried
- Assert that denied hosts are not allowed to be queried

## Implementation

The netcheck operator watches for `NetworkAssertion` objects, creates CronJobs/Jobs to carry out the tests. CronJobs for 
periodically scheduled tests (the default), and Jobs for one-off assertions.

Ultimately the operator makes the results available as `PolicyReport` instances. 

Each workload carrying out the test Pod would be ["owned"](https://kubernetes.io/docs/concepts/overview/working-with-objects/owners-dependents/) by the
`NetworkAssertion` - so if the NetworkAssertion is deleted the test gets cleaned up by the Kubernetes garbage collector 
thanks to a declared ownership model.



## Design discussions

### Scheduling

Initially Netcheck will create CronJobs in the target namespace. For a cluster with a lot of assertions this could lead
to a lot of CronJobs, Jobs and Pods in production namespaces which might be undesired.

### Fixtures

Not every assertion can be checked from inside one container, for example an assertion checking that
egress UDP packets get blocked will require a listening server on the other side of the network control 
(e.g., outside the firewall). 

Fixtures should be able to call external services, or deploy resources within the cluster. 

Likely out of scope in the first version. Initial proposal is to add a `prestartJob` to the NetworkAssertion.
This Job would have to succeed before the test is run. The Job could run a bash script to trigger or validate
deployments.

A more complicated variation would be for each `NetworkAssertion` to have a list of required `fixtures`, which could 
be deployed independently of each test. Tests would only get run once all fixtures are in a healthy state. 




### Results

How should the result data get from the Job's Pod? Would be ideal to be stateless.

Kyverno manages to stay stateless with something like a `ReportChangeRequest`, which their operator
integrates into the appropriate `PolicyReport` then deletes the change request CRD.

Options:
- Could be a netcheck api/service. So each test pod would be responsible for posting own results (e.g., to `netcheck.kube-system.svc.cluster.local`). Issue is that requires network access between the namespaced pod under test and netcheck - not a good solution for a network security assurance tool.
- By setting a `Job` Finalizer, the operator could monitor progress. Grab the Pod stdout, or attach to the pods and copy result files, then delete the Job. See https://kopf.readthedocs.io/en/stable/daemons/#spawning
- Each test pod could talk to the k8s api e.g. adding annotations, creating or modify CRDs. Doesn't seem like a good idea as the test Pod's will often be running with user provided service accounts which may not have K8s api access.

### Events and metrics

Events are created in the k8s api, and exposed via the operator's `/metrics` endpoint?

## Example manifests

Example `NetworkAssertion` with one rule to check that DNS lookups of `google.com` using cloudflare's DNS server are allowed.

Note the `spec.template` block is fully optional allowing the end user to override the created Job's Pod spec.

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
  template:
    metadata:
      labels:
        optional-label: applied-to-test-pod
    spec:
      serviceAccountName: optional-service-account
  rules:
    - name: cloudflare-dns-lookup
      type: dns
      server: 1.1.1.1
      host: google.com
      expected: pass
      validate:
        message: DNS requests to cloudflare's 1.1.1.1 should succeed.
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
